"""Structured research/release sources and source-only English extracts."""
import hashlib
import json
import re
import os
import tempfile
import time
import warnings
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape

from bs4 import BeautifulSoup
import feedparser
import requests
from .models import MODEL_NAMES


TRANSLATION_URL = 'https://api.deepseek.com/v1/chat/completions'
TRANSLATION_MODEL = 'deepseek-chat'
CACHE_PATH = Path(__file__).resolve().parent.parent / 'data' / 'translation_cache.json'
GLOSSARY_PATH = Path(__file__).resolve().parent.parent / 'data' / 'glossary.json'


def _translation_chunks(text, limit=1200):
    words = str(text or '').split()
    chunks, current = [], ''
    for word in words:
        if current and len(current) + len(word) + 1 > limit:
            chunks.append(current)
            current = ''
        if len(word) > limit:
            if current:
                chunks.append(current); current = ''
            chunks.extend(word[i:i + limit] for i in range(0, len(word), limit))
        else:
            current = (current + ' ' + word).strip()
    if current:
        chunks.append(current)
    return chunks


def _load_translation_cache():
    try:
        cache = json.loads(CACHE_PATH.read_text(encoding='utf-8'))
        if not isinstance(cache, dict) or any(
                not isinstance(key, str) or not isinstance(entry, dict)
                or not all(isinstance(entry.get(field), str) and entry[field]
                           for field in ('zh', 'model', 'ts'))
                for key, entry in cache.items()):
            raise ValueError('缓存结构或字段无效')
        return cache
    except (OSError, ValueError, TypeError) as exc:
        warnings.warn(f'翻译缓存不可用，按空缓存处理：{exc}', RuntimeWarning, stacklevel=2)
        return {}


def _save_translation_cache(cache):
    # 同目录临时文件与原子替换，避免中途写入留下损坏的 JSON。
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    while len(cache) > 5000:
        oldest = min(cache, key=lambda key: cache[key]['ts'])
        del cache[oldest]
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=CACHE_PATH.parent,
                                         prefix='.translation_cache.', suffix='.tmp',
                                         delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(cache, handle, ensure_ascii=False, indent=2)
        temporary.replace(CACHE_PATH)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _glossary_terms():
    try:
        data = json.loads(GLOSSARY_PATH.read_text(encoding='utf-8'))
        terms = data['keep_original']
        if not isinstance(terms, list) or not all(isinstance(term, str) for term in terms):
            raise ValueError('术语表格式无效')
        return terms
    except (OSError, ValueError, KeyError, TypeError) as exc:
        warnings.warn(f'术语表不可用：{exc}', RuntimeWarning, stacklevel=2)
        return []


