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


def test_generated_music_and_transition_clicks_are_quiet_mono_wav(tmp_path):
    from array import array
    import wave
    from dailyreport.render import generate_background_music, generate_transition_clicks
    music = tmp_path / 'music.wav'
    clicks = tmp_path / 'clicks.wav'
    generate_background_music(music, 1.5)
    generate_transition_clicks(clicks, 1.5, [0.5, 1.0])
    for path in (music, clicks):
        with wave.open(str(path), 'rb') as reader:
            assert (reader.getnchannels(), reader.getsampwidth(), reader.getframerate()) == (1, 2, 24000)
            assert reader.getnframes() == 36000
            samples = array('h', reader.readframes(reader.getnframes()))
        assert any(samples)
        assert max(abs(value) for value in samples) < 20000


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


def test_story_cards_advance_without_hiding_other_facts():
    from dailyreport.render import story_image
    story = {'title': '美团发布 LongCat-2.5-Preview 模型', 'category': '模型发布',
             'published': '2026-09-25', 'event_date': '2026-09-25',
             'source_name': 'LongCat API',
             'source_url': 'https://longcat.chat/platform/docs/ChangeLog.html',
             'bullets': ['新增图像理解能力。', '支持代码生成。', '兼容主流开发工具。']}
    briefing = {'date': '2026-09-27', 'stories': [story]}
    first = story_image(briefing, story, 1, active_bullet=0)
    last = story_image(briefing, story, 1, active_bullet=2)
    assert first.getpixel((135, 400)) != last.getpixel((135, 400))
    assert first.getpixel((135, 700)) != last.getpixel((135, 700))
    assert first.getpixel((320, 105)) != (234, 233, 225)


def test_oversized_summary_requests_rewrite_instead_of_paging_or_truncating():
    import pytest
    from dailyreport.render import paginate_story
    with pytest.raises(ValueError, match='重新总结'):
        paginate_story({'title': '长内容测试', 'bullets': ['完整内容不能截断。' * 100]})


def test_navigation_uses_model_names():
    from dailyreport.render import navigation_labels
    assert navigation_labels({'stories': [{'title': '新版本', 'nav_label': 'ChatGPT'},
                                          {'title': '新模型', 'nav_label': 'GLM'}]}) == ['概览', 'ChatGPT', 'GLM', '结束']


def test_navigation_is_visible_on_lead_in_frame():
    from PIL import Image
    from dailyreport.render import ACCENT, frame_with_navigation
    base = Image.new('RGB', (1920, 1080), 'white')
    frame = frame_with_navigation(base, 1, 4, 1, 2, ['概览', 'GPT', 'Claude', '结束'])
    assert frame.getpixel((600, 1040)) == tuple(bytes.fromhex(ACCENT.lstrip('#')))


def test_video_keeps_rich_display_copy_and_reads_complete_short_summary():
    from dailyreport.render import prepare_video_briefing, build_scene_plan
    briefing = {'date': '2026-09-19', 'stories': [{
        'title': '模型正式发布并公布完整能力说明',
        'bullets': ['第一项功能完整显示。', '第二项功能和限制也完整显示。'],
        'narration': '原始长稿。', 'category': '模型发布', 'source_name': '示例来源',
        'source_url': 'https://example.com/news', 'published': '2026-09-19',
        'video_title': '模型正式发布', 'video_bullets': ['核心能力已经上线，使用时仍需检查结果。'],
    }]}
    prepared = prepare_video_briefing(briefing)
    story = prepared['stories'][0]
    assert story['title'] == briefing['stories'][0]['title']
    assert story['bullets'] == briefing['stories'][0]['bullets']
    assert story['video_narration'] == '核心能力已经上线，使用时仍需检查结果。'
    scenes = build_scene_plan(prepared)
    assert scenes[0]['units'] == ['欢迎来到第1期的AI日报，今天是9月19日。本期1条消息。']
    assert scenes[1]['bullets'] == briefing['stories'][0]['bullets']
    assert scenes[1]['units'] == [story['video_narration']]

    prepared['edition_number'] = 12
    assert build_scene_plan(prepared)[0]['units'][0].startswith('欢迎来到第12期的AI日报')


def test_video_auto_summary_handles_long_title_with_list_separator():
    from dailyreport.render import prepare_video_briefing
    briefing = {'stories': [{
        'title': '阿里千问办公发布企业上下文、数字员工及 Agent 硬件 QwenNote A2',
        'bullets': ['企业可以统一管理知识，并让数字员工调用内部资料完成任务。'],
        'narration': '原始长稿。', 'category': '产品应用', 'source_name': 'IT之家',
        'source_url': 'https://example.com/qwen', 'published': '2026-09-22',
    }]}
    prepared = prepare_video_briefing(briefing)
    assert prepared['stories'][0]['video_narration'].startswith('企业可以统一管理知识')
    assert len(prepared['stories'][0]['video_narration']) <= 100


