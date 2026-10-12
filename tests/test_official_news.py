import json
import unittest
from datetime import datetime, timezone

from dailyreport.official_news import official_article_row, official_index_links


SOURCE = {'name': 'Anthropic', 'url': 'https://www.anthropic.com/news'}
NOW = datetime(2026, 10, 12, 4, tzinfo=timezone.utc)
BODY = ('Today we are introducing a Claude model update for developers. '
        'The announcement explains the available API, deployment options, and evaluation conditions. '
        'The results apply to the published test settings and should not be generalized to every task.')


def article(metadata, body=None, title='Claude model update | Anthropic'):
    if body is None:
        body = '<article><p>' + BODY + '</p></article>'
    return f'<html><head><meta property="og:title" content="{title}">{metadata}</head><body>{body}</body></html>'


def card(path, day=None):
    stamp = f'<time>{day}</time>' if day else ''
    return f'<a href="{path}">{stamp}<h2>Claude update</h2></a>'


class OfficialIndexTests(unittest.TestCase):
    def test_filters_outside_host_duplicates_navigation_and_old_cards(self):
        html = '<main>' + ''.join([
            card('/news/latest', 'Oct 11, 2026'),
            card('https://www.anthropic.com/news/latest?utm_source=test#top', 'Oct 11, 2026'),
            card('https://example.com/news/external', 'Oct 11, 2026'),
            card('http://www.anthropic.com/news/insecure', 'Oct 11, 2026'),
            card('https://[broken/news/malformed', 'Oct 11, 2026'),
            card('/news', 'Oct 11, 2026'),
            card('/news/old', 'Sep 30, 2026'),
            card('/news/future', 'Oct 15, 2026'),
            card('/research/other', 'Oct 11, 2026'),
            '<footer>' + card('/news/footer', 'Oct 11, 2026') + '</footer>',
            '<nav>' + card('/news/navigation') + '</nav>',
        ]) + '</main>'
        self.assertEqual(official_index_links(SOURCE, html, NOW, 120),
                         ['https://www.anthropic.com/news/latest'])

    def test_missing_card_date_is_candidate_not_invented_publication(self):
        html = '<main>' + card('/news/undated') + card('/news/recent', 'Oct 11, 2026') + '</main>'
        self.assertEqual(official_index_links(SOURCE, html, NOW, 24),
                         ['https://www.anthropic.com/news/recent',
                          'https://www.anthropic.com/news/undated'])

    def test_limit_defaults_to_six_and_cannot_exceed_ten(self):
        html = '<main>' + ''.join(card(f'/news/item-{i}') for i in range(15)) + '</main>'
        self.assertEqual(len(official_index_links(SOURCE, html, NOW, 24)), 6)
        self.assertEqual(len(official_index_links(dict(SOURCE, max_articles=100), html, NOW, 24)), 10)

    def test_card_date_is_not_borrowed_from_another_item(self):
        html = '<main><ul><li>' + card('/news/old', 'Sep 30, 2026') + '</li><li>' + card('/news/undated') + '</li></ul></main>'
        self.assertEqual(official_index_links(SOURCE, html, NOW, 24),
                         ['https://www.anthropic.com/news/undated'])

    def test_date_only_prefilter_preserves_timezone_boundary_candidates(self):
        html = '<main>' + card('/news/boundary', 'Oct 10, 2026') + '</main>'
        self.assertEqual(official_index_links(SOURCE, html, NOW, 24),
                         ['https://www.anthropic.com/news/boundary'])


class OfficialArticleTests(unittest.TestCase):
    def test_publication_metadata_and_full_body_preserve_qualifiers(self):
        metadata = ('<meta property="article:published_time" content="2026-10-11T17:00:00.000Z">'
                    '<meta property="article:modified_time" content="2026-10-12T02:00:00.000Z">')
        body = '<article><nav><p>Navigation</p></nav><p>' + BODY + '</p><footer><p>Footer copy</p></footer></article>'
        result = official_article_row(SOURCE, article(metadata, body), 'https://www.anthropic.com/news/model')
        self.assertEqual(result['published'], '2026-10-11T17:00:00.000Z')
        self.assertEqual(result['title'], 'Claude model update')
        self.assertEqual(result['abstract'], BODY)
        self.assertEqual(result['content_kind'], 'official_article')
        self.assertTrue(result['verify_article_event'])
        self.assertNotIn('event_date', result)
        self.assertIn('article:published_time', result['event_date_evidence'])

    def test_jsonld_publication_and_headline_fallback(self):
        data = {'@graph': [{'@type': 'Organization', 'datePublished': '2026-10-12T00:00:00Z'},
                           {'@type': 'NewsArticle', 'headline': 'Claude API update — Anthropic',
                            'datePublished': '2026-10-11T17:00:00+00:00'}]}
        html = ('<html><head><script type="application/ld+json">' + json.dumps(data)
                + '</script></head><body><main><p>' + BODY + '</p></main></body></html>')
        result = official_article_row(SOURCE, html, 'https://www.anthropic.com/news/api')
        self.assertEqual(result['published'], '2026-10-11T17:00:00+00:00')
        self.assertEqual(result['title'], 'Claude API update')
        self.assertIn('JSON-LD datePublished', result['event_date_evidence'])

    def test_missing_timezone_is_rejected(self):
        for published in ('2026-10-11', '2026-10-11T17:00:00'):
            with self.subTest(published=published):
                with self.assertRaisesRegex(ValueError, '带时区'):
                    official_article_row(SOURCE, article(
                        f'<meta property="article:published_time" content="{published}">'),
                        'https://www.anthropic.com/news/model')

    def test_modification_date_never_substitutes_for_publication(self):
        metadata = ('<meta property="article:modified_time" content="2026-10-11T17:00:00Z">'
                    '<script type="application/ld+json">{"@type":"NewsArticle",'
                    '"dateModified":"2026-10-11T17:00:00Z"}</script>')
        with self.assertRaisesRegex(ValueError, '发布时间'):
            official_article_row(SOURCE, article(metadata), 'https://www.anthropic.com/news/model')

    def test_description_and_short_intro_cannot_replace_article(self):
        metadata = ('<meta property="article:published_time" content="2026-10-11T17:00:00Z">'
                    '<meta name="description" content="' + BODY + '">')
        for body in ('<article><p>A short introduction.</p></article>', '<div><p>' + BODY + '</p></div>'):
            with self.subTest(body=body):
                with self.assertRaisesRegex(ValueError, '正文'):
                    official_article_row(SOURCE, article(metadata, body), 'https://www.anthropic.com/news/model')

    def test_long_paragraph_is_not_cut_mid_sentence(self):
        text = BODY + ' The testing limitation remains important.' * 100
        metadata = '<meta property="article:published_time" content="2026-10-11T17:00:00Z">'
        result = official_article_row(SOURCE, article(metadata, '<article><p>' + text + '</p></article>'),
                                      'https://www.anthropic.com/news/model')
        self.assertEqual(result['abstract'], text)


if __name__ == '__main__':
    unittest.main()
