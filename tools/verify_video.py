"""成片结构、音画与画面日期校验。"""

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


def duration_matches(video_seconds, subtitle_end, tolerance=1.5):
    return abs(float(video_seconds) - float(subtitle_end)) <= tolerance


def exit_code(failures, ocr_skipped):
    return 1 if failures else 2 if ocr_skipped else 0


def check_date_text(text, event_date, bullets=()):
    """检查画面事件日期和要点首次提及的事件日。

    OCR 对「事件日期 2026-09-30」这样带空格的行不稳定（常读成「事件日期2026-0」或
    多插空格），所以比对前把空白全部去掉，只比对字符序列。
    """
    if f'事件日期{event_date}' not in re.sub(r'\s+', '', text):
        return False, f'画面缺少事件日期 {event_date}'
    first = re.search(r'(\d{1,2})月(\d{1,2})日', ' '.join(bullets))
    if first:
        month, day = map(int, first.groups())
        expected = f'{month:02}-{day:02}'
        if not event_date.endswith(expected):
            return False, f'要点首次日期 {expected} 与事件日期 {event_date} 不一致'
    return True, ''


def parse_srt(content):
    matches = re.findall(r'(?m)^\ufeff?\d+\s*\n(\d\d):(\d\d):(\d\d),(\d\d\d)\s*-->\s*(\d\d):(\d\d):(\d\d),(\d\d\d)', content)
    if not matches:
        raise ValueError('字幕没有可识别的时间码')
    h, m, s, ms = map(int, matches[-1][4:])
    return len(matches), h * 3600 + m * 60 + s + ms / 1000


# 多尺度 OCR：右上角事件日期是小字，不同缩放下识别结果互补，任一命中即可。
OCR_SCALES = (
    (None, ()),
    ('scale=iw*2:ih*2:flags=lanczos', ()),
    ('scale=iw*3:ih*3:flags=lanczos', ('--psm', '6')),
)


def ocr_candidates(image_path, scratch):
    """按多种缩放对同一帧 OCR，返回各次识别文本。"""
    texts = []
    for index, (filters, extra) in enumerate(OCR_SCALES):
        target = image_path
        if filters:
            target = scratch / f'{image_path.stem}-s{index}.png'
            run_command(['ffmpeg', '-v', 'error', '-i', str(image_path), '-vf', filters, '-y', str(target)])
        text, _ = run_command(['tesseract', str(target), 'stdout', '-l', 'chi_sim+eng', *extra])
        texts.append(text)
    return texts


def required_files(directory):
    names = ('daily.mp4', 'briefing.json', 'timeline.json', 'subtitles.srt')
    missing = [name for name in names if not (directory / name).is_file()]
    if missing:
        raise FileNotFoundError('缺少文件：' + '、'.join(missing))
    frames = sorted((directory / 'assets').glob('frame-*.png'))
    if not frames:
        raise FileNotFoundError('缺少文件：assets/frame-*.png')
    return frames


def run_command(args):
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f'{args[0]} 退出码 {result.returncode}：{result.stderr.strip()[-300:]}')
    return result.stdout, result.stderr


