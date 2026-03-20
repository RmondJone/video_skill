#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频解说文案生成脚本
根据 frame_descriptions.json 生成连贯的解说文案 SRT 字幕

功能：
1. 读取帧描述 JSON，分析整体叙事流程
2. 按指定间隔（默认4秒）生成连贯的解说文案
3. 支持多种解说风格
4. 确保时间轴与视频完全对齐
"""

import json
import math
import os
import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class NarrationStyle(Enum):
    """解说风格枚举"""
    HUMOR = "humor"           # 幽默风趣
    WARM = "warm"             # 温馨感人
    TECH = "tech"             # 科技硬核
    MYSTERY = "mystery"       # 悬疑烧脑
    HEALING = "healing"       # 解压治愈


@dataclass
class Subtitle:
    """字幕数据结构"""
    index: int
    start_ms: int
    end_ms: int
    text: str


@dataclass
class NarrativeParagraph:
    """叙事段落数据结构"""
    action: str              # 动作类型
    start_timestamp: str      # 开始时间戳
    start_ms: int            # 开始毫秒
    end_ms: int              # 结束毫秒
    frames: List[Dict]       # 包含的帧
    description_summary: str  # 描述摘要


def load_frame_descriptions(json_path: str) -> Dict[str, Any]:
    """加载帧描述 JSON"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def timestamp_to_ms(timestamp: str) -> int:
    """将 HH:MM:SS 转换为毫秒"""
    parts = timestamp.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000
    return 0


def format_time(ms: int) -> str:
    """毫秒转换为 SRT 时间格式 HH:MM:SS,mmm"""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def analyze_narrative_flow(frame_descriptions: List[Dict]) -> List[NarrativeParagraph]:
    """
    分析帧描述，提取叙事流程

    算法：
    1. 扫描所有帧描述，提取关键词（砍树、挖掘、搭建、烹饪等）
    2. 根据关键词将视频划分为若干叙事段落
    3. 每个段落有明确的主题和描述摘要

    Returns:
        叙事段落列表
    """
    # 动作关键词映射
    action_keywords = {
        "行走": "exploration",
        "进入": "exploration",
        "背": "exploration",
        "砍伐": "chopping",
        "斧头": "chopping",
        "劈": "chopping",
        "挖掘": "digging",
        "挖坑": "digging",
        "泥土": "digging",
        "搭建": "building",
        "框架": "building",
        "原木": "building",
        "放置": "building",
        "固定": "building",
        "捆绑": "building",
        "棒球帽": "unknown",  # 人物特征，不算动作
        "男性": "unknown",
    }

    paragraphs = []
    current_paragraph = None

    for i, frame in enumerate(frame_descriptions):
        desc = frame["description"]
        timestamp = frame["timestamp"]

        # 检测当前帧的动作类型
        detected_action = "unknown"
        for keyword, action_type in action_keywords.items():
            if keyword in desc:
                detected_action = action_type
                break

        # 如果动作类型发生变化，创建新段落
        if current_paragraph is None or detected_action != current_paragraph.action:
            if current_paragraph:
                # 结束当前段落
                current_paragraph.end_ms = timestamp_to_ms(timestamp) - 1
                paragraphs.append(current_paragraph)

            # 创建新段落
            current_paragraph = NarrativeParagraph(
                action=detected_action,
                start_timestamp=timestamp,
                start_ms=timestamp_to_ms(timestamp),
                end_ms=0,
                frames=[frame],
                description_summary=desc[:100] + "..." if len(desc) > 100 else desc
            )
        else:
            current_paragraph.frames.append(frame)

    # 添加最后一个段落
    if current_paragraph:
        # 最后一个段落的结束时间设置为视频总时长（后面会修正）
        paragraphs.append(current_paragraph)

    # 修正段落结束时间
    for i, para in enumerate(paragraphs):
        if i < len(paragraphs) - 1:
            para.end_ms = paragraphs[i + 1].start_ms - 1
        else:
            # 最后一个段落需要从外部设置结束时间
            pass

    return paragraphs


def get_action_display_name(action: str) -> str:
    """获取动作的中文显示名称"""
    action_names = {
        "exploration": "探索",
        "chopping": "砍伐",
        "digging": "挖掘",
        "building": "搭建",
        "unknown": "忙碌",
    }
    return action_names.get(action, "忙碌")


# ============ 幽默风趣风格解说 ============

