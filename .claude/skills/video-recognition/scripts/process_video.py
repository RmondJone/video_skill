#!/usr/bin/env python3
"""
视频画面解说生成 - 主流程编排脚本

整合场景检测、关键帧提取、画面分析、解说文案生成

【核心改进】
1. 自动获取视频实际总时长
2. 场景采样数量限制（默认8-12个场景）
3. 时间轴严格对齐视频总时长
4. 每个场景间隔不小于20秒
"""

import argparse
import json
import os
import subprocess
import sys
import math


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_video_duration(video_path):
    """使用 ffprobe 获取视频实际总时长（秒）"""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        print(f"警告: 获取视频时长失败: {e}")
        return None


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


def sample_scenes(scenes_data, num_samples=10):
    """
    从检测到的场景中均匀采样

    Args:
        scenes_data: 场景检测结果
        num_samples: 采样数量，默认10个

    Returns:
        采样后的场景列表
    """
    scenes = scenes_data.get('scenes', [])
    total_scenes = len(scenes)

    if total_scenes <= num_samples:
        return scenes

    # 均匀采样：每个采样点覆盖 total_scenes / num_samples 个场景
    step = total_scenes / num_samples
    sampled = []

    for i in range(num_samples):
        index = int(i * step)
        if index < total_scenes:
            sampled.append(scenes[index])

    # 确保最后一个场景被包含
    if scenes and sampled[-1] != scenes[-1]:
        sampled[-1] = scenes[-1]

    return sampled


