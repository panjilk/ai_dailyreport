"""Bounded RSS collection and deterministic, source-only Chinese extraction."""

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import math
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

from .recency import RECENCY_DAYS, window_start, article_event_evidence, news_date
from .international import (english_blog_candidate, english_summary, english_topic,
                            paper_details, source_rows, translate_to_chinese)
from .models import MODEL_NAMES, model_labels
from .topics import ai_related, editorial_candidate, playback_priority, concrete_news
from .broadcast_log import recent_entries, url_fingerprint
from .source_health import load_health, record_result, save_health

from bs4 import BeautifulSoup
import feedparser
import requests


SHANGHAI = timezone(timedelta(hours=8), 'Asia/Shanghai')
AI_TERMS = re.compile(r'人工智能|大模型|语言模型|生成式|机器学习|深度学习|神经网络|智能体|具身智能|扩散模型|ChatGPT|OpenAI|DeepSeek|Claude|Gemini|通义千问|(?<![a-z0-9_])(?:AI|LLM|GPT(?:-\d+)?)(?![a-z0-9_])', re.I)
CORE_AI_TERMS = re.compile(r'人工智能|大模型|语言模型|生成式|机器学习|深度学习|神经网络|智能体|具身智能|扩散模型|ChatGPT|OpenAI|DeepSeek|Claude|Gemini|通义千问|(?<![a-z0-9_])(?:LLM|GPT(?:-\d+)?)(?![a-z0-9_])', re.I)
FILLER = re.compile(r'[？?]|年度旗舰答卷|交出.{0,8}答卷|表现.{0,8}干脆|自有锋芒|Slogan|让我们|拭目以待|不容错过', re.I)
DEBUNK = re.compile(r'辟谣|不实|虚假(?:消息|信息|报道)|网传(?:消息|信息)|谣言|澄清|更正|纠正|并非事实|与事实不符')


def _reject_debunk(text):
    if DEBUNK.search(text):
        raise ValueError('包含辟谣或纠正语境，抽取模式保守跳过，避免遗漏否定上下文')
NOISE = re.compile(r'advert|advertisement|navigation|related|recommend|share|comment|footer|copyright|toolbar|(^|[-_ ])ads?($|[-_ ])', re.I)
TRACKING = {'spm', 'from', 'ref', 'referrer', 'fbclid', 'gclid', 'msclkid', 'source', 'mc_cid', 'mc_eid'}


MODEL_CHANGE = re.compile(
    r'发布|推出|迭代|更新|升级|开源|上线|上新|开放|新版本|新模型|能力|评测|测评|基准|测试|'
    r'推理|数学|编程|代码生成|多模态|上下文|幻觉|准确率|语音|识别|理解|成绩|得分|超越|超过|提升')
OFF_TOPIC = re.compile(
    r'融资|收购|投资|营收|财报|估值|上市|裁员|任命|离职|薪酬|人事|贫富|'
    r'手机|手表|芯片|显卡|服务器|数据中心|存储|数据库|Habitat|Sites|建站|'
    r'订阅|套餐|涨价|降价|收费|限额|额度|优惠|浏览器|插件|办公|接入|集成', re.I)
MODEL_EFFECT = re.compile(r'模型.{0,12}(?:能力|评测|基准|推理|幻觉|准确率)|'
                          r'数学|编程能力|代码生成|多模态理解|上下文|幻觉|准确率|基准|评测|测评')


def _model_topic(title):
    """Judge the headline's subject, never a brand mentioned deep in the body."""
    # A clear model-release main clause keeps its topic when a later clause
    # mentions integration. Integration/product headlines themselves stay out.
    main_clause = re.split(r'[，,；;：:]', title, maxsplit=1)[0]
    if (MODEL_NAMES.match(main_clause) and
            re.search(r'发布|开源|推出|上线|上新|迭代|更新|升级', main_clause) and
            not OFF_TOPIC.search(main_clause)):
        title = main_clause
    named = MODEL_NAMES.search(title)
    generic = re.search(r'大模型|大语言模型|语言模型|多模态(?:基础)?模型|基础模型', title)
    if not (named or generic) or not MODEL_CHANGE.search(title):
        return False
    # A model-effect comparison can involve hardware or pricing; a product
    # announcement merely using a model remains outside the default edition.
    if re.search(r'融资|收购|投资|营收|财报|估值|上市|裁员|任命|离职|薪酬|人事|贫富|手机|手表|芯片|显卡|服务器|数据中心|存储|数据库|Habitat|Sites|建站|浏览器|插件|办公|接入|集成', title, re.I):
        return False
    if OFF_TOPIC.search(title) and not MODEL_EFFECT.search(title):
        return False
    return True


