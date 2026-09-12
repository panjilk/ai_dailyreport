"""Today-first reporting with an absolute yesterday cutoff in Beijing time."""
from datetime import datetime, timedelta, timezone, date
import re

SHANGHAI = timezone(timedelta(hours=8))


def yesterday_start(now):
    return now.astimezone(SHANGHAI).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)


def news_date(value):
    text = str(value)
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
        return date.fromisoformat(text)
    moment = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if moment.tzinfo is None:
        raise ValueError('新闻时间缺少时区')
    return moment.astimezone(SHANGHAI).date()


def enforce_recency(briefing, now):
    today = now.astimezone(SHANGHAI).date()
    oldest = yesterday_start(now).date()
    if news_date(briefing['date']) != today:
        raise ValueError('日报日期必须是北京时间今天，不能把旧稿重新作为当日日报。')
    for story in briefing.get('stories', []):
        if not story.get('event_date'):
            raise ValueError('新闻缺少 event_date，请核实模型更新或新评测实际发生日期。')
        for key in ('published', 'event_date'):
            day = news_date(story[key])
            if not oldest <= day <= today:
                raise ValueError('仅允许北京时间今天和昨天的新闻：' + story['title'])
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(story[key])):
                moment = datetime.fromisoformat(str(story[key]).replace('Z', '+00:00'))
                if moment > now:
                    raise ValueError('新闻时间不能在未来：' + story['title'])
    briefing['stories'].sort(key=lambda s: (news_date(s['event_date']), news_date(s['published'])), reverse=True)
    briefing['window_days'] = 2
    briefing.pop('window_hours', None)
    briefing['recency_policy'] = 'today_and_yesterday_only'


def article_event_date(text, published):
    """Require an explicit dated or relative-day release/evaluation; never refresh a repost."""
    published_day = news_date(published)
    date_pattern = r'(?:(20\d{2})年)?(\d{1,2})月(\d{1,2})日'
    verb = r'(?:正式发布|发布了|发布|推出|开源|上线|公布.{0,8}评测)'
    def event_follows(tail):
        match = re.match(r'([^。！？]{0,24}?)' + verb, tail)
        if not match:
            return False
        gap = match[1]
        return not re.search(r'消息|回顾|上月|去年|此前|过去|报道|\d{1,2}月\d{1,2}日', gap)
    for m in re.finditer(date_pattern, text):
        if not event_follows(text[m.end():]):
            continue
        year = int(m[1]) if m[1] else published_day.year
        event = date(year, int(m[2]), int(m[3]))
        if not m[1] and event > published_day and event.month > published_day.month:
            event = event.replace(year=year - 1)
        return event.isoformat()
    for relative in re.finditer(r'今天|今日|昨日|昨天', text):
        if event_follows(text[relative.end():]):
            return (published_day - timedelta(days=1 if relative[0] in ('昨天', '昨日') else 0)).isoformat()
    raise ValueError('无法核实模型事件或新评测日期，跳过以免新转载旧闻')
