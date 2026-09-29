from pathlib import Path
import importlib.util

import pytest

SPEC = importlib.util.spec_from_file_location('verify_video', Path(__file__).resolve().parents[1] / 'tools' / 'verify_video.py')
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


def test_date_assertion():
    assert verify.check_date_text('事件日期 2026-09-28', '2026-09-28', ['9月28日发布模型'])[0]
    assert not verify.check_date_text('事件日期 2026-09-27', '2026-09-28')[0]
    assert not verify.check_date_text('事件日期 2026-09-28', '2026-09-28', ['9月27日发布模型'])[0]


def test_duration_tolerance():
    assert verify.duration_matches(100, 101.5)
    assert not verify.duration_matches(100, 101.501)


def test_exit_codes():
    assert verify.exit_code([], False) == 0
    assert verify.exit_code([], True) == 2
    assert verify.exit_code(['失败'], True) == 1


def test_missing_files(tmp_path):
    with pytest.raises(FileNotFoundError, match='daily.mp4'):
        verify.required_files(tmp_path)