HUMOR_NARRATIONS = {
    "exploration": [
        "今天的荒野求生正式开始了",
        "这位大哥大摇大摆走进森林",
        "看看今天又要折腾什么",
        "森林里空气清新，风景独好",
        "这位老铁步伐稳健，装备齐全",
        "感觉今天的任务不简单啊",
        "走一走，看一看，这片林子真不错",
    ],
    "chopping": [
        "这把斧头今天任务艰巨",
        "二话不说，直接开干",
        "这树怕是做梦都没想到",
        "一斧下去，木屑纷飞",
        "树木保护协会发来慰问",
        "这波操作666",
        "又一颗无辜的树木倒下了",
        "森林里的树都开始瑟瑟发抖",
        "大哥砍树，专注认真",
        "木屑像雪花一样飘落",
    ],
    "digging": [
        "接下来是挖掘时间",
        "这土挖得，相当认真",
        "徒手挖坑，纯粹的手艺人",
        "挖着挖着就挖出了成就感",
        "这坑怕是能挖出宝藏",
        "土地公表示很慌",
        "地底生物都被惊动了",
        "一铲一铲，都是心血",
        "挖掘技术哪家强，荒野大哥帮你忙",
    ],
    "building": [
        "建材已备好，开始搞基建",
        "没有钉子也要搞装修",
        "这结构看着就靠谱",
        "木工活儿玩得挺溜啊",
        "徒手搭框架，手艺绝了",
        "一木一枝，皆是心血",
        "没有图纸，全凭手感",
        "这框架，稳如老狗",
        "搭建工作有序进行",
        "越来越有样子了",
    ],
    "unknown": [
        "手上的活儿根本停不下来",
        "这位大哥忙得不亦乐乎",
        "专注的男人最帅",
        "看看这波操作",
        "认真工作中，请勿打扰",
        "这姿势很专业",
        "动作行云流水",
        "一切尽在掌握中",
    ],
}


# ============ 温馨感人风格解说 ============

WARM_NARRATIONS = {
    "exploration": [
        "在这片宁静的森林里",
        "他开始了今天的旅程",
        "感受大自然的馈赠",
        "每一步都是探索",
        "与自然和谐共处",
        "这片森林充满生机",
        "用脚步丈量世界",
    ],
    "chopping": [
        "一木一枝，皆是心血",
        "在这荒野之中",
        "他用自己的双手",
        "创造着属于自己的天地",
        "每一斧都带着专注",
        "木屑纷飞，是汗水的见证",
        "劳作的身影，温暖而有力量",
    ],
    "digging": [
        "大地承载着他的梦想",
        "一铲一铲",
        "挖掘的是希望",
        "在这片土地上",
        "留下自己的印记",
        "泥土的气息，是生活的气息",
    ],
    "building": [
        "用自己的双手",
        "搭建起温暖的庇护所",
        "每一根木枝",
        "都承载着对生活的热爱",
        "在这荒野之中",
        "创造出属于自己的小天地",
        "家就在眼前",
    ],
    "unknown": [
        "专注于当下",
        "享受这份宁静",
        "感受劳作的快乐",
        "每一步都是成长",
        "与大自然融为一体",
    ],
}


# ============ 科技硬核风格解说 ============

TECH_NARRATIONS = {
    "exploration": [
        "环境勘察开始",
        "评估周边资源分布",
        "记录地形地貌特征",
        "确定作业区域范围",
        "测量安全边际",
    ],
    "chopping": [
        "执行砍伐任务",
        "选择目标树木",
        "确定砍伐角度",
        "控制力道输出",
        "监测木材完整性",
        "评估木纤维结构",
        "记录砍伐效率",
    ],
    "digging": [
        "启动挖掘作业",
        "测量坑体深度",
        "分析土壤结构",
        "控制挖掘角度",
        "记录土层分布",
        "评估承载能力",
    ],
    "building": [
        "开始结构搭建",
        "校准水平度",
        "测试稳定性",
        "优化承重分布",
        "验证结构强度",
        "记录搭建参数",
    ],
    "unknown": [
        "执行预定操作",
        "监测作业进度",
        "记录关键参数",
        "确保作业安全",
        "评估工作质量",
    ],
}


# ============ 悬疑烧脑风格解说 ============

MYSTERY_NARRATIONS = {
    "exploration": [
        "他来到了这里",
        "看似普通的森林",
        "却藏着不为人知的秘密",
        "每一步都充满未知",
        "注意观察周围的环境",
        "细节决定成败",
    ],
    "chopping": [
        "这不是普通的砍树",
        "每一斧都有讲究",
        "看似随意的动作",
        "实则经过精密计算",
        "背后的逻辑是什么",
        "答案就藏在细节里",
    ],
    "digging": [
        "为什么选择在这里挖",
        "这个位置有什么特别",
        "挖掘的深度意味着什么",
        "每一下都在接近真相",
        "不要忽略任何线索",
    ],
    "building": [
        "这个结构不简单",
        "每根木头的位置",
        "都经过深思熟虑",
        "他要做什么",
        "答案即将揭晓",
        "谜底一点点浮出水面",
    ],
    "unknown": [
        "事情远没有看起来那么简单",
        "注意看",
        "这个细节很重要",
        "每一步都有深意",
        "真相就在眼前",
    ],
}


