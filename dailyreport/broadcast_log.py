"""已播新闻台账。"""

import hashlib
import json
from pathlib import Path
import unicodedata


def url_fingerprint(url, title):
    """按标题生成跨转载站点稳定的指纹；URL 仅作为兼容参数。"""
    normalized = ''.join(
        char.casefold() for char in unicodedata.normalize('NFKC', str(title or ''))
        if not char.isspace() and not unicodedata.category(char).startswith('P')
    )
    return hashlib.sha1(normalized.encode('utf-8')).hexdigest()[:16]


def _read(log_path):
    try:
        data = json.loads(Path(log_path).read_text(encoding='utf-8'))
        if not isinstance(data, list):
            raise ValueError('顶层应为列表')
        if any(not isinstance(row, dict) or 'nav_label' not in row or
               not all(isinstance(row.get(k), str) and row[k] for k in
                       ('date', 'title', 'source_url', 'fingerprint')) for row in data):
            raise ValueError('记录缺少必要字段')
        return data, []
    except FileNotFoundError:
        return [], ['已播台账不存在，按空台账处理']
    except (OSError, ValueError, TypeError) as exc:
        return [], [f'已播台账不可用，按空台账处理：{exc}']


def recent_fingerprints(log_path, editions=3):
    rows, warnings = _read(log_path)
    dates = sorted({row['date'] for row in rows}, reverse=True)[:editions]
    recent = [row for row in rows if row['date'] in dates]
    return ({row['fingerprint'] for row in recent},
            {row['source_url'] for row in recent}, warnings)


def recent_entries(log_path, editions=3):
    rows, warnings = _read(log_path)
    dates = sorted({row['date'] for row in rows}, reverse=True)[:editions]
    return [row for row in rows if row['date'] in dates], warnings


def append_edition(briefing: dict, log_path: Path):
    rows, warnings = _read(log_path)
    known = {(row['date'], row['fingerprint']) for row in rows}
    for story in briefing.get('stories', []):
        if not isinstance(story, dict):
            warnings.append('已播台账跳过格式错误的新闻')
            continue
        title, url, day = story.get('title'), story.get('source_url'), briefing.get('date')
        if not (title and url and day):
            warnings.append('已播台账跳过缺少日期、标题或链接的新闻')
            continue
        fingerprint = url_fingerprint(url, title)
        if (day, fingerprint) in known:
            continue
        rows.append(dict(date=day, nav_label=story.get('nav_label', ''), title=title,
                         source_url=url, fingerprint=fingerprint))
        known.add((day, fingerprint))
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return warnings
