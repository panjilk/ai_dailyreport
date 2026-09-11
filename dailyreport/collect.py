"""Bounded RSS collection and deterministic, source-only Chinese extraction."""

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import math
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

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
    """Prefer full source sentences; every shortened prefix marks omission.

    Never remove a reporting prefix or select a free-standing middle clause:
    it may contain a claim whose uncertainty is stated earlier in the sentence.
    """
    if len(sentence) <= 70:
        return sentence
    endings = [end for end in _boundaries(sentence, '，,；;。！？!?') if 16 <= end <= 69]
    end = max(endings) if endings else 69
    return sentence[:end].rstrip() + '…'


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
    cutoff = now - timedelta(hours=hours)
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
    return result[:60]


def _summary(paragraphs, title):
    _reject_debunk(title + '\n' + '\n'.join(paragraphs))
    # Joining before splitting retains a short attribution paragraph such as
    # “研究团队表示：” with the quoted statement that follows it.
    sentences = _sentences(''.join(paragraphs))[:200]
    usable = {i: 16 <= len(s) <= 160 and not FILLER.search(s)
              and not re.fullmatch(r'《.*》[。]?', s)
              for i, s in enumerate(sentences)}
    terms = set(re.findall(r'(?=([\u4e00-\u9fff]{2}))', title))
    terms.update(re.findall(r'[A-Za-z][A-Za-z0-9-]+', title))
    overlap = {i: sum(t.casefold() in sentences[i].casefold() for t in terms)
               for i in range(len(sentences))}
    scores = {i: overlap[i] / max(1, len(terms)) + 0.2 * bool(AI_TERMS.search(sentences[i])) + 1 / (i + 1)
              for i in range(len(sentences))}
    # Only consecutive source sentences, never a scattered subset. Invalid
    # sentences remain barriers rather than disappearing from the middle.
    # Prefer the earliest title-related lead, then average sentence quality.
    best, best_key = None, None
    for start in range(len(sentences)):
        if not usable[start]:
            continue
        # Do not start with a naked quotation separated from its introduction.
        if sentences[start].startswith(('“', '「', '『', '"')):
            continue
        length = 0
        for end in range(start, min(start + 8, len(sentences))):
            if not usable[end]:
                break
            length += len(sentences[end])
            if length > 160:
                break
            if length < 120 or end == start:
                continue
            chosen = tuple(range(start, end + 1))
            key = (bool(overlap[start]), -start,
                   sum(scores[i] for i in chosen) / len(chosen), -abs(length - 140))
            if best_key is None or key > best_key:
                best, best_key = chosen, key
    if best is None:
        raise ValueError('正文不足以生成120–160字的完整原句摘要')
    chosen = sorted(best)
    narration = ''.join(sentences[i] for i in chosen)
    bullets = [_bullet(sentences[i]) for i in chosen[:3]]
    return bullets, narration


def collect(config: dict, now: datetime, hours: int, limit: int) -> dict:
    """Fetch enabled sources; fail explicitly if no eligible extract survives."""
    _validate(now, hours, limit)
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
                if not source.get('ai_only', False) and not (
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
            bullets, narration = _summary(paragraphs, row['title'])
            stories.append(dict(row, id=hashlib.sha256(row['source_url'].encode()).hexdigest()[:16],
                                category=classify(row['title'], narration), bullets=bullets, narration=narration,
                                evidence=narration, verification='extractive'))
        except (requests.RequestException, OSError, ValueError) as exc:
            errors.append(f"{row['source_name']} ({row['source_url']}): {exc}")
        if len(stories) >= limit:
            break
    if not stories:
        raise RuntimeError('没有可用资讯：指定窗口内无符合条件且正文可抽取的文章。' + '；'.join(errors))
    date = now.astimezone(SHANGHAI).date().isoformat()
    return dict(date=date, window_days=math.ceil(hours / 24), window_hours=hours,
                title=f'AI 日报 · {date}',
                edition_note=f'过去{hours}小时；中文原文机器抽取，未经人工核验；保留来源提供的时区日期。',
                stories=stories, collection_errors=errors)