SOURCE_NAV_LABELS = {
    'OpenAI News': 'OpenAI', 'Google DeepMind': 'Gemini',
    'Hugging Face Blog': 'Hugging Face', 'NVIDIA Blog': 'NVIDIA',
    'TechCrunch AI': 'AI行业', 'Simon Willison': 'LLM工具',
    'Gary Marcus': 'Gary Marcus', 'Dwarkesh Patel': 'Dwarkesh Patel',
    'Gwern': 'Gwern AI', 'Max Woolf': 'Max Woolf', 'Giles Thomas': 'Giles Thomas',
    'Sean Goedecke': 'Sean Goedecke', 'Martin Alderson': 'Martin Alderson',
    "Where's Your Ed At": 'AI产业', 'LCamtuf': 'AI安全',
    'IT之家': 'IT之家AI', '量子位': '量子位大模型', '雷峰网': '雷峰网AI',
    '极客公园': '极客公园AI', 'Hugging Face Papers': 'Hugging Face',
    'arXiv cs.CL': 'LLM论文', 'Transformers Releases': 'Transformers',
}


def _nav_label(title, source_name=''):
    names = model_labels(title)
    # Prefer the concrete model family when a company and its model appear
    # together, while keeping a company label for OpenAI-only announcements.
    if 'OpenAI' in names and ('GPT' in names or 'ChatGPT' in names):
        names.remove('OpenAI')
    if len(names) >= 3:
        return '多模型对比'
    label = ' / '.join(names)
    if len(names) == 2 and sum(2 if '\u4e00' <= c <= '\u9fff' else 1 for c in label) > 12:
        return '模型对比'
    return label if names else SOURCE_NAV_LABELS.get(source_name, '大模型')


def classify(title: str, narration: str) -> str:
    """Title first, then narration; ordered rules resolve overlapping topics."""
    rules = (
        ('行业动态', r'政治|选举|监管|政策|法规|法案|禁令|诉讼|法院|立法'),
        ('产品应用', r'用量|额度|限额|重置|订阅|套餐|定价|降价|涨价'),
        ('模型发布', r'(?:发布|推出|上线|开源).{0,24}(?:模型|GPT|Claude|Gemini|DeepSeek)|(?:模型|GPT|Claude|Gemini|DeepSeek).{0,24}(?:发布|推出|上线|开源)'),
        ('开发生态', r'开发者|开发工具|开源|代码仓库|开发框架|插件|(?<![a-z0-9_])(?:SDK|API|GitHub|MCP)(?![a-z0-9_])'),
        ('产品应用', r'应用|助手|手机|浏览器|办公|客户端|机器人|智能终端|产品|上线|接入'),
        ('技术洞察', r'论文|研究|架构|算法|基准|评测|测试结果|训练方法|推理|技术分析'),
        ('行业动态', r'融资|收购|投资|营收|收入|财报|上市|监管|政策|法规|合作|裁员|任命|大会'),
    )
    for text in (title, narration):
        for category, pattern in rules:
            if re.search(pattern, text, re.I):
                return category
    return '要闻'


def _boundaries(text, punctuation):
    """Yield punctuation outside quotes/brackets, including closing quotes."""
    pairs = {'“': '”', '‘': '’', '「': '」', '『': '』', '（': '）', '(': ')', '《': '》'}
    stack = []
    for i, char in enumerate(text):
        if char == '"':
            if stack and stack[-1] == char:
                stack.pop()
            else:
                stack.append(char)
        elif char in pairs:
            stack.append(pairs[char])
        elif stack and char == stack[-1]:
            stack.pop()
        if not stack:
            j = i
            while j >= 0 and text[j] in '”’」』）)》"':
                j -= 1
            if j >= 0 and text[j] in punctuation:
                yield i + 1


def _sentences(text):
    # Keep reported speech and its qualification together instead of starting
    # a new extract inside a quotation or leaving a dangling closing quote.
    result, start = [], 0
    for end in _boundaries(text, '。！？!?'):
        sentence = text[start:end].strip()
        if sentence:
            result.append(sentence)
        start = end
    if text[start:].strip():
        result.append(text[start:].strip())
    return result


def _bullet(sentence):
    """Return the entire source statement, never an abbreviated prefix."""
    return sentence.strip()



def _validate(now, hours, limit):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('now must be a timezone-aware datetime')
    if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in (hours, limit)):
        raise ValueError('hours and limit must be positive integers')


