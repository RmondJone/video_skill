---
name: video-recognition
description: 视频画面理解与解说文案生成 - 根据用户输入的抽帧间隔提取视频关键帧，分析画面内容并生成对应解说文案。当用户提到视频画面分析、画面理解、视频解说、帧图像分析时使用此技能。使用本地 Ollama qwen3-vl 模型分析画面内容。
---

# video-recognition 技能

根据用户指定的抽帧间隔提取视频关键帧，分析画面内容并生成对应解说文案。

**【重要】参考资料存放在 references 文件夹中：**

- `.claude/skills/video-recognition/references/srt_example.srt` - SRT字幕格式示例
- `.claude/skills/video-recognition/references/story_style.md` - 各风格解说文案特点说明

---

## 触发条件

用户满足以下任一条件时使用此技能：
- 用户提到"视频画面分析"、"画面理解"、"帧图像分析"
- 用户提到"根据画面生成解说"、"视频内容理解"
- 用户提供了视频文件并要求"分析画面内容"

**注意：无需用户使用 @ 触发，只需用户提供视频文件路径并说明分析画面即可。**

## 输入要求

从用户消息中提取：
1. 视频文件路径（必须存在且为支持的格式：mp4, mov, avi, mkv, webm）
2. 抽帧间隔（默认10秒一帧，用户可指定）
3. 解说风格（用户从预设中选择）

## 处理流程

### 步骤 1: 验证环境依赖（自动执行）

**自动检查以下工具是否可用，无需用户同意：**

1. **FFmpeg** - 视频处理和抽帧

```bash
# 检查 ffmpeg
which ffmpeg || brew install ffmpeg
```

### 步骤 2: 询问抽帧间隔

**询问用户抽帧间隔：**

```
请输入抽帧间隔（秒/帧）：
- 例如：10 表示每10秒抽取一帧
- 例如：100 表示抽取第100帧
- 直接回车默认使用 5 秒

请输入：
```

### 步骤 3: 询问解说风格

**【必须】让用户从预设风格中选择：**

```
请选择解说风格（直接回复数字）：

1️⃣ 幽默风趣 - 轻松诙谐，适合娱乐、搞笑类视频
2️⃣ 温馨感人 - 温暖治愈，适合情感、生活类视频
3️⃣ 科技硬核 - 专业硬核，适合科技、数码类视频
4️⃣ 悬疑烧脑 - 紧张刺激，适合悬疑、推理类视频
5️⃣ 解压治愈 - 放松舒缓，适合ASMR、冥想类视频
6️⃣ 荒野建造 - 朴实沉稳，适合荒野求生、野外建造类视频
```

**用户选择后，记录风格名称用于后续处理。**

### 步骤 4: 执行抽帧

**使用 ffmmpeg 提取视频关键帧：**

```bash
# 创建输出目录
mkdir -p output/frames

# 根据间隔抽帧
# 方式1：按时间间隔抽帧（如每10秒一帧）
ffmpeg -i input.mp4 -vf "fps=1/10" -q:v 2 output/frames/frame_%04d.jpg

# 方式2：按帧数抽帧（如每100帧抽一帧）
ffmpeg -i input.mp4 -vf "select='not(mod(n\,100))'" -vsync vfr output/frames/frame_%04d.jpg

# 获取视频时长（用于后续SRT时间对齐）
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 input.mp4
```

**输出：**
- 所有抽取的关键帧图片，保存到 `output/frames/` 目录
- 视频总时长（秒）

### 步骤 4b: 检查帧目录是否已存在

**【重要】在执行抽帧和压缩之前，必须检查是否已有现成的帧图片：**

```bash
# 检查 frames 和 frames_360p 目录
if [ -d "output/frames" ] && [ -d "output/frames_360p" ]; then
    FRAME_COUNT=$(ls output/frames/frame_*.jpg 2>/dev/null | wc -l)
    if [ "$FRAME_COUNT" -gt 0 ]; then
        echo "✓ 发现已存在的帧图片目录，跳过抽帧和压缩步骤"
        echo "  frames: $FRAME_COUNT 帧"
        echo "  frames_360p: $FRAME_COUNT 帧"
        # 直接进入步骤6（帧分组）
        goto STEP_6
    fi
else
    echo "✗ 未发现帧图片目录，开始执行抽帧和压缩..."
    # 继续执行步骤5（压缩帧图片）
fi
```

