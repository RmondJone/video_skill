#!/usr/bin/env python3
"""
画面描述生成脚本 - 分析关键帧生成场景描述
注意：实际画面分析由 Claude 自身能力完成，此脚本负责组织数据
"""

import argparse
import json
import os
import sys


def generate_description_prompt(keyframes_info):
    """
    生成画面分析的 prompt（供 Claude 分析使用）

    Args:
        keyframes_info: 关键帧信息列表

    Returns:
        分析用的提示词
    """
    prompt = """你是一个专业的视频画面分析师。请分析以下关键帧图片，用中文生成详细的场景描述。

要求：
1. 每个场景描述需要包含：场景内容、人物动作、物体细节、环境氛围
2. 描述要客观、准确、详细
3. 前后场景描述要有叙事连贯性

关键帧信息：
"""

    for kf in keyframes_info:
        prompt += f"\n【场景 {kf['scene_index']} - 时间点 {kf['time']}】"
        prompt += f"\n文件: {kf['file']}"
        prompt += "\n请分析这张图片的内容..."

    return prompt


def describe_scenes(keyframes_path, output_path):
    """
    生成画面描述

    注意：这个脚本生成分析模板，实际画面分析由 Claude 完成
    用户需要使用 Claude 分析关键帧图片后，将分析结果保存为 JSON 格式

    Args:
        keyframes_path: 关键帧 JSON 文件路径
        output_path: 输出描述 JSON 路径
    """
    with open(keyframes_path, 'r', encoding='utf-8') as f:
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

    result = {
        "video_path": keyframes_data.get('video_path'),
        "keyframes_path": keyframes_path,
        "description_count": len(descriptions),
        "descriptions": descriptions
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"描述模板已生成，共 {len(descriptions)} 个场景")
    print(f"请使用 Claude 分析关键帧图片并填写 description 字段")
    print(f"结果已保存到: {output_path}")

    return result


def update_descriptions_with_analysis(descriptions_path, analysis_results):
    """
    更新描述文件，填入 Claude 的分析结果

    Args:
        descriptions_path: 描述 JSON 路径
        analysis_results: Claude 分析结果列表
    """
    with open(descriptions_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    descriptions = data.get('descriptions', [])

    for i, desc in enumerate(descriptions):
        if i < len(analysis_results):
            desc['description'] = analysis_results[i].get('description', '')
            desc['narrator'] = analysis_results[i].get('narrator', '')

    with open(descriptions_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"描述已更新")


def main():
    parser = argparse.ArgumentParser(description='生成画面描述')
    parser.add_argument('keyframes', help='关键帧 JSON 文件路径')
    parser.add_argument('output', help='输出描述 JSON 路径')

    args = parser.parse_args()

    try:
        describe_scenes(args.keyframes, args.output)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
