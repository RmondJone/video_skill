# Video Recognition 技能实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建完整的 video-recognition 技能，实现无声视频的画面理解与解说文案生成

**Architecture:** 基于 PySceneDetect 进行场景检测，ffmpeg 提取关键帧，Claude 自身能力分析画面并生成风格化解说文案

**Tech Stack:** Python 3, PySceneDetect, ffmpeg, Claude 自身能力

---

## 文件结构

```
.claude/skills/video-recognition/
├── SKILL.md                    # 技能定义文件
├── scripts/
│   ├── detect_scenes.py        # 场景检测脚本
│   ├── extract_keyframes.py    # 关键帧提取脚本
│   ├── describe_scenes.py      # 画面描述生成脚本
│   ├── generate_narrator.py    # 叙事串联 + 风格化脚本
│   └── process_video.py        # 主流程编排脚本
└── references/
    ├── scenes_example.json      # 场景检测输出示例
    └── narrator_example.txt     # 解说文案输出示例
```

---

## Chunk 1: 环境验证与 detect_scenes.py

### Task 1: 创建 detect_scenes.py 场景检测脚本

**Files:**
- Create: `.claude/skills/video-recognition/scripts/detect_scenes.py`

- [ ] **Step 1: 创建 detect_scenes.py 脚本**

```python
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
```

- [ ] **Step 2: 测试脚本语法**

Run: `python3 -m py_compile .claude/skills/video-recognition/scripts/detect_scenes.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交**

```bash
git add .claude/skills/video-recognition/scripts/detect_scenes.py
git commit -m "feat(video-recognition): 添加场景检测脚本 detect_scenes.py"
```

---

## Chunk 2: extract_keyframes.py

### Task 2: 创建关键帧提取脚本

**Files:**
- Create: `.claude/skills/video-recognition/scripts/extract_keyframes.py`

- [ ] **Step 1: 创建 extract_keyframes.py 脚本**

```python
#!/usr/bin/env python3
"""
关键帧提取脚本 - 使用 ffmpeg 从每个场景提取关键帧
"""

import argparse
import json
import os
import subprocess
import sys


def extract_keyframes(video_path, scenes_path, output_dir, max_frames=5):
    """
    从视频场景中提取关键帧

    Args:
        video_path: 输入视频路径
        scenes_path: 场景 JSON 文件路径
        output_dir: 输出目录
        max_frames: 每个场景最大帧数
    """
    with open(scenes_path, 'r', encoding='utf-8') as f:
        scenes_data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    scenes = scenes_data.get('scenes', [])
    print(f"共有 {len(scenes)} 个场景需要提取关键帧")

    extracted = []
    for i, scene in enumerate(scenes):
        start_time = scene['start_time']
        end_time = scene['end_time']

        # 计算场景时长
        start_parts = start_time.split(':')
        end_parts = end_time.split(':')

        start_seconds = int(start_parts[0]) * 3600 + int(start_parts[1]) * 60 + float(start_parts[2])
        end_seconds = int(end_parts[0]) * 3600 + int(end_parts[1]) * 60 + float(end_parts[2])
        duration = end_seconds - start_seconds

        # 计算提取帧的时间点
        frame_times = []
        if duration <= 0:
            frame_times = [start_time]
        elif duration <= 2:
            frame_times = [start_time, end_time]
        else:
            # 均匀分布提取点
            num_frames = min(max_frames, int(duration) + 1)
            for j in range(num_frames):
                t = start_seconds + (duration * j / (num_frames - 1)) if num_frames > 1 else start_seconds
                frame_times.append(f"{int(t // 3600):02d}:{int((t % 3600) // 60):02d}:{t % 60:05.2f}")

        # 提取每帧
        scene_keyframes = []
        for j, t in enumerate(frame_times):
            output_file = os.path.join(output_dir, f"scene_{i:03d}_frame_{j:02d}.jpg")

            cmd = [
                'ffmpeg', '-y', '-ss', t,
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                output_file
            ]

            try:
                subprocess.run(cmd, check=True, capture_output=True)
                scene_keyframes.append({
                    "scene_index": i,
                    "frame_index": j,
                    "time": t,
                    "file": output_file
                })
                print(f"  场景 {i}: 提取帧 @ {t} -> {output_file}")
            except subprocess.CalledProcessError as e:
                print(f"  警告: 场景 {i} 帧 {j} 提取失败", file=sys.stderr)

        extracted.extend(scene_keyframes)

    # 保存提取结果
    result = {
        "video_path": video_path,
        "scenes_path": scenes_path,
        "output_dir": output_dir,
        "keyframes": extracted
    }

    result_file = os.path.join(output_dir, 'keyframes.json')
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n关键帧提取完成！共提取 {len(extracted)} 帧")
    print(f"结果已保存到: {result_file}")

    return result


