from datetime import datetime
from copy import deepcopy
import pytest
from dailyreport.recency import SHANGHAI, enforce_recency, article_event_date
from dailyreport.collect import select_recent

NOW = datetime(2026, 9, 12, 16, tzinfo=SHANGHAI)

def story(day, title='模型更新'):
    return dict(title=title, published=day, event_date=day)

def test_today_first_and_yesterday_allowed():
    b = dict(date='2026-09-12', stories=[story('2026-09-11'), story('2026-09-12')])
    enforce_recency(b, NOW)
    assert b['stories'][0]['event_date'] == '2026-09-12'
    assert b['window_days'] == 2

@pytest.mark.parametrize('day',['2026-09-10','2026-09-13'])
def test_reject_old_and_future_event_even_with_fresh_article(day):
    s = story(day); s['published']='2026-09-12'
    with pytest.raises(ValueError, match='仅允许'):
        enforce_recency(dict(date='2026-09-12',stories=[s]), NOW)

def test_require_actual_event_date_for_import():
    with pytest.raises(ValueError, match='event_date'):
        enforce_recency(dict(date='2026-09-12',stories=[dict(title='旧闻',published='2026-09-12')]), NOW)

def test_48_hours_never_reaches_day_before_yesterday():
    now=NOW.replace(hour=1)
    rows=[dict(title=d,published=d,source_url='https://example.com/'+str(i)) for i,d in enumerate(['2026-09-10T23:59:59+08:00','2026-09-11T00:00:00+08:00','2026-09-12T00:00:00+08:00'])]
    assert len(select_recent(rows,now,48,8))==2

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