def translate_to_chinese(text, request_post=None, *, on_event=None):
    """翻译英文展示文本；缓存命中免请求，失败时明确报错。"""
    value = re.sub(r'\s+', ' ', str(text or '')).strip()
    if not value or not re.search(r'[A-Za-z]', value):
        return value
    digest = hashlib.sha256(value.encode('utf-8')).hexdigest()
    cache = _load_translation_cache()
    if digest in cache:
        if on_event:
            on_event('cache_hit', '')
        return cache[digest]['zh']
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        raise ValueError('缺少 DEEPSEEK_API_KEY，无法翻译英文条目')
    terms = _glossary_terms()
    direct = proxy = None
    if request_post is None:
        direct = requests.Session()
        direct.trust_env = False
        proxy = requests.Session()
        request_post = direct.post
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    system = ('你是科技新闻英译中译者。只输出译文，不要解释，不要加引号。'
              '术语表里的名称保留原文；保持数字、百分比、版本号和产品名不变；'
              '不得添加原文没有的信息。术语表：' + json.dumps(terms, ensure_ascii=False))
    translated = []
    try:
        for chunk in _translation_chunks(value):
            required = [term for term in terms if term in chunk]
            result = ''
            missing = []
            for glossary_attempt in range(2):
                prompt = system
                if glossary_attempt:
                    prompt += ' 特别注意：以下名称必须在译文中逐字原样出现：' + '、'.join(missing)
                body = {'model': TRANSLATION_MODEL,
                        'messages': [{'role': 'system', 'content': prompt},
                                     {'role': 'user', 'content': chunk}],
                        'temperature': 0}
                # 初次请求加三次退避重试。直连网络失败时额外尝试一次环境代理。
                for attempt in range(4):
                    try:
                        if on_event:
                            on_event('api_call', '')
                        response = request_post(TRANSLATION_URL, headers=headers,
                                                json=body, timeout=30)
                        response.raise_for_status()
                        result = str(response.json()['choices'][0]['message']['content']).strip()
                        break
                    except (requests.Timeout, requests.ConnectionError) as exc:
                        if direct is not None and proxy is not None:
                            try:
                                if on_event:
                                    on_event('api_call', '')
                                response = proxy.post(TRANSLATION_URL, headers=headers,
                                                      json=body, timeout=30)
                                response.raise_for_status()
                                result = str(response.json()['choices'][0]['message']['content']).strip()
                                break
                            except (requests.RequestException, ValueError, KeyError, IndexError) as fallback_exc:
                                exc = fallback_exc
                        if attempt == 3:
                            raise ValueError(f'DeepSeek 翻译请求失败：{exc}') from exc
                    except requests.HTTPError as exc:
                        status = exc.response.status_code if exc.response is not None else None
                        if status != 429 and not (status is not None and 500 <= status < 600) or attempt == 3:
                            raise ValueError(f'DeepSeek 翻译请求失败：{exc}') from exc
                    except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
                        raise ValueError(f'DeepSeek 翻译响应无效：{exc}') from exc
                    time.sleep((1, 3, 7)[attempt])
                if not result or result.casefold() == chunk.casefold() or not re.search(r'[\u4e00-\u9fff]', result):
                    raise ValueError('DeepSeek 未返回有效中文译文')
                missing = [term for term in required if term not in result]
                if not missing:
                    break
            if missing and on_event:
                on_event('warning', '翻译术语未保留原文：' + '、'.join(missing))
            translated.append(result)
        output = ''.join(translated)
        cache[digest] = {'zh': output, 'model': TRANSLATION_MODEL,
                         'ts': datetime.now(timezone.utc).isoformat()}
        try:
            _save_translation_cache(cache)
        except OSError as exc:
            warnings.warn(f'翻译缓存写入失败：{exc}', RuntimeWarning, stacklevel=2)
        return output
    finally:
        if direct is not None:
            direct.close()
            proxy.close()



def english_topic(title, abstract):
    text = str(title or '') + ' ' + str(abstract or '')
    return bool(MODEL_NAMES.search(text) or re.search(r'large language model|\bLLMs?\b|foundation model|language model|multimodal|vision.language|reasoning|benchmark|evaluation', text, re.I))


def english_ai_related(title, text):
    """Broad AI filter for mixed-topic English technology feeds."""
    value = str(title or '') + ' ' + str(text or '')
    return bool(MODEL_NAMES.search(value) or re.search(
        r'\bartificial intelligence\b|\bAI\b|\bmachine learning\b|\bdeep learning\b|'
        r'\bneural networks?\b|\bLLMs?\b|\blanguage models?\b|\bgenerative AI\b|'
        r'\bAI agents?\b|\btransformers?\b|\bdiffusion models?\b|\bmodel inference\b',
        value, re.I))


def english_blog_candidate(title, text):
    """Keep AI posts whose headline is meaningful without opening the article."""
    title = re.sub(r'\s+', ' ', str(title or '')).strip()
    if not english_ai_related(title, text):
        return False
    if english_ai_related(title, ''):
        return True
    if re.match(r'^(?:quoting|note on|notes? on|link(?: blog)?|quick note)\b', title, re.I):
        return False
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", title)) >= 4