def main():
    parser = argparse.ArgumentParser(description='提取视频关键帧')
    parser.add_argument('input', help='输入视频路径')
    parser.add_argument('scenes', help='场景 JSON 文件路径')
    parser.add_argument('output', help='输出目录')
    parser.add_argument('--max-frames', type=int, default=5,
                        help='每个场景最大帧数 (默认 5)')

    args = parser.parse_args()

    try:
        extract_keyframes(args.input, args.scenes, args.output, args.max_frames)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 测试脚本语法**

Run: `python3 -m py_compile .claude/skills/video-recognition/scripts/extract_keyframes.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交**

```bash
git add .claude/skills/video-recognition/scripts/extract_keyframes.py
git commit -m "feat(video-recognition): 添加关键帧提取脚本 extract_keyframes.py"
```

---

## Chunk 3: describe_scenes.py

### Task 3: 创建画面描述生成脚本

**Files:**
- Create: `.claude/skills/video-recognition/scripts/describe_scenes.py`

- [ ] **Step 1: 创建 describe_scenes.py 脚本**

```python
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
```

- [ ] **Step 2: 测试脚本语法**

Run: `python3 -m py_compile .claude/skills/video-recognition/scripts/describe_scenes.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交**

```bash
git add .claude/skills/video-recognition/scripts/describe_scenes.py
git commit -m "feat(video-recognition): 添加画面描述生成脚本 describe_scenes.py"
```

---

## Chunk 4: generate_narrator.py

### Task 4: 创建叙事串联 + 风格化脚本

**Files:**
- Create: `.claude/skills/video-recognition/scripts/generate_narrator.py`

- [ ] **Step 1: 创建 generate_narrator.py 脚本**

```python
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
```

- [ ] **Step 2: 测试脚本语法**

Run: `python3 -m py_compile .claude/skills/video-recognition/scripts/generate_narrator.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交**

```bash
git add .claude/skills/video-recognition/scripts/generate_narrator.py
git commit -m "feat(video-recognition): 添加叙事串联脚本 generate_narrator.py"
```

---

## Chunk 5: process_video.py 主流程脚本

### Task 5: 创建主流程编排脚本

**Files:**
- Create: `.claude/skills/video-recognition/scripts/process_video.py`

- [ ] **Step 1: 创建 process_video.py 脚本**

```python
#!/usr/bin/env python3
"""
视频画面解说生成 - 主流程编排脚本

整合场景检测、关键帧提取、画面分析、解说文案生成
"""

import argparse
import json
import os
import subprocess
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


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


def process_video(video_path, output_dir, style='风趣幽默', threshold=30.0, max_frames=5):
    """
    完整处理流程

    Args:
        video_path: 输入视频路径
        output_dir: 输出目录
        style: 解说风格
        threshold: 场景检测阈值
        max_frames: 每场景最大帧数
    """
    # 验证输入
    if not os.path.exists(video_path):
        print(f"错误: 视频文件不存在: {video_path}", file=sys.stderr)
        sys.exit(1)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'keyframes'), exist_ok=True)

    video_name = os.path.splitext(os.path.basename(video_path))[0]

    # 步骤 1: 场景检测
    scenes_json = os.path.join(output_dir, 'scenes.json')
    cmd_scenes = [
        'python3', os.path.join(SCRIPT_DIR, 'detect_scenes.py'),
        video_path, scenes_json,
        '--threshold', str(threshold)
    ]

    if not run_command(cmd_scenes, "步骤 1: 场景检测"):
        sys.exit(1)

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
    cmd_describe = [
        'python3', os.path.join(SCRIPT_DIR, 'describe_scenes.py'),
        keyframes_json, descriptions_json
    ]

    if not run_command(cmd_describe, "步骤 3: 生成画面描述模板"):
        sys.exit(1)

    print(f"\n{'='*50}")
    print("画面分析阶段 - 请使用 Claude 分析关键帧")
    print(f"{'='*50}")
    print(f"关键帧目录: {keyframes_dir}")
    print(f"描述模板: {descriptions_json}")
    print("\n请分析关键帧图片后，更新 descriptions.json 中的 description 字段")

    # 步骤 4: 生成解说文案
    narrator_output = os.path.join(output_dir, 'narrator')
    cmd_narrator = [
        'python3', os.path.join(SCRIPT_DIR, 'generate_narrator.py'),
        descriptions_json, narrator_output,
        '--style', style,
        '--format', 'both'
    ]

    if not run_command(cmd_narrator, "步骤 4: 生成解说文案"):
        sys.exit(1)

    print(f"\n{'='*50}")
    print("✓ 处理完成！")
    print(f"{'='*50}")
    print(f"输出目录: {output_dir}")
    print(f"解说文案: {narrator_output}.srt / {narrator_output}.txt")


