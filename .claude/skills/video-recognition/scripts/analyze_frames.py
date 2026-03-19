#!/usr/bin/env python3
"""
视频帧图像分析脚本
使用本地 Ollama qwen3-vl 模型分析帧图片内容，生成详细画面描述
"""

import json
import os
import sys
import base64
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


# Ollama 配置
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3-vl:235b-cloud")


def load_frames_from_dir(frames_dir: str) -> List[str]:
    """加载指定目录下的所有帧图片路径"""
    frames = sorted(Path(frames_dir).glob("frame_*.jpg"))
    return [str(f) for f in frames]


def group_frames(frames: List[str], frames_per_group: int = 5) -> List[Dict[str, Any]]:
    """
    将帧图片按组划分

    Args:
        frames: 帧图片路径列表
        frames_per_group: 每组帧数量，默认5帧

    Returns:
        分组信息列表
    """
    groups = []
    for i in range(0, len(frames), frames_per_group):
        group_frames = frames[i:i + frames_per_group]
        groups.append({
            "group_id": i // frames_per_group + 1,
            "frames": group_frames,
            "start_frame": i + 1,
            "end_frame": min(i + frames_per_group, len(frames))
        })
    return groups


def encode_image_to_base64(image_path: str) -> str:
    """将图片文件编码为 base64 字符串"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def call_ollama_vlm(image_paths: List[str], prompt: str, model: str = None) -> Optional[Dict]:
    """
    调用 Ollama qwen3-vl 模型分析图片

    Args:
        image_paths: 图片路径列表
        prompt: 分析提示词
        model: 模型名称，默认使用 OLLAMA_MODEL

    Returns:
        解析后的 JSON 响应
    """
    model = model or OLLAMA_MODEL

    # 准备多图消息
    images = []
    for path in image_paths:
        if os.path.exists(path):
            images.append(encode_image_to_base64(path))
        else:
            print(f"警告: 图片不存在 {path}")

    if not images:
        print("错误: 没有有效的图片可分析")
        return None

    # 构建请求
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": images
            }
        ],
        "stream": False,
        "format": "json"
    }

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json=payload,
            timeout=300  # 5分钟超时
        )
        response.raise_for_status()
        result = response.json()

        # 解析 JSON 内容
        content = result.get("message", {}).get("content", "")
        # 尝试提取 JSON 部分
        return parse_json_response(content)

    except requests.exceptions.Timeout:
        print(f"错误: Ollama 请求超时 (5分钟)")
        return None
    except requests.exceptions.ConnectionError:
        print(f"错误: 无法连接到 Ollama ({OLLAMA_HOST})，请确保 Ollama 正在运行")
        return None
    except requests.exceptions.RequestException as e:
        print(f"错误: Ollama 请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"错误: 解析 JSON 响应失败: {e}")
        print(f"原始响应: {content[:500] if 'content' in dir() else 'N/A'}")
        return None


def parse_json_response(content: str) -> Optional[Dict]:
    """从响应内容中提取 JSON"""
    content = content.strip()

    # 如果内容以 ```json 开头，尝试提取
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]

    # 找到第一个 { 和最后一个 }
    first_brace = content.find("{")
    last_brace = content.rfind("}")

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = content[first_brace:last_brace + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # 尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def generate_frame_prompt(frames: List[str], group_id: int, start_time: float = 0, interval: float = 10) -> str:
    """
    生成帧分析的 prompt

    Args:
        frames: 帧图片路径列表
        group_id: 分组ID
        start_time: 起始时间（秒）
        interval: 抽帧间隔（秒）

    Returns:
        图像分析 prompt
    """
    prompt = f"""## 帧图像分析任务（第 {group_id} 组）

请分析以下 {len(frames)} 张连续帧图片，每张图片间隔 {interval} 秒。

### 分析要求

**【重要】画面识别要求 - 尽可能详细：**
1. 描述画面中的人物数量、性别、外貌特征、穿着
2. 描述人物正在进行的动作、表情、姿态
3. 描述场景环境、背景物品、光线氛围
4. 描述物体位置、颜色、大小
5. 描述画面中发生的事件、互动关系

**【禁止】此阶段禁止：**
- ❌ 生成解说文案
- ❌ 生成SRT字幕
- ❌ 使用任何风格化语言
- ✅ 只做纯画面内容详细描述

### 输出格式（JSON）

请严格按以下JSON格式输出，不要包含任何其他内容：

```json
{{
  "group_id": {group_id},
  "time_range": "HH:MM:SS - HH:MM:SS",
  "frames": [
    {{
      "frame_id": 1,
      "timestamp": "HH:MM:SS",
      "description": "画面详细描述：有什么人、在干什么、场景细节..."
    }},
    {{
      "frame_id": 2,
      "timestamp": "HH:MM:SS",
      "description": "画面详细描述..."
    }}
  ]
}}
```

### 帧图片列表：

"""
    for idx, frame_path in enumerate(frames):
        frame_num = idx + 1
        timestamp = f"{int(start_time // 3600):02d}:{int((start_time % 3600) // 60):02d}:{int(start_time % 60):02d}"
        prompt += f"- 帧 {frame_num}: {frame_path} (时间戳: {timestamp})\n"
        start_time += interval

    prompt += """
