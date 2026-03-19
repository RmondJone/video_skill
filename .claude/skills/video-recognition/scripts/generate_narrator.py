#!/usr/bin/env python3
"""
叙事串联 + 风格化脚本 - 将场景描述串联成连贯解说文案

【核心改进】
- 每2秒左右生成一句紧凑字幕
- 时间轴严格对齐视频总时长
- 场景间隔保持连续，字幕紧凑
"""

import argparse
import json
import sys
import math
from tqdm import tqdm


# 风格定义
STYLES = {
    '风趣幽默': {
        'name': '风趣幽默',
        'description': '轻松调侃的语气，画外音风格',
        'tone': '幽默、调侃、轻松',
        'sample': '看看这位老哥，那架势，像是要跟这棵树来一场世纪大战'
    },
    '技术硬核': {
        'name': '技术硬核',
        'description': '专业术语、深度分析',
        'tone': '专业、深入、严谨',
        'sample': '利用桦木的纤维结构，实现高效的树皮剥离'
    },
    '理性科普': {
        'name': '理性科普',
        'description': '客观陈述、逻辑清晰',
        'tone': '客观、清晰、易懂',
        'sample': '桦树皮具有良好的防水性能，常用于野外生存'
    },
    '解压治愈': {
        'name': '解压治愈',
        'description': '柔和舒缓、放松心情',
        'tone': '柔和、舒缓、治愈',
        'sample': '柔和的光线洒落在森林中，一切都是那么宁静美好'
    },
    '温馨感人': {
        'name': '温馨感人',
        'description': '情感充沛、温暖人心',
        'tone': '温暖、感人、真挚',
        'sample': '每一斧都凝聚着对生活的热爱，对自然的敬畏'
    }
}