**跳过逻辑判定条件：**
- ✅ `output/frames/` 和 `output/frames_360p/` 都存在且非空 → **跳过步骤4和5，直接进入步骤6**
- ❌ 任一目录不存在或为空 → **执行完整步骤4（抽帧）和步骤5（压缩）**

**【跳过抽帧和压缩的好处】：**
- 节省 FFmpeg 抽帧时间（每视频约1-5分钟）
- 节省压缩处理时间（每视频约2-3分钟）
- 已有高质量原始帧和压缩帧，可直接复用

---

### 步骤 5: 压缩帧图片（360P）

**将抽取的帧图片压缩为360P，减小体积以便更快分析：**

```bash
# 压缩为360P (640x360)
mkdir -p output/frames_360p
for f in output/frames/frame_*.jpg; do
  ffmpeg -i "$f" -vf "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2" -q:v 2 "output/frames_360p/$(basename "$f")"
done
```

**输出：**
- 压缩后的360P帧图片，保存到 `output/frames_360p/` 目录

### 步骤 6b: 帧分组

**将抽取的帧图片按组划分，便于并行处理：**

```python
import os
from pathlib import Path

def group_frames(frames_dir, frames_per_group=10):
    """将帧图片按组划分"""
    frames = sorted(Path(frames_dir).glob("frame_*.jpg"))
    groups = []

    for i in range(0, len(frames), frames_per_group):
        group_frames = frames[i:i + frames_per_group]
        group_info = {
            "group_id": i // frames_per_group + 1,
            "frames": [str(f) for f in group_frames],
            "start_frame": i + 1,
            "end_frame": min(i + frames_per_group, len(frames))
        }
        groups.append(group_info)

    return groups
```

**分组策略：**
- 默认每10帧为一组
- 最后一组可能不足10帧
- 每个分组对应视频中的一个时间段

### 步骤 7: 检查 frame_descriptions.json 是否已存在

**【重要】在执行帧分析之前，必须检查是否已有现成的画面描述JSON文件：**

```bash
# 检查 frame_descriptions.json 是否存在
if [ -f "output/frame_descriptions.json" ]; then
    echo "✓ 发现已存在的 frame_descriptions.json，跳过帧分析步骤"
    echo "  文件路径: output/frame_descriptions.json"
    # 直接进入步骤9（第二阶段：生成解说文案）
    goto STEP_9
else
    echo "✗ 未发现 frame_descriptions.json，开始执行帧分析..."
    # 继续执行步骤7a（第一阶段）
fi
```

**跳过逻辑判定条件：**
- ✅ 存在 `output/frame_descriptions.json` 文件 → **跳过第一阶段，直接进入第二阶段**
- ❌ 不存在该文件 → **执行完整的第一阶段（步骤7a）**

**【跳过帧分析的好处】：**
- 节省 Ollama qwen3-vl 模型调用时间（每视频约5-15分钟）
- 节省 GPU/CPU 资源
- 可以直接切换不同风格生成不同解说文案

---

### 步骤 7a: 第一阶段 - 调用 analyze_frames.py 脚本进行画面识别

**【核心-第一阶段】使用 `scripts/analyze_frames.py` 脚本调用 Ollama qwen3-vl 模型分析帧图片内容，输出JSON：**

**脚本位置：** `.claude/skills/video-recognition/scripts/analyze_frames.py`

**环境变量配置：**
```bash
export OLLAMA_HOST=http://localhost:11434          # Ollama 服务地址（默认）
export OLLAMA_MODEL=qwen3-vl:235b-cloud           # 模型名称（默认）
```

**执行命令：**
```bash
python .claude/skills/video-recognition/scripts/analyze_frames.py \
    output/frames_360p \
    output/frame_descriptions.json \
    10 \
    4
```

**命令参数说明：**
- `output/frames_360p` - 360P压缩帧图片目录
- `output/frame_descriptions.json` - 输出JSON文件路径
- `10` - 抽帧间隔（秒），与用户指定的间隔一致
- `4` - 并行分析的最大线程数

**脚本功能：**
1. 自动加载 `frames_360p` 目录下的所有 `frame_*.jpg` 图片
2. 按每组5帧进行分组
3. 并行调用 Ollama qwen3-vl 模型分析每组帧图片
4. 合并所有分组结果生成完整的 `frame_descriptions.json`

**analyze_frames.py 输出格式：**

