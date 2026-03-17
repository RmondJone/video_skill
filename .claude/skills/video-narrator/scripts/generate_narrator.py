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


def list_all_clips(clips, key_moments=None):
    """
    列出所有关键片段供用户选择

    Args:
        clips: 片段列表
        key_moments: 关键情节列表（用于显示详细描述）

    Returns:
        用户选择的片段列表
    """
    print("\n" + "="*60)
    print("请从以下关键片段中选择要保留的解说片段")
    print("="*60)
    print(f"\n共有 {len(clips)} 个关键片段可供选择\n")

    # 显示所有片段
    for i, clip in enumerate(clips, 1):
        start_time = clip.get('start_time', clip.get('start', '00:00:00'))
        end_time = clip.get('end_time', clip.get('end', '00:00:00'))
        importance = clip.get('importance', '中')
        description = clip.get('description', '')

        # 查找详细描述
        detailed_desc = ""
        if key_moments:
            try:
                start_sec = time_to_seconds(start_time)
                for km in key_moments:
                    km_sec = time_to_seconds(km.get('time', '00:00:00'))
                    if abs(km_sec - start_sec) < 30:
                        detailed_desc = km.get('detailed_description', '')
                        break
            except:
                pass

        # 重要性显示为 emoji
        importance_emoji = {
            '极高': '🔴',
            '高': '🟠',
            '中': '🟡',
            'low': '🟡',
            'high': '🟠',
            'medium': '🟡'
        }.get(str(importance).lower(), '🟡')

        print(f"[{i:2d}] {importance_emoji} {start_time} - {end_time} | {importance}")
        print(f"     {description}")
        if detailed_desc:
            # 截断过长的描述
            if len(detailed_desc) > 100:
                detailed_desc = detailed_desc[:100] + "..."
            print(f"     📝 {detailed_desc}")
        print()

    print("-"*60)
    print("选择方式：")
    print("  - 输入片段编号，用逗号分隔，如：1,3,5,8")
    print("  - 输入范围，如：1-10 表示选择前10个")
    print("  - 输入 all 表示选择全部")
    print("  - 输入数字+[a] 选择重要性为高及以上的，如：10a 表示选10个高重要性的")
    print("-"*60)

    while True:
        user_input = input("\n请输入您的选择: ").strip()

        if user_input.lower() == 'all':
            # 选择全部
            selected = clips
            break

        # 尝试解析范围格式：1-10
        if '-' in user_input and not user_input.startswith('-'):
            try:
                parts = user_input.split('-')
                start_idx = int(parts[0])
                end_idx = int(parts[1])
                if 1 <= start_idx <= end_idx <= len(clips):
                    selected = clips[start_idx-1:end_idx]
                    break
                else:
                    print(f"编号范围无效，请输入 1-{len(clips)} 之间的数字")
            except:
                print("输入格式有误，请重新输入")
                continue

        # 尝试解析逗号分隔格式：1,3,5,8
        try:
            indices = []
            for part in user_input.split(','):
                part = part.strip()
                if part:
                    indices.append(int(part))
            if indices and all(1 <= idx <= len(clips) for idx in indices):
                selected = [clips[idx-1] for idx in indices]
                break
            else:
                print(f"编号无效，请输入 1-{len(clips)} 之间的数字")
        except:
            print("输入格式有误，请重新输入")

    # 按时间排序
    selected.sort(key=lambda x: time_to_seconds(x.get('start_time', x.get('start', '00:00:00'))))

    print(f"\n✅ 已选择 {len(selected)} 个片段")

    return selected


