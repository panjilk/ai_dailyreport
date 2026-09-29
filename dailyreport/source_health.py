"""订阅源连续失败记录。"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path


_health_lock = threading.RLock()


def load_health(path):
    with _health_lock:
        return _load_health(path)


def _load_health(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('顶层应为对象')
        return data, []
    except FileNotFoundError:
        return {}, []
    except (OSError, ValueError, TypeError) as exc:
        return {}, [f'来源健康记录不可用，重新计数：{exc}']


def record_result(health, name, error=None, checked=None):
    with _health_lock:
        return _record_result(health, name, error, checked)


def _record_result(health, name, error=None, checked=None):
    previous = health.get(name, {})
    if not isinstance(previous, dict):
        previous = {}
    try:
        failures = max(0, int(previous.get('consecutive_failures', 0)))
    except (ValueError, TypeError):
        failures = 0
    failures = failures + 1 if error else 0
    row = dict(consecutive_failures=failures, last_error=str(error) if error else '',
               last_checked=checked or datetime.now(timezone.utc).isoformat())
    health[name] = row
    return failures >= 3


def save_health(path, health):
    with _health_lock:
        return _save_health(path, health)


def _save_health(path, health):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(health, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