```json
{
  "video_duration": 120.5,
  "frame_interval": 10,
  "total_frames": 12,
  "frame_descriptions": [
    {
      "frame_id": 1,
      "timestamp": "00:00:00",
      "description": "室内场景。画面中央坐着一名中年男性，短发，穿着深蓝色西装白色衬衫，表情严肃..."
    },
    {
      "frame_id": 2,
      "timestamp": "00:00:10",
      "description": "与第1帧相似，但有细微变化。同一名中年男性仍坐在办公桌前..."
    }
  ]
}
```

**【关键约束】脚本已内置以下要求：**
- 每帧至少5-10句话的详细描述
- 包含人物、场景、物体、事件四大要素
- 使用具体名词而非模糊代词
- 保持客观，不添加评论或感受
- 描述要具体（如"一个人"要说"一名中年男性"）

**【禁止】脚本已内置以下禁止项：**
- ❌ 生成解说文案
- ❌ 生成SRT字幕
- ❌ 使用任何风格化语言（如"这时一位伟人出现了"）
- ❌ 主观评价（"这个设计真好看"）
- ✅ 只做纯客观画面内容描述

### 步骤 8: 汇总画面识别结果到JSON

**收集所有子Agent的画面识别结果，合并生成完整的帧描述JSON：**

```python
def merge_frame_descriptions(group_results, video_duration, frame_interval):
    """合并所有帧描述为完整JSON"""
    all_frames = []
    for group in group_results:
        all_frames.extend(group["frames"])

    return {
        "video_duration": video_duration,
        "frame_interval": frame_interval,
        "total_frames": len(all_frames),
        "frame_descriptions": all_frames
    }
```

**【关键约束】帧描述JSON必须包含：**
- 视频总时长
- 抽帧间隔
- 每帧的时间戳和详细描述
- 所有帧必须按时间顺序排列

### 步骤 9: 第二阶段 - 根据JSON生成解说文案（4秒一句）

**【核心-第二阶段】直接使用 AI 能力生成风格化解说文案：**

**此阶段必须：**
1. 读取第一阶段生成的 `output/frame_descriptions.json`
2. 分析叙事流程，划分叙事段落
3. 根据用户选择的风格生成连贯解说文案
4. 直接输出符合SRT格式的字幕内容

**解说文案生成规则（4秒一句话）：**

```
视频总时长：T 秒
每句话时长：4 秒
字幕数量 = ceil(T / 4)

示例：
- 视频时长：120秒
- 每4秒一句话，共30条字幕
- 第1条：00:00:00,000 --> 00:00:04,000
- 第2条：00:00:04,000 --> 00:00:08,000
- ...
- 第30条：00:01:56,000 --> 00:02:00,000
```

**【AI直接生成】AI根据画面描述JSON，直接生成SRT字幕：**
1. 分析 `frame_descriptions.json` 中的帧描述内容
2. 分析叙事流程，将视频划分为若干叙事段落
3. 每个段落根据动作类型（探索、砍伐、挖掘、搭建等）生成对应解说
4. 使用自然过渡词连接相邻文案，避免生硬重复
5. 支持5种解说风格：幽默、温馨、科技、悬疑、解压
6. 时间轴自动对齐视频时长

**【5种解说风格说明】（详见 references/story_style.md）：**

| 风格 | 特点 | 适用场景 |
|------|------|----------|
| 幽默风趣 | 轻松诙谐，适当使用网络用语和流行梗 | 娱乐、搞笑、日常 |
| 温馨感人 | 温暖柔和，注重情感表达和细节描写 | 情感、生活、人文 |
| 科技硬核 | 专业术语准确，数据支撑有力 | 数码、科技、测评 |
| 悬疑烧脑 | 制造悬念，引导思考，留有想象空间 | 悬疑、推理、剧情 |
| 解压治愈 | 舒缓放松，简洁不啰嗦 | ASMR、冥想、自然 |

**【重要】每条字幕内容限制：**
- 每条字幕最多3-5句话
- 字幕时长默认4秒（可配置）
- 内容应简洁明了，适合快速阅读
- **【强制】每条字幕内容必须不同！使用自然过渡避免重复**

**【防重复指导】**
- 基础文案库循环时自动添加过渡词
- 过渡词库：然后、接下来、继续、与此同时、在此期间等
- 确保连续字幕不会完全相同

### 步骤 10: 直接输出SRT字幕内容

**【关键约束】SRT字幕时长必须和视频总时长完全对应：**
- 最后一个字幕的结束时间 ≈ 视频总时长
- 不得超出视频时长过多

**【直接输出】AI 直接生成并输出完整SRT字幕内容：**