def select_clips_by_args(clips, user_input):
    """
    通过命令行参数选择片段（非交互式）

    Args:
        clips: 片段列表
        user_input: 用户输入的字符串，如 "1,3,5,8" 或 "1-10" 或 "all"

    Returns:
        用户选择的片段列表
    """
    user_input = user_input.strip()

    if user_input.lower() == 'all':
        selected = clips
    # 尝试解析范围格式：1-10
    elif '-' in user_input and not user_input.startswith('-'):
        try:
            parts = user_input.split('-')
            start_idx = int(parts[0])
            end_idx = int(parts[1])
            if 1 <= start_idx <= end_idx <= len(clips):
                selected = clips[start_idx-1:end_idx]
            else:
                print(f"编号范围无效，请输入 1-{len(clips)} 之间的数字")
                return None
        except:
            print("输入格式有误，请重新输入")
            return None
    # 尝试解析逗号分隔格式：1,3,5,8
    else:
        try:
            indices = []
            for part in user_input.split(','):
                part = part.strip()
                if part:
                    indices.append(int(part))
            if indices and all(1 <= idx <= len(clips) for idx in indices):
                selected = [clips[idx-1] for idx in indices]
            else:
                print(f"编号无效，请输入 1-{len(clips)} 之间的数字")
                return None
        except:
            print("输入格式有误，请重新输入")
            return None

    # 按时间排序
    selected.sort(key=lambda x: time_to_seconds(x.get('start_time', x.get('start', '00:00:00'))))

    print(f"\n✅ 已通过命令行选择 {len(selected)} 个片段")

    return selected


def select_key_clips(clips, max_clips=15, importance_weight=None):
    """
    选取关键片段

    Args:
        clips: 原始片段列表
        max_clips: 最大保留片段数（默认15个，约10分钟解说）
        importance_weight: 重要性权重

    Returns:
        筛选后的片段列表
    """
    if importance_weight is None:
        importance_weight = {'极高': 3, '高': 2, '中': 1, '低': 0}

    # 给片段打分
    scored_clips = []
    for clip in clips:
        importance = clip.get('importance', clip.get('importance', '中'))
        score = importance_weight.get(importance, 1)

        # 获取时间
        start_time = clip.get('start_time', clip.get('start', '00:00:00'))
        end_time = clip.get('end_time', clip.get('end', '00:00:00'))

        # 计算时长
        try:
            start_sec = time_to_seconds(start_time)
            end_sec = time_to_seconds(end_time)
            duration = end_sec - start_sec
        except:
            duration = 120

        # 时长太长或太短的扣分
        if duration > 180:  # 超过3分钟
            score -= 1
        elif duration < 30:  # 少于30秒
            score -= 0.5

        scored_clips.append({
            'clip': clip,
            'score': score,
            'start_sec': start_sec if 'start_sec' in locals() else 0
        })

    # 按重要性排序，然后按时间排序
    scored_clips.sort(key=lambda x: (-x['score'], x['start_sec']))

    # 取前 max_clips 个
    selected = [item['clip'] for item in scored_clips[:max_clips]]

    # 按时间排序
    selected.sort(key=lambda x: time_to_seconds(x.get('start_time', x.get('start', '00:00:00'))))

    return selected