### 注意事项

1. 每帧都要有独立、详细的 description
2. 如果连续帧内容相似，也要分别描述（可能有细微变化）
3. 注意画面中的人物/物体在不同帧之间的变化和关联
4. 描述要客观、具体，避免主观评价
"""
    return prompt


def analyze_group(group: Dict, frame_interval: float = 10, model: str = None) -> Optional[Dict]:
    """
    分析单个分组的帧图片

    Args:
        group: 分组信息
        frame_interval: 抽帧间隔（秒）
        model: Ollama 模型名称

    Returns:
        分析结果
    """
    group_id = group["group_id"]
    frames = group["frames"]
    start_time = (group["start_frame"] - 1) * frame_interval

    print(f"  正在分析第 {group_id} 组 ({len(frames)} 张帧)...")

    # 生成 prompt
    prompt = generate_frame_prompt(frames, group_id, start_time, frame_interval)

    # 调用 Ollama 分析
    result = call_ollama_vlm(frames, prompt, model)

    if result:
        print(f"  ✓ 第 {group_id} 组分析完成")
        return result
    else:
        print(f"  ✗ 第 {group_id} 组分析失败")
        return None


def analyze_frames_parallel(frames_dir: str, output_path: str, frame_interval: float = 10,
                            frames_per_group: int = 5, max_workers: int = 4, model: str = None):
    """
    并行分析帧图片

    Args:
        frames_dir: 帧图片目录
        output_path: 输出 JSON 路径
        frame_interval: 抽帧间隔（秒）
        frames_per_group: 每组帧数量
        max_workers: 最大并行数
        model: Ollama 模型名称
    """
    model = model or OLLAMA_MODEL

    print(f"\n=== 帧图片分析 ===")
    print(f"模型: {model}")
    print(f"Ollama: {OLLAMA_HOST}")
    print(f"帧目录: {frames_dir}")
    print(f"输出: {output_path}")
    print(f"并行数: {max_workers}")
    print()

    # 加载帧图片
    frames = load_frames_from_dir(frames_dir)
    if not frames:
        print("错误: 没有找到帧图片")
        return
    print(f"加载了 {len(frames)} 张帧图片")

    # 分组
    groups = group_frames(frames, frames_per_group)
    print(f"分为 {len(groups)} 组 (每组 {frames_per_group} 张)")

    # 并行分析
    results = []
    failed_groups = []

    print(f"\n开始并行分析...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_group = {
            executor.submit(analyze_group, group, frame_interval, model): group
            for group in groups
        }

        for future in as_completed(future_to_group):
            group = future_to_group[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
                else:
                    failed_groups.append(group["group_id"])
            except Exception as e:
                print(f"  组 {group['group_id']} 分析异常: {e}")
                failed_groups.append(group["group_id"])

    print(f"\n分析完成: {len(results)} 成功, {len(failed_groups)} 失败")

    if failed_groups:
        print(f"失败分组: {failed_groups}")

    # 合并结果
    all_frames = []
    for group_result in sorted(results, key=lambda x: x.get("group_id", 0)):
        if "frames" in group_result:
            all_frames.extend(group_result["frames"])

    # 获取视频时长（如果可用）
    video_duration = len(frames) * frame_interval

    final_result = {
        "video_duration": video_duration,
        "frame_interval": frame_interval,
        "total_frames": len(all_frames),
        "frame_descriptions": all_frames
    }

    # 保存结果
    save_results(final_result, output_path)
    print(f"\n✓ 结果已保存到: {output_path}")

    return final_result


def merge_group_results(group_results: List[Dict], video_duration: float, frame_interval: float) -> Dict:
    """
    合并所有分组的分析结果

    Args:
        group_results: 各分组分析结果列表
        video_duration: 视频总时长（秒）
        frame_interval: 抽帧间隔（秒）

    Returns:
        合并后的完整分析结果
    """
    all_frames = []
    for group in group_results:
        if "frames" in group:
            all_frames.extend(group["frames"])

    return {
        "video_duration": video_duration,
        "frame_interval": frame_interval,
        "total_frames": len(all_frames),
        "frame_descriptions": all_frames
    }


def save_results(results: Dict, output_path: str):
    """保存分析结果到JSON文件"""
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("用法: python analyze_frames.py <frames_dir> <output_json> [frame_interval] [max_workers]")
        print("示例: python analyze_frames.py output/frames_360p output/frame_descriptions.json 10 4")
        print()
        print("环境变量:")
        print("  OLLAMA_HOST - Ollama 服务地址 (默认: http://localhost:11434)")
        print("  OLLAMA_MODEL - 模型名称 (默认: qwen3-vl:235b-cloud)")
        sys.exit(1)

    frames_dir = sys.argv[1]
    output_path = sys.argv[2]
    frame_interval = float(sys.argv[3]) if len(sys.argv) > 3 else 10
    max_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 4

    if not os.path.exists(frames_dir):
        print(f"错误: 目录不存在 {frames_dir}")
        sys.exit(1)

    analyze_frames_parallel(
        frames_dir=frames_dir,
        output_path=output_path,
        frame_interval=frame_interval,
        frames_per_group=5,
        max_workers=max_workers
    )


if __name__ == "__main__":
    main()
