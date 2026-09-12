"""Bounded RSS collection and deterministic, source-only Chinese extraction."""

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import math
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

from .recency import yesterday_start, article_event_date, news_date

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


MODEL_NAMES = re.compile(
    r'(?<![A-Za-z0-9_])(?:ChatGPT|GPT(?:[- ]?\d[\w.-]*)?|Claude|Gemini|DeepSeek|'
    r'GLM(?:[- ]?\d[\w.-]*)?|Qwen(?:[- ]?\d[\w.-]*)?|Kimi|Llama|Grok|Mistral|'
    r'ERNIE|Hunyuan)(?![A-Za-z_])|通义千问|智谱|文心|混元|豆包', re.I)
MODEL_CHANGE = re.compile(
    r'发布|推出|迭代|更新|升级|开源|新版本|新模型|能力|评测|测评|基准|测试|'
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
            re.search(r'模型(?:正式)?(?:发布|开源|推出)|发布.{0,12}模型', main_clause) and
            not OFF_TOPIC.search(main_clause)):
        title = main_clause
    named = MODEL_NAMES.search(title)
    generic = re.search(r'大语言模型|语言模型|多模态(?:基础)?模型|基础模型', title)
    if not (named or generic) or not MODEL_CHANGE.search(title):
        return False
    # A model-effect comparison can involve hardware or pricing; a product
    # announcement merely using a model remains outside the default edition.
    if re.search(r'融资|收购|投资|营收|财报|估值|上市|裁员|任命|离职|薪酬|人事|贫富|手机|手表|芯片|显卡|服务器|数据中心|存储|数据库|Habitat|Sites|建站|浏览器|插件|办公|接入|集成', title, re.I):
        return False
    if OFF_TOPIC.search(title) and not MODEL_EFFECT.search(title):
        return False
    return True


def _nav_label(title):
    names = []
    aliases = {'通义千问': 'Qwen', '智谱': 'GLM', '文心': 'ERNIE', '混元': 'Hunyuan'}
    for match in MODEL_NAMES.finditer(title):
        raw = match.group()
        name = aliases.get(raw, raw)
        for canonical in ('ChatGPT', 'GPT', 'Claude', 'Gemini', 'DeepSeek', 'GLM',
                          'Qwen', 'Kimi', 'Llama', 'Grok', 'Mistral', 'ERNIE', 'Hunyuan'):
            if name.casefold().startswith(canonical.casefold()):
                name = canonical
                break
        if name not in names:
            names.append(name)
    if len(names) >= 3:
        return '多模型对比'
    label = ' / '.join(names)
    if len(names) == 2 and sum(2 if '\u4e00' <= c <= '\u9fff' else 1 for c in label) > 12:
        return '模型对比'
    return label if names else '基础模型'


def classify(title: str, narration: str) -> str:
    """Title first, then narration; ordered rules resolve overlapping topics."""
    rules = (
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


def _canonical(url):
    try:
        parts = urlsplit(url.strip())
        if parts.scheme.lower() not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            return None
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if not k.lower().startswith('utm_') and k.lower() not in TRACKING]
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or '/', urlencode(sorted(query)), ''))
    except (AttributeError, ValueError):
        return None


def select_recent(items: list[dict], now: datetime, hours: int, limit: int) -> list[dict]:
    """Newest first; inclusive lower boundary; never infer missing timezones."""
    _validate(now, hours, limit)
    cutoff = max(now - timedelta(hours=hours), yesterday_start(now))
    eligible = []
    for row in items:
        published = _date(row.get('published'))
        url = _canonical(row.get('source_url', row.get('url', row.get('link', ''))))
        title = re.sub(r'\s+', ' ', str(row.get('title') or '')).strip()
        if published is not None and cutoff <= published <= now and url and title:
            eligible.append((published, dict(row, title=title, source_url=url, published=published.isoformat())))
    eligible.sort(key=lambda pair: pair[0], reverse=True)
    result, urls, titles = [], set(), set()
    for _, row in eligible:
        key = re.sub(r'[\W_]+', '', row['title']).casefold()
        if row['source_url'] in urls or key in titles:
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
    for selector in ('#paragraph', '[itemprop="articleBody"]', '.article-content', '.article_content', '#article-content', 'article', 'main'):
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


def collect(config: dict, now: datetime, hours: int, limit: int) -> dict:
    """Fetch enabled sources; fail explicitly if no eligible extract survives."""
    _validate(now, hours, limit)
    scope = config.get('topic_scope', 'foundation_models')
    if scope not in ('foundation_models', 'all_ai'):
        raise ValueError('topic_scope must be foundation_models or all_ai')
    rows, errors = [], []
    for source in config.get('sources', []):
        if not source.get('enabled', True):
            continue
        name, url = source.get('name', 'RSS'), source.get('url', '')
        try:
            content = _fetch(url)
            root = ET.fromstring(content)
            if root.tag.rsplit('}', 1)[-1].lower() not in ('rss', 'feed', 'rdf'):
                raise ValueError('response is not RSS/Atom XML')
            feed = feedparser.parse(content)
            for entry in feed.entries[:500]:
                title = BeautifulSoup(entry.get('title', ''), 'html.parser').get_text(' ', strip=True)
                description = BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text(' ', strip=True)
                if scope == 'foundation_models' and not _model_topic(title):
                    continue
                if scope == 'all_ai' and not source.get('ai_only', False) and not (
                        AI_TERMS.search(title) or CORE_AI_TERMS.search(description[:120])):
                    continue
                rows.append(dict(title=title, source_name=name, source_url=entry.get('link', ''), published=entry.get('published')))
        except (requests.RequestException, OSError, ValueError, ET.ParseError) as exc:
            errors.append(f'{name} ({url}): {exc}')
    # At most 20 article requests even if a caller asks for a huge edition.
    candidates = select_recent(rows, now, hours, min(20, limit * 3))
    stories = []
    for row in candidates:
        try:
            _reject_debunk(row['title'])
            paragraphs = extract_paragraphs(_fetch(row['source_url']))
            event_date = article_event_date(''.join(paragraphs), row['published'])
            if not yesterday_start(now).date() <= news_date(event_date) <= now.astimezone(SHANGHAI).date():
                raise ValueError('模型事件早于昨天或尚未发生，不能用新转载日期替代事件日期')
            bullets, narration = _summary(paragraphs, row['title'])
            stories.append(dict(row, id=hashlib.sha256(row['source_url'].encode()).hexdigest()[:16],
                                event_date=event_date, category=classify(row['title'], narration), nav_label=_nav_label(row['title']), bullets=bullets, narration=narration,
                                evidence=''.join(bullets), verification='extractive',
                                source_text='\n'.join(paragraphs)))
        except (requests.RequestException, OSError, ValueError) as exc:
            errors.append(f"{row['source_name']} ({row['source_url']}): {exc}")
        if len(stories) >= limit:
            break
    if not stories:
        raise RuntimeError('没有可用资讯：指定窗口内无符合条件且正文可抽取的文章。' + '；'.join(errors))
    date = now.astimezone(SHANGHAI).date().isoformat()
    return dict(date=date, window_days=2,
                title=f'AI 日报 · {date}',
                edition_note=f'仅北京时间今天和昨天；当天优先，不以旧闻补足条数；中文原文机器抽取的完整要点摘要，未经人工核验；保留来源提供的时区日期。',
                stories=stories, collection_errors=errors)
