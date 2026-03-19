#!/usr/bin/env python3
"""
视频画面解说生成 - 主流程编排脚本

整合场景检测、关键帧提取、画面分析、解说文案生成
"""

import argparse
import json
import os
import subprocess
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_command(cmd, description):
    """执行命令并打印状态"""
    print(f"\n{'='*50}")
    print(f"{description}")
    print(f"{'='*50}")
    print(f"命令: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print(f"错误: {description} 失败", file=sys.stderr)
        return False

    print(f"✓ {description} 完成")
    return True


def process_video(video_path, output_dir, style='风趣幽默', threshold=30.0, max_frames=5):
    """
    完整处理流程

    Args:
        video_path: 输入视频路径
        output_dir: 输出目录
        style: 解说风格
        threshold: 场景检测阈值
        max_frames: 每场景最大帧数
    """
    # 验证输入
    if not os.path.exists(video_path):
        print(f"错误: 视频文件不存在: {video_path}", file=sys.stderr)
        sys.exit(1)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'keyframes'), exist_ok=True)

    video_name = os.path.splitext(os.path.basename(video_path))[0]

    # 步骤 1: 场景检测
    scenes_json = os.path.join(output_dir, 'scenes.json')
    cmd_scenes = [
        'python3', os.path.join(SCRIPT_DIR, 'detect_scenes.py'),
        video_path, scenes_json,
        '--threshold', str(threshold)
    ]

    if not run_command(cmd_scenes, "步骤 1: 场景检测"):
        sys.exit(1)

    # 步骤 2: 关键帧提取
    keyframes_dir = os.path.join(output_dir, 'keyframes')
    keyframes_json = os.path.join(keyframes_dir, 'keyframes.json')
    cmd_keyframes = [
        'python3', os.path.join(SCRIPT_DIR, 'extract_keyframes.py'),
        video_path, scenes_json, keyframes_dir,
        '--max-frames', str(max_frames)
    ]

    if not run_command(cmd_keyframes, "步骤 2: 关键帧提取"):
        sys.exit(1)

    # 步骤 3: 画面描述（生成模板）
    descriptions_json = os.path.join(output_dir, 'descriptions.json')
    cmd_describe = [
        'python3', os.path.join(SCRIPT_DIR, 'describe_scenes.py'),
        keyframes_json, descriptions_json
    ]

    if not run_command(cmd_describe, "步骤 3: 生成画面描述模板"):
        sys.exit(1)

    print(f"\n{'='*50}")
    print("画面分析阶段 - 请使用 Claude 分析关键帧")
    print(f"{'='*50}")
    print(f"关键帧目录: {keyframes_dir}")
    print(f"描述模板: {descriptions_json}")
    print("\n请分析关键帧图片后，更新 descriptions.json 中的 description 字段")

    # 步骤 4: 生成解说文案
    narrator_output = os.path.join(output_dir, 'narrator')
    cmd_narrator = [
        'python3', os.path.join(SCRIPT_DIR, 'generate_narrator.py'),
        descriptions_json, narrator_output,
        '--style', style,
        '--format', 'both'
    ]

    if not run_command(cmd_narrator, "步骤 4: 生成解说文案"):
        sys.exit(1)

    print(f"\n{'='*50}")
    print("✓ 处理完成！")
    print(f"{'='*50}")
    print(f"输出目录: {output_dir}")
    print(f"解说文案: {narrator_output}.srt / {narrator_output}.txt")


def main():
    parser = argparse.ArgumentParser(description='视频画面解说生成 - 主流程')
    parser.add_argument('input', help='输入视频路径')
    parser.add_argument('output', help='输出目录')
    parser.add_argument('--style', default='风趣幽默',
                        help='解说风格')
    parser.add_argument('--threshold', type=float, default=30.0,
                        help='场景检测阈值')
    parser.add_argument('--max-frames', type=int, default=5,
                        help='每场景最大帧数')

    args = parser.parse_args()

    process_video(args.input, args.output, args.style, args.threshold, args.max_frames)


if __name__ == '__main__':
    main()