def test_video_auto_summary_skips_source_notice_and_reporting_boilerplate():
    from dailyreport.render import prepare_video_briefing
    briefing = {'stories': [{
        'title': '数学和人工智能咨询小组', 'nav_label': 'OpenAI',
        'bullets': [
            '官方公告原文摘录；能力与效果描述来自发布方，尚未独立复核。',
            'OpenAI正在与一个独立的数学和人工智能咨询小组合作，以指导对新兴人工智能结果的审查和沟通。',
        ],
        'narration': '原始长稿。', 'category': '行业动态', 'source_name': 'OpenAI News',
        'source_url': 'https://example.com/openai', 'published': '2026-09-22',
        'content_kind': 'official_article',
    }]}
    narration = prepare_video_briefing(briefing)['stories'][0]['video_narration']
    assert '咨询小组' in narration
    assert '原文摘录' not in narration
    assert '未经独立复核' not in narration


def test_prepare_briefing_removes_editorial_notice_from_visible_bullets():
    from dailyreport.render import prepare_briefing
    briefing = {'stories': [{
        'title': '模型能力更新',
        'bullets': [
            '英文技术博客摘录；观点与判断属于原作者，未经独立复核。',
            '模型新增工具调用能力。',
        ],
    }]}
    story = prepare_briefing(briefing)['stories'][0]
    assert story['bullets'] == ['模型新增工具调用能力。']
    assert story['narration'] == '模型能力更新。模型新增工具调用能力。'


def test_video_auto_summary_prefers_production_result_over_event_context():
    from dailyreport.render import prepare_video_briefing
    briefing = {'stories': [{
        'title': '人工智能生态系统达到生产规模', 'nav_label': 'NVIDIA',
        'bullets': [
            '官方公告原文摘录；能力与效果描述来自发布方，尚未独立复核。',
            '建设者参加了一场行业活动，讨论当地人工智能生态系统。',
            '当地开发商和企业已经准备好将基础设施投入生产使用。',
        ],
        'narration': '原始长稿。', 'category': '行业动态', 'source_name': 'NVIDIA Blog',
        'source_url': 'https://example.com/nvidia', 'published': '2026-09-22',
        'content_kind': 'official_article',
    }]}
    narration = prepare_video_briefing(briefing)['stories'][0]['video_narration']
    assert '投入生产使用' in narration
    assert '行业活动' not in narration


def test_edition_counts_from_configured_first_issue_date():
    from dailyreport.render import build_scene_plan
    briefing = {'date': '2026-09-22', 'edition_start_date': '2026-09-21', 'stories': []}
    assert build_scene_plan(briefing)[0]['units'][0].startswith('欢迎来到第2期的AI日报')


def test_english_story_routes_to_english_voice_and_new_scenes_get_lead_in():
    from dailyreport.render import (remove_tts_cue, scene_lead_in_frames,
                                    speech_voice, tts_pronunciation_text)
    jobs = [
        {'scene': 0, 'speech_language': 'zh-CN'},
        {'scene': 1, 'speech_language': 'en-US'},
        {'scene': 1, 'speech_language': 'en-US'},
    ]
    assert speech_voice(jobs[0], 'zh-CN-XiaoxiaoNeural', 'en-US-JennyNeural') == 'zh-CN-XiaoxiaoNeural'
    assert speech_voice(jobs[1], 'zh-CN-XiaoxiaoNeural', 'en-US-JennyNeural') == 'en-US-JennyNeural'
    assert [scene_lead_in_frames(jobs, i, 1.0) for i in range(3)] == [24, 24, 0]
    original = 'Grok语音升级，ChatGPT接入Word。'
    spoken = tts_pronunciation_text(original)
    assert spoken == original
    from dailyreport.render import lexical_text
    assert lexical_text(spoken) == lexical_text(original)

    words = [
        {'text': '下', 'offset': 950_000, 'duration': 2_600_000},
        {'text': '一条', 'offset': 3_550_000, 'duration': 3_900_000},
        {'text': '千问', 'offset': 12_500_000, 'duration': 3_800_000},
        {'text': '更新', 'offset': 16_300_000, 'duration': 4_500_000},
    ]
    content, trim = remove_tts_cue(words)
    assert [word['text'] for word in content] == ['千问', '更新']
    assert trim == 1.05
    assert content[0]['offset'] == 2_000_000


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
