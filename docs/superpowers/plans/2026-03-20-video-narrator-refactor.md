# Video Recognition 解说生成重构计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 video-recognition 技能的解说文案生成部分，生成连贯的、解说任务流程的SRT字幕，字幕间隙4秒，整体前后呼应。

**Architecture:**
- 新增 `scripts/generate_narration.py` 脚本
- 读取 `frame_descriptions.json` 分析整体叙事流程
- 按4秒一条生成连贯的解说文案
- 支持多种风格选项
- 确保时间轴与视频完全对齐

**Tech Stack:** Python 3, JSON, SRT字幕格式

---

## Chunk 1: 需求分析与脚本设计

### Task 1: 创建 generate_narration.py 脚本框架

**Files:**
- Create: `.claude/skills/video-recognition/scripts/generate_narration.py`

- [ ] **Step 1: 创建脚本基本框架**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频解说文案生成脚本
根据 frame_descriptions.json 生成连贯的解说文案 SRT 字幕

功能：
1. 读取帧描述 JSON，分析整体叙事流程
2. 按4秒一条生成连贯的解说文案
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


def load_frame_descriptions(json_path: str) -> Dict[str, Any]:
    """加载帧描述 JSON"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_time(ms: int) -> str:
    """毫秒转换为 SRT 时间格式 HH:MM:SS,mmm"""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("用法: python generate_narration.py <frame_descriptions.json> <output.srt> [style] [interval]")
        print("示例: python generate_narration.py output/frame_descriptions.json output/narration.srt humor 4")
        sys.exit(1)

    json_path = sys.argv[1]
    output_path = sys.argv[2]
    style = sys.argv[3] if len(sys.argv) > 3 else "humor"
    interval = float(sys.argv[4]) if len(sys.argv) > 4 else 4.0

    print(f"加载帧描述: {json_path}")
    data = load_frame_descriptions(json_path)
    print(f"视频时长: {data['video_duration']}秒")
    print(f"风格: {style}")
    print(f"字幕间隔: {interval}秒")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行测试脚本框架**

Run: `python .claude/skills/video-recognition/scripts/generate_narration.py`
Expected: 显示帮助信息

---

## Chunk 2: 叙事流程分析器

### Task 2: 实现叙事流程分析功能

**Files:**
- Modify: `.claude/skills/video-recognition/scripts/generate_narration.py`

**核心设计思路：**
```
输入：frame_descriptions.json (87帧 x 10秒间隔 = 870秒视频)
输出：
- 将视频划分为若干「叙事段落」
- 每个段落有明确的主题（如：开场、砍树、挖坑、搭建等）
- 每个段落内生成连贯的解说文案
- 按4秒一条输出SRT
```

- [ ] **Step 1: 添加叙事段落分析函数**

```python
def analyze_narrative_flow(frame_descriptions: List[Dict]) -> List[Dict]:
    """
    分析帧描述，提取叙事流程

    算法：
    1. 扫描所有帧描述，提取关键词（砍树、挖掘、搭建、烹饪等）
    2. 根据关键词将视频划分为若干叙事段落
    3. 每个段落包含：时间范围、主题、关键动作

    Returns:
        叙事段落列表
    """
    # 动作关键词映射
    action_keywords = {
        "行走": "exploration",
        "砍伐": "chopping",
        "挖掘": "digging",
        "搭建": "building",
        "搬运": "carrying",
        "敲击": "hammering",
        "切割": "cutting",
        "烹饪": "cooking",
        "整理": "organizing",
    }

    paragraphs = []
    current_paragraph = None

    for frame in frame_descriptions:
        desc = frame["description"]
        timestamp = frame["timestamp"]

        # 检测当前帧的动作类型
        detected_action = None
        for keyword, action_type in action_keywords.items():
            if keyword in desc:
                detected_action = action_type
                break

        # 如果动作类型发生变化，创建新段落
        if current_paragraph is None or (detected_action and detected_action != current_paragraph.get("action")):
            if current_paragraph:
                paragraphs.append(current_paragraph)
            current_paragraph = {
                "action": detected_action or "unknown",
                "start_timestamp": timestamp,
                "start_ms": timestamp_to_ms(timestamp),
                "frames": [frame]
            }
        else:
            current_paragraph["frames"].append(frame)

    # 添加最后一个段落
    if current_paragraph:
        paragraphs.append(current_paragraph)

    return paragraphs


def timestamp_to_ms(timestamp: str) -> int:
    """将 HH:MM:SS 转换为毫秒"""
    parts = timestamp.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000
    return 0
```

- [ ] **Step 2: 测试叙事流程分析**

Run: `python -c "from generate_narration import analyze_narrative_flow; import json; data=json.load(open('output/frame_descriptions.json')); result=analyze_narrative_flow(data['frame_descriptions']); print(len(result), 'paragraphs')"`
Expected: 输出段落数量

---

## Chunk 3: 连贯解说文案生成器

### Task 3: 实现各风格的连贯解说生成

**Files:**
- Modify: `.claude/skills/video-recognition/scripts/generate_narration.py`

- [ ] **Step 1: 添加幽默风格解说生成器**

```python
def generate_humor_narration_for_paragraph(paragraph: Dict, global_index: int) -> List[str]:
    """
    为叙事段落生成幽默风格的连贯解说

    特点：
    - 开头有引入
    - 中间有过程描述
    - 结尾有总结或过渡
    - 整体叙事连贯，前后呼应
    """
    action = paragraph["action"]
    frame_count = len(paragraph["frames"])

    narrations = []

    # 根据动作类型生成不同的解说序列
    if action == "exploration":
        narrations = [
            "今天的荒野求生开始了",
            "看看这位大哥又要整什么活",
            "森林里空气真不错",
        ]
    elif action == "chopping":
        narrations = [
            "这棵树怕是要退休了",
            "大哥抡起斧头就开始干",
            "树木保护协会表示很慌",
            "木屑纷飞，场面一度很混乱",
            "这树倒了，大地都震了一下",
        ]
    elif action == "digging":
        narrations = [
            "接下来是挖掘时间",
            "这土挖得，地底生物都惊动了",
            "徒手挖坑，纯粹的手艺人",
            "挖着挖着就挖出了成就感",
        ]
    elif action == "building":
        narrations = [
            "建材已备好，开始搞基建",
            "没有钉子也要搞装修",
            "这结构看着就靠谱",
            "木工活儿玩得挺溜啊",
            "徒手搭框架，这手艺绝了",
        ]
    # ... 其他动作类型

    return narrations
```

- [ ] **Step 2: 添加温馨感人风格解说生成器**

```python
def generate_warm_narration_for_paragraph(paragraph: Dict) -> List[str]:
    """生成温馨感人风格的连贯解说"""
    action = paragraph["action"]

    if action == "exploration":
        return [
            "在这片宁静的森林里",
            "他开始了今天的探索",
            "感受大自然的馈赠",
        ]
    elif action == "building":
        return [
            "一木一枝，皆是心血",
            "在这荒野之中",
            "他用自己的双手",
            "搭建起属于自己的一片天地",
        ]
    # ... 其他动作类型
```

- [ ] **Step 3: 实现统一的生成接口**

```python
def generate_narration_for_paragraph(paragraph: Dict, style: str, global_index: int) -> List[str]:
    """根据风格生成解说"""
    if style == "humor":
        return generate_humor_narration_for_paragraph(paragraph, global_index)
    elif style == "warm":
        return generate_warm_narration_for_paragraph(paragraph, global_index)
    # ... 其他风格
    else:
        return generate_humor_narration_for_paragraph(paragraph, global_index)
```

---

## Chunk 4: SRT字幕生成与时间轴对齐

### Task 4: 实现SRT生成与时间轴对齐

- [ ] **Step 1: 添加字幕生成函数**

```python
def generate_srt_subtitles(
    paragraphs: List[Dict],
    video_duration: float,
    style: str,
    interval: float = 4.0
) -> List[Subtitle]:
    """
    生成SRT字幕，确保时间轴完全对齐

    算法：
    1. 计算需要的字幕总数 = ceil(video_duration / interval)
    2. 将字幕均匀分配到各叙事段落
    3. 每个段落内按顺序使用该段落的解说文案
    4. 如果文案不够，循环使用（但要避免明显重复）

    Args:
        paragraphs: 叙事段落列表
        video_duration: 视频总时长（秒）
        style: 解说风格
        interval: 字幕间隔（秒）

    Returns:
        字幕列表
    """
    subtitles = []
    total_subs_needed = math.ceil(video_duration / interval)

    # 收集所有解说文案
    all_narrations = []
    for i, paragraph in enumerate(paragraphs):
        narrations = generate_narration_for_paragraph(paragraph, style, i)
        for narration in narrations:
            all_narrations.append({
                "text": narration,
                "paragraph_index": i
            })

    # 如果文案不够，扩展文案池
    while len(all_narrations) < total_subs_needed:
        for narration in all_narrations[:]:  # 复制列表避免修改
            if len(all_narrations) >= total_subs_needed:
                break
            # 添加变体版本
            variant = f"继续{narration['text']}"
            all_narrations.append({
                "text": variant,
                "paragraph_index": narration["paragraph_index"]
            })

    # 生成字幕
    for i in range(total_subs_needed):
        start_ms = int(i * interval * 1000)
        end_ms = int(min((i + 1) * interval * 1000, video_duration * 1000))

        narration_index = i % len(all_narrations)
        text = all_narrations[narration_index]["text"]

        subtitles.append(Subtitle(
            index=i + 1,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text
        ))

    return subtitles
```

- [ ] **Step 2: 添加SRT导出函数**

```python
def export_to_srt(subtitles: List[Subtitle], output_path: str):
    """导出为SRT文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for subtitle in subtitles:
            f.write(f"{subtitle.index}\n")
            f.write(f"{format_time(subtitle.start_ms)} --> {format_time(subtitle.end_ms)}\n")
            f.write(f"{subtitle.text}\n")
            f.write("\n")
