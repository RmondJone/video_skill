#!/usr/bin/env python3
"""
场景检测脚本 - 使用 PySceneDetect 检测视频场景切换点
"""

import argparse
import json
import sys
from scenedetect import SceneManager, VideoManager, StatsManager
from scenedetect.detectors import ContentDetector


def detect_scenes(video_path, output_path, threshold=30.0):
    """
    检测视频场景切换点

    Args:
        video_path: 输入视频路径
        output_path: 输出 JSON 路径
        threshold: 场景检测阈值 (默认 30.0)
    """
    video_manager = VideoManager([video_path])
    stats_manager = StatsManager()
    scene_manager = SceneManager(stats_manager)

    scene_manager.add_detector(ContentDetector(threshold=threshold))

    video_manager.set_duration()

    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)

    scene_list = scene_manager.get_scene_list()

    scenes = []
    for i, scene in enumerate(scene_list):
        scenes.append({
            "index": i,
            "start_time": str(scene[0].get_timecode()),
            "end_time": str(scene[1].get_timecode()),
            "start_frame": scene[0].get_frames(),
            "end_frame": scene[1].get_frames(),
            "duration_frames": scene[1].get_frames() - scene[0].get_frames()
        })

    result = {
        "video_path": video_path,
        "threshold": threshold,
        "scene_count": len(scenes),
        "scenes": scenes
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"检测到 {len(scenes)} 个场景")
    print(f"结果已保存到: {output_path}")

    return result


def main():
    parser = argparse.ArgumentParser(description='视频场景检测')
    parser.add_argument('input', help='输入视频路径')
    parser.add_argument('output', help='输出 JSON 路径')
    parser.add_argument('--threshold', type=float, default=30.0,
                        help='场景检测阈值 (默认 30.0)')

    args = parser.parse_args()

    try:
        detect_scenes(args.input, args.output, args.threshold)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()