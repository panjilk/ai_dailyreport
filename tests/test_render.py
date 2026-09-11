from pathlib import Path

from dailyreport.render import split_sentences, srt_time, wrap_text, font, validate_briefing


def test_srt_carries_milliseconds_without_invalid_sixty_seconds():
    assert srt_time(61.25) == '00:01:01,250'
    assert srt_time(59.9999) == '00:01:00,000'


def test_long_chinese_subtitles_preserve_all_text_and_fit():
    text = '这是一条用于检查中文换行的资讯。' * 9 + 'OpenAI 发布工具。'
    chunks = split_sentences(text, 28)
    assert ''.join(chunks) == text
    assert all(len(x) <= 28 for x in chunks)


def test_subtitle_length_boundary_never_creates_punctuation_only_speech():
    import re
    text = '新' * 28 + '。' + '报道' * 14 + '！？'
    chunks = split_sentences(text, 28)
    assert ''.join(chunks) == text
    assert all(re.search(r'[\w\u4e00-\u9fff]', x) for x in chunks)
    assert all(len(x) <= 28 for x in chunks)


def test_wrap_does_not_overflow_or_drop_long_words():
    text = '模型更新 SuperLongModelNameWithoutAnySpaces2026 新功能'
    f = font(32)
    lines = wrap_text(text, f, 250)
    assert ''.join(lines).replace(' ', '') == text.replace(' ', '')
    assert all(f.getlength(x) <= 250 for x in lines)


def test_empty_briefing_refuses_to_render():
    import pytest
    with pytest.raises(ValueError, match='资讯'):
        validate_briefing({'date': '2026-09-11', 'stories': []})


def test_missing_source_refuses_to_render():
    import pytest
    with pytest.raises(ValueError, match='source_url'):
        validate_briefing({'date': '2026-09-11', 'stories': [
            {'title': '测试', 'category': '要闻', 'narration': '测试。', 'bullets': ['测试']}
        ]})


def test_transient_speech_failure_retries_and_returns_success():
    import asyncio
    from dailyreport.render import retry_async
    attempts = []
    async def operation():
        attempts.append(1)
        if len(attempts) < 3:
            raise ConnectionError('transient')
        return 'audio'
    assert asyncio.run(retry_async(operation, delay=0)) == 'audio'
    assert len(attempts) == 3


def test_persistent_speech_failure_does_not_loop_forever():
    import asyncio
    import pytest
    from dailyreport.render import retry_async
    attempts = []
    async def operation():
        attempts.append(1)
        raise ConnectionError('persistent')
    with pytest.raises(ConnectionError):
        asyncio.run(retry_async(operation, delay=0))
    assert len(attempts) == 3
