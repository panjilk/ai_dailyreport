"""Render source-attributed editorial cards, speech and subtitle video."""
from __future__ import annotations

import asyncio
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
import wave

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
BG, INK, MUTED, ACCENT = '#F5F3ED', '#252F32', '#727977', '#BB6244'
CATEGORIES = ['要闻', '模型发布', '开发生态', '产品应用', '技术洞察', '行业动态']
COLORS = ['#BB6244', '#C89B45', '#426C68', '#A25156', '#647792', '#7B7463']


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


def prepare_video_briefing(briefing):
    """Keep the full written report; use separate concise video copy."""
    result = deepcopy(briefing)
    for story in result['stories']:
        title = story.get('video_title') or re.split(r'[，：:]', story['title'], maxsplit=1)[0]
        bullets = story.get('video_bullets')
        if bullets is None:
            source = re.escape(story['source_name'])
            candidates = []
            for bullet in story['bullets']:
                text = re.sub(r'^(?:据)?' + source + r'[^，。]{0,35}(?:消息|报道|获悉)[，：,\s]*', '', bullet)
                for sentence in re.split(r'(?<=[。！？])', text):
                    if sentence and story['source_name'] not in sentence and len(title + sentence) <= 65:
                        candidates.append(sentence)
            bullets = candidates[:1]
            if not bullets:
                raise ValueError('请为这条新闻填写约40至60字的 video_title 和 video_bullets：' + story['title'])
        story['title'], story['bullets'] = title, bullets
        story['narration'] = canonical_narration(story)
        if re.search(r'https?://|来源|据.{0,20}(?:报道|消息)', story['narration']) or story['source_name'] in story['narration']:
            raise ValueError('视频短稿仍包含新闻来源，请编辑 video_title/video_bullets：' + title)
        if len(story['narration']) > 100:
            raise ValueError('视频短稿过长，请精简到约40至60字：' + title)
    return result


def window_label(briefing):
    if briefing.get('recency_policy') == 'today_and_yesterday_only':
        today = date.fromisoformat(briefing.get('search_date', briefing['date']))
        return f'搜查窗口：{today - timedelta(days=1):%Y年%m月%d日} — {today:%m月%d日}（北京时间）'
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
    for i, label in enumerate(['模型迭代优先', '产品与用量', '政策与行业']):
        x = i * 640
        d.rectangle((x, 84, x + 640, 150), fill='#EAE9E1')
        d.line((x, 84, x, 150), fill='#D8DAD1', width=1)
        d.text((x + 320, 113), label, anchor='mm', font=font(26), fill=INK)
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
        fitted(d, story['title'], (x + 28, y + (76 if rows >= 3 else 87)),
               cw - 80, 2 if rows >= 3 else 3, 22 if rows >= 3 else 26,
               leading=1.2 if rows >= 3 else 1.4)
    return im


def story_image(briefing, story, index, bullets=None, page_no=1, page_total=1):
    im = base_canvas(briefing, story['category'])
    d = ImageDraw.Draw(im)
    color = COLORS[CATEGORIES.index(story['category'])]
    d.rounded_rectangle((85, 208, 1835, 908), radius=32, fill='#E9E8E2')
    d.rounded_rectangle((85, 203, 1835, 902), radius=32, fill='white')
    d.text((132, 237), f"{index:02} / {len(briefing['stories']):02}   ·   " + story.get('nav_label', story['category']), font=font(25, True), fill=color)
    displayed_date = news_date(story.get('event_date', story['published'])).isoformat()
    d.text((1780, 240), '事件日期 ' + displayed_date, anchor='rt', font=font(22), fill=MUTED)
    fitted(d, story['title'], (130, 290), 1640, 1, 54, bold=True)
    size, lines = single_page_layout(story)
    y = 400
    for part in lines:
        d.ellipse((137, y + 16, 147, y + 26), fill=color)
        for line in part:
            d.text((170, y), line, font=font(size), fill=INK)
            y += size * 1.4
        y += 22
    return im


def outro_image(briefing):
    im = base_canvas(briefing)
    d = ImageDraw.Draw(im)
    d.text((94, 222), 'KEEP TRACK. THINK CLEARLY.', font=font(28), fill=ACCENT)
    d.text((86, 290), '关注模型迭代，了解 AI 新动态', font=font(66, True), fill=INK)
    d.text((92, 409), '本期播报结束，我们下期再见。', font=font(33), fill=MUTED)
    return im


def frame_with_subtitle(base, text, current, total, story_index, story_count, labels=None):
    im = base.copy()
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