```

- [ ] **Step 3: 完整流程测试**

Run:
```bash
python .claude/skills/video-recognition/scripts/generate_narration.py \
    output/frame_descriptions.json \
    output/narration.srt \
    humor \
    4
```

Expected: 生成完整的SRT文件，时间轴对齐

---

## Chunk 5: 更新 SKILL.md 文档

### Task 5: 更新技能文档

**Files:**
- Modify: `.claude/skills/video-recognition/SKILL.md`

- [ ] **Step 1: 更新第二阶段说明**

将原文中：
- "2秒一句" 改为 "4秒一句（可配置）"
- 添加连贯叙事生成的说明
- 更新示例输出

- [ ] **Step 2: 添加新脚本使用说明**

```markdown
### 步骤 9b: 新脚本 - generate_narration.py（推荐）

**【新】推荐使用 `generate_narration.py` 脚本生成连贯解说：**

```bash
python .claude/skills/video-recognition/scripts/generate_narration.py \
    output/frame_descriptions.json \
    output/narration.srt \
    humor \
    4
```

**参数说明：**
- `output/frame_descriptions.json` - 帧描述JSON路径
- `output/narration.srt` - 输出SRT路径
- `humor` - 解说风格（humor/warm/tech/mystery/healing）
- `4` - 字幕间隔秒数（默认4秒）

