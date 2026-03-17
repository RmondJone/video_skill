#!/usr/bin/env python3
"""
剧情摘要和关键情节分析脚本
根据完整字幕生成剧情摘要、关键情节节点
支持长视频分段分析
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime


# 分段配置
MAX_DURATION_PER_SEGMENT = 900  # 每段最大时长（秒），默认15分钟
MAX_CHARS_PER_SEGMENT = 30000   # 每段最大字符数，默认30000


def load_srt(srt_path):
    """加载 SRT 字幕文件"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        return f.read()


def parse_srt_to_text(srt_content):
    """解析 SRT 内容为纯文本"""
    segments = []
    blocks = srt_content.strip().split('\n\n')

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            time_line = lines[1]
            start_time = time_line.split(' --> ')[0].strip()
            text = '\n'.join(lines[2:])
            segments.append({
                'start': start_time,
                'text': text
            })

    return segments


def time_to_seconds(time_str):
    """将 HH:MM:SS,mmm 转换为秒数"""
    parts = time_str.replace(',', '.').split(':')
    h = int(parts[0])
    m = int(parts[1])
    s = float(parts[2])
    return h * 3600 + m * 60 + s


def seconds_to_time(seconds):
    """将秒数转换为 HH:MM:SS 格式"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def get_total_duration(segments):
    """获取视频总时长（秒）"""
    if not segments:
        return 0
    last_time = segments[-1]['start']
    return time_to_seconds(last_time)


def split_segments_by_duration(segments, max_duration=MAX_DURATION_PER_SEGMENT):
    """按时间分段，每段约15分钟

    Args:
        segments: 字幕片段列表
        max_duration: 每段最大时长（秒）

    Returns:
        分段列表，每段包含 start_time, end_time, segments
    """
    if not segments:
        return []

    total_duration = get_total_duration(segments)
    if total_duration <= max_duration:
        # 视频较短，无需分段
        return [{
            'part_num': 1,
            'total_parts': 1,
            'start_time': '00:00:00',
            'end_time': seconds_to_time(total_duration),
            'segments': segments,
            'start_seconds': 0,
            'end_seconds': total_duration
        }]

    # 计算分段数量
    num_segments = max(2, int(total_duration / max_duration) + 1)
    segment_duration = total_duration / num_segments

    splits = []
    for i in range(num_segments):
        start_sec = i * segment_duration
        end_sec = (i + 1) * segment_duration

        # 找到对应的字幕片段
        part_segments = []
        for seg in segments:
            seg_sec = time_to_seconds(seg['start'])
            if seg_sec >= start_sec and seg_sec < end_sec:
                part_segments.append(seg)

        # 确保每段至少有一些内容
        if part_segments:
            splits.append({
                'part_num': i + 1,
                'total_parts': num_segments,
                'start_time': seconds_to_time(start_sec),
                'end_time': seconds_to_time(min(end_sec, total_duration)),
                'segments': part_segments,
                'start_seconds': start_sec,
                'end_seconds': min(end_sec, total_duration)
            })

    return splits


def split_segments_by_chars(segments, max_chars=MAX_CHARS_PER_SEGMENT):
    """按字符数分段，每段约30000字符

    Args:
        segments: 字幕片段列表
        max_chars: 每段最大字符数

    Returns:
        分段列表
    """
    if not segments:
        return []

    # 计算总字符数
    total_chars = sum(len(seg['text']) for seg in segments)

    if total_chars <= max_chars:
        # 内容较短，无需分段
        total_duration = get_total_duration(segments)
        return [{
            'part_num': 1,
            'total_parts': 1,
            'start_time': '00:00:00',
            'end_time': seconds_to_time(total_duration),
            'segments': segments,
            'start_seconds': 0,
            'end_seconds': total_duration
        }]

    # 按字符数分段
    num_parts = max(2, (total_chars // max_chars) + 1)
    chars_per_part = total_chars / num_parts

    splits = []
    current_chars = 0
    current_segments = []
    start_seconds = 0

    for i, seg in enumerate(segments):
        seg_chars = len(seg['text'])
        current_chars += seg_chars

        # 检查是否需要分段
        if current_chars >= chars_per_part and i < len(segments) - 1:
            # 找到一个合理的断点
            end_seconds = time_to_seconds(seg['start'])

            splits.append({
                'part_num': len(splits) + 1,
                'total_parts': num_parts,
                'start_time': seconds_to_time(start_seconds),
                'end_time': seconds_to_time(end_seconds),
                'segments': current_segments,
                'start_seconds': start_seconds,
                'end_seconds': end_seconds
            })

            # 重置
            current_chars = 0
            current_segments = []
            start_seconds = end_seconds

        current_segments.append(seg)

    # 添加最后一段
    if current_segments:
        last_seg = current_segments[-1]
        end_seconds = get_total_duration(segments)

        splits.append({
            'part_num': len(splits) + 1,
            'total_parts': len(splits) + 1,
            'start_time': seconds_to_time(start_seconds),
            'end_time': seconds_to_time(end_seconds),
            'segments': current_segments,
            'start_seconds': start_seconds,
            'end_seconds': end_seconds
        })

    return splits


def generate_segment_prompt(part_info):
    """为单个分段生成提示词

    Args:
        part_info: 分段信息字典

    Returns:
        提示词字符串
    """
    # 构建该分段的字幕文本
    subtitle_text = ""
    total_chars = 0
    for seg in part_info['segments']:
        text = f"[{seg['start']}] {seg['text']}\n"
        subtitle_text += text
        total_chars += len(text)

    prompt = f"""请分析以下视频字幕的第 {part_info['part_num']} 部分（共 {part_info['total_parts']} 部分）。