def normalized_feed_date(value):
    """Return an aware ISO timestamp for either Atom/ISO or RSS/RFC 822 dates."""
    text = str(value or '').strip()
    if not text:
        raise ValueError('英文技术博客条目缺少发布日期')
    try:
        moment = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        moment = parsedate_to_datetime(text)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('英文技术博客发布日期缺少时区')
    return moment.isoformat()


def source_rows(source, content):
    kind = source['type']
    if kind == 'official_changelog':
        # Official documentation has no RSS feed. Treat dated release sections
        # as entries; repeated localized sections must not become duplicate news.
        soup = BeautifulSoup(content, 'html.parser')
        seen = set()
        for heading in soup.find_all('h2'):
            match = re.search(r'Version:\s*(\d{4}-\d{2}-\d{2})', heading.get_text(' ', strip=True), re.I)
            if not match:
                continue
            released = match.group(1)
            for subheading in heading.find_next_siblings():
                if subheading.name == 'h2':
                    break
                if subheading.name != 'h3':
                    continue
                title = subheading.get_text(' ', strip=True).replace('\u200b', '').strip()
                if not MODEL_NAMES.search(title) or not re.search(
                        r'now available|release|launch', title, re.I):
                    continue
                key = (released, title.casefold())
                if key in seen:
                    continue
                seen.add(key)
                sections, feature_points = [], []
                for sibling in subheading.find_next_siblings():
                    if sibling.name in ('h2', 'h3'):
                        break
                    if sibling.name in ('p', 'ul', 'ol'):
                        sections.append(sibling.get_text(' ', strip=True))
                        if sibling.name in ('ul', 'ol'):
                            feature_points.extend(li.get_text(' ', strip=True)
                                                  for li in sibling.find_all('li', recursive=False))
                abstract = ' '.join(sections).strip()
                if len(abstract) < 50:
                    continue
                yield dict(title=title, published=released + 'T12:00:00+08:00',
                           event_date=released + 'T12:00:00+08:00',
                           event_date_evidence='官方更新日志 Version: ' + released,
                           source_url=source['url'] + '#' + (subheading.get('id') or heading.get('id', '')),
                           abstract=abstract, feature_points=feature_points,
                           content_kind='official_model_release')
    elif kind == 'sitemap':
        root = BeautifulSoup(content, 'xml')
        for item in root.find_all('url')[:500]:
            loc = item.find('loc')
            lastmod = item.find('lastmod')
            url = loc.get_text(strip=True) if loc else ''
            published = lastmod.get_text(strip=True) if lastmod else ''
            if not url or not published or not re.search(r'/news/', url, re.I):
                continue
            slug = url.rstrip('/').rsplit('/', 1)[-1].replace('-', ' ')
            title = f"{source.get('name', '官方')} {slug}"
            yield dict(title=title, published=published, event_date=published,
                       event_date_evidence='官方站点 sitemap lastmod: ' + published,
                       source_url=url, abstract='')
    elif kind == 'hf_papers':
        entries = json.loads(content)
        if not isinstance(entries, list):
            raise ValueError('Hugging Face 未返回论文列表')
        for item in entries[:500]:
            paper = item.get('paper', {})
            identifier = paper.get('id', '')
            if not re.fullmatch(r'\d{4}\.\d{4,5}', identifier):
                continue
            # Daily selection is discovery, never the publication date.
            yield dict(title=paper.get('title', ''), published=paper.get('publishedAt'),
                       source_url='https://arxiv.org/abs/' + identifier,
                       abstract=paper.get('summary', ''), content_kind='paper')
    elif kind == 'github_releases':
        entries = json.loads(content)
        if not isinstance(entries, list):
            raise ValueError('GitHub 未返回版本列表')
        for item in entries[:100]:
            if item.get('draft') or item.get('prerelease'):
                continue
            yield dict(title=source['name'] + ' ' + (item.get('tag_name') or item.get('name', '')),
                       published=item.get('published_at'), event_date=item.get('published_at'),
                       event_date_evidence='GitHub release published_at: ' + str(item.get('published_at')),
                       source_url=item.get('html_url', ''), abstract=item.get('body') or '', content_kind='release')
    elif kind == 'arxiv':
        feed = feedparser.parse(content)
        if not feed.version:
            raise ValueError('arXiv 未返回 RSS/Atom')
        for item in feed.entries[:500]:
            if item.get('arxiv_announce_type') not in (None, 'new'):
                continue
            yield dict(title=item.get('title', ''), published=item.get('published'),
                       source_url=item.get('link', ''),
                       abstract=item.get('summary', '').split('Abstract:', 1)[-1].strip(), content_kind='paper')
    elif kind == 'english_rss':
        feed = feedparser.parse(content)
        if not feed.version:
            raise ValueError('英文技术博客未返回 RSS/Atom')
        for item in feed.entries[:500]:
            published = normalized_feed_date(item.get('published') or item.get('updated'))
            content_blocks = item.get('content') or []
            article = content_blocks[0].get('value', '') if content_blocks else item.get('summary', '')
            title = unescape(re.sub(r'<[^>]+>', ' ', str(item.get('title', ''))))
            title = re.sub(r'\s+', ' ', title).strip()
            yield dict(title=title,
                       published=published, event_date=published,
                       event_date_evidence='RSS/Atom published: ' + str(published),
                       source_url=item.get('link', ''), abstract=article,
                       content_kind=source.get('content_kind', 'article'))


