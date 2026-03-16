#!/usr/bin/env python3
"""
视频剪切脚本 - 使用 FFmpeg 按时间戳剪切视频
"""
import argparse
import subprocess
import sys
import os
import json
from datetime import datetime

def parse_timestamp(ts):
    """解析时间戳为秒数"""
    parts = ts.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    else:
        return float(ts)

def format_duration(seconds):
    """将秒数格式化为 HH:MM:SS"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def get_video_duration(video_path):
    """获取视频时长"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def cut_video(input_path, start_time, end_time, output_path, codec='copy'):
    """
    剪切视频

    Args:
        input_path: 输入视频路径
        start_time: 开始时间 (秒)
        end_time: 结束时间 (秒)
        output_path: 输出视频路径
        codec: 编码方式 ('copy' 为快速复制, 'libx264' 为重新编码)
    """
    duration = end_time - start_time

    if codec == 'copy':
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start_time),
            '-i', input_path,
            '-t', str(duration),
            '-c', 'copy',
            output_path
        ]
    else:
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start_time),
            '-i', input_path,
            '-t', str(duration),
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            output_path
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"错误: FFmpeg 执行失败", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return False

    return True

def main():
    parser = argparse.ArgumentParser(description='视频剪切 - 按时间戳剪切视频片段')
    parser.add_argument('input', help='输入视频文件路径')
    parser.add_argument('start', help='开始时间 (HH:MM:SS 或 MM:SS)')
    parser.add_argument('end', help='结束时间 (HH:MM:SS 或 MM:SS)')
    parser.add_argument('output', help='输出视频文件路径')
    parser.add_argument('--re-encode', action='store_true', help='重新编码而非快速复制')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    # 解析时间戳
    start_sec = parse_timestamp(args.start)
    end_sec = parse_timestamp(args.end)

    if end_sec <= start_sec:
        print(f"错误: 结束时间必须大于开始时间", file=sys.stderr)
        sys.exit(1)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)

    # 执行剪切
    codec = 'libx264' if args.re_encode else 'copy'
    print(f"正在剪切视频: {args.start} -> {args.end}")
    print(f"输出: {args.output}")

    success = cut_video(args.input, start_sec, end_sec, args.output, codec)

    if success:
        duration = end_sec - start_sec
        print(f"完成! 片段时长: {format_duration(duration)}")
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
