from datetime import datetime
from copy import deepcopy
import pytest
from dailyreport.recency import SHANGHAI, enforce_recency, article_event_date
from dailyreport.collect import select_recent

NOW = datetime(2026, 9, 12, 16, tzinfo=SHANGHAI)

def story(day, title='模型更新'):
    return dict(title=title, published=day, event_date=day)

def test_recent_five_days_are_allowed_newest_first():
    b = dict(date='2026-09-12', stories=[story('2026-09-08'), story('2026-09-12')])
    enforce_recency(b, NOW)
    assert b['stories'][0]['event_date'] == '2026-09-12'
    assert b['window_days'] == 5


def test_same_priority_uses_full_published_timestamp_before_event_date():
    newer_report = story('2026-09-10', '普通行业观察甲')
    newer_report['published'] = '2026-09-12T15:30:00+08:00'
    older_report = story('2026-09-12', '普通行业观察乙')
    older_report['published'] = '2026-09-12T15:00:00+08:00'
    briefing = dict(date='2026-09-12', stories=[older_report, newer_report])

    enforce_recency(briefing, NOW)

    assert [s['title'] for s in briefing['stories']] == ['普通行业观察甲', '普通行业观察乙']


def test_same_day_published_timestamps_are_compared_across_timezones():
    local = story('2026-09-12', '普通行业观察甲')
    local['published'] = '2026-09-12T15:00:00+08:00'
    utc = story('2026-09-12', '普通行业观察乙')
    utc['published'] = '2026-09-12T07:30:00Z'
    briefing = dict(date='2026-09-12', stories=[local, utc])

    enforce_recency(briefing, NOW)

    assert [s['title'] for s in briefing['stories']] == ['普通行业观察乙', '普通行业观察甲']


def test_date_only_event_on_hourly_cutoff_day_is_allowed_but_earlier_day_is_not():
    cutoff_day = story('2026-09-11', '截点当天事件')
    cutoff_day['published'] = '2026-09-12T15:00:00+08:00'
    earlier = story('2026-09-10', '更早事件')
    earlier['published'] = '2026-09-12T15:30:00+08:00'
    briefing = dict(date='2026-09-12', stories=[earlier, cutoff_day])

    enforce_recency(briefing, NOW, hours=24)

    assert [s['title'] for s in briefing['stories']] == ['截点当天事件']
    assert briefing['window_start'] == '2026-09-11T16:00:00+08:00'
    assert briefing['window_end'] == '2026-09-12T16:00:00+08:00'
    assert briefing['window_hours'] == 24


def test_large_hour_value_is_still_capped_at_five_beijing_calendar_days():
    briefing = dict(date='2026-09-12', stories=[story('2026-09-07'), story('2026-09-08')])

    enforce_recency(briefing, NOW, hours=240)

    assert [s['event_date'] for s in briefing['stories']] == ['2026-09-08']
    assert briefing['window_start'] == '2026-09-08T00:00:00+08:00'

@pytest.mark.parametrize('day',['2026-09-07','2026-09-13'])
def test_reject_old_and_future_event_even_with_fresh_article(day):
    s = story(day); s['published']='2026-09-12'
    with pytest.raises(ValueError, match='仅允许'):
        enforce_recency(dict(date='2026-09-12',stories=[s]), NOW)


def test_edition_date_does_not_expand_search_window():
    b = dict(date='2026-08-01', stories=[story('2026-09-07'), story('2026-09-08'), story('2026-09-12')])
    enforce_recency(b, NOW)
    assert b['date'] == '2026-08-01'
    assert b['search_date'] == '2026-09-12'
    assert [s['event_date'] for s in b['stories']] == ['2026-09-12', '2026-09-08']
    assert len(b['excluded_stories']) == 1
    enforce_recency(b, NOW)
    assert len(b['excluded_stories']) == 1


def test_stale_search_date_in_input_cannot_bypass_recency():
    with pytest.raises(ValueError, match='没有可用资讯'):
        enforce_recency(dict(date='2026-08-01', search_date='2026-08-01', stories=[story('2026-08-01')]), NOW)


@pytest.mark.parametrize('text', [
    '9月12日计划发布新模型，目前尚未上线。',
    '9月12日并未发布新模型。',
    '预计9月12日正式发布新模型。',
    '9月12日将正式发布新模型。',
    '9月12日发布新模型的计划已经公布。',
    '9月12日发布了活动预告。',
    '今天回顾上月发布的模型。',
])
def test_unconfirmed_or_non_model_event_is_not_release(text):
    with pytest.raises(ValueError, match='无法核实'):
        article_event_date(text, '2026-09-12')


def test_spaced_date_and_evidence_preserved():
    from dailyreport.recency import article_event_evidence
    sentence = '2026 年 9 月 12 日正式发布 DeepSeek 新模型。'
    assert article_event_evidence(sentence, '2026-09-12', 'DeepSeek 新模型发布') == {
        'event_date': '2026-09-12', 'event_date_evidence': sentence}


def test_date_is_bound_to_named_model_in_title():
    text = '8月20日发布Claude模型。今天发布DeepSeek新模型。'
    assert article_event_date(text, '2026-09-12', 'DeepSeek 新模型发布') == '2026-09-12'
    with pytest.raises(ValueError, match='多个不同日期'):
        article_event_date('8月20日发布旧模型。今天发布新模型。', '2026-09-12')
    assert article_event_date('8月20日发布DeepSeek模型，今天发布Claude模型。', '2026-09-12', 'DeepSeek 模型发布') == '2026-08-20'


def test_preview_announcement_cannot_refresh_old_model():
    assert article_event_date('9月12日发布了活动预告。新模型早在8月20日发布。', '2026-09-12') == '2026-08-20'


def test_year_rollover():
    assert article_event_date('12 月 31 日发布新模型。', '2027-01-01') == '2026-12-31'

def test_require_actual_event_date_for_import():
    with pytest.raises(ValueError, match='event_date'):
        enforce_recency(dict(date='2026-09-12',stories=[dict(title='旧闻',published='2026-09-12')]), NOW)

def test_120_hours_never_reaches_before_five_day_window():
    now=NOW.replace(hour=1)
    rows=[dict(title=d,published=d,source_url='https://example.com/'+str(i)) for i,d in enumerate(['2026-09-07T23:59:59+08:00','2026-09-08T00:00:00+08:00','2026-09-12T00:00:00+08:00'])]
    assert len(select_recent(rows,now,120,8))==2

def test_new_report_does_not_refresh_old_release():
    assert article_event_date('9月10日正式发布DeepSeek新模型。','2026-09-12T10:00:00+08:00')=='2026-09-10'


def test_report_date_alone_is_not_event_evidence():
    with pytest.raises(ValueError, match='无法核实'):
        article_event_date('消息称这款模型已经发布，本文介绍其功能。', '2026-09-12')


def test_nested_old_date_is_not_attached_to_current_news_header():
    assert article_event_date('9月12日消息，回顾8月20日发布的模型。', '2026-09-12')=='2026-08-20'
    with pytest.raises(ValueError):
        article_event_date('今天回顾上月发布的模型。', '2026-09-12')

def test_space_separated_future_timestamp_is_rejected():
    s=story('2026-09-12');s['published']='2026-09-12 23:00:00+08:00'
    with pytest.raises(ValueError, match='未来'):
        enforce_recency(dict(date='2026-09-12',stories=[s]), NOW)