def _date(value):
    try:
        if isinstance(value, datetime):
            result = value
        elif isinstance(value, str):
            try:
                result = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
            except ValueError:
                result = parsedate_to_datetime(value)
        else:
            return None
        return result if result.tzinfo is not None and result.utcoffset() is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def _canonical(url, keep_fragment=False):
    try:
        parts = urlsplit(url.strip())
        if parts.scheme.lower() not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            return None
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if not k.lower().startswith('utm_') and k.lower() not in TRACKING]
        fragment = parts.fragment if keep_fragment and re.fullmatch(r'[A-Za-z0-9_-]+', parts.fragment) else ''
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or '/',
                           urlencode(sorted(query)), fragment))
    except (AttributeError, ValueError):
        return None


def select_recent(items: list[dict], now: datetime, hours: int, limit: int, stats=None) -> list[dict]:
    """Newest first; inclusive lower boundary; never infer missing timezones."""
    _validate(now, hours, limit)
    cutoff = max(now - timedelta(hours=hours), window_start(now))
    stats = stats if stats is not None else {}
    for key in ('invalid_metadata', 'outside_window', 'duplicates'):
        stats.setdefault(key, 0)
    eligible = []
    for row in items:
        published = _date(row.get('published'))
        url = _canonical(row.get('source_url', row.get('url', row.get('link', ''))),
                         keep_fragment=row.get('content_kind') == 'official_model_release')
        title = re.sub(r'\s+', ' ', str(row.get('title') or '')).strip()
        if published is None or not url or not title:
            stats['invalid_metadata'] += 1
        elif not cutoff <= published <= now:
            stats['outside_window'] += 1
        else:
            eligible.append((published, dict(row, title=title, source_url=url, published=published.isoformat())))
    eligible.sort(key=lambda pair: pair[0], reverse=True)
    result, urls, titles = [], set(), set()
    for _, row in eligible:
        key = re.sub(r'[\W_]+', '', row['title']).casefold()
        if row['source_url'] in urls or key in titles:
            stats['duplicates'] += 1
            continue
        urls.add(row['source_url'])
        titles.add(key)
        result.append(row)
        if len(result) == limit:
            break
    return result


def _fetch(url):
    # Limit each response and avoid streaming an unbounded page into memory.
    with requests.get(url, timeout=15, stream=True, headers={'User-Agent': 'AI-DailyReport/1.0 (RSS reader)'}) as response:
        response.raise_for_status()
        chunks, size = [], 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > 3_000_000:
                raise ValueError('response exceeds 3 MB')
            chunks.append(chunk)
        return b''.join(chunks)


def extract_paragraphs(html) -> list[str]:
    """Use article containers only: no fallback to the entire site body."""
    soup = BeautifulSoup(html, 'html.parser')
    for node in list(soup.select('script,style,nav,header,footer,aside,form,iframe')):
        node.decompose()
    for node in list(soup.find_all(True)):
        if node.attrs is not None and NOISE.search(' '.join([node.get('id', ''), *node.get('class', [])])):
            node.decompose()
    root = None
    for selector in ('#paragraph', '[itemprop="articleBody"]', '.article-content', '.article_content', '#article-content', 'article', '.article', 'main'):
        root = soup.select_one(selector)
        if root is not None:
            break
    if root is None:
        return []
    # Check the whole article container before length limits or paragraph
    # filtering: the denial can be a very short line at the end of the page.
    _reject_debunk(root.get_text(' ', strip=True))
    result = []
    for node in root.find_all('p'):
        # A related headline is not evidence about the current article. Keep
        # ordinary prose containing an inline citation, including its wording.
        outside_links = ''.join(str(part) for part in node.find_all(string=True)
                                if part.find_parent('a') is None)
        if node.find('a') and not re.sub(r'[\s《》〈〉「」“”\[\]（）():：、，。·-]', '', outside_links):
            continue
        text = re.sub(r'\s+', ' ', node.get_text(' ', strip=True)).strip()
        if len(re.findall(r'[\u4e00-\u9fff]', text)) < 4:
            continue
        if re.search(r'广告声明|相关阅读|扫码|微信公众号|责任编辑|投诉水文|优惠券|返利|点击下载|下载客户端', text):
            continue
        if text not in result:
            result.append(text)
    return result


def _spoken_title(title):
    return re.sub(r'[。！？!?.…；;：:，,\s]+$', '', title.strip()) + '。'


# Reporting phrases deliberately exclude a bare 据 (which also occurs in 数据).
REPORTING = re.compile(
    r'(?<!数)据(?:介绍|报道|悉|称|了解)|(?<!数)据[^。！？，,]{1,32}(?:透露|报道|表示|称|介绍)|'
    r'IT之家[^。]{0,20}消息|表示|指出|认为|声称|透露|谈到|(?:官方|报告|研究|测试)数据显示|'
    r'[A-Za-z\u4e00-\u9fff]+\s*称')
