#!/usr/bin/env python3
"""
关键帧提取脚本 - 使用 ffmpeg 从每个场景提取关键帧
"""

import argparse
import json
import os
import subprocess
import sys
from tqdm import tqdm


def extract_keyframes(video_path, scenes_path, output_dir, max_frames=5):
    """
    从视频场景中提取关键帧

    Args:
        video_path: 输入视频路径
        scenes_path: 场景 JSON 文件路径
        output_dir: 输出目录
        max_frames: 每个场景最大帧数
    """
    with open(scenes_path, 'r', encoding='utf-8') as f:
        scenes_data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    scenes = scenes_data.get('scenes', [])
    print(f"共有 {len(scenes)} 个场景需要提取关键帧")

    extracted = []
    for i, scene in enumerate(tqdm(scenes, desc="提取关键帧", unit="场景")):
        start_time = scene['start_time']
        end_time = scene['end_time']

        # 计算场景时长
        start_parts = start_time.split(':')
        end_parts = end_time.split(':')

        start_seconds = int(start_parts[0]) * 3600 + int(start_parts[1]) * 60 + float(start_parts[2])
        end_seconds = int(end_parts[0]) * 3600 + int(end_parts[1]) * 60 + float(end_parts[2])
        duration = end_seconds - start_seconds

        # 计算提取帧的时间点
        frame_times = []
        if duration <= 0:
            frame_times = [start_time]
        elif duration <= 2:
            frame_times = [start_time, end_time]
        else:
            # 均匀分布提取点
            num_frames = min(max_frames, int(duration) + 1)
            for j in range(num_frames):
                t = start_seconds + (duration * j / (num_frames - 1)) if num_frames > 1 else start_seconds
                frame_times.append(f"{int(t // 3600):02d}:{int((t % 3600) // 60):02d}:{t % 60:05.2f}")

        # 提取每帧
        scene_keyframes = []
        for j, t in enumerate(frame_times):
            output_file = os.path.join(output_dir, f"scene_{i:03d}_frame_{j:02d}.jpg")

            cmd = [
                'ffmpeg', '-y', '-ss', t,
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                output_file
            ]

            try:
                subprocess.run(cmd, check=True, capture_output=True)
                scene_keyframes.append({
                    "scene_index": i,
                    "frame_index": j,
                    "time": t,
                    "file": output_file
                })
            except subprocess.CalledProcessError as e:
                print(f"  警告: 场景 {i} 帧 {j} 提取失败", file=sys.stderr)

        extracted.extend(scene_keyframes)

    # 保存提取结果
    result = {
        "video_path": video_path,
        "scenes_path": scenes_path,
        "output_dir": output_dir,
        "keyframes": extracted
    }

    result_file = os.path.join(output_dir, 'keyframes.json')
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n关键帧提取完成！共提取 {len(extracted)} 帧")
    print(f"结果已保存到: {result_file}")

    return result


def main():
    parser = argparse.ArgumentParser(description='提取视频关键帧')
    parser.add_argument('input', help='输入视频路径')
    parser.add_argument('scenes', help='场景 JSON 文件路径')
    parser.add_argument('output', help='输出目录')
    parser.add_argument('--max-frames', type=int, default=5,
                        help='每个场景最大帧数 (默认 5)')

    args = parser.parse_args()

    try:
        extract_keyframes(args.input, args.scenes, args.output, args.max_frames)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()