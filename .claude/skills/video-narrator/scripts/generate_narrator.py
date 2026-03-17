#!/usr/bin/env python3
"""
解说文案生成脚本 - 基于字幕和片段信息生成 AI 解说文案
"""
import argparse
import json
import os
import sys


def load_srt(srt_path):
    """加载 SRT 字幕文件"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content


def parse_srt_to_segments(srt_content):
    """解析 SRT 内容为片段列表"""
    segments = []
    blocks = srt_content.strip().split('\n\n')

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            # 解析时间行: 00:00:00,000 --> 00:00:05,000
            time_line = lines[1]
            start_time, end_time = time_line.split(' --> ')
            start_time = start_time.strip().replace(',', '.')
            end_time = end_time.strip().replace(',', '.')

            # 解析文本
            text = '\n'.join(lines[2:])

            segments.append({
                'start': start_time,
                'end': end_time,
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


def seconds_to_srt_time(seconds):
    """将秒数转换为 SRT 时间格式"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_timestamp(seconds):
    """将秒数格式化为 HH:MM:SS"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def find_related_subtitles(segments, start_time, end_time, padding=3):
    """查找与片段时间范围相关的字幕"""
    start_sec = time_to_seconds(start_time) - padding
    end_sec = time_to_seconds(end_time) + padding

    related = []
    for seg in segments:
        seg_start = time_to_seconds(seg['start'])
        seg_end = time_to_seconds(seg['end'])

        # 检查是否重叠
        if seg_start <= end_sec and seg_end >= start_sec:
            related.append(seg)

    return related


def generate_narrator_srt(clips, full_srt_path, output_path, analysis_json_path=None):
    """
    生成解说文案 SRT 文件

    这个脚本生成一个模板，实际的解说文案需要 LLM 生成
    """
    # 加载完整字幕
    full_srt = load_srt(full_srt_path)
    segments = parse_srt_to_segments(full_srt)

    # 尝试加载剧情摘要
    story_summary = ""
    if analysis_json_path and os.path.exists(analysis_json_path):
        try:
            with open(analysis_json_path, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
            # 提取剧情摘要（从 key_moments 中提取或从 summary 字段）
            if 'summary' in analysis_data:
                story_summary = analysis_data['summary']
            elif 'story_summary' in analysis_data:
                story_summary = analysis_data['story_summary']
            elif 'key_moments' in analysis_data and analysis_data['key_moments']:
                # 如果有关键情节，取前几个重要情节作为上下文
                important_moments = [m for m in analysis_data['key_moments']
                                   if m.get('importance') in ['高', 'high', '中', 'medium']]
                if important_moments:
                    story_summary = "关键情节节点：\n"
                    for m in important_moments[:10]:
                        story_summary += f"- {m.get('time', '')} | {m.get('description', '')}\n"
        except Exception as e:
            print(f"警告: 读取剧情摘要失败: {e}", file=sys.stderr)

    # 构建提示词（供 LLM 使用）
    prompt = """请根据以下视频信息和字幕内容，为每个视频片段生成解说文案。

要求：
1. 解说文案要简洁、生动、符合原视频内容
2. 每个片段 1-3 句话为宜
3. 输出格式：片段编号 | 时间范围 | 解说文案

示例格式：
1 | 00:06:00-00:08:30 | Walter 接到电话，Jesse 在 RV 里醒来，情况紧急，两人惊慌失措。
2 | 00:15:25-00:16:56 | Walter 询问 Crazy8 的背景，得知他曾试图杀死他们。

"""

    # 添加剧情摘要
    if story_summary:
        prompt += f"\n【视频剧情摘要】:\n{story_summary}\n"
    else:
        prompt += "\n【视频剧情摘要】（请根据字幕内容分析生成）:\n\n"

    # 添加片段信息（包含每个片段对应的原始字幕）
    prompt += "\n【视频片段列表】（包含对应字幕）:\n"
    for i, clip in enumerate(clips, 1):
        start_time = clip.get('start_time', clip.get('start', '00:00:00'))
        end_time = clip.get('end_time', clip.get('end', '00:00:00'))

        # 查找该片段对应的字幕
        related_subtitles = find_related_subtitles(segments, start_time, end_time, padding=5)
        subtitle_text = ""
        if related_subtitles:
            subtitle_text = " | ".join([s['text'][:100] for s in related_subtitles[:3]])
            if len(" | ".join([s['text'] for s in related_subtitles[:3]])) > 200:
                subtitle_text = subtitle_text[:200] + "..."

        prompt += f"{i} | {start_time}-{end_time}"
        if subtitle_text:
            prompt += f" | 原文: {subtitle_text}"
        prompt += "\n"

    # 保存提示词到文件
    prompt_path = output_path.replace('.srt', '_prompt.txt')
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt)

    print(f"解说文案生成提示词已保存到: {prompt_path}")
    print("请使用 LLM 生成解说文案，然后手动创建 SRT 文件")

    return prompt_path


def create_narrator_srt_from_llm_output(clips, llm_output, output_path):
    """
    根据 LLM 输出创建解说文案 SRT

    Args:
        clips: 片段列表
        llm_output: LLM 生成的解说文案
        output_path: 输出 SRT 文件路径
    """
    # 解析 LLM 输出（需要按照约定格式）
    # 格式：片段编号 | 时间范围 | 建议解说文案
    lines = llm_output.strip().split('\n')

    with open(output_path, 'w', encoding='utf-8') as f:
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            # 尝试解析格式
            parts = line.split('|')
            if len(parts) >= 3:
                # 使用用户指定的时间范围
                time_range = parts[1].strip()
                start_time, end_time = time_range.split('-')
                narrator_text = parts[-1].strip()
            else:
                # 使用片段对应的时间
                if i <= len(clips):
                    clip = clips[i - 1]
                    start_time = clip['start_time']
                    end_time = clip['end_time']
                    narrator_text = line
                else:
                    continue

            # 写入 SRT
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{narrator_text}\n\n")

    print(f"解说文案字幕已生成: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='生成解说文案')
    parser.add_argument('--clips', required=True, help='片段信息 JSON 文件')
    parser.add_argument('--srt', required=True, help='完整字幕 SRT 文件')
    parser.add_argument('--output', required=True, help='输出文件路径')
    parser.add_argument('--narrator', help='LLM 生成的解说文案（可选）')
    parser.add_argument('--analysis', help='剧情分析 JSON 文件（包含剧情摘要）')

    args = parser.parse_args()

    # 加载片段信息
    with open(args.clips, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    # 支持从 clips 或 key_moments 中读取片段信息
    clips = manifest.get('clips', [])
    if not clips and 'key_moments' in manifest:
        # 将 key_moments 转换为 clips 格式
        clips = []
        for km in manifest['key_moments']:
            time_parts = km.get('time', '00:00:00').split(':')
            if len(time_parts) == 3:
                start_sec = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])
                # 每个片段默认持续 2 分钟
                end_sec = start_sec + 120
                clips.append({
                    'start_time': km.get('time', '00:00:00'),
                    'end_time': f"{int(end_sec // 3600):02d}:{int((end_sec % 3600) // 60):02d}:{int(end_sec % 60):02d}"
                })

    if args.narrator:
        # 直接从 LLM 输出创建 SRT
        create_narrator_srt_from_llm_output(clips, args.narrator, args.output)
    else:
        # 生成提示词供 LLM 使用
        generate_narrator_srt(clips, args.srt, args.output, args.analysis)


if __name__ == '__main__':
    main()