【重要】这是视频的中间/结尾部分，请特别注意：
- 不要遗漏任何重要情节
- 关注该时段的完整故事线

时间范围：{part_info['start_time']} - {part_info['end_time']}

请分析这部分内容，生成：

1. 该部分的剧情摘要（100字左右）

2. 关键情节节点（按时间顺序列出重要事件，至少5个）：
   格式：时间点 | 事件描述 | 重要程度（高/中/低）
   例如：00:05:30 | 主角发现重要线索 | 高

字幕内容：
{subtitle_text}

请严格按照格式输出关键情节节点。"""

    return prompt, subtitle_text


def generate_summary_prompt(all_moments, total_duration):
    """生成汇总提示词，让 LLM 整合所有分段的关键情节

    Args:
        all_moments: 所有分段的关键情节列表（每个元素是 (分段编号, 关键情节列表) 的元组）
        total_duration: 视频总时长

    Returns:
        汇总提示词字符串
    """
    # 收集所有关键时间点
    all_moments_text = ""
    for part_num, moments in all_moments:
        all_moments_text += f"\n=== 第 {part_num} 部分 ===\n"
        if moments:
            for m in moments:
                all_moments_text += f"{m['time']} | {m['description']} | {m['importance']}\n"
        else:
            all_moments_text += "（该部分无关键情节）\n"

    prompt = f"""请根据以下各分段的关键情节节点，生成完整的剧情分析报告。

【任务】整合所有分段的信息，生成连贯完整的剧情分析

视频总时长：{seconds_to_time(total_duration)}

各分段关键情节汇总：
{all_moments_text}

请生成：

1. 完整视频剧情摘要（300字左右）

2. 完整关键情节节点（按时间顺序排列，至少15个）：
   格式：时间点 | 事件描述 | 重要程度（高/中/低）

3. 剧情结构分析：
   - 开端（0-20%）
   - 发展（20-60%）
   - 高潮（60-80%）
   - 结局（80-100%）

请严格按照格式输出，确保剧情连贯完整。"""

    return prompt


def generate_prompt_for_llm(segments, max_chars=200000):
    """生成发送给 LLM 的提示词（兼容旧版本）"""

    # 构建字幕文本（限制长度）
    subtitle_text = ""
    total_chars = 0
    for seg in segments:
        text = f"[{seg['start']}] {seg['text']}\n"
        if total_chars + len(text) > max_chars:
            break
        subtitle_text += text
        total_chars += len(text)

    prompt = f"""请分析以下视频字幕，生成：

1. 视频大致剧情/内容摘要（200字左右）

2. 关键情节节点（按时间顺序列出重要事件，至少10个）：
   格式：时间点 | 事件描述 | 重要程度（高/中/低）
   例如：00:05:30 | 主角发现重要线索 | 高

字幕内容：
{subtitle_text}