def verify(directory):
    failures = []
    scratch = Path(tempfile.mkdtemp(prefix='verify-video-'))
    def report(label, ok, reason=''):
        print(f'{label}：{"通过" if ok else "失败" + ("：" + reason if reason else "")}')
        if not ok:
            failures.append(f'{label}：{reason}')

    try:
        frames = required_files(directory)
        briefing = json.loads((directory / 'briefing.json').read_text('utf-8-sig'))
        timeline = json.loads((directory / 'timeline.json').read_text('utf-8-sig'))
        subtitle_count, subtitle_end = parse_srt((directory / 'subtitles.srt').read_text('utf-8-sig'))
        report('文件和字幕', True)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report('文件和字幕', False, str(exc))
        return 1

    stories = briefing.get('stories', [])
    segments = timeline.get('segments', [])
    pages = timeline.get('pages', [])
    report('新闻条数与画面页数', len(pages) == len(stories) + 2,
           f'新闻 {len(stories)} 条，画面页 {len(pages)} 页')
    report('画面帧数', len(frames) == len(segments),
           f'帧 {len(frames)} 张，时间轴段 {len(segments)} 段')
    cues = sum(bool(seg.get('text')) for seg in segments)
    report('字幕条数', subtitle_count == cues,
           f'字幕 {subtitle_count} 条，时间轴口播 {cues} 条')
    try:
        raw, _ = run_command(['ffprobe', '-v', 'error', '-show_entries',
                              'format=duration:stream=codec_type,codec_name,width,height,r_frame_rate',
                              '-of', 'json', str(directory / 'daily.mp4')])
        probe = json.loads(raw)
        streams = probe['streams']
        video = next(s for s in streams if s['codec_type'] == 'video')
        fps = video.get('r_frame_rate', '0/1').split('/')
        frame_rate = int(fps[0]) / int(fps[1])
        ok = (video['codec_name'] == 'h264' and video['width'] == 1920 and
              video['height'] == 1080 and frame_rate == 24)
        report('视频编码与画幅', ok,
               f'{video.get("codec_name")} / {video.get("width")}×{video.get("height")} / {frame_rate:g} fps')
        report('音频流', any(s['codec_type'] == 'audio' for s in streams), '未发现音频流')
        seconds = float(probe['format']['duration'])
        report('时长与字幕', duration_matches(seconds, subtitle_end),
               f'视频 {seconds:.3f} 秒，字幕结束 {subtitle_end:.3f} 秒')
    except (OSError, RuntimeError, KeyError, ValueError, ZeroDivisionError, StopIteration) as exc:
        report('ffprobe', False, str(exc))

    try:
        _, stderr = run_command(['ffmpeg', '-nostdin', '-v', 'info', '-i', str(directory / 'daily.mp4'),
                                  '-af', 'volumedetect', '-vn', '-f', 'null', '-'])
        match = re.search(r'mean_volume:\s*(-?\d+(?:\.\d+)?) dB', stderr)
        if not match:
            raise ValueError('没有读到 mean_volume')
        volume = float(match.group(1))
        report('音频平均电平', volume > -40, f'{volume:g} dB，要求高于 -40 dB')
    except (OSError, RuntimeError, ValueError) as exc:
        report('音频平均电平', False, str(exc))

    ocr_skipped = shutil.which('tesseract') is None
    if ocr_skipped:
        print('OCR 检查已跳过（未安装 tesseract）')
    else:
        for index, story in enumerate(stories, 1):
            scene_frames = [frames[n] for n, seg in enumerate(segments)
                            if seg.get('chapter') == index and seg.get('text') and n < len(frames)]
            if not scene_frames:
                report(f'第 {index} 条画面日期', False, '找不到该条新闻的画面帧')
                continue
            try:
                # 同一新闻各帧有相同的事件日期栏；首张口播帧即可校验。
                # 右上角日期是小字，单一缩放会读残，所以按多种缩放各 OCR 一次，任一命中即通过。
                ok, reason = False, '画面缺少事件日期 ' + story['event_date']
                for text in ocr_candidates(scene_frames[0], scratch):
                    ok, reason = check_date_text(text, story['event_date'], story.get('bullets', []))
                    if ok:
                        break
                report(f'第 {index} 条画面日期', ok, reason)
            except (OSError, RuntimeError, KeyError) as exc:
                report(f'第 {index} 条画面日期', False, str(exc))
    code = exit_code(failures, ocr_skipped)
    print(f'校验结论：{"通过" if code == 0 else "存在硬失败" if code == 1 else "仅 OCR 跳过"}（退出码 {code}）')
    return code


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('用法：python3 tools/verify_video.py <成片目录>')
        raise SystemExit(1)
    raise SystemExit(verify(Path(sys.argv[1])))
