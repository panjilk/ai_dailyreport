"""Render source-attributed editorial cards, speech and subtitle video."""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from functools import lru_cache
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
    for char in text:
        if char == '\n':
            lines.append(line); line = ''; continue
        if line and face.getlength(line + char) > width:
            lines.append(line.rstrip()); line = char.lstrip()
        else:
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
        if not isinstance(story['bullets'], list) or not all(isinstance(x, str) and x.strip() for x in story['bullets']):
            raise ValueError('bullets 必须为非空文字数组')
        if not re.search(r'\w', story['narration']):
            raise ValueError('narration 必须包含可朗读的文字')


def window_label(briefing):
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
    d.text((296, 26), '/  人工智能日报', font=font(23), fill=MUTED)
    d.text((1550, 26), briefing['date'] + '   /   中文版', font=font(23), fill=MUTED)
    for i, category in enumerate(CATEGORIES):
        x = i * 320
        selected = active == category
        d.rectangle((x, 84, x + 320, 150), fill=COLORS[i] if selected else '#EAE9E1')
        d.line((x, 84, x, 150), fill='#D8DAD1', width=1)
        d.text((x + 160, 113), category, anchor='mm', font=font(26, selected), fill='white' if selected else INK)
    return im


def overview_image(briefing):
    im = base_canvas(briefing)
    d = ImageDraw.Draw(im)
    d.text((90, 184), 'THE DAILY BRIEF  /  每日精选', font=font(22), fill=ACCENT)
    d.text((84, 220), briefing['date'] + ' 资讯概览', font=font(70, True), fill=ACCENT)
    d.text((90, 319), window_label(briefing) + f"     ·     {len(briefing['stories'])} 条资讯     ·     来源见日报", font=font(26), fill=MUTED)
    for i, category in enumerate(CATEGORIES):
        x, y = 86 + (i % 3) * 590, 390 + (i // 3) * 260
        d.rounded_rectangle((x, y + 4, x + 566, y + 240), radius=24, fill='#E9E8E2')
        d.rounded_rectangle((x, y, x + 566, y + 236), radius=24, fill='#FFFFFF')
        d.rounded_rectangle((x + 26, y + 30, x + 32, y + 67), radius=3, fill=COLORS[i])
        d.text((x + 48, y + 25), category, font=font(32, True), fill=COLORS[i])
        stories = [s for s in briefing['stories'] if s['category'] == category]
        if stories:
            for k, story in enumerate(stories[:2]):
                fitted(d, '· ' + story['title'], (x + 28, y + 89 + k * 66), 508, 2, 25, leading=1.2)
            if len(stories) > 2:
                d.text((x + 430, y + 29), f'+{len(stories) - 2} 条', font=font(22), fill=MUTED)
        else:
            d.text((x + 30, y + 105), '本期未收录', font=font(25), fill='#969D99')
    return im


def story_image(briefing, story, index):
    im = base_canvas(briefing, story['category'])
    d = ImageDraw.Draw(im)
    color = COLORS[CATEGORIES.index(story['category'])]
    d.text((82, 218), 'TODAY’S BRIEF', font=font(22), fill=MUTED)
    d.text((68, 256), f'{index:02}', font=font(172, True), fill=color)
    d.line((90, 498, 322, 498), fill='#D3D8CF', width=2)
    d.text((90, 526), story['category'], font=font(38, True), fill=color)
    d.text((90, 590), f"{index:02} / {len(briefing['stories']):02}", font=font(25), fill=MUTED)
    d.rounded_rectangle((90, 670, 325, 770), radius=16, fill='#EAECE5')
    d.text((110, 686), '原文发布日期', font=font(20), fill=MUTED)
    d.text((110, 721), story['published'][:10], font=font(24, True), fill=INK)
    d.rounded_rectangle((385, 208, 1832, 908), radius=32, fill='#E9E8E2')
    d.rounded_rectangle((385, 203, 1832, 902), radius=32, fill='white')
    d.rounded_rectangle((433, 250, 557, 287), radius=10, fill=color)
    d.text((495, 268), '资讯速读', anchor='mm', font=font(20, True), fill='white')
    title_height = fitted(d, story['title'], (433, 315), 1330, 2, 57, bold=True, leading=1.25)
    y = max(458, 330 + title_height)
    bullets = story['bullets'][:3]
    # Fit the entire bullet group to its allocated height, preserving all selected text.
    for size in range(37, 21, -1):
        lengths = [len(wrap_text(t, font(size), 1228)) for t in bullets]
        if sum(n * size * 1.45 + 30 for n in lengths) <= 790 - y:
            break
    else:
        raise ValueError('摘要过长，无法放入资讯卡片，请缩短 bullets。')
    for bullet in bullets:
        d.ellipse((440, y + 17, 450, y + 27), fill=color)
        height = fitted(d, bullet, (475, y), 1228, 6, size, leading=1.45)
        y += height + 30
    d.line((435, 812, 1775, 812), fill='#E6E9E3', width=2)
    domain = re.sub(r'^https?://', '', story['source_url']).split('/')[0]
    fitted(d, f"来源  {story['source_name']}  ·  {domain}", (435, 840), 1320, 1, 22, fill=MUTED)
    return im


def outro_image(briefing):
    im = base_canvas(briefing)
    d = ImageDraw.Draw(im)
    d.text((94, 222), 'KEEP TRACK. THINK CLEARLY.', font=font(28), fill=ACCENT)
    d.text((86, 290), '每天几分钟，了解 AI 新进展', font=font(66, True), fill=INK)
    d.text((92, 409), '完整来源、文字日报与字幕，已随视频保存。', font=font(33), fill=MUTED)
    d.rounded_rectangle((90, 515, 1830, 885), radius=30, fill='white')
    sources = list(dict.fromkeys(s['source_name'] for s in briefing['stories']))
    for i, name in enumerate(sources[:8]):
        x, y = 130 + (i % 2) * 825, 550 + (i // 2) * 76
        fitted(d, f'{i + 1:02}  {name}', (x, y), 770, 1, 27, fill=INK)
    return im


def frame_with_subtitle(base, text, current, total, story_index, story_count):
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
        label = '概览' if i == 0 else '来源' if i == nav_count - 1 else f'资讯 {i:02}'
        d.text(((left + right) / 2, 1046), label, anchor='mm', font=font(19), fill='white' if selected else MUTED)
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


async def edge_speech(jobs, voice):
    import edge_tts
    semaphore = asyncio.Semaphore(2)

    async def one(job):
        async with semaphore:
            target = Path(job['path'])
            mp3 = target.with_suffix('.mp3')
            async def request():
                await asyncio.wait_for(edge_tts.Communicate(job['text'], voice, rate='-8%').save(str(mp3)), 35)
            await retry_async(request)
            run_ffmpeg(['-i', str(mp3), '-ar', '24000', '-ac', '1', '-c:a', 'pcm_s16le', str(target)])
    # Probe first to avoid dispatching many requests when the service is unavailable.
    await one(jobs[0])
    await asyncio.gather(*(one(job) for job in jobs[1:]))


def synthesize(jobs, directory, voice, engine):
    if engine in ('auto', 'edge'):
        try:
            asyncio.run(edge_speech(jobs, voice))
            return f'Edge TTS / {voice}'
        except Exception as exc:
            if engine == 'edge':
                raise RuntimeError(f'联网中文配音失败（{type(exc).__name__}: {exc}）。可使用 --tts sapi 选择 Windows 本地语音。') from exc
            print(f'联网配音不可用（{type(exc).__name__}），正在使用 Windows 中文语音。', flush=True)
    if os.name != 'nt':
        raise RuntimeError('Windows 本地配音仅支持 Windows；请恢复联网语音连接。')
    manifest = directory / 'speech-jobs.json'
    manifest.write_text(json.dumps(jobs, ensure_ascii=False), encoding='utf-8')
    script = Path(__file__).with_name('speech.ps1')
    shell = shutil.which('pwsh') or shutil.which('powershell.exe')
    if not shell:
        raise RuntimeError('找不到 PowerShell，无法调用 Windows 本地语音。')
    process = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                              '-File', str(script), '-Manifest', str(manifest)], capture_output=True,
                             text=True, encoding='utf-8', errors='replace', timeout=max(180, len(jobs) * 15))
    if process.returncode:
        raise RuntimeError('Windows 中文配音失败：' + process.stderr[-2000:])
    return 'Windows SAPI / ' + process.stdout.strip()