LIMITATION = re.compile(
    r'尚未|尚无|未经|未能|不支持|不提供|不允许|不能|不适用|无法|'
    r'仅(?:限|在|适用|支持|供)|只(?:能|限|支持)|局限|仍需|仍面临|'
    r'但|然而|不过|受限|限制(?:为|在|于)|存在.{0,12}风险')
DEPENDENT = re.compile(r'^(?:但|然而|不过|因此|所以|这些|上述|这一|这项|该结果|其|他|她|“|「|『|")')
HISTORICAL = re.compile(r'最初|此前|过去|曾经|当时|旧版|背景|历史|早期|在20[0-2][0-5]年')


def _summary(paragraphs, title):
    """Extract up to three complete points for a single-page model briefing.

    Reporting and caveats are dependencies, not reasons to read the entire
    article. Target 150–220 Chinese characters including the spoken title.
    Short stories may have only one or two points. Overlong essential context
    fails explicitly instead of being abbreviated or split into huge bullets.
    """
    text = ''.join(paragraphs)
    _reject_debunk(title + '\n' + text)
    sentences = _sentences(text)
    spoken_title = _spoken_title(title)

    def complete(sentence):
        return bool(re.search(r'[。！？!?][”’」』）)》"]*$', sentence)) and not re.search(r'…|\.{3}', sentence)

    usable = {i for i, sentence in enumerate(sentences)
              if complete(sentence) and len(sentence) >= 8
              and (not FILLER.search(sentence) or REPORTING.search(sentence))
              and not re.fullmatch(r'《.*》[。]?', sentence)}
    starts = [i for i in sorted(usable)
              if not DEPENDENT.search(sentences[i]) and not FILLER.search(sentences[i])]
    if not usable or not starts:
        raise ValueError('正文不足以生成保留归属语境的完整要点摘要')
    start = starts[0]
    # An incomplete caveat must not silently disappear from the source.
    if any(LIMITATION.search(s) and not complete(s) for s in sentences):
        raise ValueError('无法安全保留不完整原文的限定语境')
    terms = set(re.findall(r'(?=([\u4e00-\u9fff]{2}))', title))
    terms.update(t.casefold() for t in re.findall(r'[A-Za-z][A-Za-z0-9-]+', title))
    overlap = [sum(t in s.casefold() for t in terms) for s in sentences]
    reports = [i for i, s in enumerate(sentences) if REPORTING.search(s)]
    facets = (
        re.compile(r'发布|推出|上线|开源|重写|迁移'),
        re.compile(r'支持|可以|能够|提供|功能|域名|进行分析|发出提醒|custom.?domain', re.I),
        re.compile(r'提升|提高|降低|效率|延迟|性能|每秒|每周|测试结果|[0-9]+%'),
        re.compile(r'价格|定价|美元|费用|免费|付费|套餐|开放|接口|部署|下载'),
        LIMITATION,
        re.compile(r'计划|预计|未来几|后续将'),
    )
    features = [{n for n, pattern in enumerate(facets) if pattern.search(s)} for s in sentences]

    def related(i, j):
        # Ignore generic prose when connecting a caveat to a remote claim.
        tokens = set(re.findall(r'[a-z][a-z0-9-]+|[\u4e00-\u9fff]{2}', sentences[i].casefold()))
        tokens -= {'数据', '团队', '模型', '用户', '介绍', '文章', '相关', '其中', '这些', '上述'}
        return any(t in sentences[j].casefold() for t in tokens)

    # The initial reporting sentence is shared context even when it scores
    # below a later feature. Subsequent reports are attached only as needed.
    initial_report = next((i for i in reports if i >= start and
                           i <= start + 2), None)
    mandatory = {start}
    if initial_report is not None:
        mandatory.add(initial_report)

    def dependencies(indices):
        result = set(indices)
        pending = list(indices)
        while pending:
            i = pending.pop()
            needed = set()
            if DEPENDENT.search(sentences[i]):
                if i == 0:
                    raise ValueError('无法安全确定引语或限定语的归属')
                antecedent = i - 1
                if LIMITATION.search(sentences[i]):
                    while antecedent > start and HISTORICAL.search(sentences[antecedent]):
                        antecedent -= 1
                needed.add(antecedent)
            # Local attribution can govern several intervening factual claims.
            previous = next((j for j in reversed(reports) if j < i), None)
            if previous is not None and previous != initial_report and previous != start:
                if i - previous <= 3 and not REPORTING.search(sentences[i]):
                    needed.add(previous)
            for j in (i - 1, i + 1):
                if 0 <= j < len(sentences) and LIMITATION.search(sentences[j]) and not HISTORICAL.search(sentences[j]):
                    if DEPENDENT.search(sentences[j]) or related(i, j):
                        needed.add(j)
            # A middle caveat about the reported results remains relevant to
            # later performance claims even if background separates them.
            if 2 in features[i]:
                needed.update(j for j in range(start, i)
                              if LIMITATION.search(sentences[j]) and
                              not HISTORICAL.search(sentences[j]) and
                              re.search(r'这些结果|上述结果|该结果|这些性能|上述性能', sentences[j]))
            for j in needed - result:
                if j not in usable:
                    raise ValueError('无法安全保留原文的归属和限定语境')
                result.add(j)
                pending.append(j)
        return result

    def bullets_for(indices):
        # Merge only adjacent complete statements to fit three topical groups.
        groups = [[i] for i in sorted(indices)]
        while len(groups) > 3:
            pair = next((k for k in range(len(groups) - 1)
                         if groups[k][-1] + 1 == groups[k + 1][0]
                         and len(groups[k]) + len(groups[k + 1]) <= 3
                         and sum(len(sentences[i]) for i in groups[k] + groups[k + 1]) <= 300), None)
            if pair is None:
                raise ValueError('无法安全压缩为三组完整要点')
            groups[pair:pair + 2] = [groups[pair] + groups[pair + 1]]
        return [''.join(_bullet(sentences[i]) for i in group) for group in groups]

    # A substantive model capability/result and its caveats must survive even
    # when an overlong lead would otherwise consume the entire page budget.
    substantive = [i for i in usable if i != start and not HISTORICAL.search(sentences[i])
                   and (1 in features[i] or 2 in features[i])]
    if substantive:
        mandatory.add(max(substantive, key=lambda i: (overlap[i], 2 in features[i], -i)))
    caveats = [i for i in usable if LIMITATION.search(sentences[i])
               and not HISTORICAL.search(sentences[i])]
    if caveats:
        mandatory.add(max(caveats, key=lambda i: (overlap[i], i)))
    selected = dependencies(mandatory)

    def fits(indices):
        narration = spoken_title + ''.join(sentences[i] for i in sorted(indices))
        return len(re.findall(r'[\u4e00-\u9fff]', narration)) <= 220 and len(narration) <= 360

    if not fits(selected):
        raise ValueError('摘要过长：保留核心事实与归属限定需超过220汉字或360字符，无法安全压缩为一页')
    candidates = usable - selected
    while candidates:
        covered = set().union(*(features[i] for i in selected))

        def score(i):
            s = sentences[i]
            novelty = len(features[i] - covered)
            duplicate = max((len(set(re.findall(r'(?=(.{2}))', s)) &
                                 set(re.findall(r'(?=(.{2}))', sentences[j]))) / max(1, len(s) - 1)
                             for j in selected), default=0)
            return (2 * novelty + min(overlap[i], 5) * 0.6 +
                    2 * bool(re.search(r'自定义域名|custom.?domain|不支持|尚未|未经|受限|发出提醒', s, re.I)) +
                    3 * bool(re.search(r'\d+(?:%| 倍| 万| 亿| 美元)', s)) -
                    4 * bool(HISTORICAL.search(s)) - 5 * duplicate - len(s) / 250,
                    -i)

        i = max(candidates, key=score)
        candidates.remove(i)
        if any(sentences[i] == sentences[j] for j in selected) or score(i)[0] <= 0:
            continue
        try:
            proposed = dependencies(selected | {i})
            bullets = bullets_for(proposed)
        except ValueError:
            # Do not strip the dependency and keep an unqualified claim.
            continue
        if not fits(proposed):
            continue
        if len(bullets_for(selected)) >= 3:
            continue
        selected = proposed
    bullets = bullets_for(selected)
    if not bullets or not fits(selected):
        raise ValueError('摘要过长或正文不足，无法安全生成一页完整要点摘要')
    return bullets, spoken_title + ''.join(bullets)


