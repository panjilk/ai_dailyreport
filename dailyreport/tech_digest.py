"""Run the pinned digest pipeline and adapt its evidence into news candidates.

Social posts, search snippets, and incomplete release records are deliberately
kept as review leads; the normal collector still fetches and checks RSS articles.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .recency import SHANGHAI, window_start
from .credentials import api_environment


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_TOPICS = frozenset({'llm', 'ai-agent', 'ai_models'})
TWITTER_KEYS = ('X_BEARER_TOKEN', 'TWITTERAPI_IO_KEY', 'GETX_API_KEY')
WEB_KEYS = ('TAVILY_API_KEY', 'BRAVE_API_KEY', 'BRAVE_API_KEYS')
SECRET_KEYS = TWITTER_KEYS + WEB_KEYS + ('GITHUB_TOKEN', 'GH_TOKEN')
CHANNEL_NAMES = {'RSS': 'rss', 'Twitter': 'twitter', 'GitHub': 'github', 'Web': 'web'}


def _resolve(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _load(path):
    with path.open(encoding='utf-8') as stream:
        return json.load(stream)


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def _redact(value, secrets):
    """Scrub credential values even in upstream exception strings and metadata."""
    if isinstance(value, dict):
        return {key: _redact(item, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item, secrets) for item in value]
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, '[REDACTED]')
        value = re.sub(r'(?i)(bearer\s+)[^\s"\']+', r'\1[REDACTED]', value)
        value = re.sub(r'(?i)((?:api[_-]?key|access[_-]?token|token|authorization)=)[^&\s"\']+',
                       r'\1[REDACTED]', value)
    return value


def _moment(value):
    text = str(value or '').strip()
    try:
        moment = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        moment = parsedate_to_datetime(text)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('missing timezone')
    return moment


def _url(value):
    """Return a public HTTP URL identity, ignoring only tracking parameters."""
    text = str(value or '').strip()
    if not text or re.search(r'\s|[\x00-\x1f\\]', text):
        raise ValueError('invalid URL')
    parts = urlsplit(text)
    host = (parts.hostname or '').lower()
    if parts.scheme not in ('http', 'https') or not host or parts.username or parts.password:
        raise ValueError('invalid URL')
    if '.' not in host or host.endswith(('.local', '.localhost')):
        raise ValueError('non-public URL')
    try:
        if not ipaddress.ip_address(host).is_global:
            raise ValueError('non-public URL')
    except ValueError as exc:
        if str(exc) == 'non-public URL':
            raise
        if not re.fullmatch(r'[a-z0-9.\-]+', host):
            raise ValueError('invalid hostname') from exc
    port = parts.port  # Validate malformed and out-of-range port numbers.
    host = 'x.com' if host in ('twitter.com', 'www.twitter.com', 'www.x.com') else host
    netloc = host + (f':{port}' if port and port not in (80, 443) else '')
    query = urlencode([(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
                       if not key.lower().startswith('utm_')
                       and key.lower() not in {'fbclid', 'gclid', 'ref_src'}])
    return urlunsplit((parts.scheme, netloc, parts.path.rstrip('/') or '/', query, ''))


def _profile(defaults):
    source_data = _load(defaults / 'sources.json')
    topic_data = _load(defaults / 'topics.json')
    if not isinstance(source_data, dict) or not isinstance(topic_data, dict):
        raise ValueError('invalid model-news profile')
    sources = source_data.get('sources')
    topics = topic_data.get('topics')
    if not isinstance(sources, list) or not sources or not isinstance(topics, list) or not topics:
        raise ValueError('empty or invalid model-news profile')
    if any(not isinstance(topic, dict) or topic.get('id') not in ALLOWED_TOPICS for topic in topics):
        raise ValueError('profile contains non-model topics')
    if any(not isinstance(source, dict) for source in sources):
        raise ValueError('invalid model-news sources')
    enabled = [source for source in sources if source.get('enabled', False)]
    if not enabled or any(not source.get('id') or not source.get('type')
                          or not set(source.get('topics', []))
                          or not set(source.get('topics', [])) <= ALLOWED_TOPICS for source in enabled):
        raise ValueError('profile contains invalid or non-model sources')
    return {source['id']: source for source in enabled}


def _finish(result, run_dir, secrets):
    result = _redact(result, secrets)
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        _write(run_dir / 'review-candidates.json', result['pending'])
        _write(run_dir / 'collection-status.json', result['status'])
    except OSError:
        result['errors'].append('tech-news-digest 状态及待审核线索无法保存。')
    return result


def _sanitize_files(run_dir, secrets):
    """Scrub partial files too, including an interrupted JSON document."""
    payloads, errors = {}, []
    for path in run_dir.rglob('*.json'):
        try:
            original = path.read_text(encoding='utf-8')
            try:
                payload = _redact(json.loads(original), secrets)
                _write(path, payload)
                payloads[path] = payload
            except ValueError:
                path.write_text(_redact(original, secrets), encoding='utf-8')
                errors.append('tech-news-digest 输出 JSON 无法读取：' + path.name)
        except OSError:
            errors.append('tech-news-digest 输出 JSON 无法读取或脱敏：' + path.name)
    return payloads, errors


def _raw_articles(data, channel):
    if channel == 'web':
        for topic in data.get('topics', []):
            for article in topic.get('articles', []):
                yield dict(article, source_type=channel, source_id='web-' + topic.get('topic_id', ''),
                           source_name='Web Search', topics=article.get('topics') or [topic.get('topic_id')])
    else:
        for source in data.get('sources', []):
            if source.get('status') not in (None, 'ok'):
                continue
            for article in source.get('articles', []):
                enriched = dict(article)
                enriched.update(source_type=channel, source_id=source.get('source_id', ''),
                                source_name=('@' + source.get('handle', '').lstrip('@'))
                                if channel == 'twitter' else source.get('name', ''),
                                account=source.get('handle', ''),
                                topics=article.get('topics') or source.get('topics', []))
                yield enriched


def _adapt(articles, profile, now, hours):
    start = max(now.astimezone(SHANGHAI) - timedelta(hours=hours), window_start(now))
    rows, pending, seen = [], [], set()
    rejected = {'irrelevant_topic': 0, 'invalid_url': 0, 'invalid_date': 0, 'outside_window': 0}
    # Raw Twitter leads come first, so a merged survivor cannot hide its X evidence.
    articles = sorted(articles, key=lambda item: item.get('source_type') != 'twitter')
    for article in articles:
        channel = article.get('source_type', '')
        if channel not in ('rss', 'twitter', 'github', 'web'):
            continue
        source_id = article.get('source_id', '')
        source = profile.get(source_id, {})
        topics = set(article.get('all_topics') or article.get('topics') or source.get('topics', []))
        if not topics & ALLOWED_TOPICS:
            rejected['irrelevant_topic'] += 1
            continue
        try:
            identity = _url(article.get('link') or article.get('source_url'))
        except (ValueError, TypeError):
            rejected['invalid_url'] += 1
            continue
        if identity in seen:
            continue
        title = str(article.get('title') or article.get('text') or '').strip()
        if not title:
            continue
        timestamp = (article.get('original_published') if channel == 'rss' and 'original_published' in article
                     else article.get('published_at') or article.get('date') or article.get('published') or '')
        published = ''
        try:
            moment = _moment(timestamp)
            if not start <= moment <= now:
                rejected['outside_window'] += 1
                continue
            published = moment.isoformat()
        except (ValueError, TypeError, OverflowError):
            if channel not in ('twitter', 'web'):
                rejected['invalid_date'] += 1
                continue
        seen.add(identity)
        abstract = str(article.get('body') or article.get('text') or article.get('summary')
                       or article.get('snippet') or '')
        row = {'title': title, 'published': published,
               'source_url': str(article.get('link') or article.get('source_url')),
               'source_name': article.get('source_name') or source.get('name') or source_id,
               'source_id': source_id, 'source_channel': channel, 'original_channel': channel,
               'collection_backend': 'tech-news-digest', 'abstract': abstract,
               'original_article': article, 'topics': sorted(topics & ALLOWED_TOPICS)}
        if channel == 'rss':
            row.update(requires_full_article=True, event_date=published,
                       event_date_evidence='原始 RSS published/date 字段仅证明发表日期，正文仍需核对事件发生日期。')
            # Chinese RSS goes through the existing Chinese article quality gate.
            if not re.search(r'[\u4e00-\u9fff]', title + abstract):
                row['content_kind'] = 'official_article' if source.get('official') is True else 'article'
            rows.append(row)
            continue
        if channel == 'github':
            link = urlsplit(identity)
            tag = article.get('tag_name') or link.path.rsplit('/', 1)[-1]
            unstable = re.search(r'(?:^|[\W_]|\d)(?:alpha|beta|rc|dev|nightly|preview|pre)(?:[\W_\d]|$)', tag, re.I)
            complete = (article.get('published_at') and article.get('body')
                        and article.get('draft') is False and article.get('prerelease') is False
                        and link.hostname == 'github.com'
                        and re.fullmatch(r'/[^/]+/[^/]+/releases/tag/[^/]+', link.path)
                        and not unstable)
            if complete:
                row.update(content_kind='release', event_date=published,
                           event_date_evidence='GitHub 正式 release published_at，完整发布说明，draft=false/prerelease=false。')
                rows.append(row)
                continue
            row.update(content_kind='github_candidate',
                       pending_fields=['full_release_notes', 'published_at', 'stable_release_status'],
                       review_reason='上游 release/Atom 摘要未提供完整发布说明与稳定版本证据，或版本带预发布标识。')
        elif channel == 'twitter':
            row.update(content_kind='social_post', account=article.get('account') or row['source_name'],
                       source_text=article.get('text') or title,
                       pending_fields=['original_post', 'publication_time', 'claim_verification', 'event_date'],
                       claim_status='unverified_social_statement',
                       review_reason='负责人/机构社交帖须核实原帖；投票、意向和预告不能当作已决定或已发布。')
            for key in ('poll', 'polls', 'attachments'):
                if key in article:
                    row[key] = article[key]
            if (article.get('poll') or article.get('polls') or article.get('attachments', {}).get('poll_ids')
                    or re.search(r'\bpoll\b|投票', abstract or title, re.I)):
                row['pending_fields'].append('poll_question_options_deadline')
        else:
            row.update(content_kind='web_candidate',
                       pending_fields=['full_article', 'publication_time', 'event_date', 'claim_verification'],
                       review_reason='搜索摘要及上游 date 可能仅是检索时间，须打开原文核实。')
        row.update(review_status='pending', discovered_at=now.isoformat())
        pending.append(row)
    return rows, pending, rejected


def collect_digest(config, now, hours, work_dir):
    """Run the vendored pipeline once, preserving partial successes and raw leads.

    API credentials are inherited only by the child process. Their values never
    appear in returned errors, metadata, or saved upstream JSON artifacts.
    """
    options = config.get('tech_news_digest', {})
    result = {'rows': [], 'pending': [], 'errors': [],
              'status': {'enabled': bool(options.get('enabled')), 'backend': 'tech-news-digest'}}
    if not options.get('enabled'):
        result['status']['state'] = 'disabled'
        return result
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('now must be a timezone-aware datetime')
    if isinstance(hours, bool) or not isinstance(hours, int) or hours < 1:
        raise ValueError('hours must be a positive integer')
    env = api_environment(ROOT)
    secrets = sorted({item.strip() for key in SECRET_KEYS for item in env.get(key, '').split(',') if item.strip()},
                     key=len, reverse=True)
    run_dir = Path(work_dir)
    layers = {'rss': {'state': 'pending'}, 'github': {'state': 'pending'},
              'twitter': {'state': 'skipped_missing_credentials'},
              'web': {'state': 'skipped_missing_credentials'},
              'trending': {'state': 'disabled'}, 'reddit': {'state': 'disabled'}}
    result['status']['layers'] = layers
    for channel, keys in [('twitter', TWITTER_KEYS), ('web', WEB_KEYS)]:
        if any(env.get(key, '').strip() for key in keys):
            layers[channel]['state'] = 'pending'
    active = [channel for channel in ('rss', 'github', 'twitter', 'web')
              if layers[channel]['state'] == 'pending']
    try:
        skill = _resolve(options.get('skill_dir', 'vendor/tech-news-digest'))
        defaults = _resolve(options.get('defaults_dir', 'config/tech-news-digest'))
        pipeline = skill / 'scripts' / 'run-pipeline.py'
        if not pipeline.is_file():
            raise FileNotFoundError('missing pinned pipeline')
        profile = _profile(defaults)
        timeout = int(options.get('step_timeout_seconds', 90))
        if timeout < 1:
            raise ValueError('invalid step timeout')
        run_dir.mkdir(parents=True, exist_ok=True)
        raw_dir = run_dir / 'raw'
        raw_dir.mkdir()
        state_dir = ROOT / 'outputs' / '.tech-news-digest-state'
        state_dir.mkdir(parents=True, exist_ok=True)
        output = run_dir / 'merged.json'
        meta_path = output.with_suffix('.meta.json')
        env.update(TECH_NEWS_DIGEST_STATE_DIR=str(state_dir), PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
        command = [sys.executable, str(pipeline), '--defaults', str(defaults), '--hours', str(hours),
                   '--freshness', 'pw' if hours > 24 else 'pd', '--step-timeout', str(timeout),
                   '--only', ','.join(active), '--skip', 'trending,reddit', '--reuse-dir', str(raw_dir),
                   '--output', str(output), '--debug']
        process = subprocess.run(command, cwd=str(ROOT), env=env, capture_output=True,
                                 text=True, encoding='utf-8', errors='replace',
                                 timeout=timeout + 120, shell=False)
        result['status'].update(returncode=process.returncode, output_path=str(output),
                                meta_path=str(meta_path), debug_dir=str(raw_dir))
    except (FileNotFoundError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
        result['errors'].append('tech-news-digest 配置、文件或执行失败；请检查已锁定的上游文件、专用大模型配置和运行时。')
        result['status']['state'] = 'failed'
        result['status']['reason'] = ('execution_timeout' if isinstance(exc, subprocess.TimeoutExpired)
                                     else 'required_file_missing' if isinstance(exc, FileNotFoundError)
                                     else 'configuration_or_execution_error')
        for channel in active:
            layers[channel] = {'state': 'failed', 'reason': result['status']['reason']}
        _, errors = _sanitize_files(run_dir, secrets)
        result['errors'].extend(errors)
        # Never interpolate child exceptions: they can contain API credentials.
        return _finish(result, run_dir, secrets)

    raw, meta, merged = {}, {}, {}
    # Sanitize every artifact written by upstream before it is exposed downstream.
    payloads, errors = _sanitize_files(run_dir, secrets)
    result['errors'].extend(errors)
    for path, payload in payloads.items():
        if not isinstance(payload, dict):
            result['errors'].append('tech-news-digest 输出 JSON 格式不符合接口：' + path.name)
            continue
        if path == meta_path:
            meta = payload
        elif path == output:
            merged = payload
        elif path.parent == raw_dir and path.stem in active:
            raw[path.stem] = payload

    steps = {CHANNEL_NAMES[step['name']]: step for step in meta.get('steps', [])
             if step.get('name') in CHANNEL_NAMES}
    for channel in active:
        step = steps.get(channel, {})
        data = raw.get(channel)
        state = step.get('status')
        if data is None:
            layers[channel] = {'state': 'failed', 'reason': 'missing_output'}
        elif state not in ('ok', 'error', 'timeout'):
            layers[channel] = {'state': 'failed', 'reason': 'missing_step_metadata'}
        else:
            source_list = data.get('topics' if channel == 'web' else 'sources', [])
            ok = sum(source.get('status') == 'ok' for source in source_list)
            failed = len(source_list) - ok
            layer_state = ('partial' if ok and failed else 'failed' if failed else 'ok')
            if state != 'ok':
                layer_state = 'partial' if ok else 'failed'
            layers[channel] = {'state': layer_state, 'sources_total': len(source_list),
                               'sources_ok': ok, 'items': data.get('total_articles', 0),
                               'pipeline_step': state}
        if layers[channel]['state'] in ('failed', 'partial'):
            result['errors'].append(f'tech-news-digest {channel} 采集层未完全成功，已保留可用层；请查看脱敏元数据。')
    merge_ok = meta.get('merge', {}).get('status') == 'ok' and bool(merged)
    if not merge_ok:
        result['errors'].append('tech-news-digest 合并输出失败或缺少元数据；仅保留原始层的可核验线索。')
    articles = []
    if merge_ok:
        for group in merged.get('topics', {}).values():
            articles.extend(group.get('articles', []))
    else:
        for channel in ('rss', 'github', 'web'):
            articles.extend(_raw_articles(raw.get(channel, {}), channel))
    # Merge uses title similarity and domain caps; raw X is the evidence archive.
    articles = list(_raw_articles(raw.get('twitter', {}), 'twitter')) + articles
    result['rows'], result['pending'], rejected = _adapt(articles, profile, now, hours)
    result['status']['rejected'] = rejected
    healthy = any(layers[channel]['state'] in ('ok', 'partial') for channel in active)
    result['status']['state'] = ('failed' if not healthy else 'partial'
                                if result['errors'] or process.returncode != 0 else 'ok')
    result['status'].update(rows=len(result['rows']), pending=len(result['pending']))
    return _finish(result, run_dir, secrets)