def verify_word_coverage(text, words, duration):
    expected = lexical_text(text)
    actual = lexical_text(''.join(word['text'] for word in words))
    if not words or expected != actual:
        raise ValueError('配音没有完整覆盖稿件文字，停止交付以防漏读。')
    final_word_end = (words[-1]['offset'] + words[-1]['duration']) / 10_000_000
    if final_word_end > duration + 0.12:
        raise ValueError('音频在最后一个词结束前截断。')


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


async def edge_speech(jobs, voice, rate=20):
    import edge_tts
    semaphore = asyncio.Semaphore(2)

    async def one(job):
        async with semaphore:
            target = Path(job['path'])
            mp3 = target.with_suffix('.mp3')
            async def request():
                words = []
                communicate = edge_tts.Communicate(job['text'], voice, rate=f'{rate:+d}%', boundary='WordBoundary')
                with mp3.open('wb') as writer:
                    async for event in communicate.stream():
                        if event['type'] == 'audio':
                            writer.write(event['data'])
                        elif event['type'] == 'WordBoundary':
                            words.append(event)
                run_ffmpeg(['-i', str(mp3), '-ar', '24000', '-ac', '1', '-c:a', 'pcm_s16le', str(target)])
                with wave.open(str(target)) as reader:
                    duration = reader.getnframes() / reader.getframerate()
                verify_word_coverage(job['text'], words, duration)
                target.with_suffix('.words.json').write_text(json.dumps(words, ensure_ascii=False), encoding='utf-8')
            async def bounded_request():
                return await asyncio.wait_for(request(), 65)
            await retry_async(bounded_request)
    # Probe first to avoid dispatching many requests when the service is unavailable.
    await one(jobs[0])
    await asyncio.gather(*(one(job) for job in jobs[1:]))


def synthesize(jobs, directory, voice, engine, rate=20):
    if engine in ('auto', 'edge'):
        try:
            asyncio.run(edge_speech(jobs, voice, rate))
            return f'Edge TTS / {voice} / {rate:+d}%'
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
    intro = f'AI快报，本期{count}条消息。'
    scenes = [{'image': overview_image(briefing), 'units': [intro], 'label': '资讯概览', 'chapter': 0, 'bullets': []}]
    for i, story in enumerate(briefing['stories'], 1):
        pages = paginate_story(story)
        if ''.join(part for page in pages for part in page) != ''.join(story['bullets']):
            raise ValueError('摘要分页没有完整覆盖原稿。')
        for p, bullets in enumerate(pages):
            units = [canonical_narration(story)]
            scenes.append({'image': story_image(briefing, story, i, bullets, p + 1, len(pages)),
                           'units': units, 'label': story['title'], 'chapter': i,
                           'page': p + 1, 'page_count': len(pages), 'bullets': bullets})
        actual = ''.join(text for scene in scenes if scene['chapter'] == i for text in scene['units'])
        if actual != canonical_narration(story):
            raise ValueError('资讯口播未完整覆盖标题和全部摘要。')
    outro = '本期播报结束，下期再见。'
    scenes.append({'image': outro_image(briefing), 'units': [outro], 'label': '结束', 'chapter': count + 1, 'bullets': []})
    return scenes


