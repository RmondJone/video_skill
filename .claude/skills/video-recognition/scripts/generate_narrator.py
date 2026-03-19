#!/usr/bin/env python3
"""
叙事串联 + 风格化脚本 - 将场景描述串联成连贯解说文案
"""

import argparse
import json
import sys


# 风格定义
STYLES = {
    '风趣幽默': {
        'name': '风趣幽默',
        'description': '轻松调侃的语气，画外音风格',
        'tone': '幽默、调侃、轻松',
        'template': '开头有趣 + 中间调侃 + 结尾留悬念'
    },
    '技术硬核': {
        'name': '技术硬核',
        'description': '专业术语、深度分析',
        'tone': '专业、深入、严谨',
        'template': '技术背景 + 原理分析 + 专业评价'
    },
    '理性科普': {
        'name': '理性科普',
        'description': '客观陈述、逻辑清晰',
        'tone': '客观、清晰、易懂',
        'template': '事实陈述 + 逻辑展开 + 总结归纳'
    },
    '解压治愈': {
        'name': '解压治愈',
        'description': '柔和舒缓、放松心情',
        'tone': '柔和、舒缓、治愈',
        'template': '放松氛围 + 美好细节 + 心灵慰藉'
    },
    '温馨感人': {
        'name': '温馨感人',
        'description': '情感充沛、温暖人心',
        'tone': '温暖、感人、真挚',
        'template': '情感铺垫 + 感动瞬间 + 温暖收尾'
    }
}


def load_descriptions(descriptions_path):
    """加载场景描述"""
    with open(descriptions_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_srt_entry(index, start_time, end_time, text):
    """生成 SRT 格式条目"""
    # 转换时间格式为 SRT 格式
    srt_start = format_srt_time(start_time)
    srt_end = format_srt_time(end_time)

    return f"{index}\n{srt_start} --> {srt_end}\n{text}\n"


def format_srt_time(time_str):
    """
    将 HH:MM:SS 格式转换为 HH:MM:SS,mmm
    """
    parts = time_str.split(':')
    if len(parts) != 3:
        return "00:00:00,000"

    hours, minutes, seconds = parts
    if '.' in seconds:
        sec, ms = seconds.split('.')
        ms = ms.ljust(3, '0')[:3]
    else:
        sec = seconds
        ms = "000"

    return f"{hours}:{minutes}:{sec},{ms}"


def generate_narrator(descriptions_path, output_path, style_name='风趣幽默', output_format='both'):
    """
    生成解说文案

    Args:
        descriptions_path: 场景描述 JSON 路径
        output_path: 输出路径（不含扩展名）
        style_name: 风格名称
        output_format: 输出格式 (srt/txt/both)
    """
    data = load_descriptions(descriptions_path)
    descriptions = data.get('descriptions', [])

    if not descriptions:
        print("错误: 没有找到场景描述", file=sys.stderr)
        sys.exit(1)

    style = STYLES.get(style_name, STYLES['风趣幽默'])

    print(f"使用风格: {style['name']} - {style['description']}")
    print(f"共有 {len(descriptions)} 个场景需要生成解说")

    # 生成叙事文本
    narrator_segments = []

    for i, desc in enumerate(descriptions):
        scene_desc = desc.get('description', '')
        scene_time = desc.get('time', '00:00:00')

        # 下一场景的开始时间作为当前场景的结束时间
        if i < len(descriptions) - 1:
            next_time = descriptions[i + 1].get('time', '00:00:00')
        else:
            # 最后一个场景，默认 5 秒
            parts = scene_time.split(':')
            last_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2]) + 5
            next_time = f"{int(last_seconds // 3600):02d}:{int((last_seconds % 3600) // 60):02d}:{last_seconds % 60:05.2f}"

        narrator_segments.append({
            "index": i + 1,
            "start_time": scene_time,
            "end_time": next_time,
            "scene_index": desc.get('scene_index'),
            "text": scene_desc  # 实际由 Claude 填写的解说文案
        })

    # 输出 SRT 格式
    if output_format in ('srt', 'both'):
        srt_path = f"{output_path}.srt" if '.' not in output_path else output_path.replace('.txt', '.srt')
        if output_format == 'both' and '.' not in output_path:
            srt_path = f"{output_path}.srt"

        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(narrator_segments):
                text = seg['text'] if seg['text'] else f"【场景 {seg['scene_index']}】"
                entry = generate_srt_entry(seg['index'], seg['start_time'], seg['end_time'], text)
                f.write(entry)
                f.write('\n')

        print(f"SRT 格式已保存到: {srt_path}")

    # 输出 TXT 格式
    if output_format in ('txt', 'both'):
        txt_path = f"{output_path}.txt" if '.' not in output_path else output_path
        if output_format == 'both' and '.' not in output_path:
            txt_path = f"{output_path}.txt"

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"# {data.get('video_path', '视频')} 解说文案\n")
            f.write(f"# 风格: {style['name']}\n\n")

            for seg in narrator_segments:
                text = seg['text'] if seg['text'] else f"【场景 {seg['scene_index']}】"
                time_info = f"[{seg['start_time']}]"
                f.write(f"{time_info} {text}\n\n")

        print(f"TXT 格式已保存到: {txt_path}")

    print(f"\n解说文案生成完成！")


def main():
    parser = argparse.ArgumentParser(description='生成风格化解说文案')
    parser.add_argument('input', help='场景描述 JSON 路径')
    parser.add_argument('output', help='输出路径（不含扩展名）')
    parser.add_argument('--style', default='风趣幽默',
                        help='解说风格: 风趣幽默/技术硬核/理性科普/解压治愈/温馨感人')
    parser.add_argument('--format', default='both',
                        choices=['srt', 'txt', 'both'],
                        help='输出格式: srt/txt/both')

    args = parser.parse_args()

    try:
        generate_narrator(args.input, args.output, args.style, args.format)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()