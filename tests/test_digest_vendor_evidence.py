"""Exercise local vendor evidence patches without network or real credentials."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from urllib.error import HTTPError

import pytest

from dailyreport.tech_digest import _adapt


SCRIPTS = Path(__file__).resolve().parents[1] / 'vendor' / 'tech-news-digest' / 'scripts'
CUTOFF = datetime(2026, 10, 8, tzinfo=timezone.utc)
NOW = datetime(2026, 10, 12, 20, tzinfo=timezone.utc)
PUBLISHED = '2026-10-12T08:00:00Z'
LONG_TEXT = ('This is an original model announcement with concrete details. ' * 15
             + 'The complete final sentence must survive.')


class Response:
    def __init__(self, data):
        self.body = data.encode('utf-8') if isinstance(data, str) else json.dumps(data).encode('utf-8')
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


@pytest.fixture
def vendor(monkeypatch, tmp_path):
    state = tmp_path / '独立采集状态'
    monkeypatch.setenv('TECH_NEWS_DIGEST_STATE_DIR', str(state))
    monkeypatch.syspath_prepend(str(SCRIPTS))

    def load(name):
        spec = importlib.util.spec_from_file_location('vendor_evidence_' + name, SCRIPTS / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, 'time'):
            monkeypatch.setattr(module.time, 'sleep', lambda _duration: None)
        monkeypatch.setattr(module, 'urlopen', lambda *_args, **_kwargs: pytest.fail('unexpected network call'))
        return module

    return load, state


def twitter_source():
    return {'id': 'tibo', 'name': 'Tibo', 'handle': '@thsottiaux', 'priority': True, 'topics': ['llm']}


def test_vendor_caches_obey_project_state_override(vendor):
    load, state = vendor
    twitter = load('fetch-twitter')
    web = load('fetch-web')
    assert Path(twitter.ID_CACHE_PATH) == state / 'twitter-id-cache.json'
    assert Path(web.BRAVE_RATE_LIMIT_CACHE) == state / 'brave-rate-limit.json'
    assert state.is_dir()
    twitter.OfficialBackend._save_id_cache({'thsottiaux': {'id': '123', 'ts': 1}})
    assert json.loads((state / 'twitter-id-cache.json').read_text())['thsottiaux']['id'] == '123'


def test_official_x_keeps_full_note_and_poll_evidence(vendor, monkeypatch):
    load, _state = vendor
    twitter = load('fetch-twitter')
    poll = {'id': 'p1', 'duration_minutes': 1440, 'end_datetime': '2026-10-13T08:00:00Z',
            'options': [{'position': 1, 'label': 'Reset now', 'votes': 40},
                        {'position': 2, 'label': 'Keep current limits', 'votes': 30}],
            'voting_status': 'open'}
    original = {'id': 'post1', 'created_at': PUBLISHED, 'text': 'Truncated text...',
                'note_post': {'text': LONG_TEXT}, 'attachments': {'poll_ids': ['p1']},
                'public_metrics': {'like_count': 100}, 'referenced_posts': []}
    reply = dict(original, id='reply', referenced_posts=[{'type': 'replied_to', 'id': 'parent'}])
    requests = []

    def request(req, **_kwargs):
        requests.append(req)
        return Response({'data': [original, reply], 'includes': {'polls': [poll]}})

    monkeypatch.setattr(twitter, 'urlopen', request)
    result = twitter.OfficialBackend('test-token')._fetch_user_tweets(twitter_source(), CUTOFF, user_id='42')
    assert result['status'] == 'ok'
    assert len(result['articles']) == 1
    post = result['articles'][0]
    assert post['text'] == LONG_TEXT
    assert len(post['title']) == 280 and post['title'].endswith('...')
    assert post['original_post'] == original
    assert post['attachments']['poll_ids'] == ['p1']
    assert post['polls'] == [poll]
    assert post['polls'][0]['end_datetime'] == poll['end_datetime']
    assert post['polls'][0]['options'][1]['votes'] == 30
    query = parse_qs(urlsplit(requests[0].full_url).query)
    assert 'note_post' in query['post.fields'][0]
    assert 'referenced_posts' in query['post.fields'][0]
    assert 'attachments.poll_ids' in query['expansions'][0]
    assert {'options', 'end_datetime', 'voting_status'} <= set(query['poll.fields'][0].split(','))
    assert 'tweet.fields' not in query


@pytest.mark.parametrize('backend_name,envelope', [
    ('TwitterApiIoBackend', 'data'), ('GetXApiBackend', 'flat')])
def test_third_party_x_retains_full_original_post(vendor, monkeypatch, backend_name, envelope):
    load, _state = vendor
    twitter = load('fetch-twitter')
    original = {'id': 'long1', 'text': LONG_TEXT, 'createdAt': 'Mon Oct 12 08:00:00 +0000 2026',
                'url': 'https://x.com/thsottiaux/status/long1',
                'poll': {'ends_at': '2026-10-13T08:00:00Z', 'options': ['A', 'B']}}
    payload = {'tweets': [original]}
    if envelope == 'data':
        payload = {'data': payload}
    requests = []

    def request(req, **_kwargs):
        requests.append(req)
        return Response(payload)

    monkeypatch.setattr(twitter, 'urlopen', request)
    backend = getattr(twitter, backend_name)('test-api-key-long-enough')
    result = backend._fetch_user_tweets(twitter_source(), CUTOFF)
    assert result['status'] == 'ok' and len(requests) == 1
    post = result['articles'][0]
    assert post['text'] == LONG_TEXT
    assert post['original_post'] == original
    assert post['original_post']['poll']['ends_at'] == '2026-10-13T08:00:00Z'
    assert post['title'] != LONG_TEXT  # Presentation title may shorten; evidence must not.


def github_source():
    return {'id': 'transformers', 'name': 'Transformers', 'repo': 'huggingface/transformers',
            'priority': True, 'topics': ['llm']}


def test_github_rest_retains_full_notes_and_real_release_state(vendor, monkeypatch):
    load, _state = vendor
    github = load('fetch-github')
    stable = {'tag_name': 'v6.0.0', 'html_url': 'https://github.com/huggingface/transformers/releases/tag/v6.0.0',
              'published_at': PUBLISHED, 'updated_at': '2026-10-12T10:00:00Z',
              'body': LONG_TEXT, 'draft': False, 'prerelease': False}
    prerelease = dict(stable, tag_name='v7.0.0', prerelease=True,
                      html_url=stable['html_url'].replace('v6.0.0', 'v7.0.0'))
    draft = dict(stable, tag_name='v8.0.0', draft=True)
    unknown = dict(stable, tag_name='v9.0.0', html_url=stable['html_url'].replace('v6.0.0', 'v9.0.0'))
    unknown.pop('prerelease')
    requests = []

    def request(req, **_kwargs):
        requests.append(req)
        return Response([stable, prerelease, draft, unknown])

    monkeypatch.setattr(github, 'urlopen', request)
    result = github.fetch_releases_with_retry(github_source(), CUTOFF, github_token='test-token', no_cache=True)
    assert result['status'] == 'ok' and len(requests) == 1
    assert requests[0].full_url == 'https://api.github.com/repos/huggingface/transformers/releases'
    releases = result['articles']
    assert len(releases) == 3  # Draft never enters candidates.
    assert releases[0]['body'] == LONG_TEXT
    assert len(releases[0]['summary']) < len(LONG_TEXT)
    assert releases[0]['published_at'] == PUBLISHED
    assert releases[0]['date'] == '2026-10-12T08:00:00+00:00'
    assert releases[0]['tag_name'] == 'v6.0.0'
    assert releases[0]['draft'] is False and releases[0]['prerelease'] is False
    assert releases[1]['prerelease'] is True
    assert releases[2]['prerelease'] is None
    enriched = [dict(release, source_type='github', source_id='transformers') for release in releases]
    rows, pending, _rejected = _adapt(enriched, {'transformers': github_source()}, NOW, 120)
    assert len(rows) == 1 and rows[0]['abstract'] == LONG_TEXT
    assert {row['original_article']['tag_name'] for row in pending} == {'v7.0.0', 'v9.0.0'}


def test_unauthenticated_atom_is_a_lead_not_false_stable_evidence(vendor, monkeypatch):
    load, _state = vendor
    github = load('fetch-github')
    atom = '''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
        <id>tag:github.com,2008:Repository/123/v6.0.0</id><title>v6.0.0</title>
        <updated>2026-10-12T08:00:00Z</updated>
        <link href="https://github.com/huggingface/transformers/releases/tag/v6.0.0"/>
        <content type="html">Short release summary</content></entry></feed>'''
    requests = []

    def request(req, **_kwargs):
        requests.append(req)
        return Response(atom)

    monkeypatch.setattr(github, 'urlopen', request)
    result = github.fetch_releases_with_retry(github_source(), CUTOFF, github_token=None, no_cache=True)
    assert result['status'] == 'ok' and len(result['articles']) == 1
    assert requests[0].full_url.endswith('/releases.atom')
    record = dict(result['articles'][0], source_type='github', source_id='transformers')
    rows, pending, _rejected = _adapt([record], {'transformers': github_source()}, NOW, 120)
    assert rows == [] and len(pending) == 1
    assert 'stable_release_status' in pending[0]['pending_fields']


def rss_source():
    return {'id': 'google', 'name': 'Google AI', 'url': 'https://example.com/feed',
            'priority': True, 'topics': ['llm'], 'official': True}


@pytest.mark.parametrize('raw_date', ['2026-10-12', '2026-10-12T08:00:00',
                                     'Mon, 12 Oct 2026 08:00:00'])
def test_rss_parser_never_invents_source_timezone(vendor, raw_date):
    load, _state = vendor
    rss = load('fetch-rss')
    content = ('<rss><channel><item><title>Gemini model release</title>'
               '<link>https://example.com/new</link><pubDate>' + raw_date +
               '</pubDate></item></channel></rss>')
    assert rss.parse_date_regex(raw_date) is None
    assert rss.parse_feed_feedparser(content, CUTOFF, 'https://example.com/feed') == []
    assert rss.parse_feed_regex(content, CUTOFF, 'https://example.com/feed') == []


def test_rss_preserves_original_published_and_ignores_newer_updated(vendor):
    load, _state = vendor
    rss = load('fetch-rss')
    atom = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry>'
            '<title>Gemini model release</title><link href="https://example.com/new"/>'
            '<published>2026-10-10T03:00:00+08:00</published>'
            '<updated>2026-10-12T08:00:00Z</updated></entry></feed>')
    for parser in (rss.parse_feed_feedparser, rss.parse_feed_regex):
        result = parser(atom, CUTOFF, 'https://example.com/feed')
        assert result[0]['date'] == '2026-10-10T03:00:00+08:00'
        assert result[0]['original_published'] == '2026-10-10T03:00:00+08:00'


def test_rss_expanding_window_bypasses_subset_cache_and_narrowing_refilters(vendor, monkeypatch):
    load, _state = vendor
    rss = load('fetch-rss')
    rss._rss_cache = {}
    content = ('<rss><channel>'
               '<item><title>Gemini new</title><link>https://example.com/new</link>'
               '<pubDate>Mon, 12 Oct 2026 08:00:00 GMT</pubDate></item>'
               '<item><title>Gemini previous</title><link>https://example.com/previous</link>'
               '<pubDate>Sat, 10 Oct 2026 08:00:00 GMT</pubDate></item>'
               '</channel></rss>')
    requests = []

    def request(req, **_kwargs):
        requests.append(req)
        if req.get_header('If-none-match'):
            raise HTTPError(req.full_url, 304, 'Not Modified', {}, None)
        response = Response(content)
        response.headers = {'ETag': 'unchanged-feed'}
        return response

    monkeypatch.setattr(rss, 'urlopen', request)
    narrow = datetime(2026, 10, 12, 7, tzinfo=timezone.utc)
    assert len(rss.fetch_feed_with_retry(rss_source(), narrow)['articles']) == 1
    assert len(rss.fetch_feed_with_retry(rss_source(), CUTOFF)['articles']) == 2
    assert requests[1].get_header('If-none-match') is None
    narrowed = rss.fetch_feed_with_retry(rss_source(), narrow)
    assert narrowed['not_modified'] and len(narrowed['articles']) == 1


def test_adapter_rejects_raw_naive_date_even_if_normalized_date_has_timezone(vendor):
    load, _state = vendor
    rss = load('fetch-rss')
    record = {'title': 'Gemini model release', 'source_type': 'rss', 'source_id': 'google',
              'link': 'https://example.com/new', 'topics': ['llm'],
              'date': PUBLISHED, 'original_published': '2026-10-12'}
    rows, pending, rejected = _adapt([record], {'google': rss_source()}, NOW, 120)
    assert rows == [] and pending == [] and rejected['invalid_date'] == 1