读取 `output/frame_descriptions.json` 后，直接按照SRT格式输出字幕内容，无需调用任何脚本。

**SRT字幕格式要求：**
```
1
00:00:00,000 --> 00:00:04,000
字幕内容第一句

2
00:00:04,000 --> 00:00:08,000
字幕内容第二句

3
00:00:08,000 --> 00:00:12,000
字幕内容第三句
...
```

**【重要】生成完成后：**
1. 将完整SRT内容保存到 `output/narration.srt`
2. 告知用户输出文件路径

**【5种解说风格】**

| 风格 | 特点 | 适用场景 |
|------|------|----------|
| humor | 幽默风趣，轻松诙谐 | 娱乐、搞笑、日常 |
| warm | 温馨感人，温暖治愈 | 情感、生活、人文 |
| tech | 科技硬核，专业严谨 | 数码、科技、测评 |
| mystery | 悬疑烧脑，紧张刺激 | 悬疑、推理、剧情 |
| healing | 解压治愈，放松舒缓 | ASMR、冥想、自然 |

### 步骤 11: 输出文件

**保存处理结果：**

```
output/
├── frames/                    # 抽取的关键帧图片(原始1080P)
│   ├── frame_0001.jpg
│   ├── frame_0002.jpg
│   └── ...
├── frames_360p/              # 压缩后的360P帧图片
│   ├── frame_0001.jpg
│   ├── frame_0002.jpg
│   └── ...
├── frames_info.json          # 帧分组信息
├── frame_descriptions.json   # 【第一阶段】画面识别JSON（详细描述）
├── narration.srt             # 【第二阶段】生成的解说字幕（4秒/句）
└── manifest.json             # 处理清单
```

**frame_descriptions.json 格式（第一阶段输出）：**

```json
{
  "video_file": "input.mp4",
  "video_duration": 120.5,
  "frame_interval": 10,
  "total_frames": 12,
  "frame_descriptions": [
    {
      "frame_id": 1,
      "timestamp": "00:00:00",
      "description": "详细描述：画面中有X个人...正在做...场景是..."
    },
    {
      "frame_id": 2,
      "timestamp": "00:00:10",
      "description": "详细描述..."
    }
  ]
}
```

**manifest.json 格式：**

```json
{
  "video_file": "input.mp4",
  "video_duration": 120.5,
  "frame_interval": 10,
  "total_frames": 12,
  "groups_count": 2,
  "subtitle_interval": 4,
  "style": "幽默风趣",
  "output_files": {
    "frames_dir": "output/frames",
    "frames_360p_dir": "output/frames_360p",
    "frame_descriptions_json": "output/frame_descriptions.json",
    "narration_srt": "output/narration.srt"
  }
}
```

## 风格化解说要点

根据用户选择的风格，解说文案应有不同特点：

**1. 幽默风趣**
- 语言轻松诙谐
- 适当加入网络用语
- 调侃但不失重点

**2. 温馨感人**
- 温暖柔和的语调
- 注重情感表达
- 强调人文关怀

**3. 科技硬核**
- 专业术语准确
- 逻辑清晰严密
- 数据支撑有力

**4. 悬疑烧脑**
- 制造悬念感
- 引导思考
- 留有想象空间

**5. 解压治愈**
- 舒缓放松语调
- 简洁不啰嗦
- 营造宁静氛围

## 使用示例

### 示例 1: 基本使用
```
用户: 分析这个视频的画面内容 /Users/videos/demo.mp4

技能响应:
1️⃣ 正在验证 FFmpeg...
   ✓ FFmpeg 已安装

2️⃣ 请输入抽帧间隔（秒/帧）：
   直接回车默认使用 10 秒

3️⃣ 请选择解说风格（直接回复数字）：
   1️⃣ 幽默风趣  2️⃣ 温馨感人  3️⃣ 科技硬核  4️⃣ 悬疑烧脑  5️⃣ 解压治愈  6️⃣ 荒野建造

用户: 3

4️⃣ 正在提取关键帧 [████████░░░░] 80%
   视频时长: 120.5 秒
   提取帧数: 12 帧

5️⃣ 正在压缩为360P...
   ✓ 12帧已压缩

6️⃣ 正在分组处理...
   分组数: 2 组（每组10帧）

7️⃣ 【第一阶段】正在并行分析画面内容...
   ✓ 第1组画面识别完成 → frame_descriptions.json
   ✓ 第2组画面识别完成 → frame_descriptions.json

8️⃣ 正在汇总画面识别结果到JSON...
   ✓ frame_descriptions.json 已生成（12帧详细描述）

9️⃣ 【第二阶段】AI 正在根据帧描述JSON生成解说文案...
   ✓ 60条解说文案已生成（科技硬核风格）
   ✓ SRT字幕已生成

🔟 正在对齐SRT字幕时长...
   ✓ 时长对齐完成 (120.5秒 = 00:02:00.500)

✅ 完成！生成文件：
- output/frames/ (12帧原始图片)
- output/frames_360p/ (12帧360P压缩图片)
- output/frame_descriptions.json (画面识别JSON)
- output/narration.srt (60条解说字幕)
```