def process_video(video_path, output_dir, style='风趣幽默',
                 threshold=30.0, max_frames=5, num_scenes=10):
    """
    完整处理流程

    【核心改进】
    1. 自动获取视频实际总时长
    2. 场景采样数量限制
    3. 时间轴严格对齐视频总时长

    Args:
        video_path: 输入视频路径
        output_dir: 输出目录
        style: 解说风格
        threshold: 场景检测阈值
        max_frames: 每场景最大帧数
        num_scenes: 最终输出的场景数量（默认10个）
    """
    # 验证输入
    if not os.path.exists(video_path):
        print(f"错误: 视频文件不存在: {video_path}", file=sys.stderr)
        sys.exit(1)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'keyframes'), exist_ok=True)

    video_name = os.path.splitext(os.path.basename(video_path))[0]

    # 获取视频总时长
    print(f"\n{'='*50}")
    print(f"获取视频信息...")
    print(f"{'='*50}")

    duration = get_video_duration(video_path)
    if duration:
        print(f"✓ 视频总时长: {int(duration // 3600):02d}:{int((duration % 3600) // 60):02d}:{duration % 60:05.2f} ({duration:.1f}秒)")
    else:
        duration = 600  # 默认10分钟
        print(f"⚠ 无法获取时长，使用默认值: {duration}秒")

    # 步骤 1: 场景检测
    scenes_json = os.path.join(output_dir, 'scenes.json')
    cmd_scenes = [
        'python3', os.path.join(SCRIPT_DIR, 'detect_scenes.py'),
        video_path, scenes_json,
        '--threshold', str(threshold)
    ]

    if not run_command(cmd_scenes, "步骤 1: 场景检测"):
        sys.exit(1)

    # 加载场景检测结果，进行采样
    with open(scenes_json, 'r', encoding='utf-8') as f:
        scenes_data = json.load(f)

    original_scene_count = len(scenes_data.get('scenes', []))
    print(f"\n检测到 {original_scene_count} 个原始场景")

    # 根据视频时长计算合理的场景数量
    # 规则：每分钟视频约 1-2 个解说场景，最少8个，最多15个
    duration_minutes = duration / 60 if duration else 10
    recommended_scenes = max(8, min(15, int(duration_minutes * 1.5)))

    if num_scenes is None:
        num_scenes = recommended_scenes

    print(f"视频时长 {duration_minutes:.1f} 分钟，推荐场景数量: {num_scenes}")

    # 采样场景
    if original_scene_count > num_scenes:
        sampled_scenes = sample_scenes(scenes_data, num_scenes)
        print(f"场景采样: {original_scene_count} -> {len(sampled_scenes)} 个")

        # 更新 scenes.json
        scenes_data['scenes'] = sampled_scenes
        scenes_data['sampled_from'] = original_scene_count
        scenes_data['num_scenes'] = len(sampled_scenes)

        with open(scenes_json, 'w', encoding='utf-8') as f:
            json.dump(scenes_data, f, ensure_ascii=False, indent=2)
    else:
        scenes_data['num_scenes'] = original_scene_count
        sampled_scenes = scenes_data.get('scenes', [])
        print(f"场景数量在合理范围内: {original_scene_count} 个")

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

    # 读取关键帧信息
    with open(keyframes_json, 'r', encoding='utf-8') as f:
        keyframes_data = json.load(f)

    keyframes = keyframes_data.get('keyframes', [])

    # 生成描述模板
    descriptions = []
    for kf in keyframes:
        descriptions.append({
            "scene_index": kf['scene_index'],
            "frame_index": kf['frame_index'],
            "time": kf['time'],
            "image_file": kf['file'],
            "description": "",  # 由 Claude 填写
            "narrator": ""      # 由 Claude 填写
        })

    desc_result = {
        "video_path": video_path,
        "video_duration": duration,
        "video_duration_formatted": f"{int(duration // 3600):02d}:{int((duration % 3600) // 60):02d}:{duration % 60:05.2f}",
        "keyframes_path": keyframes_json,
        "description_count": len(descriptions),
        "descriptions": descriptions
    }

    with open(descriptions_json, 'w', encoding='utf-8') as f:
        json.dump(desc_result, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 描述模板已生成: {descriptions_json}")
    print(f"  - 场景数量: {len(descriptions)}")
    print(f"  - 视频时长: {desc_result['video_duration_formatted']}")

    # 步骤 4: 生成解说文案（跳过手动分析阶段，直接生成）
    # 注意：这里需要 Claude 分析关键帧后填入 narrators

    print(f"\n{'='*50}")
    print("画面分析阶段")
    print(f"{'='*50}")
    print(f"关键帧目录: {keyframes_dir}")
    print(f"描述模板: {descriptions_json}")
    print(f"\n请使用 Claude 分析关键帧图片，更新 descriptions.json 中的 description 和 narrator 字段")
    print(f"然后运行:")
    print(f"  python3 {os.path.join(SCRIPT_DIR, 'generate_narrator.py')} \\")
    print(f"    {descriptions_json} {os.path.join(output_dir, 'narrator')} \\")
    print(f"    --style {style} --format both --duration {duration} --scenes {len(descriptions)}")

    # 尝试自动生成（如果有描述内容）
    has_narrator = any(d.get('narrator', d.get('description', '')) for d in descriptions)

    if has_narrator:
        narrator_output = os.path.join(output_dir, 'narrator')
        cmd_narrator = [
            'python3', os.path.join(SCRIPT_DIR, 'generate_narrator.py'),
            descriptions_json, narrator_output,
            '--style', style,
            '--format', 'both',
            '--duration', str(duration),
            '--scenes', str(len(descriptions))
        ]

        if run_command(cmd_narrator, "步骤 4: 生成解说文案"):
            print(f"\n{'='*50}")
            print("✓ 处理完成！")
            print(f"{'='*50}")
            print(f"输出目录: {output_dir}")
            print(f"解说文案: {narrator_output}.srt / {narrator_output}.txt")
    else:
        print(f"\n⚠ 请先分析关键帧图片，填写 narrator 字段后再生成解说文案")


def main():
    parser = argparse.ArgumentParser(
        description='视频画面解说生成 - 主流程（时间轴严格对齐视频总时长，场景间隔≥20秒）'
    )
    parser.add_argument('input', help='输入视频路径')
    parser.add_argument('output', help='输出目录')
    parser.add_argument('--style', default='风趣幽默',
                        help='解说风格')
    parser.add_argument('--threshold', type=float, default=30.0,
                        help='场景检测阈值')
    parser.add_argument('--max-frames', type=int, default=5,
                        help='每场景最大帧数')
    parser.add_argument('--scenes', type=int, default=10,
                        help='最终输出场景数量（默认10个）')

    args = parser.parse_args()

    process_video(args.input, args.output, args.style, args.threshold, args.max_frames, args.scenes)


if __name__ == '__main__':
    main()
