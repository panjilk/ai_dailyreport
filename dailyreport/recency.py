"""Bounded reporting windows and deterministic ranking in Beijing time."""
from datetime import datetime, timedelta, timezone, date
import re
from .models import MODEL_NAMES, model_labels
from .topics import ai_related, news_priority

SHANGHAI = timezone(timedelta(hours=8))
RECENCY_DAYS = 5


def yesterday_start(now):
    return now.astimezone(SHANGHAI).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)


def window_start(now, days=RECENCY_DAYS):
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        raise ValueError('days must be a positive integer')
    return now.astimezone(SHANGHAI).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)


def news_date(value):
    text = str(value)
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
        return date.fromisoformat(text)
    moment = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if moment.tzinfo is None:
        raise ValueError('新闻时间缺少时区')
    return moment.astimezone(SHANGHAI).date()


def _news_moment(value):
    """Return an aware instant; date-only values mean Beijing midnight."""
    text = str(value)
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
        return datetime.fromisoformat(text).replace(tzinfo=SHANGHAI), True
    moment = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('新闻时间缺少时区')
    return moment, False


def _recency_bounds(now, hours):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('now must be a timezone-aware datetime')
    if isinstance(hours, bool) or not isinstance(hours, int) or hours < 1:
        raise ValueError('hours must be a positive integer')
    end = now.astimezone(SHANGHAI)
    return max(end - timedelta(hours=hours), window_start(end)), end


def enforce_recency(briefing, now, hours=None):
    if hours is None:
        hours = briefing.get('window_hours', RECENCY_DAYS * 24)
    oldest, end = _recency_bounds(now, hours)
    today = end.date()
    news_date(briefing['date'])  # Edition labels do not determine the search window.
    retained, excluded = [], []
    for story in briefing.get('stories', []):
        if not story.get('event_date'):
            raise ValueError('新闻缺少 event_date，请核实模型更新或新评测实际发生日期。')
        reason = None
        for key in ('published', 'event_date'):
            moment, date_only = _news_moment(story[key])
            if date_only:
                # Extracted event evidence often identifies only a Beijing
                # calendar day. Keep the cutoff day because its exact event
                # time is unknown; timestamped values remain exact below.
                if not oldest.date() <= moment.date() <= today:
                    reason = f'仅允许搜查最近{hours}小时且不早于北京时间最近5天首日零点的新闻'
            elif moment > end:
                reason = '新闻时间不能在未来'
            elif moment < oldest:
                reason = f'仅允许搜查最近{hours}小时且不早于北京时间最近5天首日零点的新闻'
        if reason:
            excluded.append({'title': story['title'], 'reason': reason})
        else:
            retained.append(story)
    if not retained:
        raise ValueError('没有可用资讯：' + '；'.join(x['reason'] + '：' + x['title'] for x in excluded))
    briefing['stories'] = retained
    briefing.setdefault('excluded_stories', []).extend(excluded)
    briefing['search_date'] = today.isoformat()
    briefing['stories'].sort(
        key=lambda s: (_news_moment(s['published'])[0], _news_moment(s['event_date'])[0]),
        reverse=True,
    )
    briefing['stories'].sort(key=news_priority)
    briefing['window_days'] = RECENCY_DAYS
    briefing['window_hours'] = hours
    briefing['window_start'] = oldest.isoformat()
    briefing['window_end'] = end.isoformat()
    briefing['recency_policy'] = 'bounded_hours'


def article_event_evidence(text, published, title='', *, scope='foundation_models'):
    """Require an explicit dated or relative-day release/evaluation; never refresh a repost."""
    published_day = news_date(published)
    date_pattern = r'(?:(?P<year>20\d{2})\s*年\s*)?(?P<month>\d{1,2})\s*月\s*(?P<day>\d{1,2})\s*日|(?P<relative>今天|今日|昨日|昨天)'
    verb = re.compile(r'发布|推出|开源|上线|公布|更新|升级|迭代|上新|开放')
    if scope == 'all_ai':
        verb = re.compile(r'发布|推出|开源|上线|公布|更新|升级|迭代|上新|开放|宣布|重置|恢复|调整|提高|降低|通过|签署|生效|实施|启动|批准|禁止|叫停|起诉|裁定|举行|召开|达成|完成|获得|回应|表示|警告|讨论|调查|任命|离职|裁员')
    uncertain = re.compile(r'计划|预计|即将|将于|将会|拟于|拟定|有望|预告|预期|可能|传闻|否认|尚未|并未|未曾|没有|不会|不再|未能|未发布|未上线|未推出|未开源|并非|并不|不打算')
    context = re.compile(r'模型|GPT|Claude|Gemini|DeepSeek|Qwen|Kimi|GLM|Llama|Grok|Mistral|评测|测评|基准', re.I)
    targets = set(model_labels(title))
    candidates = []
    for sentence in re.split(r'(?<=[。！？!?])|\n', text):
        matches = list(re.finditer(date_pattern, sentence))
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(sentence)
            tail = sentence[m.end():end]
            action = verb.search(tail)
            if not action or action.start() > 32:
                continue
            gap = tail[:action.start()]
            prefix = sentence[max(0, m.start() - 12):m.start()]
            if re.search(r'消息|回顾|上月|去年|此前|过去|报道', gap) or uncertain.search(prefix + gap + action.group()) or re.search(r'将(?:正式)?$', gap):
                continue
            if re.search(r'^(?:了)?\s*(?:活动|会议|发布会)?(?:预告|预热|计划|通知|海报|预期)', tail[action.end():]):
                continue
            evidence = sentence[:end].strip()
            # Only bind the model in this dated clause, not an earlier event.
            start = max(sentence.rfind(mark, 0, m.start()) for mark in ('，', ',', '；', ';')) + 1
            event_clause = sentence[start:end]
            related = ai_related(event_clause) if scope == 'all_ai' else context.search(event_clause) or MODEL_NAMES.search(event_clause)
            if not related or (scope != 'all_ai' and uncertain.search(event_clause)):
                continue
            mentioned = set(model_labels(event_clause))
            overlap = bool(targets & mentioned)
            if targets and mentioned and not overlap:
                continue
            if m['relative']:
                event = published_day - timedelta(days=int(m['relative'] in ('昨天', '昨日')))
            else:
                year = int(m['year'] or published_day.year)
                month, day = int(m['month']), int(m['day'])
                if not m['year'] and (month, day) > (published_day.month, published_day.day) and month > published_day.month:
                    year -= 1
                event = date(year, month, day)
            candidates.append((overlap, event.isoformat(), evidence))
    if candidates:
        best = [x for x in candidates if x[0] == max(c[0] for c in candidates)]
        if len({x[1] for x in best}) != 1:
            raise ValueError('无法核实模型事件日期：正文存在多个不同日期，需人工确认对应事件')
        return {'event_date': best[0][1], 'event_date_evidence': best[0][2]}
    raise ValueError('无法核实模型事件或新评测日期，跳过以免新转载旧闻')


def article_event_date(text, published, title=''):
    return article_event_evidence(text, published, title)['event_date']