def main():
    parser = argparse.ArgumentParser(description='视频画面解说生成 - 主流程')
    parser.add_argument('input', help='输入视频路径')
    parser.add_argument('output', help='输出目录')
    parser.add_argument('--style', default='风趣幽默',
                        help='解说风格')
    parser.add_argument('--threshold', type=float, default=30.0,
                        help='场景检测阈值')
    parser.add_argument('--max-frames', type=int, default=5,
                        help='每场景最大帧数')

    args = parser.parse_args()

    process_video(args.input, args.output, args.style, args.threshold, args.max_frames)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 测试脚本语法**

Run: `python3 -m py_compile .claude/skills/video-recognition/scripts/process_video.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交**

```bash
git add .claude/skills/video-recognition/scripts/process_video.py
git commit -m "feat(video-recognition): 添加主流程编排脚本 process_video.py"
```

---

## Chunk 6: SKILL.md 技能定义文件

### Task 6: 更新 SKILL.md

**Files:**
- Modify: `.claude/skills/video-recognition/SKILL.md`

- [ ] **Step 1: 更新 SKILL.md**

```markdown
---
name: video-recognition
description: 视频画面解说生成器 - 用户粘贴视频路径即可自动处理，进行场景检测、关键帧提取、画面分析，生成风格化解说文案（SRT/TXT格式）。当用户提供无声视频、需要画面解说、提到风格化解说时使用此技能。
---

# 视频画面解说生成器技能

用户提供本地视频文件路径，自动完成场景检测、关键帧提取、画面分析，生成风格化解说文案。

**【重要】参考资料存放在 references 文件夹中：**

- `.claude/skills/video-recognition/references/scenes_example.json` - 场景检测输出示例
- `.claude/skills/video-recognition/references/narrator_example.txt` - 解说文案输出示例

---

## 触发条件

用户满足以下任一条件时使用此技能：
- 用户粘贴了本地视频文件路径并要求画面解说
- 用户提到"无声视频解说"、"画面分析"、"纯视觉解说"
- 用户提到需要风格化解说（风趣幽默、技术硬核、理性科普、解压治愈、温馨感人）

**注意：无需用户使用 @ 触发，只需用户提供视频文件路径即可自动识别并处理。**

## 输入要求

从用户消息中提取视频文件路径，确保：
1. 视频文件存在且为支持的格式（mp4, mov, avi, mkv, webm）
2. 提取输出目录（用户指定或默认）

## 处理流程

### 步骤 1: 验证环境依赖（自动执行）

**自动检查以下工具是否可用，无需用户同意：**
1. **FFmpeg** - 视频处理和关键帧提取
2. **PySceneDetect** - 场景检测
3. **Python** - 运行环境

如果缺少依赖，自动提示用户安装并执行安装命令：
```bash
# 检查并安装 ffmpeg (macOS)
which ffmpeg || brew install ffmpeg

# 检查并安装 PySceneDetect
python3 -c "import scenedetect" 2>/dev/null || pip install scenedetect
```

### 步骤 2: 选择解说风格

**必须询问用户选择解说风格：**

```
请选择解说风格（直接回复数字或风格名）：
1. 风趣幽默（默认）- 轻松调侃的语气，画外音风格
2. 技术硬核 - 专业术语、深度分析
3. 理性科普 - 客观陈述、逻辑清晰
4. 解压治愈 - 柔和舒缓、放松心情
5. 温馨感人 - 情感充沛、温暖人心
```

**风格说明：**

| 风格 | 说明 | 适用场景 |
|------|------|----------|
| 风趣幽默（默认）| 轻松调侃的语气，画外音风格 | 日常vlog、娱乐内容 |
| 技术硬核 | 专业术语、深度分析 | 科技、编程、工业 |
| 理性科普 | 客观陈述、逻辑清晰 | 知识讲解、教育 |
| 解压治愈 | 柔和舒缓、放松心情 | ASMR、冥想、自然 |
| 温馨感人 | 情感充沛、温暖人心 | 亲情、友情、励志 |

### 步骤 3: 场景检测

```bash
python3 .claude/skills/video-recognition/scripts/detect_scenes.py input.mp4 output/scenes.json --threshold 30
```

### 步骤 4: 关键帧提取

```bash
python3 .claude/skills/video-recognition/scripts/extract_keyframes.py input.mp4 output/scenes.json output/keyframes/ --max-frames 5
```

### 步骤 5: 画面描述生成

**【核心】使用 Claude 自身能力分析关键帧：**
1. 读取关键帧图片
2. 分析每个场景的画面内容
3. 生成场景描述文本

### 步骤 6: 叙事串联 + 风格化