# ============ 解压治愈风格解说 ============

HEALING_NARRATIONS = {
    "exploration": [
        "远离喧嚣",
        "走进这片宁静的森林",
        "让心灵好好休息",
        "不急不躁",
        "慢慢来",
        "感受这一刻的美好",
    ],
    "chopping": [
        "木屑轻轻飘落",
        "节奏舒缓",
        "没有催促",
        "只有专注",
        "享受这份宁静",
        "让烦恼随风而去",
    ],
    "digging": [
        "泥土的气息",
        "纯净而自然",
        "一铲一铲",
        "身心放松",
        "没有目的",
        "只是享受过程",
    ],
    "building": [
        "慢慢来",
        "不着急",
        "一根一根",
        "用心摆放",
        "享受搭建的乐趣",
        "让时间慢下来",
    ],
    "unknown": [
        "什么都不用想",
        "专注于当下",
        "让思绪飘远",
        "享受这份宁静",
        "时间仿佛静止",
    ],
}


def get_narration_dict(style: str) -> Dict[str, List[str]]:
    """获取指定风格的解说文案库"""
    style_map = {
        "humor": HUMOR_NARRATIONS,
        "warm": WARM_NARRATIONS,
        "tech": TECH_NARRATIONS,
        "mystery": MYSTERY_NARRATIONS,
        "healing": HEALING_NARRATIONS,
    }
    return style_map.get(style, HUMOR_NARRATIONS)