def load_descriptions(descriptions_path):
    """加载场景描述"""
    with open(descriptions_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_seconds(seconds):
    """将秒数转换为 HH:MM:SS 格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:05.2f}"


def format_srt_time(seconds):
    """将秒数转换为 SRT 时间格式 HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    whole_sec = int(secs)
    ms = int((secs - whole_sec) * 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_sec:02d},{ms:03d}"


def split_to_sentences(text, max_duration=3.0):
    """
    将长文本分割成适合2秒左右的短句

    Args:
        text: 原始描述文本
        max_duration: 每句最大时长（秒）

    Returns:
        分割后的短句列表
    """
    if not text:
        return []

    # 简单按标点符号分割
    sentences = []
    current = ""

    for char in text:
        current += char
        if char in '。！？，；.!?,;':
            if current.strip():
                sentences.append(current.strip())
            current = ""

    if current.strip():
        sentences.append(current.strip())

    # 如果分割太少，再按逗号分割
    if len(sentences) < 2:
        sentences = []
        parts = text.replace('，', '|').replace(',', '|').split('|')
        for part in parts:
            if part.strip():
                sentences.append(part.strip())

    return sentences


def generate_narrator(descriptions_path, output_path, style_name='风趣幽默',
                     output_format='both', total_duration=None, sentence_duration=2.0):
    """
    生成解说文案（每2秒一句紧凑字幕）

    【核心改进】
    - 按固定时长（2秒）生成紧凑字幕
    - 内容按场景描述的字数比例分配
    - 时间轴严格对齐视频总时长

    Args:
        descriptions_path: 场景描述 JSON 路径
        output_path: 输出路径（不含扩展名）
        style_name: 风格名称
        output_format: 输出格式 (srt/txt/both)
        total_duration: 视频总时长（秒）
        sentence_duration: 每句时长（秒），默认2秒
    """
    data = load_descriptions(descriptions_path)
    descriptions = data.get('descriptions', [])

    if not descriptions:
        print("错误: 没有找到场景描述", file=sys.stderr)
        sys.exit(1)

    style = STYLES.get(style_name, STYLES['风趣幽默'])

    print(f"使用风格: {style['name']} - {style['description']}")
    print(f"场景数量: {len(descriptions)}")
    print(f"每句时长: ~{sentence_duration}秒")

    # 获取视频总时长
    if total_duration is None:
        total_duration = data.get('video_duration', 600)

    print(f"视频总时长: {format_seconds(total_duration)} ({total_duration:.1f}秒)")

    # 计算每个场景的时间范围（按场景数量均匀分配）
    scene_time_ranges = []
    total_scenes = len(descriptions)
    for i, scene in enumerate(descriptions):
        start_ratio = i / total_scenes
        end_ratio = (i + 1) / total_scenes
        start_time = total_duration * start_ratio
        end_time = total_duration * end_ratio
        scene_time_ranges.append((start_time, end_time))

    # 合并所有场景描述为一个连续文本
    all_text_parts = []
    for scene_idx, scene in enumerate(descriptions):
        scene_desc = scene.get('description', '') or scene.get('narrator', '')
        if scene_desc:
            # 按标点分割成更短的单元
            parts = split_to_sentences(scene_desc)
            if parts:
                all_text_parts.append((scene_idx, parts))
            else:
                all_text_parts.append((scene_idx, [scene_desc]))

    # 计算需要的字幕数量（每2秒一句）
    num_subtitles = int(total_duration / sentence_duration) + 1

    # 按固定间隔生成字幕
    all_entries = []
    current_time = 0.0
    subtitle_index = 1

    # 收集所有句子用于分配
    all_sentences = []
    for scene_idx, parts in all_text_parts:
        for part in parts:
            all_sentences.append((scene_idx, part))

    # 如果句子数量不够，重复使用句子
    while len(all_sentences) < num_subtitles:
        # 复制句子直到足够
        all_sentences.extend(all_sentences[:num_subtitles - len(all_sentences)])

    # 计算每个场景应该分配的句子数量
    sentences_per_scene = len(all_sentences) // total_scenes

    for i in tqdm(range(num_subtitles), desc="生成解说文案", unit="句"):
        if current_time >= total_duration:
            break

        # 确定当前字幕属于哪个场景
        scene_idx = min(int((current_time / total_duration) * total_scenes), total_scenes - 1)

        # 确定该场景在all_sentences中的范围
        scene_start_idx = scene_idx * sentences_per_scene
        scene_end_idx = (scene_idx + 1) * sentences_per_scene if scene_idx < total_scenes - 1 else len(all_sentences)

        # 取句子索引
        local_idx = i - (scene_idx * sentences_per_scene)
        if local_idx < (scene_end_idx - scene_start_idx):
            sentence_text = all_sentences[scene_start_idx + local_idx][1]
        else:
            # 超出该场景句子数量，截断或跳过
            sentence_text = ""

        # 计算结束时间
        end_time = min(current_time + sentence_duration, total_duration)

        # 如果文本为空，使用前一句或跳过
        if not sentence_text:
            sentence_text = all_entries[-1]['text'] if all_entries else ""

        all_entries.append({
            'index': subtitle_index,
            'start': current_time,
            'end': end_time,
            'text': sentence_text
        })

        subtitle_index += 1
        current_time = end_time

    # 确保最后一个条目结束时间 = 视频总时长
    if all_entries and all_entries[-1]['end'] < total_duration:
        all_entries[-1]['end'] = total_duration

    print(f"生成字幕: {len(all_entries)} 句")

    # 输出 SRT 格式
    if output_format in ('srt', 'both'):
        srt_path = f"{output_path}.srt" if '.' not in output_path else output_path.replace('.txt', '.srt')

        with open(srt_path, 'w', encoding='utf-8') as f:
            for entry in all_entries:
                srt_time = f"{format_srt_time(entry['start'])} --> {format_srt_time(entry['end'])}"
                f.write(f"{entry['index']}\n{srt_time}\n{entry['text']}\n\n")

        print(f"SRT 格式已保存到: {srt_path}")

    # 输出 TXT 格式
    if output_format in ('txt', 'both'):
        txt_path = f"{output_path}.txt" if '.' not in output_path else output_path

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"# {data.get('video_path', '视频')} 解说文案\n")
            f.write(f"# 风格: {style['name']}\n")
            f.write(f"# 视频总时长: {format_seconds(total_duration)}\n")
            f.write(f"# 字幕数量: {len(all_entries)} 句\n")
            f.write(f"# 每句时长: ~{sentence_duration}秒\n\n")

            for entry in all_entries:
                time_info = f"[{format_seconds(entry['start'])} --> {format_seconds(entry['end'])}]"
                f.write(f"{entry['index']}. {time_info}\n{entry['text']}\n\n")

        print(f"TXT 格式已保存到: {txt_path}")

    # 验证时间轴
    if all_entries:
        first_start = all_entries[0]['start']
        last_end = all_entries[-1]['end']
        print(f"\n时间轴验证:")
        print(f"  首个字幕: {format_seconds(first_start)}")
        print(f"  末个字幕: {format_seconds(last_end)}")
        print(f"  视频总时长: {format_seconds(total_duration)}")
        if abs(last_end - total_duration) < 1:
            print(f"  ✓ 时间轴对齐正常")
        else:
            print(f"  ⚠ 时间轴偏差: {last_end - total_duration:.1f}秒")

    print(f"\n解说文案生成完成！")

    return all_entries


def main():
    parser = argparse.ArgumentParser(
        description='生成解说文案（每2秒一句紧凑字幕）'
    )
    parser.add_argument('input', help='场景描述 JSON 路径')
    parser.add_argument('output', help='输出路径（不含扩展名）')
    parser.add_argument('--style', default='风趣幽默',
                        help='解说风格: 风趣幽默/技术硬核/理性科普/解压治愈/温馨感人')
    parser.add_argument('--format', default='both',
                        choices=['srt', 'txt', 'both'],
                        help='输出格式: srt/txt/both')
    parser.add_argument('--duration', type=float, default=None,
                        help='视频总时长（秒）')
    parser.add_argument('--sentence-duration', type=float, default=2.0,
                        help='每句时长（秒），默认2秒')

    args = parser.parse_args()

    try:
        generate_narrator(args.input, args.output, args.style, args.format,
                        args.duration, args.sentence_duration)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