def paper_details(content):
    soup = BeautifulSoup(content, 'html.parser')
    history = soup.select_one('.submission-history')
    match = re.search(r'\[v1\]\s*([^\n(]+(?:UTC|GMT))', history.get_text(' ', strip=True) if history else '')
    if not match:
        raise ValueError('论文缺少可核实的首次提交时间，不能使用推荐或修订日期')
    timestamp = parsedate_to_datetime(match[1]).isoformat()
    abstract = soup.select_one('meta[name="citation_abstract"]')
    text = abstract.get('content', '') if abstract else ''
    if not text:
        block = soup.select_one('blockquote.abstract')
        text = block.get_text(' ', strip=True) if block else ''
    if not text:
        raise ValueError('论文缺少摘要')
    return text, dict(event_date=timestamp, event_date_evidence='arXiv [v1] ' + match[1])


def english_summary(text, kind):
    """Keep whole statements, attribution and caveats; do not invent translations."""
    if not isinstance(text, (str, bytes)):
        raise ValueError('英文正文不足以抽取摘要')
    text = BeautifulSoup(text, 'html.parser').get_text(' ', strip=True)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'[`#*]', '', text)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+(?=[A-Z])|\n+', text)
                 if len(s.strip()) >= 30 and re.search(r'[A-Za-z]', s)]
    if not sentences:
        raise ValueError('英文正文不足以抽取摘要')
    caveats = [s for s in sentences if re.search(r'\b(?:however|limitation|limited|only|cannot|not|bottleneck|failure|may|suggest)\b', s, re.I)]
    selected = [sentences[0]]
    result = next((s for s in sentences[1:] if re.search(r'\b(?:achiev|improv|result|outperform|benchmark|evaluat|support)\w*', s, re.I)), None)
    if result:
        selected.append(result)
    selected = list(dict.fromkeys(selected + caveats))
    if any(re.search(r'…|\.{3}', sentence) for sentence in selected):
        raise ValueError('英文 Feed 摘要包含省略号或截断文字')
    # Keep every detected qualification; fail rather than silently drop one.
    if len(selected) > 3 or sum(map(len, selected)) > 1100:
        raise ValueError('英文摘要与必要限定超过单页容量，需人工精简')
    notice = ('论文摘要摘录，结果为作者报告；未核实同行评审或独立复测。' if kind == 'paper'
              else '官方版本说明摘录；工具更新不等于模型本身发布。' if kind == 'release'
              else '官方公告原文摘录；能力与效果描述来自发布方，尚未独立复核。' if kind == 'official_article'
              else '英文技术博客摘录；观点与判断属于原作者，未经独立复核。')
    return [notice] + selected
