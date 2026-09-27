"""Render source-attributed editorial cards, speech and subtitle video."""
from __future__ import annotations

import asyncio
from array import array
from copy import deepcopy
from datetime import date, timedelta, datetime
from .recency import enforce_recency, news_date, SHANGHAI
from functools import lru_cache
from html import unescape
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlsplit
import wave

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
BG, INK, MUTED, ACCENT = '#F5F3ED', '#252F32', '#727977', '#BB6244'
CATEGORIES = ['要闻', '模型发布', '开发生态', '产品应用', '技术洞察', '行业动态']
COLORS = ['#BB6244', '#C89B45', '#426C68', '#A25156', '#647792', '#7B7463']
VIDEO_NOTICE_PREFIXES = ('论文摘要摘录', '官方版本说明摘录', '官方公告原文摘录', '英文技术博客摘录')


def _write_mono_wav(path, samples, sample_rate=24000):
    with wave.open(str(path), 'wb') as writer:
        writer.setparams((1, 2, sample_rate, 0, 'NONE', 'not compressed'))
        writer.writeframes(samples.tobytes())


def generate_background_music(path, duration, sample_rate=24000):
    """Create a quiet, original instrumental bed with soft pads and bell-like arpeggios."""
    length = max(1, math.ceil(duration * sample_rate))
    audio = array('h', [0]) * length
    chords = [
        (261.63, 329.63, 392.00, 493.88),  # Cmaj7
        (220.00, 261.63, 329.63, 392.00),  # Am7
        (174.61, 220.00, 261.63, 329.63),  # Fmaj7
        (196.00, 246.94, 293.66, 440.00),  # Gadd9
    ]
    chord_seconds = 8.0
    for i in range(length):
        t = i / sample_rate
        chord_index = int(t // chord_seconds) % len(chords)
        local = t % chord_seconds
        edge = min(1.0, local / 1.2, (chord_seconds - local) / 1.2)
        value = sum(math.sin(2 * math.pi * frequency * t) for frequency in chords[chord_index])
        # The pad stays intentionally quiet and fades across chord changes.
        audio[i] = round(32767 * 0.032 * edge * value)
    step_seconds = 0.75
    pluck_duration = 0.9
    steps = math.ceil(duration / step_seconds)
    for step in range(steps):
        start = round(step * step_seconds * sample_rate)
        chord = chords[(step // 8) % len(chords)]
        frequency = chord[(step * 3) % len(chord)] * 2
        count = min(round(pluck_duration * sample_rate), length - start)
        for j in range(max(0, count)):
            t = j / sample_rate
            envelope = math.exp(-4.8 * t)
            tone = math.sin(2 * math.pi * frequency * t) + 0.22 * math.sin(4 * math.pi * frequency * t)
            value = audio[start + j] + round(32767 * 0.09 * envelope * tone)
            audio[start + j] = max(-32768, min(32767, value))
    fade = min(round(2 * sample_rate), length // 2)
    for i in range(fade):
        gain = i / max(1, fade)
        audio[i] = round(audio[i] * gain)
        audio[-i - 1] = round(audio[-i - 1] * gain)
    _write_mono_wav(path, audio, sample_rate)


def generate_transition_clicks(path, duration, transition_times, sample_rate=24000):
    """Create a restrained two-part mouse click at each story transition."""
    length = max(1, math.ceil(duration * sample_rate))
    audio = array('h', [0]) * length
    for moment in transition_times:
        start = round(moment * sample_rate)
        for offset, amplitude in ((0.0, 0.28), (0.038, 0.15)):
            click_start = start + round(offset * sample_rate)
            click_length = round(0.045 * sample_rate)
            for j in range(click_length):
                index = click_start + j
                if not 0 <= index < length:
                    continue
                t = j / sample_rate
                envelope = math.exp(-82 * t)
                tone = math.sin(2 * math.pi * 1850 * t) + 0.35 * math.sin(2 * math.pi * 3100 * t)
                value = audio[index] + round(32767 * amplitude * envelope * tone)
                audio[index] = max(-32768, min(32767, value))
    _write_mono_wav(path, audio, sample_rate)


@lru_cache(maxsize=60)
def font(size: int, bold: bool = False):
    custom = os.environ.get('DAILYREPORT_FONT')
    paths = [custom] if custom else []
    paths += [f'C:/Windows/Fonts/{"msyhbd.ttc" if bold else "msyh.ttc"}',
              '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    for path in paths:
        if path and Path(path).is_file():
            return ImageFont.truetype(path, size)
    raise RuntimeError('找不到中文字体，请设置 DAILYREPORT_FONT 为中文字体文件路径。')


def wrap_text(text: str, face, width: int) -> list[str]:
    lines, line = [], ''
    tokens = re.findall(r'[A-Za-z0-9][A-Za-z0-9._/+%\-]*|[\s\S]', text)
    for token in tokens:
        if token == '\n':
            lines.append(line); line = ''; continue
        if line and face.getlength(line + token) > width:
            lines.append(line.rstrip()); line = ''
        if not line:
            token = token.lstrip()
        # Ordinary English names move intact to the next line. Exceptionally
        # long unbroken strings must still wrap to keep the card in bounds.
        for char in token:
            if line and face.getlength(line + char) > width:
                lines.append(line.rstrip()); line = ''
            line += char
    if line:
        lines.append(line.rstrip())
    return lines


def split_sentences(text: str, max_chars: int = 28) -> list[str]:
    if max_chars < 1:
        raise ValueError('max_chars must be positive')
    chunks, part = [], ''
    # Bind trailing punctuation to the spoken character before it. A period at
    # the line-length boundary must never become a separate silent TTS job.
    tokens = re.findall(r'\w[^\w]*|[^\w]+', text, flags=re.UNICODE)
    for token in tokens:
        if part and len(part + token) > max_chars:
            chunks.append(part); part = ''
        part += token
        if re.search(r'[。！？；]', token):
            chunks.append(part); part = ''
    if part:
        chunks.append(part)
    return chunks


def srt_time(seconds: float) -> str:
    ms = round(seconds * 1000)
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def canonical_narration(story):
    return story['title'].rstrip('。！？.!?') + '。' + ''.join(story['bullets'])


def prepare_briefing(briefing):
    result = deepcopy(briefing)
    for story in result.get('stories', []):
        if story.get('title') and story.get('bullets'):
            visible_bullets = [bullet for bullet in story['bullets']
                               if not bullet.strip().startswith(VIDEO_NOTICE_PREFIXES)]
            if visible_bullets:
                story['bullets'] = visible_bullets
            story['narration'] = canonical_narration(story)
    return result


def validate_briefing(briefing: dict):
    date.fromisoformat(briefing['date'])
    if not briefing.get('stories'):
        raise ValueError('没有可生成视频的资讯。')
    if len(briefing['stories']) > 12:
        raise ValueError('每期最多 12 条资讯。')
    for story in briefing['stories']:
        for field in ('title', 'category', 'narration', 'bullets', 'source_url', 'source_name', 'published'):
            if not story.get(field):
                raise ValueError(f'资讯缺少 {field}')
        if story['category'] not in CATEGORIES:
            raise ValueError('未知资讯分类：' + story['category'])
        if not re.match(r'^https?://[^\s/]+', story['source_url']):
            raise ValueError('source_url 必须为 HTTP(S) 来源地址')
        for source in story.get('supporting_sources', []):
            if not source.get('name') or not re.match(r'^https?://[^\s/]+', source.get('url', '')):
                raise ValueError('补充来源必须包含名称和 HTTP(S) 地址')
        if not isinstance(story['bullets'], list) or not all(isinstance(x, str) and x.strip() for x in story['bullets']):
            raise ValueError('bullets 必须为非空文字数组')
        if not re.search(r'\w', story['narration']):
            raise ValueError('narration 必须包含可朗读的文字')
        if any(re.search(r'…|\.{3}', text) for text in [story['title'], story['narration'], *story['bullets']]):
            raise ValueError('资讯包含省略号或截断文字，请补齐完整摘要后再生成。')


def single_page_layout(story):
    """Fit the complete summary on one readable page; never omit text."""
    for size in range(38, 29, -2):
        lines = [wrap_text(text, font(size), 1580) for text in story['bullets']]
        height = sum(len(part) * size * 1.4 + 22 for part in lines)
        if height <= 380:
            return size, lines
    raise ValueError('摘要超过单页容量，请将新闻重新总结为约150至220字的完整要点，不能截断或翻页。')


def paginate_story(story):
    single_page_layout(story)
    return [list(story['bullets'])]


def navigation_labels(briefing):
    return ['概览'] + [s.get('nav_label') or s['title'] for s in briefing['stories']] + ['结束']


def _clean_video_fact(text, source_name):
    text = re.sub(r'\s+', ' ', text).strip()
    source = re.escape(source_name)
    text = re.sub(r'^(?:据)?' + source + r'[^，。]{0,40}(?:消息|报道|获悉)[，：,:\s]*', '', text)
    text = re.sub(r'^(?:据|根据)[^，,。]{1,45}(?:报道|消息|透露|估计|数据|称)[，,:：\s]*', '', text)
    text = re.sub(r'^[^，,。]{1,28}(?:表示|指出|宣布|披露)[，,:：\s]*', '', text)
    text = re.sub(r'^消息人士(?:透露|称)[，,:：\s]*', '', text)
    return text.strip(' ，,')


def _compact_video_fact(text, max_chars=76):
    text = re.sub(r'\s+([，。！？；：])', r'\1', text).strip()
    if len(text) <= max_chars:
        return text.rstrip('。！？') + '。'
    # Machine-translated RSS summaries may use colons or hyphens where
    # Chinese extractive summaries use commas. Treat these as clause
    # boundaries so one malformed long sentence cannot abort an edition.
    clauses = [part.strip(' ，,；;。:：—-') for part in re.split(r'[，,；;:：—-]', text) if part.strip(' ，,；;。:：—-')]
    while len(clauses) > 1 and re.match(r'^(?:今天|本周|近日|日前|在.{0,35}(?:会上|专场上|期间|活动中))$', clauses[0]):
        clauses.pop(0)
    chosen = []
    for clause in clauses:
        candidate = '，'.join(chosen + [clause])
        if len(candidate) > max_chars:
            break
        chosen.append(clause)
        if len(candidate) >= 32:
            break
    if not chosen:
        raise ValueError('核心事实过长且缺少可压缩的完整分句')
    return '，'.join(chosen).rstrip('。！？') + '。'


def _video_fact_score(text):
    weighted_terms = (
        (r'投入生产|正式使用|量产|上线|开源', 4),
        (r'发布|推出|新增|升级|提升|超过|达到|增长|下降', 3),
        (r'支持|合作|训练|准确率|性能|能力', 1),
    )
    return sum(weight * len(re.findall(pattern, text, re.I)) for pattern, weight in weighted_terms)


def prepare_video_briefing(briefing):
    """Keep full display notes while producing a distinct, concise spoken brief."""
    result = deepcopy(briefing)
    for story in result['stories']:
        bullets = story.get('video_bullets')
        if bullets is None:
            candidates = []
            for bullet in story['bullets']:
                if bullet.strip().startswith(VIDEO_NOTICE_PREFIXES):
                    continue
                text = _clean_video_fact(bullet, story['source_name'])
                for sentence in re.split(r'(?<=[。！？])', text):
                    sentence = sentence.strip()
                    if len(sentence) >= 12 and story['source_name'] not in sentence:
                        candidates.append(sentence)
            if candidates:
                fact = max(enumerate(candidates),
                           key=lambda item: (_video_fact_score(item[1]), -item[0]))[1]
                if re.search(r'[？?]', story['title']) and re.search(r'黑客新闻|^我对', fact):
                    topic = story['title'].rstrip('？?。')
                    fact = f'文章围绕“{topic}”展开讨论。'
                bullets = [_compact_video_fact(fact)]
            else:
                bullets = []
            if not bullets:
                raise ValueError('请为这条新闻填写约40至60字的 video_title 和 video_bullets：' + story['title'])
        if not isinstance(bullets, list) or not bullets or not all(isinstance(x, str) and x.strip() for x in bullets):
            raise ValueError('video_bullets 必须是非空文字数组：' + story['title'])
        story['video_narration'] = ''.join(bullets)
        source_is_subject = story['source_name'] in story['title']
        if (re.search(r'https?://|来源|据.{0,20}(?:报道|消息)', story['video_narration']) or
                (not source_is_subject and story['source_name'] in story['video_narration'])):
            raise ValueError('视频短稿仍包含新闻来源，请编辑 video_bullets：' + story['title'])
        if len(story['video_narration']) > 100:
            raise ValueError('视频短稿过长，请精简到约40至60字：' + story['title'])
    return result


def window_label(briefing):
    if briefing.get('window_start') and briefing.get('window_end'):
        start = datetime.fromisoformat(str(briefing['window_start']).replace('Z', '+00:00')).astimezone(SHANGHAI)
        end = datetime.fromisoformat(str(briefing['window_end']).replace('Z', '+00:00')).astimezone(SHANGHAI)
        return f'搜查窗口：{start:%Y年%m月%d日 %H:%M} — {end:%m月%d日 %H:%M}（北京时间）'
    if briefing.get('recency_policy') in ('today_and_yesterday_only', 'recent_days_only'):
        today = date.fromisoformat(briefing.get('search_date', briefing['date']))
        days = max(1, int(briefing.get('window_days', 5)))
        return f'搜查窗口：{today - timedelta(days=days - 1):%Y年%m月%d日} — {today:%m月%d日}（北京时间）'
    if briefing.get('window_hours'):
        return f"采集窗口：最近 {briefing['window_hours']} 小时"
    end = date.fromisoformat(briefing['date'])
    start = end - timedelta(days=max(1, int(briefing.get('window_days', 1))) - 1)
    return f'资讯范围：{start:%Y.%m.%d} — {end:%m.%d}'


def fitted(draw, text, xy, width, max_lines, size, fill=INK, bold=False, leading=1.35):
    for chosen in range(size, 17, -2):
        face = font(chosen, bold)
        lines = wrap_text(text, face, width)
        if len(lines) <= max_lines:
            break
    else:
        raise ValueError(f'文字过长，无法清晰排版：{text[:50]}')
    for n, line in enumerate(lines):
        draw.text((xy[0], xy[1] + n * chosen * leading), line, font=face, fill=fill)
    return len(lines) * chosen * leading


def base_canvas(briefing, active=None):
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 84), fill='#FAF9F5')
    d.rounded_rectangle((62, 25, 94, 57), radius=9, fill=ACCENT)
    d.line((70, 41, 86, 41), fill='white', width=3)
    d.line((78, 33, 78, 49), fill='white', width=3)
    d.text((110, 22), 'AI DAILY', font=font(28, True), fill=INK)
    d.text((296, 26), '/  AI 综合日报', font=font(23), fill=MUTED)
    d.text((1550, 26), briefing['date'] + '   /   中文版', font=font(23), fill=MUTED)
    active_tab = (0 if active in ('要闻', '模型发布', '开发生态', '技术洞察') else
                  1 if active == '产品应用' else 2 if active == '行业动态' else None)
    for i, label in enumerate(['模型迭代优先', '产品与用量', '政策与行业']):
        x = i * 640
        selected = i == active_tab
        d.rectangle((x, 84, x + 640, 150), fill=ACCENT if selected else '#EAE9E1')
        d.line((x, 84, x, 150), fill='#D8DAD1', width=1)
        d.text((x + 320, 113), label, anchor='mm', font=font(26), fill='white' if selected else INK)
    return im


def overview_image(briefing):
    im = base_canvas(briefing)
    d = ImageDraw.Draw(im)
    d.text((90, 184), 'THE DAILY BRIEF  /  每日精选', font=font(22), fill=ACCENT)
    d.text((84, 220), briefing['date'] + ' 资讯概览', font=font(70, True), fill=ACCENT)
    d.text((90, 319), window_label(briefing) + f"     ·     {len(briefing['stories'])} 条资讯", font=font(26), fill=MUTED)
    for i, story in enumerate(briefing['stories']):
        columns = min(3, len(briefing['stories'])) if len(briefing['stories']) <= 6 else 4
        rows = math.ceil(len(briefing['stories']) / columns)
        cw, ch = 1760 / columns, 520 / rows
        x, y = 86 + (i % columns) * cw, 390 + (i // columns) * ch
        color = COLORS[i % len(COLORS)]
        d.rounded_rectangle((x, y, x + cw - 24, y + ch - 20), radius=24, fill='white')
        fitted(d, story.get('nav_label', story['category']), (x + 28, y + 24), cw - 80, 1, 32, fill=color, bold=True)
        fitted(d, story.get('display_title') or story['title'], (x + 28, y + (76 if rows >= 3 else 87)),
               cw - 80, 2 if rows >= 3 else 3, 22 if rows >= 3 else 26,
               leading=1.2 if rows >= 3 else 1.4)
    return im


def story_image(briefing, story, index, bullets=None, page_no=1, page_total=1,
                active_bullet=0):
    im = base_canvas(briefing, story['category'])
    d = ImageDraw.Draw(im)
    color = COLORS[CATEGORIES.index(story['category'])]
    d.rounded_rectangle((85, 208, 1835, 908), radius=32, fill='#E9E8E2')
    d.rounded_rectangle((85, 203, 1835, 902), radius=32, fill='white')
    d.text((132, 237), f"{index:02} / {len(briefing['stories']):02}   ·   " + story.get('nav_label', story['category']), font=font(25, True), fill=color)
    displayed_date = news_date(story.get('event_date', story['published'])).isoformat()
    d.text((1780, 240), '事件日期 ' + displayed_date, anchor='rt', font=font(22), fill=MUTED)
    fitted(d, story.get('display_title') or story['title'], (130, 290), 1640, 1, 54, bold=True)
    facts = list(bullets if bullets is not None else story['bullets'])
    if not facts:
        raise ValueError('资讯缺少画面要点')
    # Facts remain readable at all times; the current one advances with the
    # speech subtitle, so a single static slide does not linger for the story.
    card_top, card_bottom = 389, 832
    row_height = (card_bottom - card_top) / len(facts)
    for fact_index, fact in enumerate(facts):
        y0 = round(card_top + fact_index * row_height)
        y1 = round(card_top + (fact_index + 1) * row_height - 12)
        selected = fact_index == active_bullet
        d.rounded_rectangle((130, y0, 1788, y1), radius=16,
                            fill='#F7EEE8' if selected else '#F5F5F1')
        d.rounded_rectangle((130, y0, 140, y1), radius=5,
                            fill=color if selected else '#CAD0CC')
        d.text((166, y0 + 16), f'{fact_index + 1:02}', font=font(25, True),
               fill=color if selected else MUTED)
        available_height = y1 - y0 - 18
        for size in range(33, 23, -2):
            face = font(size, selected)
            lines = wrap_text(fact, face, 1490)
            if (len(lines) * size * 1.27 <= available_height and
                    not any(re.fullmatch(r'[，。！？；：,.!?;:]+', line) for line in lines)):
                break
        else:
            raise ValueError('新闻要点过长，无法放入分镜卡片，请缩短摘要。')
        line_y = y0 + (y1 - y0 - len(lines) * size * 1.27) / 2
        for line in lines:
            d.text((235, line_y), line, font=face, fill=INK)
            line_y += size * 1.27
    source = story.get('source_name', '官方来源')
    domain = urlsplit(story['source_url']).hostname or ''
    fitted(d, '来源  ' + source + ('  ·  ' + domain if domain else ''),
           (135, 853), 1640, 1, 22, fill=MUTED)
    return im


def outro_image(briefing):
    im = base_canvas(briefing)
    d = ImageDraw.Draw(im)
    d.text((94, 222), 'KEEP TRACK. THINK CLEARLY.', font=font(28), fill=ACCENT)
    d.text((86, 290), '关注模型迭代，了解 AI 新动态', font=font(66, True), fill=INK)
    d.text((92, 409), '本期播报结束，我们下期再见。', font=font(33), fill=MUTED)
    return im


def frame_with_navigation(base, current, total, story_index, story_count, labels=None):
    im = base.copy()
    d = ImageDraw.Draw(im)
    nav_count = story_count + 2
    for i in range(nav_count):
        left, right = i * W / nav_count, (i + 1) * W / nav_count
        selected = i == story_index
        d.rectangle((left, 1020, right - 2, 1073), fill=ACCENT if selected else '#E5E7DE')
        label = labels[i] if labels else ('概览' if i == 0 else '结束' if i == nav_count - 1 else '模型更新')
        face = font(19)
        if face.getlength(label) > right - left - 16:
            raise ValueError('底部导航名称过长，请填写简短的 nav_label 模型名称。')
        d.text(((left + right) / 2, 1046), label, anchor='mm', font=face, fill='white' if selected else MUTED)
    d.rectangle((0, 1074, W, 1079), fill='#DCDDD5')
    d.rectangle((0, 1074, round(W * current / total), 1079), fill=ACCENT)
    return im


def frame_with_subtitle(base, text, current, total, story_index, story_count, labels=None):
    im = frame_with_navigation(base, current, total, story_index, story_count, labels)
    d = ImageDraw.Draw(im)
    face = font(34)
    lines = wrap_text(text, face, 1680)
    if len(lines) > 2:
        raise ValueError('单条字幕过长')
    width = min(1760, max(face.getlength(line) for line in lines) + 70)
    height = len(lines) * 43 + 18
    top = 995 - height
    d.rounded_rectangle(((W - width) / 2, top, (W + width) / 2, 995), radius=14, fill='#3E4543')
    for k, line in enumerate(lines):
        d.text((W / 2, top + 7 + 43 * k), line, anchor='mt', font=face, fill='white')
    return im


def run_ffmpeg(args, cwd=None):
    proc = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-y', *args],
                          cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                          encoding='utf-8', errors='replace')
    if proc.returncode:
        raise RuntimeError('视频处理失败：\n' + proc.stderr[-3500:])
    return proc.stderr


async def retry_async(operation, attempts=3, delay=1.5):
    for attempt in range(attempts):
        try:
            return await operation()
        except Exception:
            if attempt + 1 == attempts:
                raise
            await asyncio.sleep(delay * (attempt + 1))


def lexical_text(text):
    return re.sub(r'[\W_]+', '', unescape(text), flags=re.UNICODE).casefold()


TTS_CUE = '下一条。'
TTS_PREROLL_SECONDS = 0.2


def verify_word_coverage(text, words, duration, min_preroll=0):
    expected = lexical_text(text)
    actual = lexical_text(''.join(word['text'] for word in words))
    if not words or expected != actual:
        raise ValueError('配音没有完整覆盖稿件文字，停止交付以防漏读。')
    first_word_start = words[0]['offset'] / 10_000_000
    if first_word_start + 0.01 < min_preroll:
        raise ValueError('配音首词前没有足够的起声缓冲，停止交付以防漏读。')
    final_word_end = (words[-1]['offset'] + words[-1]['duration']) / 10_000_000
    if final_word_end > duration + 0.12:
        raise ValueError('音频在最后一个词结束前截断。')


def remove_tts_cue(words, cue=TTS_CUE, preroll_seconds=TTS_PREROLL_SECONDS):
    """Remove an audible synthesis cue while retaining safe audio before the real first word."""
    cue_text = lexical_text(cue)
    consumed = ''
    boundary = 0
    while boundary < len(words) and len(consumed) < len(cue_text):
        consumed += lexical_text(words[boundary]['text'])
        boundary += 1
    if consumed != cue_text or boundary >= len(words):
        raise ValueError('无法从配音中定位起声提示词。')
    content_words = [dict(word) for word in words[boundary:]]
    first_word_start = content_words[0]['offset'] / 10_000_000
    trim_seconds = max(0, first_word_start - preroll_seconds)
    shift = round(trim_seconds * 10_000_000)
    for word in content_words:
        word['offset'] = max(0, word['offset'] - shift)
    return content_words, trim_seconds


def subtitle_cues(text, words, total_frames):
    """Subtitle division never drives speech requests; timing comes from audio."""
    chunks = split_sentences(text, 32)
    def frame_at(character):
        if words:
            count = 0
            for word in words:
                length = len(lexical_text(word['text']))
                if count + length > character:
                    seconds = (word['offset'] + word['duration'] * (character - count) / max(1, length)) / 10_000_000
                    return round(seconds * 24)
                count += length
        return round(total_frames * character / max(1, len(lexical_text(text))))
    result, character, previous = [], 0, 0
    for i, chunk in enumerate(chunks):
        character += len(lexical_text(chunk))
        end = total_frames if i == len(chunks) - 1 else frame_at(character)
        end = min(total_frames - (len(chunks) - i - 1), max(previous + 1, end))
        result.append({'start_frame': previous, 'end_frame': end, 'text': chunk})
        previous = end
    return result


def speech_voice(job, chinese_voice, english_voice):
    language = str(job.get('speech_language', '')).lower()
    return english_voice if language.startswith('en') else chinese_voice


def tts_pronunciation_text(text):
    """Keep the narrator's punctuation; script switches are not sentence breaks."""
    return text


def scene_lead_in_frames(jobs, index, seconds):
    """Give a new visual scene time to settle before its first spoken word."""
    if seconds <= 0:
        return 0
    if index and jobs[index - 1]['scene'] == jobs[index]['scene']:
        return 0
    return math.ceil(seconds * 24)


async def edge_speech(jobs, voice, rate=20, pitch_hz=0, warm=False,
                      english_voice='zh-CN-XiaoxiaoNeural'):
    import edge_tts
    semaphore = asyncio.Semaphore(2)
    # aiohttp does not trust proxy environment variables by default. The
    # workstation commonly reaches external TTS services through HTTPS_PROXY.
    tts_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')

    async def one(job):
        async with semaphore:
            target = Path(job['path'])
            mp3 = target.with_suffix('.mp3')
            async def request():
                words = []
                job_voice = speech_voice(job, voice, english_voice)
                job_pitch = 0 if job_voice == english_voice and english_voice != voice else pitch_hz
                spoken_text = tts_pronunciation_text(job['text'])
                job['tts_text'] = spoken_text
                # A spoken cue gives the neural voice real acoustic context before
                # the first news word. It is removed after synthesis while 200 ms
                # of its following pause is retained as protected preroll.
                request_text = TTS_CUE + spoken_text
                communicate = edge_tts.Communicate(
                    request_text, job_voice, rate=f'{rate:+d}%', pitch=f'{job_pitch:+d}Hz',
                    boundary='WordBoundary', proxy=tts_proxy)
                with mp3.open('wb') as writer:
                    async for event in communicate.stream():
                        if event['type'] == 'audio':
                            writer.write(event['data'])
                        elif event['type'] == 'WordBoundary':
                            words.append(event)
                words, trim_seconds = remove_tts_cue(words)
                filters = [f'atrim=start={trim_seconds:.6f}', 'asetpts=PTS-STARTPTS']
                if warm:
                    filters += ['highpass=f=62',
                                'equalizer=f=170:t=q:w=1:g=1.7',
                                'equalizer=f=4900:t=q:w=1:g=-1.4',
                                'acompressor=threshold=0.11:ratio=1.6:attack=30:release=210:makeup=1.12',
                                'loudnorm=I=-17:TP=-1.5:LRA=7']
                conversion = ['-i', str(mp3), '-ar', '24000', '-ac', '1',
                              '-af', ','.join(filters)]
                conversion += ['-c:a', 'pcm_s16le', str(target)]
                run_ffmpeg(conversion)
                with wave.open(str(target)) as reader:
                    duration = reader.getnframes() / reader.getframerate()
                verify_word_coverage(spoken_text, words, duration, TTS_PREROLL_SECONDS)
                job['tts_preroll_seconds'] = TTS_PREROLL_SECONDS
                target.with_suffix('.words.json').write_text(json.dumps(words, ensure_ascii=False), encoding='utf-8')
            async def bounded_request():
                return await asyncio.wait_for(request(), 65)
            # Edge TTS connections can drop intermittently while a long batch is
            # being synthesized; retry each segment with a longer backoff so one
            # transient disconnect does not discard the completed segments.
            await retry_async(bounded_request, attempts=6, delay=2.0)
    # Probe first to avoid dispatching many requests when the service is unavailable.
    await one(jobs[0])
    await asyncio.gather(*(one(job) for job in jobs[1:]))


def synthesize(jobs, directory, voice, engine, rate=20, pitch_hz=0, warm=False,
               english_voice='zh-CN-XiaoxiaoNeural'):
    if engine in ('auto', 'edge'):
        try:
            asyncio.run(edge_speech(jobs, voice, rate, pitch_hz, warm, english_voice))
            tone = ' / warm' if warm else ''
            uses_english = any(str(job.get('speech_language', '')).lower().startswith('en') for job in jobs)
            bilingual = f' / English {english_voice}' if uses_english and english_voice != voice else ''
            return f'Edge TTS / {voice} / {rate:+d}% / {pitch_hz:+d}Hz{tone}{bilingual}'
        except Exception as exc:
            if engine == 'edge':
                raise RuntimeError(f'联网中文配音失败（{type(exc).__name__}: {exc}）。可使用 --tts sapi 选择 Windows 本地语音。') from exc
            print(f'联网配音不可用（{type(exc).__name__}），正在使用 Windows 中文语音。', flush=True)
    if os.name != 'nt':
        raise RuntimeError('Windows 本地配音仅支持 Windows；请恢复联网语音连接。')
    manifest = directory / 'speech-jobs.json'
    manifest.write_text(json.dumps(jobs, ensure_ascii=False), encoding='utf-8')
    for job in jobs:
        Path(job['path']).with_suffix('.words.json').unlink(missing_ok=True)
    script = Path(__file__).with_name('speech.ps1')
    shell = shutil.which('pwsh') or shutil.which('powershell.exe')
    if not shell:
        raise RuntimeError('找不到 PowerShell，无法调用 Windows 本地语音。')
    process = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                              '-File', str(script), '-Manifest', str(manifest), '-Rate', str(round(rate / 10))], capture_output=True,
                             text=True, encoding='utf-8', errors='replace', timeout=max(180, len(jobs) * 15))
    if process.returncode:
        raise RuntimeError('Windows 中文配音失败：' + process.stderr[-2000:])
    return 'Windows SAPI / ' + process.stdout.strip() + f' / rate {round(rate / 10)}'


def build_scene_plan(briefing):
    count = len(briefing['stories'])
    report_date = date.fromisoformat(briefing['date'])
    edition = briefing.get('edition_number')
    if edition is None:
        start_raw = briefing.get('edition_start_date')
        edition = (report_date - date.fromisoformat(start_raw)).days + 1 if start_raw else 1
    if isinstance(edition, bool) or not isinstance(edition, int) or edition < 1:
        raise ValueError('edition_number 必须为正整数，日报日期不能早于 edition_start_date。')
    intro = (f'欢迎来到第{edition}期的AI日报，今天是{report_date.month}月{report_date.day}日。'
             f'本期{count}条消息。')
    scenes = [{'image': overview_image(briefing), 'units': [intro], 'label': '资讯概览',
               'chapter': 0, 'bullets': [], 'speech_language': 'zh-CN'}]
    for i, story in enumerate(briefing['stories'], 1):
        pages = paginate_story(story)
        if ''.join(part for page in pages for part in page) != ''.join(story['bullets']):
            raise ValueError('摘要分页没有完整覆盖原稿。')
        for p, bullets in enumerate(pages):
            units = [story['video_narration']] if p == 0 else []
            scenes.append({'image': story_image(briefing, story, i, bullets, p + 1, len(pages)),
                           'units': units, 'label': story['title'], 'chapter': i,
                           'page': p + 1, 'page_count': len(pages), 'bullets': bullets,
                           'speech_language': story.get('speech_language') or
                                              story.get('summary_language') or
                                              story.get('language') or 'zh-CN'})
        actual = ''.join(text for scene in scenes if scene['chapter'] == i for text in scene['units'])
        if actual != story['video_narration']:
            raise ValueError('资讯口播没有完整覆盖视频总结。')
    outro = '本期播报结束，下期再见。'
    scenes.append({'image': outro_image(briefing), 'units': [outro], 'label': '结束',
                   'chapter': count + 1, 'bullets': [], 'speech_language': 'zh-CN'})
    return scenes


def render(briefing: dict, output: Path, voice='zh-CN-XiaoxiaoNeural', engine='auto', rate=10,
           *, pitch_hz=-8, warm=True, english_voice='zh-CN-XiaoxiaoNeural',
           scene_lead_in_seconds=0.25, background_music_volume=0.42,
           transition_click_volume=0.32, search_time=None) -> Path:
    briefing = prepare_briefing(briefing)
    validate_briefing(briefing)
    enforce_recency(briefing, search_time or datetime.now(SHANGHAI))
    briefing = prepare_video_briefing(briefing)
    if not isinstance(rate, int) or not -10 <= rate <= 60:
        raise ValueError('语速 rate 必须为 -10 至 60 的整数。')
    if isinstance(pitch_hz, bool) or not isinstance(pitch_hz, int) or not -20 <= pitch_hz <= 20:
        raise ValueError('音高 pitch_hz 必须为 -20 至 20 的整数。')
    if isinstance(scene_lead_in_seconds, bool) or not isinstance(scene_lead_in_seconds, (int, float)) or not 0 <= scene_lead_in_seconds <= 2:
        raise ValueError('场景开口缓冲必须为0至2秒。')
    if isinstance(background_music_volume, bool) or not isinstance(background_music_volume, (int, float)) or not 0 <= background_music_volume <= 1:
        raise ValueError('背景音乐音量必须为0至1。')
    if isinstance(transition_click_volume, bool) or not isinstance(transition_click_volume, (int, float)) or not 0 <= transition_click_volume <= 1:
        raise ValueError('切换音效音量必须为0至1。')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = output / 'assets'
    work.mkdir(exist_ok=True)
    count = len(briefing['stories'])
    scenes = build_scene_plan(briefing)
    # Check navigation before spending time on speech generation.
    frame_with_subtitle(scenes[0]['image'], '预览', 0, 1, 0, count, navigation_labels(briefing))
    scenes[0]['image'].save(output / 'cover.png')
    script = []
    for chapter in range(count + 2):
        pages = [scene for scene in scenes if scene['chapter'] == chapter]
        script.append(pages[0]['label'] + '\n' + ''.join(text for page in pages for text in page['units']))
    (output / 'script.txt').write_text('\n\n'.join(script), encoding='utf-8')
    jobs = []
    for i, scene in enumerate(scenes):
        scene['image'].save(work / f'scene-{i:02}.png')
        for sentence in scene['units']:
            number = len(jobs)
            path = work / f'speech-{number:03}.wav'
            jobs.append({'text': sentence, 'path': str(path), 'scene': i,
                         'chapter': scene['chapter'],
                         'speech_language': scene.get('speech_language', 'zh-CN')})
    print(f'正在以 {rate:+d}% 语速生成 {len(jobs)} 段完整口播……', flush=True)
    engine_used = synthesize(jobs, work, voice, engine, rate, pitch_hz, warm, english_voice)
    print(f'配音完成：{engine_used}', flush=True)
    cursor_frames, srt, concat, timeline, speech_units = 0, [], ['ffconcat version 1.0'], [], []
    combined = output / 'narration.wav'
    with wave.open(str(combined), 'wb') as writer:
        writer.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        for n, job in enumerate(jobs):
            with wave.open(job['path'], 'rb') as reader:
                if (reader.getnchannels(), reader.getsampwidth(), reader.getframerate()) != (1, 2, 24000):
                    raise RuntimeError('配音音频格式不一致。')
                frames = reader.readframes(reader.getnframes())
                if not frames:
                    raise RuntimeError('配音生成了空音频。')
            samples = len(frames) // 2
            audio_duration = samples / 24000
            word_file = Path(job['path']).with_suffix('.words.json')
            words = json.loads(word_file.read_text('utf-8')) if word_file.exists() else []
            if engine_used.startswith('Edge'):
                verify_word_coverage(job['text'], words, audio_duration)
            # Show each new page before speech begins so players and Bluetooth
            # devices cannot mask the first syllable during the visual change.
            lead_frames = scene_lead_in_frames(jobs, n, scene_lead_in_seconds)
            lead_samples = lead_frames * 1000
            if lead_frames:
                number = len(timeline)
                start, end = cursor_frames / 24, (cursor_frames + lead_frames) / 24
                image_path = work / f'frame-{number:03}.png'
                frame_with_navigation(
                    scenes[job['scene']]['image'], n, len(jobs), job['chapter'], count,
                    navigation_labels(briefing),
                ).save(image_path)
                concat += [f"file 'frame-{number:03}.png'", 'option framerate 24',
                           f'duration {lead_frames / 24:.9f}']
                timeline.append({'start': round(start, 4), 'end': round(end, 4),
                                 'scene': job['scene'], 'chapter': job['chapter'],
                                 'unit': n, 'text': '', 'lead_in': True})
            # Full audio determines the page's lifetime. No fixed per-story cap.
            pause = 0.08 if n + 1 < len(jobs) and jobs[n + 1]['scene'] == job['scene'] else 0.3
            if n == len(jobs) - 1:
                pause = 0.6
            target_samples = math.ceil((samples + pause * 24000) / 1000) * 1000
            unit_frames = target_samples // 1000
            writer.writeframes(b'\0' * (lead_samples * 2) + frames +
                               b'\0' * ((target_samples - samples) * 2))
            cues = subtitle_cues(job['text'], words, unit_frames)
            if ''.join(c['text'] for c in cues) != job['text']:
                raise ValueError('字幕没有完整覆盖口播。')
            for cue_index, cue in enumerate(cues):
                number = len(timeline)
                start = (cursor_frames + lead_frames + cue['start_frame']) / 24
                end = (cursor_frames + lead_frames + cue['end_frame']) / 24
                srt.append(f'{len(srt) + 1}\n{srt_time(start)} --> {srt_time(end)}\n{cue["text"]}\n')
                image_path = work / f'frame-{number:03}.png'
                scene = scenes[job['scene']]
                focus = None
                image = scene['image']
                if scene['bullets']:
                    focus = round(cue_index * (len(scene['bullets']) - 1) / max(1, len(cues) - 1))
                    image = story_image(briefing, briefing['stories'][job['chapter'] - 1],
                                        job['chapter'], scene['bullets'], scene['page'],
                                        scene['page_count'], active_bullet=focus)
                frame_with_subtitle(image, cue['text'], n + 1, len(jobs), job['chapter'], count, navigation_labels(briefing)).save(image_path)
                concat += [f"file 'frame-{number:03}.png'", 'option framerate 24', f'duration {(cue["end_frame"] - cue["start_frame"]) / 24:.9f}']
                timeline.append({'start': round(start, 4), 'end': round(end, 4), 'scene': job['scene'],
                                 'chapter': job['chapter'], 'unit': n, 'text': cue['text'],
                                 'focus_bullet': focus})
            speech_units.append({'text': job['text'], 'scene': job['scene'], 'chapter': job['chapter'],
                                 'start': round(cursor_frames / 24, 4),
                                 'audio_start': round((cursor_frames + lead_frames) / 24, 4),
                                 'audio_end': round((cursor_frames + lead_frames) / 24 + audio_duration, 4),
                                 'end': round((cursor_frames + lead_frames + unit_frames) / 24, 4),
                                  'speech_language': job.get('speech_language', 'zh-CN'),
                                  'tts_text': job.get('tts_text', job['text']),
                                  'tts_preroll_seconds': job.get('tts_preroll_seconds', 0),
                                  'coverage': 'word-boundary-verified' if words else 'sapi-synchronous-completion'})
            cursor_frames += lead_frames + unit_frames
    cursor = cursor_frames / 24
    concat += [f"file 'frame-{len(timeline) - 1:03}.png'", 'option framerate 24']
    (work / 'frames.ffconcat').write_text('\n'.join(concat) + '\n', encoding='utf-8')
    (output / 'subtitles.srt').write_text('\n'.join(srt), encoding='utf-8-sig')
    chapters = [{'title': next(s['label'] for s in scenes if s['chapter'] == chapter),
                 'start': next(t['start'] for t in timeline if t['chapter'] == chapter)} for chapter in range(count + 2)]
    pages = [{'title': scene['label'], 'chapter': scene['chapter'], 'bullets': scene['bullets'],
              'start': next(t['start'] for t in timeline if t['scene'] == i),
              'end': next(t['end'] for t in reversed(timeline) if t['scene'] == i)} for i, scene in enumerate(scenes)]
    music = output / 'background_music.wav'
    clicks = output / 'transition_clicks.wav'
    transition_times = [chapter['start'] for chapter in chapters[1:count + 1]]
    generate_background_music(music, cursor)
    generate_transition_clicks(clicks, cursor, transition_times)
    manifest = {'duration_seconds': round(cursor, 3), 'width': W, 'height': H, 'fps': 24,
                'speech_engine': engine_used, 'speech_rate_percent': rate,
                'speech_pitch_hz': pitch_hz, 'speech_warmth': bool(warm),
                'english_voice': english_voice, 'scene_lead_in_seconds': scene_lead_in_seconds,
                'background_music': 'original generated instrumental',
                'background_music_volume': background_music_volume,
                'transition_click_volume': transition_click_volume,
                'transition_click_times': transition_times,
                'navigation_labels': navigation_labels(briefing), 'segments': timeline,
                'speech_units': speech_units, 'chapters': chapters, 'pages': pages}
    (output / 'timeline.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    target = output / 'daily.mp4'
    temporary = output / 'daily.partial.mp4'
    print(f'正在合成 1080p 视频，预计时长 {cursor / 60:.1f} 分钟……', flush=True)
    audio_filter = (
        f'[1:a]aresample=48000,asplit=2[narration_mix][narration_sidechain];'
        f'[2:a]aresample=48000,volume={background_music_volume:.3f}[music];'
        f'[music][narration_sidechain]sidechaincompress=threshold=0.018:ratio=6:attack=20:release=450[ducked];'
        f'[3:a]aresample=48000,volume={transition_click_volume:.3f}[clicks];'
        f'[narration_mix][ducked][clicks]amix=inputs=3:normalize=0:dropout_transition=0,'
        f'loudnorm=I=-16:TP=-1.5:LRA=11[audio]')
    log = run_ffmpeg(['-f', 'concat', '-safe', '0', '-i', 'frames.ffconcat',
                     '-i', str(combined), '-i', str(music), '-i', str(clicks),
                     '-filter_complex', audio_filter, '-map', '0:v:0', '-map', '[audio]',
                     '-vf', f'fps=24,fade=t=in:d=0.35,fade=t=out:st={max(0, cursor - .4):.3f}:d=0.4',
                     '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'stillimage', '-crf', '20',
                     '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-ar', '48000',
                     '-t', f'{cursor:.6f}', '-movflags', '+faststart', str(temporary)], cwd=work)
    (output / 'render.log').write_text(log, encoding='utf-8')
    temporary.replace(target)
    return target