def generate_narrator_srt(clips, full_srt_path, output_path, analysis_json_path=None,
                          max_clips=20, clip_duration=30):
    """
    生成解说文案 SRT 文件

    这个脚本生成一个模板，实际的解说文案需要 LLM 生成

    Args:
        clips: 片段列表
        full_srt_path: 完整字幕路径
        output_path: 输出路径
        analysis_json_path: 剧情分析 JSON 路径
        max_clips: 最大片段数（默认20个，约10分钟）
        clip_duration: 每个片段默认时长（秒，默认30秒）
    """
    # 加载完整字幕
    full_srt = load_srt(full_srt_path)
    segments = parse_srt_to_segments(full_srt)

    # 筛选关键片段
    selected_clips = select_key_clips(clips, max_clips=max_clips)

    print(f"已从 {len(clips)} 个片段中精选 {len(selected_clips)} 个关键片段")
    print(f"预计解说时长: 约 {len(selected_clips) * clip_duration // 60} 分钟")

    # 尝试加载剧情摘要
    story_summary = ""
    key_moments = []
    if analysis_json_path and os.path.exists(analysis_json_path):
        try:
            with open(analysis_json_path, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)

            # 提取剧情摘要
            if 'summary' in analysis_data:
                story_summary = analysis_data['summary']

            # 提取关键情节节点
            if 'key_moments' in analysis_data:
                key_moments = analysis_data['key_moments']
        except Exception as e:
            print(f"警告: 读取剧情摘要失败: {e}", file=sys.stderr)

    # 构建提示词（供 LLM 使用）
    prompt = f"""# 视频解说文案生成任务

你是专业的视频解说专家。请为以下视频生成引人入胜的中文解说文案。

## 核心要求

1. **精简有力**：每个片段 {clip_duration} 秒左右，4-5 句话
2. **戏剧性**：用问题、悬念、对比吸引观众
3. **画面感**：描述观众能看到的内容，而不是简单复述对话
4. **专业感**：适当使用专业术语或点评，增加深度

## 输出格式

SRT 字幕格式：
```
序号
开始时间 --> 结束时间
解说文案

序号
开始时间 --> 结束时间
解说文案
```

## 视频信息

"""

    # 添加剧情摘要
    if story_summary:
        prompt += f"【剧情概要】\n{story_summary}\n\n"

    # 添加视频信息
    prompt += f"【视频总时长】: 约 48 分钟\n"
    prompt += f"【解说目标时长】: 约 {len(selected_clips) * clip_duration // 60} 分钟\n"
    prompt += f"【片段数量】: {len(selected_clips)} 个\n\n"

    # 添加解说要点（从 key_moments 中提取）
    if key_moments:
        prompt += "【关键情节参考】:\n"
        for km in key_moments[:20]:
            if km.get('importance') in ['极高', '高', 'high']:
                prompt += f"- {km.get('time', '')} | {km.get('description', '')}\n"
        prompt += "\n"

    # 添加片段信息
    prompt += f"【解说片段】(共 {len(selected_clips)} 个):\n\n"

    for i, clip in enumerate(selected_clips, 1):
        start_time = clip.get('start_time', clip.get('start', '00:00:00'))
        end_time = clip.get('end_time', clip.get('end', '00:00:00'))

        # 计算实际时长
        try:
            start_sec = time_to_seconds(start_time)
            end_sec = time_to_seconds(end_time)
            duration = end_sec - start_sec
        except:
            duration = clip_duration

        # 限制解说时长
        if duration > clip_duration * 1.5:
            # 如果原始片段太长，截取精华部分
            adjusted_end_sec = start_sec + clip_duration
            end_time = format_timestamp(adjusted_end_sec)
            duration = clip_duration

        # 查找该片段对应的字幕（用于参考）
        related_subtitles = find_related_subtitles(segments, start_time, end_time, padding=5)
        subtitle_text = ""
        if related_subtitles:
            # 取前3条字幕
            texts = [s['text'][:80] for s in related_subtitles[:3]]
            subtitle_text = " | ".join(texts)

        # 获取重要性描述
        importance = clip.get('importance', '中')

        prompt += f"### 片段 {i} [{start_time} - {end_time}] (约 {duration}秒, 重要性: {importance})\n"

        if subtitle_text:
            prompt += f"原文参考: {subtitle_text}\n"

        # 添加剧情背景
        if key_moments:
            # 找对应的关键情节
            for km in key_moments:
                km_time = km.get('time', '00:00:00')
                try:
                    km_sec = time_to_seconds(km_time)
                    if abs(km_sec - start_sec) < 30:
                        prompt += f"情节: {km.get('description', '')}\n"
                        if km.get('detailed_description'):
                            prompt += f"详情: {km.get('detailed_description', '')[:100]}...\n"
                        break
                except:
                    pass

        prompt += "\n"

    prompt += """
## 解说技巧参考

### 不好的解说（太无聊）：
"Jesse感谢Walter的救命之恩，他们的车陷进了沟渠。"

### 好的解说（有戏剧性）：
"车陷沟渠、咖啡洒裤，Jesse快要崩溃了。但更糟的是——RV里还有一个人没死！"

### 不好的解说（太流水账）：
"Walter在课堂上讲授化学，他解释了手性分子的概念。"

### 好的解说（有意思）：
"讲台上的Walter还不知道，几天后他会把课堂上学到的化学知识，用来溶解一具尸体。"

---

请直接生成 SRT 格式的解说文案，不要添加其他说明。"""

    # 保存提示词到文件
    prompt_path = output_path.replace('.srt', '_prompt.txt')
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt)

    print(f"解说文案生成提示词已保存到: {prompt_path}")
    print(f"请使用 LLM 生成解说文案，然后手动创建 SRT 文件")
    print(f"\n提示：解说目标时长约 {len(selected_clips) * clip_duration // 60} 分钟，共 {len(selected_clips)} 个片段")

    return prompt_path, selected_clips


