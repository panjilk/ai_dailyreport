"""Parse dated official news pages without fetching or guessing publication times."""

from datetime import datetime, timedelta
import json
import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .recency import SHANGHAI, window_start


_MAX_ARTICLES = 10
_MAX_PARAGRAPHS = 80
_MIN_BODY_CHARS = 160
_ARTICLE_TYPES = {'Article', 'NewsArticle', 'BlogPosting', 'TechArticle', 'Report'}


def _official_url(source, value, *, news_only=False):
    try:
        base = urlsplit(str(source.get('url', '')))
        parsed = urlsplit(urljoin(source.get('url', ''), str(value or '').strip()))
    except (TypeError, ValueError):
        return None
    if (base.scheme != 'https' or not base.hostname or parsed.scheme != 'https'
            or parsed.netloc.casefold() != base.netloc.casefold()
            or parsed.username is not None or parsed.password is not None):
        return None
    if news_only and not re.fullmatch(r'/news/[^/]+/?', parsed.path):
        return None
    return urlunsplit(('https', parsed.netloc.lower(), parsed.path.rstrip('/'), '', ''))


def _visible_card_day(anchor):
    """Only use a card's own visible date, never an unrelated nearby list date."""
    card = anchor
    stamp = card.find('time')
    if stamp is None and anchor.parent and anchor.parent.name in ('li', 'article'):
        card = anchor.parent
        stamp = card.find('time')
    if stamp is None:
        return None
    text = stamp.get_text(' ', strip=True)
    for date_format in ('%b %d, %Y', '%B %d, %Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            pass
    return None


def official_index_links(source, html, now, hours):
    """Return bounded same-host news candidates; exact article dates decide eligibility."""
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('now must be a timezone-aware datetime')
    if isinstance(hours, bool) or not isinstance(hours, int) or hours < 1:
        raise ValueError('hours must be a positive integer')
    maximum = source.get('max_articles', 6)
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1:
        raise ValueError('max_articles must be a positive integer')
    maximum = min(maximum, _MAX_ARTICLES)
    end = now.astimezone(SHANGHAI)
    start = max(end - timedelta(hours=hours), window_start(end))
    # The visible card has no clock/zone. Leave a day of margin for the article's
    # authoritative timestamp; this is a prefilter, not an invented event date.
    first_day = start.date() - timedelta(days=1)
    last_day = end.date() + timedelta(days=1)
    soup = BeautifulSoup(html, 'html.parser')
    for node in soup.select('nav, header, footer, aside, script, style, [role="navigation"]'):
        node.decompose()
    scope = soup.find('main') or soup
    candidates, seen = [], set()
    for anchor in scope.find_all('a', href=True):
        url = _official_url(source, anchor['href'], news_only=True)
        if not url or url in seen or not anchor.get_text(' ', strip=True):
            continue
        seen.add(url)
        day = _visible_card_day(anchor)
        if day is not None and not first_day <= day <= last_day:
            continue
        candidates.append((day, len(candidates), url))
    candidates.sort(key=lambda row: (row[0] is not None, row[0] or first_day, -row[1]),
                    reverse=True)
    return [row[2] for row in candidates[:maximum]]


def _jsonld_articles(soup):
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            value = json.loads(script.string or script.get_text())
        except (TypeError, ValueError):
            continue
        pending = [value]
        while pending:
            item = pending.pop()
            if isinstance(item, list):
                pending.extend(reversed(item))
            elif isinstance(item, dict):
                types = item.get('@type', [])
                if isinstance(types, str):
                    types = [types.rsplit('/', 1)[-1]]
                elif not isinstance(types, list):
                    types = ['invalid']
                if ('datePublished' in item
                        and (not types or any(isinstance(t, str) and t in _ARTICLE_TYPES
                                              for t in types))):
                    yield item
                pending.extend(reversed([v for v in item.values()
                                         if isinstance(v, (dict, list))]))


def _publication(value):
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    try:
        moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    if moment.tzinfo is None or moment.utcoffset() is None:
        return None
    return value


def _clean_title(value, source):
    value = re.sub(r'\s+', ' ', str(value or '')).strip()
    publishers = {'Anthropic', str(source.get('publisher', '')).strip(),
                  str(source.get('name', '')).strip()}
    for publisher in publishers:
        if publisher:
            value = re.sub(r'\s*(?:\||—|–|-|·)\s*' + re.escape(publisher) + r'\s*$',
                           '', value, flags=re.I).strip()
    return value


def official_article_row(source, html, url):
    """Extract full original paragraphs and timezone-bearing publication metadata."""
    canonical_url = _official_url(source, url)
    if not canonical_url:
        raise ValueError('官方文章链接必须是同域 HTTPS 地址')
    soup = BeautifulSoup(html, 'html.parser')
    structured = list(_jsonld_articles(soup))
    published, evidence = None, None
    for meta in soup.find_all('meta', attrs={'property': 'article:published_time'}):
        published = _publication(meta.get('content'))
        if published:
            evidence = 'article:published_time'
            break
    if not published:
        for item in structured:
            published = _publication(item.get('datePublished'))
            if published:
                evidence = 'JSON-LD datePublished'
                break
    if not published:
        raise ValueError('官方文章缺少带时区的发布时间')
    title_node = soup.find('meta', attrs={'property': 'og:title'})
    title = _clean_title(title_node.get('content') if title_node else '', source)
    if not title:
        title = next((_clean_title(item.get('headline'), source) for item in structured
                      if _clean_title(item.get('headline'), source)), '')
    if not title:
        title_scope = soup.find('article') or soup.find('main') or soup
        heading = title_scope.find('h1')
        title = _clean_title(heading.get_text(' ', strip=True) if heading else '', source)
    if not title:
        raise ValueError('官方文章缺少标题')
    for node in soup.select('nav, header, footer, aside, script, style, noscript, form, '
                            '[role="navigation"], [aria-hidden="true"]'):
        node.decompose()
    article = soup.find('article') or soup.find('main')
    if article is None:
        raise ValueError('官方文章缺少可核实的正文')
    paragraphs, seen = [], set()
    for paragraph in article.find_all('p'):
        text = re.sub(r'\s+', ' ', paragraph.get_text(' ', strip=True)).strip()
        linked = ' '.join(a.get_text(' ', strip=True) for a in paragraph.find_all('a'))
        if not text or text in seen or text == linked:
            continue
        seen.add(text)
        paragraphs.append(text)
        if len(paragraphs) == _MAX_PARAGRAPHS:
            break
    abstract = '\n\n'.join(paragraphs)
    if len(''.join(paragraphs)) < _MIN_BODY_CHARS:
        raise ValueError('官方文章正文不足，不能用简介代替正文')
    return dict(title=title, published=published, source_url=canonical_url,
                source_name=source.get('name', '官方'), abstract=abstract,
                content_kind='official_article', verify_article_event=True,
                event_date_evidence=f'官方文章发布元数据 {evidence}: {published}')
