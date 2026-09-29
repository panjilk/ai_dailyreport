"""有界、按输入顺序回收的 I/O 并发工具。"""

import os
from concurrent.futures import ThreadPoolExecutor


def collection_workers(config):
    value = os.environ.get('COLLECT_CONCURRENCY', config.get('collection_concurrency', 6))
    if isinstance(value, bool) or not isinstance(value, int) and not (
            isinstance(value, str) and value.isdecimal()):
        raise ValueError('collection_concurrency 必须为1至16的整数')
    value = int(value)
    if not 1 <= value <= 16:
        raise ValueError('collection_concurrency 必须为1至16的整数')
    return value


def run_ordered(items, worker, workers, on_error=None):
    """返回与输入对应的结果；异常占据原位置，或交给 on_error 转换。"""
    if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
        raise ValueError('workers 必须为正整数')
    def resolve(future):
        try:
            return future.result()
        except Exception as exc:
            return on_error(exc) if on_error else exc
    if workers == 1:
        result = []
        for item in items:
            try:
                result.append(worker(item))
            except Exception as exc:
                result.append(on_error(exc) if on_error else exc)
        return result
    with ThreadPoolExecutor(max_workers=workers) as pool:
        indexed = [(index, pool.submit(worker, item)) for index, item in enumerate(items)]
        returned = [(index, resolve(future)) for index, future in indexed]
        return [value for _, value in sorted(returned, key=lambda pair: pair[0])]