def render(briefing: dict, output: Path, voice='zh-CN-XiaoxiaoNeural', engine='auto') -> Path:
    validate_briefing(briefing)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = output / 'assets'
    work.mkdir(exist_ok=True)
    overview = overview_image(briefing)
    overview.save(output / 'cover.png')
    count = len(briefing['stories'])
    intro = f'大家好，欢迎收看人工智能日报。本期整理了{count}条资讯。'
    if briefing.get('window_hours'):
        intro += f"新闻采集窗口为最近{briefing['window_hours']}小时，摘要由程序从来源原文中自动摘选。"
    else:
        end = date.fromisoformat(briefing['date'])
        start = end - timedelta(days=max(1, briefing.get('window_days', 1)) - 1)
        intro += f'本期报道范围为{start.month}月{start.day}日至{end.month}月{end.day}日，画面保留各条原文的发布日期。'
    scenes = [{'image': overview, 'text': intro, 'label': '资讯概览'}]
    scenes += [{'image': story_image(briefing, s, i + 1), 'text': s['narration'], 'label': s['title']}
               for i, s in enumerate(briefing['stories'])]
    scenes += [{'image': outro_image(briefing), 'text': '以上就是本期人工智能日报。完整来源链接和文字稿已随视频保存，欢迎查阅原文。感谢收看，我们下期再见。', 'label': '来源与结语'}]
    jobs, segments = [], []
    for i, scene in enumerate(scenes):
        scene['image'].save(work / f'scene-{i:02}.png')
        for sentence in split_sentences(scene['text']):
            number = len(jobs)
            path = work / f'speech-{number:03}.wav'
            jobs.append({'text': sentence, 'path': str(path)})
            segments.append({'scene': i, 'text': sentence, 'audio': path})
    print(f'正在生成 {len(jobs)} 段中文配音……', flush=True)
    engine_used = synthesize(jobs, work, voice, engine)
    print(f'配音完成：{engine_used}', flush=True)
    cursor, srt, concat, timeline = 0., [], ['ffconcat version 1.0'], []
    combined = output / 'narration.wav'
    with wave.open(str(combined), 'wb') as writer:
        writer.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        for n, seg in enumerate(segments):
            with wave.open(str(seg['audio']), 'rb') as reader:
                if (reader.getnchannels(), reader.getsampwidth(), reader.getframerate()) != (1, 2, 24000):
                    raise RuntimeError('配音音频格式不一致。')
                frames = reader.readframes(reader.getnframes())
                if not frames:
                    raise RuntimeError('配音生成了空音频。')
            # Quantize audio + pause to exact 24fps frames so image/subtitle boundaries do not drift.
            pause = 0.16 if n + 1 < len(segments) and segments[n + 1]['scene'] == seg['scene'] else 0.5
            samples = len(frames) // 2
            target_samples = math.ceil((samples + pause * 24000) / 1000) * 1000
            duration = target_samples / 24000
            writer.writeframes(frames + b'\0' * ((target_samples - samples) * 2))
            end = cursor + duration
            srt.append(f'{n + 1}\n{srt_time(cursor)} --> {srt_time(end)}\n{seg["text"]}\n')
            image_path = work / f'frame-{n:03}.png'
            frame_with_subtitle(scenes[seg['scene']]['image'], seg['text'], n + 1, len(segments), seg['scene'], count).save(image_path)
            concat += [f"file 'frame-{n:03}.png'", f'duration {duration:.9f}']
            timeline.append({'start': round(cursor, 4), 'end': round(end, 4), 'scene': seg['scene'], 'text': seg['text']})
            cursor = end
    concat.append(f"file 'frame-{len(segments) - 1:03}.png'")
    (work / 'frames.ffconcat').write_text('\n'.join(concat) + '\n', encoding='utf-8')
    (output / 'subtitles.srt').write_text('\n'.join(srt), encoding='utf-8-sig')
    manifest = {'duration_seconds': round(cursor, 3), 'width': W, 'height': H, 'fps': 24,
                'speech_engine': engine_used, 'segments': timeline,
                'chapters': [{'title': scene['label'], 'start': next(t['start'] for t in timeline if t['scene'] == i)} for i, scene in enumerate(scenes)]}
    (output / 'timeline.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    target = output / 'daily.mp4'
    temporary = output / 'daily.partial.mp4'
    print(f'正在合成 1080p 视频，预计时长 {cursor / 60:.1f} 分钟……', flush=True)
    log = run_ffmpeg(['-f', 'concat', '-safe', '0', '-i', 'frames.ffconcat', '-i', str(combined),
                     '-map', '0:v:0', '-map', '1:a:0', '-vf', f'fps=24,fade=t=in:d=0.35,fade=t=out:st={max(0, cursor - .4):.3f}:d=0.4',
                     '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'stillimage', '-crf', '20',
                     '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
                     '-t', f'{cursor:.6f}', '-movflags', '+faststart', str(temporary)], cwd=work)
    (output / 'render.log').write_text(log, encoding='utf-8')
    temporary.replace(target)
    return target
