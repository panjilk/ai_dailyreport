"""Check configured news APIs with one small request per service, without logging keys."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dailyreport.credentials import api_environment


def _check(service, key, request):
    result = {'service': service, 'configured': bool(key)}
    if not key:
        return dict(result, state='missing_credentials')
    try:
        response = request()
        result['http_status'] = response.status_code
        if response.status_code != 200:
            return dict(result, state='http_error')
        payload = response.json()
        if not isinstance(payload, dict):
            return dict(result, state='invalid_response')
        data = payload.get('data', payload)
        items = data.get('tweets') if service == 'twitterapi.io' and isinstance(data, dict) else payload.get('results')
        if (payload.get('status') in ('error', 'failed') or payload.get('error')
                or not isinstance(items, list)):
            return dict(result, state='api_error')
        return dict(result, state='ok', returned_items=len(items))
    except requests.RequestException:
        return dict(result, state='network_error')
    except (ValueError, TypeError, KeyError):
        return dict(result, state='invalid_response')


def check_access(env):
    twitter = env.get('TWITTERAPI_IO_KEY', '')
    tavily = env.get('TAVILY_API_KEY', '')

    def check_twitter():
        return _check('twitterapi.io', twitter, lambda: requests.get(
            'https://api.twitterapi.io/twitter/user/last_tweets',
            params={'userName': 'thsottiaux', 'includeReplies': 'false'},
            headers={'X-API-Key': twitter, 'User-Agent': 'AI-DailyReport/1.0'},
            timeout=20, allow_redirects=False))

    def check_tavily():
        return _check('Tavily', tavily, lambda: requests.post(
            'https://api.tavily.com/search',
            headers={'Authorization': 'Bearer ' + tavily, 'User-Agent': 'AI-DailyReport/1.0'},
            json={'query': 'site:openai.com/news model update', 'search_depth': 'basic',
                  'max_results': 1, 'include_answer': False, 'include_raw_content': False},
            timeout=20, allow_redirects=False))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda check: check(), (check_twitter, check_tavily)))
    return {'checked_at': datetime.now(timezone.utc).isoformat(), 'services': results}


def main(argv=None):
    parser = argparse.ArgumentParser(description='小额验证新闻采集接口，不输出或记录密钥。')
    parser.add_argument('--output', type=Path, help='可选：将不含密钥的状态写入新 JSON 文件')
    args = parser.parse_args(argv)
    try:
        if args.output and args.output.exists():
            raise ValueError('状态文件已存在，请指定新文件。')
        report = check_access(api_environment(ROOT))
        encoded = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding='utf-8')
        print(encoded)
        return 0 if all(service['state'] == 'ok' for service in report['services']) else 1
    except (OSError, ValueError):
        print('接口配置或状态保存失败，请检查本地配置格式及输出路径。', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
