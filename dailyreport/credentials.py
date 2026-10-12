"""Load project-local API settings without changing the parent environment."""
from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path


ALLOWED_VARIABLES = frozenset({
    'X_BEARER_TOKEN', 'TWITTERAPI_IO_KEY', 'GETX_API_KEY',
    'TAVILY_API_KEY', 'BRAVE_API_KEY', 'BRAVE_API_KEYS',
    'GITHUB_TOKEN', 'GH_TOKEN', 'TWITTER_API_BACKEND', 'WEB_SEARCH_BACKEND',
})


def api_environment(root: Path, environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Copy the environment and fill missing API settings from ``.env.local``.

    Only the named file is read. Values are literal: shell expansion, inline
    comments, and escape sequences are not interpreted. Diagnostics never
    include a setting's value or an underlying filesystem exception.
    """
    environment = dict(os.environ if environ is None else environ)
    try:
        contents = (root / '.env.local').read_text(encoding='utf-8-sig')
    except FileNotFoundError:
        return environment
    except (OSError, UnicodeError):
        raise ValueError('Unable to read project API settings from .env.local.') from None

    seen = set()
    for line_number, line in enumerate(contents.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise ValueError(f'Invalid API setting syntax at line {line_number}.')
        key, value = (part.strip() for part in line.split('=', 1))
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key):
            raise ValueError(f'Invalid API setting name at line {line_number}.')
        if key not in ALLOWED_VARIABLES:
            raise ValueError(f'Unknown API setting {key} at line {line_number}.')
        if key in seen:
            raise ValueError(f'Duplicate API setting {key} at line {line_number}.')
        seen.add(key)
        if value and (value[0] in "\"'" or value[-1] in "\"'"):
            if len(value) < 2 or value[0] not in "\"'" or value[-1] != value[0]:
                raise ValueError(f'Incomplete quoted API setting {key} at line {line_number}.')
            quote = value[0]
            value = value[1:-1]
            if quote in value:
                raise ValueError(f'Invalid quoted API setting {key} at line {line_number}.')
        if value.strip() and not environment.get(key, '').strip():
            environment[key] = value
    return environment