**脚本特点：**
1. 自动分析叙事流程，划分叙事段落
2. 生成连贯的解说文案，前后呼应
3. 支持多种解说风格
4. 时间轴自动对齐
```

---

## Chunk 6: 验证与测试

### Task 6: 验证生成结果

- [ ] **Step 1: 验证时间轴对齐**

```bash
# 检查SRT时长
tail -4 output/narration.srt

# 检查视频时长
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 inputs/1111.mp4
```

Expected: 最后一条字幕结束时间应等于视频时长

- [ ] **Step 2: 验证字幕连贯性**

检查生成的SRT，确认：
1. 解说文案是否描述了完整的故事流程
2. 是否有明显重复或突兀的过渡
3. 整体风格是否一致

- [ ] **Step 3: 测试不同风格**

```bash
# 温馨感人风格
python .claude/skills/video-recognition/scripts/generate_narration.py \
    output/frame_descriptions.json \
    output/narration_warm.srt \
    warm \
    4

# 科技硬核风格
python .claude/skills/video-recognition/scripts/generate_narration.py \
    output/frame_descriptions.json \
    output/narration_tech.srt \
    tech \
    4
```

---

## 验收标准

1. ✅ `generate_narration.py` 脚本存在且可执行
2. ✅ 支持幽默、温馨、科技、悬疑、解压治愈5种风格
3. ✅ 生成的SRT字幕时间轴与视频完全对齐
4. ✅ 解说文案描述完整的故事流程，前后呼应
5. ✅ 字幕间隔可配置（默认4秒）
6. ✅ SKILL.md 文档已更新
