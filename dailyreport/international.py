"""Structured research/release sources and source-only English extracts."""
import json
import re
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup
import feedparser
from .models import MODEL_NAMES


def english_topic(title, abstract):
    text = title + ' ' + abstract
    return bool(MODEL_NAMES.search(text) or re.search(r'large language model|\bLLMs?\b|foundation model|language model|multimodal|vision.language|reasoning|benchmark|evaluation', text, re.I))


def source_rows(source, content):
    kind = source['type']
    if kind == 'hf_papers':
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
                       source_url=item.get('html_url', ''), abstract=item.get('body', ''), content_kind='release')
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
    # Keep every detected qualification; fail rather than silently drop one.
    if len(selected) > 3 or sum(map(len, selected)) > 1100:
        raise ValueError('英文摘要与必要限定超过单页容量，需人工精简')
    notice = ('论文摘要摘录，结果为作者报告；未核实同行评审或独立复测。' if kind == 'paper'
              else '官方版本说明摘录；工具更新不等于模型本身发布。')
    return [notice] + selected