def generate_human_readable_narration(
    paragraphs: List[NarrativeParagraph],
    video_duration: float,
    style: str,
    interval: float = 4.0
) -> List[str]:
    """
    生成人类可读的连贯解说文案

    特点：
    1. 根据段落时长均匀分配解说文案
    2. 整体叙事连贯，前后呼应
    3. 避免重复，使用自然的文案轮询

    Returns:
        解说文案列表
    """
    narration_dict = get_narration_dict(style)

    # 计算总需要的字幕数量
    total_subs_needed = math.ceil(video_duration / interval)

    # 扩展每个动作类型的文案库（通过自然过渡实现去重）
    def expand_narrations(narration_list: List[str], needed: int) -> List[str]:
        """扩展文案列表，使用自然的过渡变化避免重复"""
        if needed <= len(narration_list):
            return narration_list[:needed]

        result = list(narration_list)  # 先复制所有基础文案
        idx = len(narration_list)

        # 自然过渡词库
        transitions = [
            "然后", "接下来", "继续", "与此同时", "与此同时",
            "在此期间", "与此同时", "经过一番努力",
            "功夫不负有心人", "付出总有回报",
        ]

        while len(result) < needed:
            base_idx = (idx - len(narration_list)) % len(narration_list)
            base = narration_list[base_idx]
            trans_idx = (idx // len(narration_list)) - 1

            # 使用过渡词连接
            transition = transitions[trans_idx % len(transitions)]
            result.append(f"{transition}，{base}")

            idx += 1

        return result

    # 按段落分配字幕数量
    paragraph_narrations = []
    paragraph_durations = []

    total_para_duration = sum(
        (para.end_ms - para.start_ms) / 1000 if para.end_ms > 0 else 0
        for para in paragraphs
    )

    for para in paragraphs:
        action = para.action
        action_narrations = narration_dict.get(action, narration_dict["unknown"])

        # 根据段落时长比例分配字幕数
        para_duration = (para.end_ms - para.start_ms) / 1000 if para.end_ms > 0 else interval
        if total_para_duration > 0:
            para_share = max(1, round((para_duration / total_para_duration) * total_subs_needed))
        else:
            para_share = max(1, round(total_subs_needed / len(paragraphs)))

        # 扩展该段落需要的文案
        expanded = expand_narrations(action_narrations, para_share)
        paragraph_narrations.append(expanded)
        paragraph_durations.append(para_duration)

    # 合并所有段落文案
    all_narrations = []
    for i, expanded in enumerate(paragraph_narrations):
        for text in expanded:
            if len(all_narrations) < total_subs_needed:
                all_narrations.append(text)

    # 确保第一个文案有欢迎语
    if all_narrations:
        all_narrations[0] = f"欢迎来到荒野求生，{all_narrations[0]}"

    return all_narrations[:total_subs_needed]


def generate_srt_subtitles(
    paragraphs: List[NarrativeParagraph],
    video_duration: float,
    style: str,
    interval: float = 4.0
) -> List[Subtitle]:
    """
    生成SRT字幕，确保时间轴完全对齐

    Args:
        paragraphs: 叙事段落列表
        video_duration: 视频总时长（秒）
        style: 解说风格
        interval: 字幕间隔（秒）

    Returns:
        字幕列表
    """
    # 生成解说文案
    narrations = generate_human_readable_narration(paragraphs, video_duration, style, interval)

    # 生成字幕
    subtitles = []
    total_subs = len(narrations)

    for i, text in enumerate(narrations):
        start_ms = int(i * interval * 1000)
        end_ms = int(min((i + 1) * interval * 1000, video_duration * 1000))

        # 确保最后一条字幕覆盖完整视频
        if i == total_subs - 1 and end_ms < video_duration * 1000:
            end_ms = int(video_duration * 1000)

        subtitles.append(Subtitle(
            index=i + 1,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text
        ))

    return subtitles


def export_to_srt(subtitles: List[Subtitle], output_path: str):
    """导出为SRT文件"""
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for subtitle in subtitles:
            f.write(f"{subtitle.index}\n")
            f.write(f"{format_time(subtitle.start_ms)} --> {format_time(subtitle.end_ms)}\n")
            f.write(f"{subtitle.text}\n")
            f.write("\n")


def print_paragraphs_summary(paragraphs: List[NarrativeParagraph]):
    """打印段落摘要"""
    print(f"\n叙事段落分析 ({len(paragraphs)} 个段落):")
    print("-" * 60)
    for i, para in enumerate(paragraphs):
        duration_ms = para.end_ms - para.start_ms if para.end_ms > 0 else 0
        duration_sec = duration_ms / 1000
        print(f"段落 {i+1}: {get_action_display_name(para.action)} | "
              f"{para.start_timestamp} | 约 {duration_sec:.0f}秒 | "
              f"{len(para.frames)} 帧")
    print("-" * 60)


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("用法: python generate_narration.py <frame_descriptions.json> <output.srt> [style] [interval]")
        print()
        print("参数:")
        print("  frame_descriptions.json  - 帧描述JSON文件路径")
        print("  output.srt              - 输出SRT文件路径")
        print("  style                   - 解说风格 (humor/warm/tech/mystery/healing)")
        print("  interval                - 字幕间隔秒数 (默认4秒)")
        print()
        print("示例:")
        print("  python generate_narration.py output/frame_descriptions.json output/narration.srt humor 4")
        print("  python generate_narration.py output/frame_descriptions.json output/narration_warm.srt warm 4")
        print()
        print("风格说明:")
        print("  humor   - 幽默风趣，轻松诙谐")
        print("  warm    - 温馨感人，温暖治愈")
        print("  tech    - 科技硬核，专业严谨")
        print("  mystery - 悬疑烧脑，紧张刺激")
        print("  healing - 解压治愈，放松舒缓")
        sys.exit(1)

    json_path = sys.argv[1]
    output_path = sys.argv[2]
    style = sys.argv[3] if len(sys.argv) > 3 else "humor"
    interval = float(sys.argv[4]) if len(sys.argv) > 4 else 4.0

    print("=" * 60)
    print("视频解说文案生成器")
    print("=" * 60)

    # 加载帧描述
    print(f"\n加载帧描述: {json_path}")
    data = load_frame_descriptions(json_path)
    video_duration = data["video_duration"]
    frame_descriptions = data["frame_descriptions"]

    print(f"视频时长: {video_duration:.1f}秒")
    print(f"帧数: {len(frame_descriptions)}帧")
    print(f"解说风格: {style}")
    print(f"字幕间隔: {interval}秒")

    # 分析叙事流程
    print("\n分析叙事流程...")
    paragraphs = analyze_narrative_flow(frame_descriptions)

    # 设置最后一个段落的结束时间
    if paragraphs:
        paragraphs[-1].end_ms = int(video_duration * 1000)

    print_paragraphs_summary(paragraphs)

    # 生成字幕
    print(f"\n生成SRT字幕...")
    subtitles = generate_srt_subtitles(paragraphs, video_duration, style, interval)

    # 导出
    print(f"导出到: {output_path}")
    export_to_srt(subtitles, output_path)

    # 输出摘要
    print("\n" + "=" * 60)
    print("生成完成!")
    print(f"  字幕总数: {len(subtitles)}条")
    print(f"  视频时长: {video_duration:.1f}秒")
    print(f"  第一条: {format_time(subtitles[0].start_ms)} --> {format_time(subtitles[0].end_ms)}")
    print(f"  最后一条: {format_time(subtitles[-1].start_ms)} --> {format_time(subtitles[-1].end_ms)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
