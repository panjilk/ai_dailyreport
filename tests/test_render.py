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


def test_wrap_keeps_english_model_names_whole_when_word_fits():
    f = font(32)
    lines = wrap_text('人工智能 OpenAI 研究', f, int(f.getlength('人工智能 Ope')))
    assert any('OpenAI' in line for line in lines)
    assert ''.join(lines).replace(' ', '') == '人工智能OpenAI研究'


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


def test_complete_model_summary_fits_exactly_one_page():
    from dailyreport.render import paginate_story, single_page_layout
    bullets = ['新版本提升了模型的推理与代码能力，开发者可以通过官方接口使用。',
               '厂商公布了基准测试结果，测试条件和工具配置会影响实际表现。',
               '目前缺少独立复测，复杂任务仍需检查结果，不能将自测成绩视为所有场景的保证。']
    story = {'title': '模型版本更新', 'bullets': bullets}
    assert paginate_story(story) == [bullets]
    size, lines = single_page_layout(story)
    assert size >= 30
    assert sum(len(x) * size * 1.4 + 22 for x in lines) <= 380


def test_oversized_summary_requests_rewrite_instead_of_paging_or_truncating():
    import pytest
    from dailyreport.render import paginate_story
    with pytest.raises(ValueError, match='重新总结'):
        paginate_story({'title': '长内容测试', 'bullets': ['完整内容不能截断。' * 100]})


def test_navigation_uses_model_names():
    from dailyreport.render import navigation_labels
    assert navigation_labels({'stories': [{'title': '新版本', 'nav_label': 'ChatGPT'},
                                          {'title': '新模型', 'nav_label': 'GLM'}]}) == ['概览', 'ChatGPT', 'GLM', '来源']


def test_every_displayed_summary_point_is_in_the_spoken_transcript():
    from dailyreport.render import canonical_narration
    story = {'title': '模型正式发布', 'bullets': ['第一项功能。', '第二项功能。', '最后一项限制必须读完。'], 'narration': '旧的半截稿子'}
    assert canonical_narration(story) == '模型正式发布。第一项功能。第二项功能。最后一项限制必须读完。'


def test_speech_verification_rejects_a_missing_final_word():
    from dailyreport.render import verify_word_coverage
    import pytest
    with pytest.raises(ValueError, match='配音.*完整'):
        verify_word_coverage('完整内容必须读完。', [{'text': '完整内容', 'offset': 0, 'duration': 10000000}], 3)


def test_speech_verification_accepts_all_words_and_checks_audio_tail():
    from dailyreport.render import verify_word_coverage
    import pytest
    words = [{'text': '完整内容', 'offset': 1000000, 'duration': 10000000},
             {'text': '必须读完', 'offset': 12000000, 'duration': 10000000}]
    verify_word_coverage('完整内容，必须读完。', words, 2.3)
    with pytest.raises(ValueError, match='音频'):
        verify_word_coverage('完整内容，必须读完。', words, 1.5)


def test_subtitle_cues_preserve_entire_sentence_and_hold_the_last_word():
    from dailyreport.render import subtitle_cues
    text = '这是完整新闻，讲清楚事件、细节和限制，最后一句话也必须全部读完。'
    cues = subtitle_cues(text, [], 360)
    assert ''.join(c['text'] for c in cues) == text
    assert cues[0]['start_frame'] == 0
    assert cues[-1]['end_frame'] == 360
    assert all(c['end_frame'] > c['start_frame'] for c in cues)
    assert all(cues[i-1]['end_frame'] == cues[i]['start_frame'] for i in range(1,len(cues)))