def collect(config: dict, now: datetime, hours: int, limit: int, log_path=None, health_path=None) -> dict:
    """Fetch enabled sources; fail explicitly if no eligible extract survives."""
    _validate(now, hours, limit)
    event_cutoff_date = max(now - timedelta(hours=hours), window_start(now)).astimezone(SHANGHAI).date()
    today = now.astimezone(SHANGHAI).date()
    scope = config.get('topic_scope', 'foundation_models')
    if scope not in ('foundation_models', 'all_ai'):
        raise ValueError('topic_scope must be foundation_models or all_ai')
    budget = config.get('article_request_budget', 40)
    if isinstance(budget, bool) or not isinstance(budget, int) or not 1 <= budget <= 100:
        raise ValueError('article_request_budget 必须为1至100的整数')
    stats = dict(feed_entries=0, off_topic=0, source_failures=0,
                 article_requests=0, fetch_failures=0, date_rejected=0,
                 content_rejected=0, summary_rejected=0, summary_parked=0,
                 summary_parked_overflow=0, selected=0,
                 translation_api_calls=0, translation_cache_hits=0, translation_failures=0,
                 source_cap_skipped=0, article_request_budget=budget,
                 skipped_recently_broadcast=0)
    source_caps = {}
    for source in config.get('sources', []):
        cap = source.get('max_stories')
        if cap is not None:
            if isinstance(cap, bool) or not isinstance(cap, int) or not 1 <= cap <= 12:
                raise ValueError('来源 max_stories 必须为1至12的整数')
            source_caps[source.get('name', 'RSS')] = cap
    rows, errors = [], []
    health, health_warnings = load_health(health_path) if health_path else ({}, [])
    errors.extend(health_warnings)
    stale_sources = []
    for source in config.get('sources', []):
        if not source.get('enabled', True):
            continue
        name, url = source.get('name', 'RSS'), source.get('url', '')
        try:
            content = _fetch(url)
            if source.get('type') in ('hf_papers', 'arxiv', 'github_releases', 'english_rss', 'official_changelog'):
                for row in source_rows(source, content):
                    stats['feed_entries'] += 1
                    if scope == 'foundation_models' and not english_topic(row['title'], row['abstract']):
                        stats['off_topic'] += 1
                        continue
                    if (scope == 'all_ai' and source.get('type') == 'english_rss'
                            and not source.get('ai_only', False)
                            and not english_blog_candidate(row['title'], row['abstract'])):
                        stats['off_topic'] += 1
                        continue
                    rows.append(dict(row, source_name=name))
                if health_path:
                    record_result(health, name, checked=now.isoformat())
                continue
            root = ET.fromstring(content)
            if root.tag.rsplit('}', 1)[-1].lower() not in ('rss', 'feed', 'rdf'):
                raise ValueError('response is not RSS/Atom XML')
            feed = feedparser.parse(content)
            for entry in feed.entries[:500]:
                stats['feed_entries'] += 1
                title = BeautifulSoup(entry.get('title', ''), 'html.parser').get_text(' ', strip=True)
                description = BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text(' ', strip=True)
                if not editorial_candidate(title):
                    stats['off_topic'] += 1
                    continue
                if scope == 'foundation_models' and not _model_topic(title):
                    stats['off_topic'] += 1
                    continue
                if scope == 'all_ai' and not source.get('ai_only', False) and not (
                        ai_related(title) or ai_related(description[:300])):
                    stats['off_topic'] += 1
                    continue
                # Atom may only provide updated; event evidence is still mandatory.
                row = dict(title=title, source_name=name, source_url=entry.get('link', ''),
                           published=entry.get('published') or entry.get('updated'))
                if source.get('use_feed_content'):
                    content_blocks = entry.get('content') or []
                    embedded = content_blocks[0].get('value', '') if content_blocks else entry.get('summary', '')
                    if embedded:
                        row['feed_content'] = embedded
                rows.append(row)
            if health_path:
                record_result(health, name, checked=now.isoformat())
        except (requests.RequestException, OSError, ValueError, ET.ParseError) as exc:
            stats['source_failures'] += 1
            errors.append(f'{name} ({url}): {exc}')
            if health_path and record_result(health, name, exc, now.isoformat()):
                warning = f'[源疑似失效] {name}：连续失败 {health[name]["consecutive_failures"]} 次：{exc}'
                print(warning, flush=True)
                stale_sources.append(dict(name=name, url=url, **health[name]))
    if health_path:
        save_health(health_path, health)
    # Scan the complete eligible pool; an exhausted article budget only blocks
    # candidates that actually require another request.
    candidates = select_recent(rows, now, hours, max(1, len(rows)), stats)
    if scope == 'all_ai':
        candidates.sort(key=playback_priority)  # Stable: newest first within each priority.
    stats['eligible_candidates'] = len(candidates)
    recently_broadcast = []
    if log_path:
        entries, warnings = recent_entries(log_path)
        errors.extend(warnings)
        by_fingerprint = {entry['fingerprint']: entry for entry in entries}
        by_url = {entry['source_url']: entry for entry in entries}
        fresh = []
        for row in candidates:
            match = by_fingerprint.get(url_fingerprint(row['source_url'], row['title'])) or by_url.get(row['source_url'])
            if match:
                stats['skipped_recently_broadcast'] += 1
                recently_broadcast.append(dict(title=row['title'], source_url=row['source_url'],
                                               appeared_date=match['date']))
            else:
                fresh.append(row)
        candidates = fresh
    selected_stories = []
    source_selected = {}
    parked_candidates = {}
    considered, attempted, budget_blocked = set(), set(), set()

    def needs_article_request(row):
        return row.get('content_kind') == 'paper' or (
            not row.get('content_kind') and not row.get('feed_content'))

    def translation_event(kind, detail):
        if kind == 'api_call':
            stats['translation_api_calls'] += 1
        elif kind == 'cache_hit':
            stats['translation_cache_hits'] += 1
        elif kind == 'warning':
            errors.append('翻译警告：' + detail)

    def translate_copy(value):
        try:
            return translate_to_chinese(value, on_event=translation_event)
        except (requests.RequestException, OSError, ValueError):
            stats['translation_failures'] += 1
            raise

    def process_candidate(index, row):
        """Try one candidate exactly once and retain its global ranking index."""
        if index in attempted:
            return
        attempted.add(index)
        considered.add(index)
        source_name = row['source_name']
        stage = 'content_rejected'
        original = ''
        paragraphs = []
        event = {}
        try:
            if row.get('content_kind'):
                kind = row['content_kind']
                if kind == 'paper':
                    stage = 'fetch_failures'
                    stats['article_requests'] += 1
                    content = _fetch(row['source_url'])
                    stage = 'date_rejected'
                    original, event = paper_details(content)
                else:
                    original = row['abstract']
                    event = {k: row[k] for k in ('event_date', 'event_date_evidence')}
                stage = 'date_rejected'
                moment = _date(event['event_date'])
                if moment is None or not max(now - timedelta(hours=hours), window_start(now)) <= moment <= now:
                    raise ValueError('论文首次提交或正式版本发布日期不在本次搜查窗口内')
                stage = 'summary_rejected'
                if kind == 'official_model_release':
                    model_name = re.sub(r'\s+(?:Now Available|Release|Launched?).*$',
                                        '', row['title'], flags=re.I).strip()
                    if not model_name or not row.get('feature_points'):
                        raise ValueError('官方模型更新缺少模型名称或具体特性')
                    source_bullets = [f'{model_name} model was released on {moment.date().isoformat()}.']
                    source_bullets.extend(row['feature_points'][:2])
                else:
                    source_bullets = english_summary(original, kind)
                display_title = translate_copy(row['title'])
                bullets = [translate_copy(bullet) if re.search(r'[A-Za-z]', bullet) else bullet
                           for bullet in source_bullets]
                # Reject an oversized extract before it can fail the whole video.
                if config.get('require_concrete_news') and not concrete_news(display_title, bullets):
                    raise ValueError('摘要缺少具体主体、事件或可说明的变化，不作为新闻入选')
                from .render import single_page_layout
                single_page_layout({'bullets': bullets})
                narration = _spoken_title(display_title) + ''.join(bullets)
                category = ('模型发布' if kind == 'official_model_release' else
                            '要闻' if kind == 'official_article' else
                            '技术洞察' if kind in ('paper', 'article') else '开发生态')
                nav_text = (row['title'] if kind == 'official_model_release' else
                            ' '.join((row.get('title', ''), row.get('abstract', ''),
                                      row.get('source_name', ''))))
                nav_label = _nav_label(nav_text, row.get('source_name', ''))
                if nav_label == '大模型':
                    nav_label = ('论文' if kind == 'paper' else
                                 '官方' if kind == 'official_article' else
                                 '模型工具')
                story = dict(row, title=display_title, source_title=row['title'],
                             **{k: v for k, v in event.items() if k not in row},
                             id=hashlib.sha256(row['source_url'].encode()).hexdigest()[:16],
                             category=category, nav_label=nav_label,
                             bullets=bullets, narration=narration, evidence=''.join(bullets),
                             verification='machine_translated_english_source', language='zh',
                             source_language='en', source_text=original)
                selected_stories.append((index, story))
                source_selected[source_name] = source_selected.get(source_name, 0) + 1
                return
            _reject_debunk(row['title'])
            if row.get('feed_content'):
                content = '<article>' + row['feed_content'] + '</article>'
            else:
                stage = 'fetch_failures'
                stats['article_requests'] += 1
                content = _fetch(row['source_url'])
            stage = 'content_rejected'
            paragraphs = extract_paragraphs(content)
            if not paragraphs:
                raise ValueError('没有可抽取的中文正文')
            stage = 'date_rejected'
            event = article_event_evidence('\n'.join(paragraphs), row['published'], row['title'], scope=scope)
            event_date = event['event_date']
            if not event_cutoff_date <= news_date(event_date) <= today:
                raise ValueError('新闻事件早于本次搜查截止日期或尚未发生，不能用新转载日期替代事件日期')
            stage = 'summary_rejected'
            bullets, narration = _summary(paragraphs, row['title'])
            if config.get('require_concrete_news') and not concrete_news(row['title'], bullets):
                raise ValueError('摘要缺少具体主体、事件或可说明的变化，不作为新闻入选')
            public_row = {k: v for k, v in row.items() if k != 'feed_content'}
            story = dict(public_row, id=hashlib.sha256(row['source_url'].encode()).hexdigest()[:16],
                         **event, category=classify(row['title'], narration), nav_label=_nav_label(row['title']) if MODEL_NAMES.search(row['title']) or scope == 'foundation_models' else classify(row['title'], narration), bullets=bullets, narration=narration,
                         evidence=''.join(bullets), verification='extractive',
                         source_text='\n'.join(paragraphs))
            selected_stories.append((index, story))
            source_selected[source_name] = source_selected.get(source_name, 0) + 1
        except (requests.RequestException, OSError, ValueError) as exc:
            stats[stage] += 1
            errors.append(f"{row['source_name']} ({row['source_url']}): {exc}")
            if stage == 'summary_rejected':
                fingerprint = url_fingerprint(row['source_url'], row['title'])
                if fingerprint not in parked_candidates:
                    source_text = original if row.get('content_kind') else '\n'.join(paragraphs)
                    parked_candidates[fingerprint] = dict(
                        title=row['title'], source_name=source_name,
                        source_url=row['source_url'], published=row.get('published') or '',
                        event_date=event.get('event_date') or '',
                        event_date_evidence=event.get('event_date_evidence') or '',
                        reason=str(exc),
                        snippet=re.sub(r'\s+', ' ', str(source_text or '')).strip()[:200])

    deferred = []
    for index, row in enumerate(candidates):
        if len(selected_stories) >= limit:
            break
        source_name = row['source_name']
        cap = source_caps.get(source_name)
        if cap is not None and source_selected.get(source_name, 0) >= cap:
            considered.add(index)
            deferred.append((index, row))
            stats['source_cap_skipped'] += 1
            continue
        if needs_article_request(row) and stats['article_requests'] >= budget:
            budget_blocked.add(index)
            continue
        process_candidate(index, row)

    # Source caps are a diversity preference. If the capped first pass cannot
    # fill the edition, retry only the deferred candidates in their original
    # global ranking order, without processing any candidate twice.
    if len(selected_stories) < limit:
        for index, row in deferred:
            if len(selected_stories) >= limit:
                break
            if needs_article_request(row) and stats['article_requests'] >= budget:
                budget_blocked.add(index)
                continue
            process_candidate(index, row)

    stories = [story for _, story in sorted(selected_stories, key=lambda pair: pair[0])]
    summary_parked = []
    parked_per_source = {}

    def parked_time(item):
        value = item['event_date'] or item['published']
        moment = _date(value)
        if moment is None:
            try:
                moment = datetime.fromisoformat(value).replace(tzinfo=SHANGHAI)
            except (TypeError, ValueError):
                return datetime.min.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc)

    for parked in sorted(parked_candidates.values(), key=parked_time, reverse=True):
        name = parked['source_name']
        if len(summary_parked) >= 30 or parked_per_source.get(name, 0) >= 3:
            stats['summary_parked_overflow'] += 1
            continue
        summary_parked.append(parked)
        parked_per_source[name] = parked_per_source.get(name, 0) + 1
    stats['summary_parked'] = len(summary_parked)
    stats['selected'] = len(stories)
    stats['unexamined_candidates'] = len(candidates) - len(considered)
    stats['budget_exhausted'] = bool(budget_blocked) and len(stories) < limit
    if not stories:
        raise RuntimeError('没有可用资讯：指定窗口内无符合条件且正文可抽取的文章。筛选统计：' + str(stats) + '；'.join(errors))
    date = now.astimezone(SHANGHAI).date().isoformat()
    return dict(date=date, window_days=RECENCY_DAYS,
                title=f'AI 日报 · {date}',
                edition_note=f'仅北京时间最近{RECENCY_DAYS}天；热点消息优先，同一热点等级按发布时间从新到旧；不以窗口外旧闻补足条数；中英文原文机器抽取的完整要点摘要，未经人工核验；英文保留原文；论文结果为作者报告；保留来源提供的时区日期。',
                stories=stories, summary_parked=summary_parked,
                collection_errors=errors, collection_stats=stats,
                recently_broadcast=recently_broadcast, stale_sources=stale_sources)