def generate_prompt_for_selected_clips(selected_clips, all_clips, full_srt_path, output_path,
                                      analysis_json_path=None, clip_duration=30):
    """
    为用户选择的片段生成解说文案提示词

    Args:
        selected_clips: 用户选择的片段列表
        all_clips: 所有原始片段列表
        full_srt_path: 完整字幕路径
        output_path: 输出路径
        analysis_json_path: 剧情分析 JSON 路径
        clip_duration: 每个片段默认时长
    """
    # 加载完整字幕
    full_srt = load_srt(full_srt_path)
    segments = parse_srt_to_segments(full_srt)

    print(f"\n✅ 已选择 {len(selected_clips)} 个片段")
    print(f"预计解说时长: 约 {len(selected_clips) * clip_duration // 60} 分钟")

    # 尝试加载剧情摘要
    story_summary = ""
    key_moments = []
    if analysis_json_path and os.path.exists(analysis_json_path):
        try:
            with open(analysis_json_path, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)

            # 提取剧情摘要
            if 'summary' in analysis_data:
                story_summary = analysis_data['summary']

            # 提取关键情节节点
            if 'key_moments' in analysis_data:
                key_moments = analysis_data['key_moments']
        except Exception as e:
            print(f"警告: 读取剧情摘要失败: {e}", file=sys.stderr)

    # 构建提示词
    prompt = f"""# 视频解说文案生成任务

你是专业的视频解说专家。请为以下视频生成引人入胜的中文解说文案。

## 核心要求

1. **精简有力**：每个片段 {clip_duration} 秒左右，4-5 句话
2. **戏剧性**：用问题、悬念、对比吸引观众
3. **画面感**：描述观众能看到的内容，而不是简单复述对话
4. **专业感**：适当使用专业术语或点评，增加深度

## 输出格式

SRT 字幕格式：
```
序号
开始时间 --> 结束时间
解说文案

序号
开始时间 --> 结束时间
解说文案
```

## 视频信息

"""

    # 添加剧情摘要
    if story_summary:
        prompt += f"【剧情概要】\n{story_summary}\n\n"

    # 添加视频信息
    prompt += f"【视频总时长】: 约 48 分钟\n"
    prompt += f"【解说目标时长】: 约 {len(selected_clips) * clip_duration // 60} 分钟\n"
    prompt += f"【片段数量】: {len(selected_clips)} 个\n\n"

    # 添加解说要点（从 key_moments 中提取）
    if key_moments:
        prompt += "【关键情节参考】:\n"
        for km in key_moments:
            if km.get('importance') in ['极高', '高', 'high']:
                prompt += f"- {km.get('time', '')} | {km.get('description', '')}\n"
        prompt += "\n"

    # 添加用户选择的片段信息
    prompt += f"【解说片段】(共 {len(selected_clips)} 个，用户已选择):\n\n"

    for i, clip in enumerate(selected_clips, 1):
        start_time = clip.get('start_time', clip.get('start', '00:00:00'))
        end_time = clip.get('end_time', clip.get('end', '00:00:00'))

        # 计算实际时长
        try:
            start_sec = time_to_seconds(start_time)
            end_sec = time_to_seconds(end_time)
            duration = end_sec - start_sec
        except:
            duration = clip_duration

        # 限制解说时长
        if duration > clip_duration * 1.5:
            adjusted_end_sec = start_sec + clip_duration
            end_time = format_timestamp(adjusted_end_sec)
            duration = clip_duration

        # 查找该片段对应的字幕
        related_subtitles = find_related_subtitles(segments, start_time, end_time, padding=5)
        subtitle_text = ""
        if related_subtitles:
            texts = [s['text'][:80] for s in related_subtitles[:3]]
            subtitle_text = " | ".join(texts)

        # 获取重要性描述
        importance = clip.get('importance', '中')

        prompt += f"### 片段 {i} [{start_time} - {end_time}] (约 {duration}秒, 重要性: {importance})\n"

        if subtitle_text:
            prompt += f"原文参考: {subtitle_text}\n"

        # 添加剧情背景
        if key_moments:
            for km in key_moments:
                km_time = km.get('time', '00:00:00')
                try:
                    km_sec = time_to_seconds(km_time)
                    if abs(km_sec - start_sec) < 30:
                        prompt += f"情节: {km.get('description', '')}\n"
                        if km.get('detailed_description'):
                            prompt += f"详情: {km.get('detailed_description', '')[:100]}...\n"
                        break
                except:
                    pass

        prompt += "\n"

    prompt += """
## 解说技巧参考

### 不好的解说（太无聊）：
"Jesse感谢Walter的救命之恩，他们的车陷进了沟渠。"

### 好的解说（有戏剧性）：
"车陷沟渠、咖啡洒裤，Jesse快要崩溃了。但更糟的是——RV里还有一个人没死！"

### 不好的解说（太流水账）：
"Walter在课堂上讲授化学，他解释了手性分子的概念。"

### 好的解说（有意思）：
"讲台上的Walter还不知道，几天后他会把课堂上学到的化学知识，用来溶解一具尸体。"

---

请直接生成 SRT 格式的解说文案，不要添加其他说明。"""

    # 保存提示词到文件
    prompt_path = output_path.replace('.srt', '_prompt.txt')
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt)

    print(f"解说文案生成提示词已保存到: {prompt_path}")
    print(f"请使用 LLM 生成解说文案，然后手动创建 SRT 文件")

    return prompt_path, selected_clips


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
    parser.add_argument('--max-clips', type=int, default=20, help='最大片段数（默认20个，约10分钟）')
    parser.add_argument('--clip-duration', type=int, default=30, help='每个片段默认时长秒数（默认30秒）')
    parser.add_argument('--interactive', action='store_true', help='交互式选择片段（列出所有关键片段供用户选择）')
    parser.add_argument('--select', type=str, help='通过命令行选择片段（可选，指定片段编号：1,3,5,8 或范围：1-10 或 all）')
    parser.add_argument('--list-only', action='store_true', help='仅列出片段，不生成解说文案')

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
                # 每个片段默认持续指定时长
                end_sec = start_sec + args.clip_duration
                clips.append({
                    'start_time': km.get('time', '00:00:00'),
                    'end_time': f"{int(end_sec // 3600):02d}:{int((end_sec % 3600) // 60):02d}:{int(end_sec % 60):02d}",
                    'importance': km.get('importance', '中'),
                    'description': km.get('description', ''),
                    'detailed_description': km.get('detailed_description', '')
                })

    # 加载关键情节（用于显示详细描述）
    key_moments = []
    if args.analysis and os.path.exists(args.analysis):
        try:
            with open(args.analysis, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
            key_moments = analysis_data.get('key_moments', [])
        except:
            pass

    if args.narrator:
        # 直接从 LLM 输出创建 SRT
        create_narrator_srt_from_llm_output(clips, args.narrator, args.output)
    elif args.select:
        # 命令行选择模式（通过 --select 参数指定选择）
        selected_clips = select_clips_by_args(clips, args.select)
        if selected_clips is None:
            return

        # 如果只是列出选择，不生成文案
        if args.list_only:
            print(f"\n已选择 {len(selected_clips)} 个片段:")
            for i, clip in enumerate(selected_clips, 1):
                print(f"  {i}. {clip.get('start_time')} - {clip.get('end_time')} | {clip.get('description')}")
            return

        # 生成选定片段的解说文案
        generate_prompt_for_selected_clips(selected_clips, clips, args.srt, args.output, args.analysis,
                                          clip_duration=args.clip_duration)
    elif args.interactive:
        # 交互式选择模式：列出所有片段供用户选择（仅在本地终端可用）
        # 如果提供了 --select 参数，直接使用命令行选择
        if args.select:
            selected_clips = select_clips_by_args(clips, args.select)
            if selected_clips is None:
                return
            print(f"\n✅ 已通过 --select 参数选择 {len(selected_clips)} 个片段")
        elif args.list_only:
            # 如果只是列出片段（--list-only），则打印片段列表后退出，不等待输入
            print(f"\n共有 {len(clips)} 个关键片段可供选择:\n")
            for i, clip in enumerate(clips, 1):
                start_time = clip.get('start_time', clip.get('start', '00:00:00'))
                end_time = clip.get('end_time', clip.get('end', '00:00:00'))
                importance = clip.get('importance', '中')
                description = clip.get('description', '')

                importance_emoji = {
                    '极高': '🔴',
                    '高': '🟠',
                    '中': '🟡',
                    'low': '🟡',
                    'high': '🟠',
                    'medium': '🟡'
                }.get(str(importance).lower(), '🟡')

                print(f"[{i:2d}] {importance_emoji} {start_time} - {end_time} | {importance}")
                print(f"     {description}")
                print()

            print("-"*60)
            print("选择方式：")
            print("  - 输入片段编号，用逗号分隔，如：1,3,5,8")
            print("  - 输入范围，如：1-10 表示选择前10个")
            print("  - 输入 all 表示选择全部")
            print("  - 使用 --select 参数直接指定选择，如：--select 1,3,5,8")
            print("-"*60)
            return
        else:
            # 尝试交互式选择，如果失败则自动选择高重要性及以上的片段
            try:
                selected_clips = list_all_clips(clips, key_moments)
            except EOFError:
                # 自动化环境无法获取输入时，自动选择高重要性及以上的片段
                print("\n⚠️ 无法获取交互式输入，自动选择高重要性及以上的片段")
                high_importance = ['极高', '高']
                selected_clips = [clip for clip in clips if clip.get('importance', '中') in high_importance]
                if not selected_clips:
                    selected_clips = clips
                print(f"✅ 已自动选择 {len(selected_clips)} 个高重要性片段")

        # 如果只是列出选择，不生成文案
        if args.list_only:
            print(f"\n已选择 {len(selected_clips)} 个片段:")
            for i, clip in enumerate(selected_clips, 1):
                print(f"  {i}. {clip.get('start_time')} - {clip.get('end_time')} | {clip.get('description')}")
            return

        # 生成选定片段的解说文案
        # 继续调用 generate_narrator_srt 生成提示词
        generate_prompt_for_selected_clips(selected_clips, clips, args.srt, args.output, args.analysis,
                                          clip_duration=args.clip_duration)
    else:
        # 自动选择模式（原有逻辑）
        generate_narrator_srt(clips, args.srt, args.output, args.analysis,
                            max_clips=args.max_clips,
                            clip_duration=args.clip_duration)


if __name__ == '__main__':
    main()