### 示例 2: 指定抽帧间隔
```
用户: 分析这个视频，每100帧抽一帧 /Users/videos/demo.mp4
```

### 示例 3: 跳过帧分析（已存在JSON）
```
用户: 用温馨感人风格重新生成这个视频的解说 /Users/videos/demo.mp4

技能响应:
1️⃣ 正在验证 FFmpeg...
   ✓ FFmpeg 已安装

2️⃣ 请输入抽帧间隔（秒/帧）：
   直接回车默认使用 10 秒

3️⃣ 请选择解说风格（直接回复数字）：
   1️⃣ 幽默风趣  2️⃣ 温馨感人  3️⃣ 科技硬核  4️⃣ 悬疑烧脑  5️⃣ 解压治愈  6️⃣ 荒野建造

用户: 2

4️⃣ 检查 frame_descriptions.json 是否存在...
   ✓ 发现已存在的 frame_descriptions.json
   ✓ 跳过帧分析步骤，直接进入第二阶段

5️⃣ 【第二阶段】正在读取画面描述JSON...
   ✓ frame_descriptions.json 已加载（12帧描述）

6️⃣ 【第二阶段】正在生成解说文案（2秒/句）...
   ✓ 60条解说文案已生成（温馨感人风格）
   ✓ SRT字幕已生成

7️⃣ 正在对齐SRT字幕时长...
   ✓ 时长对齐完成 (120.5秒 = 00:02:00.500)

✅ 完成！生成文件：
- output/narration.srt (60条解说字幕 - 温馨感人风格)
- 输出文件覆盖旧版本 narration.srt
```

## 注意事项

1. **抽帧数量控制**：建议间隔不要过小，否则会产生大量帧图片
2. **SRT时长对齐**：生成的字幕总时长必须等于视频时长
3. **子Agent调用**：必须使用 dispatching-parallel-agents 技能并行处理
4. **风格一致性**：同一视频的所有解说必须保持同一风格
5. **多级跳过逻辑**：
   - 如果 `frames/` 和 `frames_360p/` 存在 → 跳过抽帧和压缩
   - 如果 `frame_descriptions.json` 存在 → 跳过帧分析
   - 可直接切换不同风格重新生成解说

## 【强制】禁止行为

**第一阶段（画面识别）禁止：**
- ❌ 生成解说文案
- ❌ 生成SRT字幕
- ❌ 使用风格化语言
- ✅ 只做纯画面内容详细描述

**全局禁止：**
- ❌ 禁止自己编写代码进行帧分析
- ❌ 禁止生成与视频时长不对应的SRT字幕
- ✅ 必须使用 Ollama qwen3-vl 模型分析帧图片内容
- ✅ 必须参照 references/ 目录中的示例格式

## 两阶段处理流程总结

### 第一阶段：画面识别（frame_descriptions.json）
1. 抽帧 → 压缩为360P → 分组
2. 并行子Agent分析每组帧图片
3. 详细描述：有什么人、在干什么、场景细节
4. 输出：`frame_descriptions.json`

**【重要】第一阶段支持多级跳过：**
| 检查项 | 存在？ | 动作 |
|--------|--------|------|
| `frames/` 和 `frames_360p/` | ✅ 是 | 跳过抽帧和压缩，直接分组 |
| `frame_descriptions.json` | ✅ 是 | 跳过帧分析，直接生成解说 |
| 上述都不存在 | ❌ 否 | 执行完整第一阶段流程 |

### 第二阶段：解说文案生成（narration.srt）
1. 读取 `frame_descriptions.json`
2. AI 自动分析叙事流程，划分叙事段落
3. AI 根据用户预设风格，按4秒一句生成连贯解说文案
4. AI 直接输出符合SRT格式的字幕内容
5. 保存到：`narration.srt`