**【核心】使用 Claude 自身能力生成连贯解说文案：**
1. 串联所有场景描述
2. 应用用户选择的风格
3. 生成最终解说文案

### 步骤 7: 输出解说文案

```bash
python3 .claude/skills/video-recognition/scripts/generate_narrator.py output/descriptions.json output/narrator --style 幽默 --format both
```

## 输出文件结构

```
output/<视频名>/
├── scenes.json          # 场景检测结果
├── keyframes/           # 关键帧图片
│   ├── scene_001.jpg
│   ├── scene_002.jpg
├── descriptions.json    # 画面描述
├── narrator.srt         # 解说文案（SRT格式）
└── narrator.txt         # 解说文案（TXT格式）
```

## 使用示例

### 示例 1: 基本使用
```
用户: 处理一下这个无声视频 /Users/guohanlin/videos/demo.mp4

技能响应:
1. 正在验证环境...
2. 请选择解说风格...
3. 正在检测场景...
4. 正在提取关键帧...
5. 正在分析画面...
6. 正在生成解说文案...

完成! 解说文案已保存到: /Users/guohanlin/videos/demo_output/
```

### 示例 2: 指定风格
```
用户: 处理 /Users/guohanlin/videos/demo.mp4，风格选技术硬核
```

## 依赖说明

| 工具 | 说明 | 安装方式 |
|------|------|----------|
| ffmpeg | 视频处理、关键帧提取 | `brew install ffmpeg` |
| PySceneDetect | 场景检测 | `pip install scenedetect` |

**注意：不需要配置任何外部 AI API Key！**

解说文案生成直接使用 Claude 自身的能力。

## 脚本工具

**所有脚本位于 `.claude/skills/video-recognition/scripts/` 目录**

1. **detect_scenes.py** - 场景检测脚本
2. **extract_keyframes.py** - 关键帧提取脚本
3. **describe_scenes.py** - 画面描述生成脚本
4. **generate_narrator.py** - 叙事串联 + 风格化脚本
5. **process_video.py** - 主流程编排脚本

**脚本完整路径：**
```bash
# 脚本基础路径
SCRIPT_DIR=".claude/skills/video-recognition/scripts"

# 场景检测
python3 ${SCRIPT_DIR}/detect_scenes.py input.mp4 output/scenes.json

# 关键帧提取
python3 ${SCRIPT_DIR}/extract_keyframes.py input.mp4 output/scenes.json output/keyframes/

# 生成描述模板
python3 ${SCRIPT_DIR}/describe_scenes.py output/keyframes/keyframes.json output/descriptions.json

# 生成解说文案
python3 ${SCRIPT_DIR}/generate_narrator.py output/descriptions.json output/narrator --style 风趣幽默 --format both

# 一键执行完整流程
python3 ${SCRIPT_DIR}/process_video.py input.mp4 output/ --style 风趣幽默
```
```

- [ ] **Step 2: 提交**

```bash
git add .claude/skills/video-recognition/SKILL.md
git commit -m "feat(video-recognition): 完成 SKILL.md 技能定义文件"
```

---

## Chunk 7: references 参考示例文件

### Task 7: 创建参考示例文件

**Files:**
- Create: `.claude/skills/video-recognition/references/scenes_example.json`
- Create: `.claude/skills/video-recognition/references/narrator_example.txt`

- [ ] **Step 1: 创建 scenes_example.json**

```json
{
  "video_path": "example.mp4",
  "threshold": 30.0,
  "scene_count": 5,
  "scenes": [
    {
      "index": 0,
      "start_time": "00:00:00.000",
      "end_time": "00:00:15.500",
      "start_frame": 0,
      "end_frame": 387,
      "duration_frames": 387
    },
    {
      "index": 1,
      "start_time": "00:00:15.500",
      "end_time": "00:00:32.200",
      "start_frame": 387,
      "end_frame": 805,
      "duration_frames": 418
    }
  ]
}
```

- [ ] **Step 2: 创建 narrator_example.txt**

```
# 示例视频解说文案
# 风格: 风趣幽默

[00:00:00.000] 画面开场，一片宁静的田园风光迎面扑来。

[00:00:15.500] 突然，一只傲娇的小猫闯入镜头，仿佛在说："这片田野，朕承包了！"

[00:00:32.200] 只见小猫优雅地踱步而过，留下一个销魂的背影。
```

- [ ] **Step 3: 创建 references 目录并提交**

```bash
mkdir -p .claude/skills/video-recognition/references
git add .claude/skills/video-recognition/references/
git commit -m "feat(video-recognition): 添加参考示例文件"
```

---

## 实施完成

所有任务完成后，执行最终提交：

```bash
git add -A
git status
```

预期输出：
```
On branch main
nothing to commit, working tree clean
```

或显示新创建的文件待提交。