def render(briefing: dict, output: Path, voice='zh-CN-XiaoxiaoNeural', engine='auto', rate=20, *, search_time=None) -> Path:
    briefing = prepare_briefing(briefing)
    validate_briefing(briefing)
    enforce_recency(briefing, search_time or datetime.now(SHANGHAI))
    briefing = prepare_video_briefing(briefing)
    if not isinstance(rate, int) or not -10 <= rate <= 60:
        raise ValueError('语速 rate 必须为 -10 至 60 的整数。')
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
            jobs.append({'text': sentence, 'path': str(path), 'scene': i, 'chapter': scene['chapter']})
    print(f'正在以 {rate:+d}% 语速生成 {len(jobs)} 段完整口播……', flush=True)
    engine_used = synthesize(jobs, work, voice, engine, rate)
    # Fit complete short narration to 9.7 seconds plus a 0.3 second scene pause.
    for job in jobs:
        if not 1 <= job['chapter'] <= count:
            continue
        path = Path(job['path'])
        with wave.open(str(path)) as reader:
            duration = reader.getnframes() / reader.getframerate()
        factor = duration / 9.7
        if not 0.65 <= factor <= 1.5:
            raise ValueError(f'短稿配音为{duration:.1f}秒，无法自然调整到约10秒，请重新精简或补充短稿。')
        normalized = path.with_name(path.stem + '-timed.wav')
        run_ffmpeg(['-i', str(path), '-af', f'atempo={factor:.9f},apad,atrim=duration=9.7',
                    '-ar', '24000', '-ac', '1', '-c:a', 'pcm_s16le', str(normalized)])
        normalized.replace(path)
        word_path = path.with_suffix('.words.json')
        if word_path.exists():
            words = json.loads(word_path.read_text('utf-8'))
            for word in words:
                word['offset'] = round(word['offset'] / factor)
                word['duration'] = round(word['duration'] / factor)
            word_path.write_text(json.dumps(words, ensure_ascii=False), encoding='utf-8')
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
            # Full audio determines the page's lifetime. No fixed per-story cap.
            pause = 0.08 if n + 1 < len(jobs) and jobs[n + 1]['scene'] == job['scene'] else 0.3
            if n == len(jobs) - 1:
                pause = 0.6
            target_samples = math.ceil((samples + pause * 24000) / 1000) * 1000
            unit_frames = target_samples // 1000
            writer.writeframes(frames + b'\0' * ((target_samples - samples) * 2))
            cues = subtitle_cues(job['text'], words, unit_frames)
            if ''.join(c['text'] for c in cues) != job['text']:
                raise ValueError('字幕没有完整覆盖口播。')
            for cue in cues:
                number = len(timeline)
                start, end = (cursor_frames + cue['start_frame']) / 24, (cursor_frames + cue['end_frame']) / 24
                srt.append(f'{number + 1}\n{srt_time(start)} --> {srt_time(end)}\n{cue["text"]}\n')
                image_path = work / f'frame-{number:03}.png'
                frame_with_subtitle(scenes[job['scene']]['image'], cue['text'], n + 1, len(jobs), job['chapter'], count, navigation_labels(briefing)).save(image_path)
                concat += [f"file 'frame-{number:03}.png'", 'option framerate 24', f'duration {(cue["end_frame"] - cue["start_frame"]) / 24:.9f}']
                timeline.append({'start': round(start, 4), 'end': round(end, 4), 'scene': job['scene'],
                                 'chapter': job['chapter'], 'unit': n, 'text': cue['text']})
            speech_units.append({'text': job['text'], 'scene': job['scene'], 'chapter': job['chapter'],
                                 'start': round(cursor_frames / 24, 4),
                                 'audio_end': round(cursor_frames / 24 + audio_duration, 4),
                                 'end': round((cursor_frames + unit_frames) / 24, 4),
                                 'coverage': 'word-boundary-verified' if words else 'sapi-synchronous-completion'})
            cursor_frames += unit_frames
    cursor = cursor_frames / 24
    concat += [f"file 'frame-{len(timeline) - 1:03}.png'", 'option framerate 24']
    (work / 'frames.ffconcat').write_text('\n'.join(concat) + '\n', encoding='utf-8')
    (output / 'subtitles.srt').write_text('\n'.join(srt), encoding='utf-8-sig')
    chapters = [{'title': next(s['label'] for s in scenes if s['chapter'] == chapter),
                 'start': next(t['start'] for t in timeline if t['chapter'] == chapter)} for chapter in range(count + 2)]
    pages = [{'title': scene['label'], 'chapter': scene['chapter'], 'bullets': scene['bullets'],
              'start': next(t['start'] for t in timeline if t['scene'] == i),
              'end': next(t['end'] for t in reversed(timeline) if t['scene'] == i)} for i, scene in enumerate(scenes)]
    manifest = {'duration_seconds': round(cursor, 3), 'width': W, 'height': H, 'fps': 24,
                'speech_engine': engine_used, 'speech_rate_percent': rate, 'navigation_labels': navigation_labels(briefing), 'segments': timeline,
                'speech_units': speech_units, 'chapters': chapters, 'pages': pages}
    (output / 'timeline.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    target = output / 'daily.mp4'
    temporary = output / 'daily.partial.mp4'
    print(f'正在合成 1080p 视频，预计时长 {cursor / 60:.1f} 分钟……', flush=True)
    log = run_ffmpeg(['-f', 'concat', '-safe', '0', '-i', 'frames.ffconcat', '-i', str(combined),
                     '-map', '0:v:0', '-map', '1:a:0', '-vf', f'fps=24,fade=t=in:d=0.35,fade=t=out:st={max(0, cursor - .4):.3f}:d=0.4',
                     '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'stillimage', '-crf', '20',
                     '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', '48000',
                     '-t', f'{cursor:.6f}', '-movflags', '+faststart', str(temporary)], cwd=work)
    (output / 'render.log').write_text(log, encoding='utf-8')
    temporary.replace(target)
    return target