请严格按照格式输出关键情节节点。"""

    return prompt, subtitle_text


def parse_llm_key_moments(llm_output):
    """解析 LLM 输出的关键情节节点"""
    key_moments = []

    lines = llm_output.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 尝试解析格式：时间点 | 描述 | 重要程度
        parts = line.split('|')
        if len(parts) >= 3:
            time_str = parts[0].strip()
            description = parts[1].strip()
            importance = parts[2].strip()

            # 验证时间格式
            if re.match(r'\d{2}:\d{2}:\d{2}', time_str):
                key_moments.append({
                    'time': time_str,
                    'description': description,
                    'importance': importance,  # 高/中/低
                    'start_seconds': time_to_seconds(time_str)
                })

    return key_moments


def create_clips_from_key_moments(key_moments, padding=5):
    """根据关键情节节点创建视频片段

    Args:
        key_moments: 关键情节节点列表
        padding: 片段前后扩展秒数

    Returns:
        按时间顺序排序的片段列表
    """
    clips = []

    for i, moment in enumerate(key_moments):
        start_sec = max(0, moment['start_seconds'] - padding)
        end_sec = moment['start_seconds'] + padding

        # 格式化时间
        start_time = f"{int(start_sec // 3600):02d}:{int((start_sec % 3600) // 60):02d}:{int(start_sec % 60):02d}"
        end_time = f"{int(end_sec // 3600):02d}:{int((end_sec % 3600) // 60):02d}:{int(end_sec % 60):02d}"

        clips.append({
            'id': f'clip_{i+1:03d}',
            'start_time': start_time,
            'end_time': end_time,
            'duration': round(end_sec - start_sec, 1),
            'description': moment['description'],
            'importance': moment['importance'],
            'output_file': f'clips/clip_{i+1:03d}.mp4'
        })

    # 按时间顺序排序
    clips.sort(key=lambda x: x['start_time'])

    return clips


def save_analysis_results(key_moments, clips, output_path):
    """保存分析结果"""
    result = {
        'analysis_time': datetime.now().isoformat(),
        'video_type': 'dialogue',
        'key_moments': key_moments,
        'clips': clips
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


def main():
    parser = argparse.ArgumentParser(description='剧情摘要和关键情节分析')
    parser.add_argument('--srt', required=True, help='完整字幕 SRT 文件')
    parser.add_argument('--output', required=True, help='输出 JSON 文件')
    parser.add_argument('--mode', choices=['auto', 'short', 'long'], default='auto',
                        help='分段模式: auto=自动检测, short=短视频模式(单次), long=强制分段')

    args = parser.parse_args()

    if not os.path.exists(args.srt):
        print(f"错误: 字幕文件不存在: {args.srt}", file=sys.stderr)
        sys.exit(1)

    # 加载字幕
    print(f"加载字幕: {args.srt}")
    srt_content = load_srt(args.srt)
    segments = parse_srt_to_text(srt_content)
    print(f"解析到 {len(segments)} 个字幕片段")

    total_duration = get_total_duration(segments)
    print(f"视频时长: {seconds_to_time(total_duration)}")

    # 确定是否需要分段
    needs_splitting = args.mode == 'long' or (args.mode == 'auto' and total_duration > MAX_DURATION_PER_SEGMENT)

    if not needs_splitting:
        # 短视频模式：生成单个提示词
        prompt, subtitle_text = generate_prompt_for_llm(segments)

        # 保存提示词
        prompt_path = args.output.replace('.json', '_prompt.txt')
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 50 + "\n")
            f.write("剧情摘要和关键情节分析提示词\n")
            f.write("=" * 50 + "\n\n")
            f.write(prompt)
            f.write("\n\n")
            f.write("=" * 50 + "\n")
            f.write("完整字幕内容\n")
            f.write("=" * 50 + "\n\n")
            f.write(subtitle_text)

        print(f"\n提示词已保存到: {prompt_path}")
        print("\n" + "=" * 50)
        print("请将提示词发送给 LLM 分析")
        print("=" * 50 + "\n")
    else:
        # 长视频模式：生成分段提示词
        print(f"\n视频时长 {seconds_to_time(total_duration)} 超过15分钟，将自动分段处理")

        # 按时间分段
        splits = split_segments_by_duration(segments)
        print(f"自动分为 {len(splits)} 个分段")

        # 保存每个分段的提示词
        prompt_files = []
        for split in splits:
            prompt, subtitle_text = generate_segment_prompt(split)

            prompt_path = args.output.replace('.json', f'_prompt_p{split["part_num"]}.txt')
            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write(f"剧情分析 - 第 {split['part_num']} 部分（共 {split['total_parts']} 部分）\n")
                f.write(f"时间范围: {split['start_time']} - {split['end_time']}\n")
                f.write("=" * 60 + "\n\n")
                f.write(prompt)
                f.write("\n\n")
                f.write("=" * 60 + "\n")
                f.write("字幕内容\n")
                f.write("=" * 60 + "\n\n")
                f.write(subtitle_text)

            prompt_files.append(prompt_path)
            print(f"分段 {split['part_num']} 提示词已保存: {prompt_path}")

        # 生成汇总提示词
        summary_path = args.output.replace('.json', '_prompt_summary.txt')

        # 创建示例汇总内容（用户需要填入各分段的分析结果）
        summary_parts = []
        for i in range(len(splits)):
            summary_parts.append(f"""【请在此填入第{i+1}部分的分析结果】
=== 第 {i+1} 部分 ===
（将第{i+1}分段提示词发送给LLM后的结果粘贴到这里）

""")

        example_summary = f"""请根据以下各分段的关键情节节点，生成完整的剧情分析报告。

视频总时长：{seconds_to_time(total_duration)}

{''.join(summary_parts)}
请生成最终的完整剧情分析报告。
"""

        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("剧情分析 - 汇总提示词\n")
            f.write("=" * 60 + "\n\n")
            f.write(example_summary)

        print(f"汇总提示词已保存: {summary_path}")

        print("\n" + "=" * 60)
        print("分段分析工作流程：")
        print("=" * 60)
        for i, pf in enumerate(prompt_files):
            print(f"{i+1}. 将 {pf} 发送给 LLM 分析")
        print(f"{len(prompt_files) + 1}. 将所有分段的分析结果汇总，生成最终报告")
        print("=" * 60 + "\n")

    print("预期的 LLM 输出格式：")
    print("""
1. 剧情摘要：xxxxx

2. 关键情节节点：
00:05:30 | 主角发现重要线索 | 高
00:10:15 | 发生激烈冲突 | 高
00:15:45 | 情节转折 | 中
...
    """)


if __name__ == '__main__':
    main()
