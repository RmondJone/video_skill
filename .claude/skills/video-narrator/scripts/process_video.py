#!/usr/bin/env python3
"""
视频解说生成器 - 主处理脚本
整合语音识别、AI文案生成、视频剪切、导出文件生成
"""
import argparse
import json
import os
import sys
import subprocess
from datetime import datetime

# 尝试导入 faster-whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

def check_dependencies():
    """检查依赖工具"""
    # 检查 FFmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误: FFmpeg 未安装，请运行: brew install ffmpeg", file=sys.stderr)
        return False

    # 检查 faster-whisper
    if not WHISPER_AVAILABLE:
        print("警告: faster-whisper 未安装，语音识别功能不可用")
        print("安装: pip install faster-whisper")

    return True

def parse_timestamp(ts):
    """解析时间戳为秒数"""
    parts = ts.replace(',', '.').split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(ts)

def format_time(seconds):
    """将秒数格式化为 HH:MM:SS"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def transcribe_video(video_path, output_dir, model_size='base'):
    """语音识别"""
    if not WHISPER_AVAILABLE:
        print("错误: faster-whisper 未安装，无法进行语音识别")
        return None

    print(f"加载 Whisper {model_size} 模型...")
    model = WhisperModel(model_size, device='cpu', compute_type='int8')

    print(f"正在识别语音: {video_path}")
    segments, info = model.transcribe(video_path, beam_size=5)

    # 保存 SRT
    srt_path = os.path.join(output_dir, 'subtitles', 'full.srt')
    os.makedirs(os.path.dirname(srt_path), exist_ok=True)

    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments, 1):
            start = format_timestamp_hms(segment.start)
            end = format_timestamp_hms(segment.end)
            text = segment.text.strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

    print(f"语音识别完成: {srt_path}")
    return srt_path

def check_subtitle_exists(output_dir):
    """检查字幕文件是否已存在"""
    subtitle_path = os.path.join(output_dir, "subtitles", "full.srt")
    return os.path.exists(subtitle_path), subtitle_path

def format_timestamp_hms(seconds):
    """将秒数转换为 SRT 时间格式"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def cut_video_clips(video_path, clips_info, output_dir):
    """剪切视频片段"""
    clips_dir = os.path.join(output_dir, 'clips')
    os.makedirs(clips_dir, exist_ok=True)

    output_clips = []

    for i, clip_info in enumerate(clips_info, 1):
        start = clip_info['start']
        end = clip_info['end']
        clip_name = f"clip_{i:03d}.mp4"
        output_path = os.path.join(clips_dir, clip_name)

        duration = parse_timestamp(end) - parse_timestamp(start)

        print(f"剪切片段 {i}: {start} -> {end}")

        cmd = [
            'ffmpeg', '-y',
            '-ss', str(parse_timestamp(start)),
            '-i', video_path,
            '-t', str(duration),
            '-c', 'copy',
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            output_clips.append({
                'id': f"clip_{i:03d}",
                'source_file': video_path,
                'start_time': start,
                'end_time': end,
                'duration': duration,
                'output_file': output_path
            })
            print(f"  -> 已保存: {clip_name}")
        else:
            print(f"  -> 剪切失败", file=sys.stderr)

    return output_clips

def generate_manifest(clips, output_dir):
    """生成素材清单"""
    manifest = {
        'project': 'video-narrator-export',
        'created': datetime.now().isoformat(),
        'clips': clips,
        'subtitles': [
            {'file': 'subtitles/full.srt', 'type': 'full'},
        ]
    }

    manifest_path = os.path.join(output_dir, 'manifest.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"素材清单已生成: {manifest_path}")
    return manifest_path

def main():
    parser = argparse.ArgumentParser(description='视频解说生成器 - 主处理脚本')
    parser.add_argument('input', help='输入视频文件路径')
    parser.add_argument('--output', '-o', help='输出目录路径')
    parser.add_argument('--clips', help='片段时间信息 JSON 文件')
    parser.add_argument('--whisper-model', default='small',
                        choices=['tiny', 'base', 'small', 'medium', 'large'],
                        help='Whisper 模型大小')

    args = parser.parse_args()

    # 验证输入
    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 设置输出目录
    if args.output:
        output_dir = args.output
    else:
        input_name = os.path.splitext(os.path.basename(args.input))[0]
        # 默认输出到 output/<文件名>/ 目录
        output_dir = os.path.join("output", input_name)

    os.makedirs(output_dir, exist_ok=True)
    print(f"输出目录: {output_dir}")

    # 步骤 1: 检测字幕是否存在
    subtitle_exists, subtitle_path = check_subtitle_exists(output_dir)

    # 步骤 1.5: 如果字幕已存在，跳过识别，直接进入剧情分析
    if subtitle_exists:
        print(f"✓ 检测到已有字幕文件: {subtitle_path}")
        print("  跳过语音识别，直接进入剧情分析阶段")
        srt_path = subtitle_path
    elif WHISPER_AVAILABLE:
        # 字幕不存在，执行语音识别
        srt_path = transcribe_video(args.input, output_dir, args.whisper_model)
    else:
        print("跳过语音识别（faster-whisper 未安装）")
        srt_path = None

    # 步骤 2: 加载片段信息
    if args.clips:
        with open(args.clips, 'r') as f:
            clips_info = json.load(f)
    else:
        # 示例：用户需要手动提供或使用默认逻辑
        print("提示: 请使用 --clips 参数提供片段时间信息 JSON 文件")
        print("JSON 格式: [{\"start\": \"00:00:10\", \"end\": \"00:00:30\"}, ...]")
        clips_info = []

    # 步骤 3: 剪切视频
    if clips_info:
        clips = cut_video_clips(args.input, clips_info, output_dir)
        generate_manifest(clips, output_dir)

        # 生成 XML 和 EDL
        try:
            from generate_xml import create_xml_project
            xml_path = os.path.join(output_dir, 'timeline', 'project.xml')
            os.makedirs(os.path.dirname(xml_path), exist_ok=True)
            create_xml_project(clips, xml_path)
        except Exception as e:
            print(f"XML 生成失败: {e}", file=sys.stderr)

        try:
            from generate_edl import create_edl
            edl_path = os.path.join(output_dir, 'timeline', 'project.edl')
            os.makedirs(os.path.dirname(edl_path), exist_ok=True)
            create_edl(clips, edl_path, fps=30, reel_name="VIDEO")
        except Exception as e:
            print(f"EDL 生成失败: {e}", file=sys.stderr)

    print("\n处理完成!")
    print(f"输出目录: {output_dir}")

if __name__ == '__main__':
    main()
