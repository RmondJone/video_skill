---
name: video-narrator
description: 视频解说生成器 - 用户粘贴视频路径即可自动处理，进行语音识别、AI解说文案生成、视频片段剪切，导出PR可编辑的文件（视频片段+SRT字幕+XML时间线）。当用户提供视频文件路径、提到视频解说、视频剪辑、字幕生成、视频切片、语音转文字、需要导出PR/Adobe Premiere文件时使用此技能。
---

# 视频解说生成器技能

用户提供本地视频文件路径，自动完成语音识别、AI 解说文案生成、视频片段剪切，导出 PR 可编辑的文件。

**【重要】参考资料存放在 references 文件夹中：**

- `.claude/skills/video-narrator/references/analysis_example.json` - analysis.json 详细示例
- `.claude/skills/video-narrator/references/narrator_example.srt` - narrator.srt 详细示例

---

## 触发条件

用户满足以下任一条件时使用此技能：
- 用户粘贴了本地视频文件路径（无需@符号）
- 用户提到"视频解说"、"语音转文字"、"字幕生成"
- 用户要求"视频切片"、"导出PR文件"
- 用户需要将视频导出为 Premiere/Final Cut 可编辑的格式

**注意：无需用户使用 @ 触发，只需用户提供视频文件路径即可自动识别并处理。**

## 输入要求

从用户消息中提取视频文件路径，确保：
1. 视频文件存在且为支持的格式（mp4, mov, avi, mkv, webm）
2. 提取输出目录（用户指定或默认）

## 处理流程

**【进度感知】处理流程包含以下阶段，用户会看到实时进度更新：**

| 阶段 | 状态输出 | 进度条 |
|------|----------|--------|
| 1️⃣ 验证环境依赖 | "正在验证 FFmpeg 和 faster-whisper..." | 无（快速检查） |
| 2️⃣ 字幕检测 | "正在检测字幕文件..." | 无（单次检查） |
| 3️⃣ 语音识别 | "正在进行语音识别 [████████░░░░░] 80%" | ✅ tqdm 进度条 |
| 4️⃣ 剧情分析 | "正在进行剧情分析..." | AI 处理，无进度条 |
| 5️⃣ 视频剪切 | "正在剪切视频片段 [██░░░░░░░░] 3/10" | ✅ tqdm 进度条 |
| 6️⃣ 解说文案生成 | "正在生成解说文案 [████░░░░░░] 5/25" | ✅ tqdm 进度条 |
| 7️⃣ 导出文件 | "正在生成 Premiere XML..." | 无（快速生成） |

### 步骤 1: 验证环境依赖（自动执行）

**自动检查以下工具是否可用，无需用户同意：**
1. **FFmpeg** - 视频处理
2. **faster-whisper** - 语音识别
3. **Python** - 运行环境

如果缺少依赖，自动提示用户安装并执行安装命令：
```bash
# 检查并安装 ffmpeg (macOS)
which ffmpeg || brew install ffmpeg

# 检查并安装 faster-whisper
python3 -c "import faster_whisper" 2>/dev/null || pip install faster-whisper
```

### 步骤 1.5: 检测字幕是否存在（关键改动）

**自动检测：检测字幕文件是否已存在**

在执行语音识别之前，自动检测目标输出目录是否已存在 `full.srt` 字幕文件：

**检测逻辑：**
```python
import os

def check_subtitle_exists(output_dir):
    """检查字幕文件是否已存在"""
    subtitle_path = os.path.join(output_dir, "subtitles", "full.srt")
    return os.path.exists(subtitle_path)
```

**检测路径：**
- 默认检测路径：`output/<文件名>/subtitles/full.srt`（例如：`output/test1/subtitles/full.srt`）
- 如果用户指定了输出目录，则检测 `用户指定目录/subtitles/full.srt`

**【关键改动】处理方式：**

1. **字幕不存在**：正常执行步骤 2（语音识别）

2. **字幕已存在**：直接跳过识别阶段，进入剧情分析阶段
   - 直接使用现有 `full.srt` 字幕文件
   - **不再进行视频类型判断**（跳过步骤 2.5）
   - 直接进入**步骤 3：剧情分析阶段**

**用户交互示例：**
```
检测到已有字幕文件: output/test1/subtitles/full.srt

✓ 跳过语音识别，直接进入剧情分析阶段
```

**跳过识别时：**
- 直接使用现有 `full.srt` 字幕文件
- 跳过视频类型判断（不再区分有对话/纯音乐）
- 直接执行步骤 3 的剧情分析

**参数支持（可选）：**

用户也可以通过参数直接指定处理方式：

| 参数 | 说明 |
|------|------|
| `--skip-asr` | 直接跳过语音识别，使用现有字幕（默认行为） |
| `--force-asr` | 强制重新执行语音识别 |

**命令示例：**
```bash
# 默认行为：检测到字幕则自动跳过识别
python3 .claude/skills/video-narrator/scripts/transcribe.py input.mp4 output/subtitles/full.srt

# 强制重新识别
python3 .claude/skills/video-narrator/scripts/transcribe.py input.mp4 output/subtitles/full.srt --force
```

### 步骤 2: 语音识别 (ASR)

**需要用户交互：选择 Whisper 模型**

在运行语音识别之前，必须先询问用户选择模型。如果用户未选择或选择"默认"，使用 **small** 模型。

**Whisper 模型选择（必须展示给用户）：**

| 模型 | 精准度 | 预估时间（10分钟视频） | 推荐场景 |
|------|--------|----------------------|----------|
| tiny | ★☆☆☆☆ 基础 | ~30秒 | 快速测试 |
| base | ★★☆☆☆ 较好 | ~1分钟 | 速度快，精度一般 |
| **small** | ★★★☆☆ 良好 | ~2分钟 | **默认推荐**，平衡速度和精度 |
| medium | ★★★★☆ 优秀 | ~5分钟 | 需要更高精度 |
| large | ★★★★★ 最佳 | ~15分钟 | 最高精度，速度最慢 |

**询问用户示例：**
```
请选择语音识别模型（直接回复数字或模型名）：
1. small (默认) - 推荐，平衡速度和精度
2. base - 速度快，精度一般
3. medium - 需要更高精度
4. large - 最高精度，速度最慢
5. tiny - 快速测试
```

**用户选择后执行：**
```bash
# 使用用户选择的模型运行语音识别脚本
python3 .claude/skills/video-narrator/scripts/transcribe.py input.mp4 output.srt --model <选择的模型>

# 默认使用 small 模型
python3 .claude/skills/video-narrator/scripts/transcribe.py input.mp4 output.srt --model small
```

输出：
- 完整语音文字稿
- 每个片段的时间戳信息
- 生成 `full.srt` 字幕文件

### 步骤 2.5: 检测是否为纯音乐（仅首次识别时执行）

**【重要】此步骤仅在首次进行语音识别时执行。如果字幕已存在（步骤 1.5 跳过识别），则直接进入步骤 3 的剧情分析阶段，不再进行视频类型判断。**

**关键改进：自动检测视频是否为纯音乐（无对话/旁白）**

语音识别完成后，分析识别结果判断是否为纯音乐：

**判断条件：**
1. 识别出的文字字数 < 50 字
2. 识别出的片段数 < 10 个
3. 平均每个片段的文字数 < 5 字

满足以上任一条件，判定为**纯音乐视频**。

```python
# 判断逻辑示例
total_words = sum(len(seg.text.split()) for seg in segments)
avg_words_per_segment = total_words / len(segments) if segments else 0

is_instrumental = (
    total_words < 50 or  # 文字太少
    len(segments) < 10 or  # 片段太少
    avg_words_per_segment < 5  # 每片段平均字数少
)
```

**【关键】字幕已存在时的处理：**
- 如果步骤 1.5 检测到字幕已存在并跳过识别
- 则直接进入**步骤 3：剧情分析阶段**
- **不再执行步骤 2.5 的视频类型判断**
- 直接使用字幕内容进行剧情分析

### 步骤 2.6: 检测 analysis.json 是否存在（关键改动）

**【重要】在进入剧情分析阶段之前，必须检测 analysis.json 是否已存在！**

自动检测目标输出目录是否已存在 `analysis.json` 分析结果文件：

**检测逻辑：**
```python
import os

def check_analysis_exists(output_dir):
    """检查 analysis.json 是否已存在"""
    analysis_path = os.path.join(output_dir, "analysis.json")
    return os.path.exists(analysis_path)
```

**检测路径：**
- 默认检测路径：`output/<文件名>/analysis.json`（例如：`output/test1/analysis.json`）
- 如果用户指定了输出目录，则检测 `用户指定目录/analysis.json`

**【关键改动】处理方式：**

1. **analysis.json 不存在**：正常执行步骤 3（剧情分析）

2. **analysis.json 已存在**：**必须询问用户是否重新生成！**
   - 向用户展示已存在的内容概要（关键情节数量、生成时间等）
   - 询问用户选择：
     - 重新生成：删除旧的 analysis.json，重新执行步骤 3 的剧情分析
     - 继续使用：跳过剧情分析，直接进入**步骤 3.3：视频剪切阶段**

**用户交互示例：**
```
检测到已有 analysis.json 文件: output/test1/analysis.json

文件概要：
- 视频类型: 对话/旁白视频
- 关键情节: 25 个
- 角色: 6 个
- 主题: 5 个
- 生成时间: 2026-03-16 10:30:00

请选择：
1. 重新生成 - 删除旧的分析结果，重新执行剧情分析
2. 继续使用 - 直接使用现有的 analysis.json，跳过剧情分析

请回复数字或"重新生成"/"继续"：
```

**【强制规则】**
- 如果用户选择"重新生成"，必须先删除旧的 `analysis.json` 文件后再执行新的剧情分析
- 如果用户选择"继续使用"，直接跳过步骤 3.1 和 3.2，进入步骤 3.3（视频剪切）

**后续处理：**
- 选择重新生成：执行完整的剧情分析流程（步骤 3.1-3.2）
- 选择继续使用：直接进入步骤 3.3（视频剪切），然后执行步骤 3.4（生成解说文案）

### 步骤 3: 情况 A - 有对话/旁白视频处理流程

**【强制规则】所有剧情摘要、关键情节分析、解说文案生成等需要 AI 分析的操作，必须通过预设脚本完成，禁止自己生成脚本或动态创建代码执行。**

**重要规则：**
- **有对话/旁白的视频**：禁用音频能量分析！必须基于字幕内容分析
- **纯音乐/无旁白视频**：使用音频能量分析

#### 情况 A: 有旁白/对话视频（必须按顺序执行）

当检测到视频包含对话/旁白时（识别片段数 >= 10 或文字数 >= 50），执行以下流程：

**步骤 3.1: 【必须】直接使用自身能力分析字幕，生成 analysis.json**

【核心改动】不再需要将提示词发送给外部 LLM！直接使用我的能力分析字幕内容并生成 analysis.json。

**【必须执行】处理流程：**

1. **读取字幕文件**：读取 `output/ subtitles/full.srt` 内容
2. **直接分析**：根据字幕内容，直接生成符合格式的 analysis.json
3. **保存结果**：将分析结果写入 `output/analysis.json`

**【重要】长视频分段处理：**

- **自动检测**：当视频时长超过 15 分钟时，自动将字幕分为多个段落
- **分段模式** (`--mode` 参数)：
  - `auto` (默认)：自动检测，超过 15 分钟自动分段
  - `short`：强制不分段，适用于短视频
  - `long`：强制分段，无论视频多长都分为多段处理

**【长视频分析工作流程】**

对于超过 15 分钟的长视频，需要分段处理以避免上下文限制：

1. 脚本运行后会生成分段提示词文件（如果不使用脚本，也可手动分段）
2. **【直接分析】** 对每个分段的字幕内容直接进行本地分析
3. 汇总所有分段的分析结果，创建完整的 analysis.json

**【必须使用 analysis_example.json 作为格式参照】**

生成 analysis.json 时，必须严格参照 `references/analysis_example.json` 的格式：

- ✅ 必须有 video_type 字段（dialogue/instrumental）
- ✅ 必须有 summary 字段（整体剧情摘要，200-400字）
- ✅ 必须有各分 part_summary 字段（长视频需要，每个分段400-500字）
- ✅ key_moments 必须有 importance="高" 的节点
- ✅ key_moments 必须有 detailed_description 字段（50字以上，包含场景细节）
- ✅ key_moments 必须有 scene 字段
- ✅ key_moments 必须有 start 和 end 时间
- ✅ characters 数组必须包含主要角色
- ✅ 必须有 themes 数组

**【关键约束】禁止行为：**
- ❌ 禁止将提示词发送给外部 LLM API
- ❌ 禁止自己编写 Python/JS 代码生成分析结果
- ❌ 禁止手动发送提示词给任何外部 LLM 服务
- ✅ 直接使用自身能力分析字幕内容
- ✅ 必须参考 analysis_example.json 来生成 analysis.json

**步骤 3.2: 【必须】使用 analysis.json 中的关键情节创建片段**

检查脚本生成的 `analysis.json` 文件，使用其中的关键情节节点（必须包含 start 和 end 时间）：

```json
{
  "analysis_time": "2026-01-01T00:00:00",
  "video_type": "dialogue",
  "key_moments": [
    {
      "start": "00:05:20",
      "end": "00:06:10",
      "description": "主角发现重要线索",
      "importance": "高"
    },
    {
      "start": "00:10:05",
      "end": "00:10:55",
      "description": "发生激烈冲突",
      "importance": "高"
    }
  ],
  "clips": []
}
```

然后基于这些关键情节节点创建视频片段：
1. **【重要】保留所有 key_moments 中的片段**，不进行重要性筛选
2. 每个片段前后扩展 2-5 秒作为缓冲
3. **【关键】必须按时间顺序排序**，不是按能量排序

**步骤 3.3: 【必须】选择片段并进行视频剪切**

**根据生成的剧情片段进行视频剪切：**

使用 cut_video.py 脚本进行**批量剪切，只需要确认一次即可**：

```bash
# 运行视频剪切脚本
python3 .claude/skills/video-narrator/scripts/cut_video.py <输入视频> <开始时间> <结束时间> <输出文件>

# 示例：
python3 .claude/skills/video-narrator/scripts/cut_video.py input.mp4 00:01:30 00:02:45 output/clips/clip_001.mp4
```

**脚本参数说明：**
- `input`: 输入视频路径
- `start`: 开始时间 (格式: HH:MM:SS 或 MM:SS)
- `end`: 结束时间 (格式: HH:MM:SS 或 MM:SS)
- `output`: 输出视频路径
- `--re-encode`: 可选参数，添加此参数会重新编码（默认使用 copy 快速复制）

**重要：必须为每个精彩片段分别调用一次脚本！【必须】要求批量操作，不要一个个执行**

**步骤 3.4: 【必须】直接生成解说文案**

【核心改动】不再需要将提示词发送给外部 LLM！直接使用我的能力生成解说文案。

**【必须执行】处理流程：**
1. 读取已生成的 `analysis.json` 中的关键情节信息
2. 读取字幕文件 `full.srt` 内容
3. **直接使用自身能力**为每个关键情节生成解说文案
4. 按照 narrator_example.srt 的格式生成 `narrator.srt` 文件

**解说文案格式要求（参照 narrator_example.srt）：**
- SRT 格式：序号 + 时间戳 + 解说文案
- 时间戳格式：`HH:MM:SS,mmm --> HH:MM:SS,mmm`
- 每段 1-3 句话为宜
- 内容简洁、生动、与视频内容对应
- 使用中文解说

**【关键约束】禁止行为：**
- ❌ 禁止将提示词发送给外部 LLM API
- ✅ 直接使用自身能力生成解说文案
- ✅ 必须参照 narrator_example.srt 格式

### 步骤 3 续: 情况 B - 纯音乐/无旁白视频处理流程

当判定为纯音乐时（识别片段数 < 10 或 文字数 < 50），使用**音频能量分析**识别精彩片段：

**重要：此方法仅用于纯音乐视频！有对话视频禁止使用！**

**【强制】必须使用预设脚本 analyze_energy.py 进行音频能量分析：**

```bash
# 使用预设脚本分析音频能量（默认保留全部高能片段）
python3 .claude/skills/video-narrator/scripts/analyze_energy.py input.mp4 output/energy.json

# 指定保留最多10个高能片段
python3 .claude/skills/video-narrator/scripts/analyze_energy.py input.mp4 output/energy.json --max-clips 10

# 指定能量阈值（百分位，越高越严格）
python3 .claude/skills/video-narrator/scripts/analyze_energy.py input.mp4 output/energy.json --threshold 80
```

**【禁止行为】**
- ❌ 禁止自己编写 Python/JS 代码进行音频分析
- ❌ 禁止手动使用 ffmpeg 命令分析能量
- ✅ 只能使用预设的 `analyze_energy.py` 脚本

**重要：默认保留所有识别出的高能片段，不进行数量限制！**

**【重要】输出片段按时间顺序排序！**
- 识别出的精彩片段按时间顺序（从视频开头到结尾）排列
- 不是按能量高低排序，保持视频叙事的连贯性
- 有对话视频和纯音乐视频的处理结果均按时间顺序排列

**必须使用脚本！** 运行 scripts/cut_video.py 脚本进行剪切：

```bash
# 运行视频剪切脚本
python3 .claude/skills/video-narrator/scripts/cut_video.py <输入视频> <开始时间> <结束时间> <输出文件>

# 示例：
python3 .claude/skills/video-narrator/scripts/cut_video.py input.mp4 00:01:30 00:02:45 output/clip_001.mp4
```

**脚本参数说明：**
- `input`: 输入视频路径
- `start`: 开始时间 (格式: HH:MM:SS 或 MM:SS)
- `end`: 结束时间 (格式: HH:MM:SS 或 MM:SS)
- `output`: 输出视频路径
- `--re-encode`: 可选参数，添加此参数会重新编码（默认使用 copy 快速复制）

**重要：必须为每个精彩片段分别调用一次脚本！要求批量操作，用户只需确认一次**

### 步骤 5: 纯音乐视频解说文案（特殊处理）

**仅适用于步骤 2.5 判定为纯音乐的视频！**

在视频剪切完成后，生成纯音乐解说文案。

如果判定为纯音乐，解说文案应该描述音乐情绪和结构，而不是基于字幕内容。

**【强制】使用预设脚本生成纯音乐解说文案：**

可以使用 `generate_narrator.py` 脚本生成音乐解说文案模板，然后根据实际情况调整：

```bash
python3 .claude/skills/video-narrator/scripts/generate_narrator.py \
    --clips output/energy.json \
    --srt output/subtitles/full.srt \
    --output output/subtitles/narrator.srt
```

**【禁止】**
- ❌ 禁止自己编写音乐分析代码
- ❌ 禁止手动生成音乐结构分析文案

### 步骤 6: 生成导出文件

**必须使用脚本！** 先生成 manifest.json，然后调用 generate_xml.py 脚本。

#### 步骤 6.1: 生成 manifest.json

首先需要创建素材清单 manifest.json，包含所有片段的时间信息：

```json
{
  "project": "video-narrator-export",
  "created": "2026-03-16T10:30:00Z",
  "video_type": "instrumental",
  "clips": [
    {
      "id": "clip_001",
      "start_time": "00:01:30",
      "end_time": "00:02:45",
      "duration": 75,
      "output_file": "clips/clip_001.mp4"
    }
  ]
}
```

#### 步骤 6.2: 生成 Premiere XML

**必须使用脚本！**

```bash
python3 .claude/skills/video-narrator/scripts/generate_xml.py <片段目录> <输出XML路径> --manifest <manifest.json路径> --fps <帧率>

# 示例：
python3 .claude/skills/video-narrator/scripts/generate_xml.py output/clips output/timeline/project.xml --manifest output/manifest.json --fps 25
```

#### 目录结构
```
output/
├── clips/              # 剪切后的视频片段
│   ├── clip_001.mp4
│   ├── clip_002.mp4
├── subtitles/          # 字幕文件
│   ├── full.srt        # 完整语音识别字幕
│   ├── narrator.srt    # AI 解说文案字幕
│   └── narrator_prompt.txt  # 解说文案生成提示词（供 LLM 使用）
├── timeline/           # 时间线文件
│   └── project.xml     # Premiere XML
├── energy.json         # 音频能量分析数据
└── manifest.json       # 素材清单
```

#### 导出文件格式

**1. 视频片段 (MP4)**
- 使用 H.264 编码
- 保持原始分辨率

**2. SRT 字幕**
- 标准 SRT 格式
- 时间戳格式: `HH:MM:SS,mmm`

**3. Premiere XML 时间线**

正确的 Premiere XML 格式（可直接导入 Premiere）：

```xml
<?xml version='1.0' encoding='utf-8'?>
<xmeml version="5">
  <sequence explodedTracks="true">
    <name>Video Narrator Export</name>
    <duration>36</duration>
    <rate>
      <timebase>30</timebase>
      <ntsc>FALSE</ntsc>
    </rate>
    <media>
      <video>
        <format>
          <samplecharacteristics>
            <width>1920</width>
            <height>1080</height>
            <pixelaspectratio>square</pixelaspectratio>
            <rate>
              <timebase>30</timebase>
              <ntsc>FALSE</ntsc>
            </rate>
          </samplecharacteristics>
        </format>
        <track>
          <clipitem id="clipitem-1">
            <name>clip_001</name>
            <enabled>TRUE</enabled>
            <start>0</start>
            <end>180</end>
            <in>0</in>
            <out>180</out>
            <file id="file-1">
              <name>clip_001.mp4</name>
              <pathurl>/path/to/clip_001.mp4</pathurl>
              <timecode>
                <string>00:00:00:00</string>
                <displayformat>NDF</displayformat>
                <rate>
                  <timebase>30</timebase>
                  <ntsc>FALSE</ntsc>
                </rate>
              </timecode>
              <!-- 完整的 media 信息 -->
            </file>
            <link>
              <linkclipref>clipitem-1</linkclipref>
              <mediatype>video</mediatype>
              <trackindex>1</trackindex>
              <clipindex>1</clipindex>
            </link>
          </clipitem>
        </track>
      </video>
      <!-- 音频部分：双轨道 stereo 结构 -->
      <audio>
        <numOutputChannels>2</numOutputChannels>
        <track>
          <!-- 音频片段 -->
        </track>
      </audio>
    </media>
  </sequence>
</xmeml>
```

**关键要点：**
- 根元素直接是 `<sequence>`，无 `<project>` 包装
- 需要 `explodedTracks="true"` 属性
- 需要完整的 `<format>` 和 `<samplecharacteristics>` 视频信息
- 音频使用双轨道 stereo 结构
- 路径使用 `/` 格式（不带 `file://` 前缀）
- 使用 `ntsc="FALSE"`

**5. 素材清单 (manifest.json)**
```json
{
  "project": "video-narrator-export",
  "created": "2026-03-16T10:30:00Z",
  "video_type": "instrumental", 
  "clips": [
    {
      "id": "clip_001",
      "source_file": "input.mp4",
      "start_time": "00:01:30",
      "end_time": "00:02:45",
      "duration": 75,
      "output_file": "clips/clip_001.mp4",
      "energy_level": "high"
    }
  ],
  "subtitles": [
    {
      "file": "subtitles/full.srt",
      "type": "full"
    }
  ]
}
```

## 使用示例

### 示例 1: 有旁白的视频（含进度条显示）
```
用户: 处理一下这个视频 /Users/guohanlin/videos/demo.mp4

技能响应:
1️⃣ 正在验证 FFmpeg 和 faster-whisper...
   ✓ FFmpeg 已安装
   ✓ faster-whisper 已安装

2️⃣ 正在检测字幕文件...
   ⚠️ 未检测到字幕，开始语音识别

3️⃣ 正在进行语音识别 [████████░░░░░░░░░░░] 80% [80片段/100预估]
   预估片段数: 100 个
   检测语言: zh (概率: 0.95)
   正在生成字幕文件...

4️⃣ 正在进行剧情分析，请稍候...
   （AI 分析过程，无进度条）

5️⃣ 正在剪切视频片段 [██░░░░░░░░░░░░░] 3/25
   视频剪切: 00:05:20 -> 00:06:10
   输出: output/clips/clip_001.mp4
   完成! 片段时长: 00:00:50

6️⃣ 正在生成解说文案 [████░░░░░░░░░░] 5/25
   解说文案生成提示词已保存

7️⃣ 正在生成 Premiere XML...
   ✓ manifest.json 已生成
   ✓ project.xml 已生成

✅ 完成! 导出文件已保存到: /Users/guohanlin/videos/demo_output/
```

### 示例 2: 纯音乐视频（含进度条显示）
```
用户: 处理一下这个音乐视频 /Users/guohanlin/videos/music.mp4

技能响应:
1️⃣ 正在验证 FFmpeg 和 faster-whisper...
   ✓ FFmpeg 已安装
   ✓ faster-whisper 已安装

2️⃣ 正在检测字幕文件...
   ⚠️ 未检测到字幕，开始语音识别

3️⃣ 正在进行语音识别 [████████████░░░░] 120/150 片段
   预估片段数: 150 个
   ⚠️ 检测到为纯音乐视频（语音识别结果少于50字）

4️⃣ 正在使用音频能量分析识别精彩片段 [██████░░░░░░░░░░] 60%
   音频能量分析: 正在分析 00:00:00 - 00:03:00 (能量: 0.45)
   音频能量分析: 正在分析 00:03:00 - 00:06:00 (能量: 0.72)
   ...
   能量阈值: 0.65 (第 75% 百分位)
   识别到 8 个高能片段

5️⃣ 正在剪切视频片段 [███████░░░░░░░░] 7/8
   ...

6️⃣ 正在生成音乐解说文案 [████████░░░░░░░░] 7/8
   ...

7️⃣ 正在生成导出文件...
   ...

✅ 完成! 导出文件已保存到: /Users/guohanlin/videos/music_output/
- 视频类型: 纯音乐（无旁白）
- 精彩片段: 基于音频能量分析识别
```

### 示例 3: 指定输出目录
```
用户: 处理 /Users/guohanlin/videos/demo.mp4，输出到 /Users/guohanlin/output/
```

## 配置说明

### 用户自定义选项

在调用技能时可以指定以下参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| --max-clips | 解说片段最大数量（用于筛选关键片段，0或空表示保留全部） | 0 |
| --clip-duration | 每个解说片段时长（秒） | 40 |
| --energy-threshold | 音频能量阈值(百分位)，越高越严格 | 75 |
| --skip-asr | 跳过语音识别，使用现有字幕 | 否 |
| --force-asr | 强制重新执行语音识别 | 否 |

**解说时长参考：**
| 片段数 | 每段时长 | 总时长 |
|--------|----------|--------|
| 8 | 40秒 | ~5分钟 |
| 15 | 40秒 | ~10分钟 |
| 20 | 40秒 | ~13分钟 |
| 25 | 40秒 | ~17分钟 |

**使用示例：**
```
用户: 处理视频 /Users/guohanlin/videos/demo.mp4，生成10分钟解说
用户: 处理视频 /Users/guohanlin/videos/demo.mp4，生成5分钟精简版
用户: 处理视频 /Users/guohanlin/videos/demo.mp4 --max-clips 8
```

### 环境变量 (可选)

| 变量名 | 必填 | 说明 | 默认值 |
|--------|------|------|--------|
| WHISPER_MODEL | 否 | Whisper 模型大小 (tiny/base/small/medium/large) | **small** |
| CUDA_ENABLED | 否 | 是否启用 GPU 加速 (true/false) | auto (自动检测) |
| MIN_CLIP_DURATION | 否 | 片段最小时长(秒) | 5 |
| MAX_CLIP_DURATION | 否 | 片段最大时长(秒) | 120 |
| ENERGY_THRESHOLD | 否 | 音频能量阈值(百分位) | 75 |
| MAX_CLIPS | 否 | 默认最大片段数量，0表示全部保留 | 0（全部） |

**重要：不需要配置任何 AI API Key！**

AI 文案生成直接使用当前 Claude 会话的能力，无需外部 API。

## 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| 视频文件不存在 | 提示用户检查文件路径 |
| FFmpeg 不可用 | 提示安装 FFmpeg |
| Whisper 模型失败 | 提供手动下载指引 |
| 音频分析失败 | 回退到默认剪切策略（均匀切片） |
| 磁盘空间不足 | 提示清理空间 |
| 视频格式不支持 | 提示转换格式 |

## 脚本工具

**重要：所有脚本位于 `.claude/skills/video-narrator/scripts/` 目录**

技能提供以下辅助脚本：

1. **transcribe.py** - 语音识别脚本
2. **cut_video.py** - 视频剪切脚本
3. **generate_xml.py** - Premiere XML 生成脚本
4. **analyze_energy.py** - 音频能量分析脚本（纯音乐视频）
5. **generate_narrator.py** - 解说文案生成脚本（有对话视频）

**脚本完整路径：**
```bash
# 脚本基础路径
SCRIPT_DIR=".claude/skills/video-narrator/scripts"

# 语音识别
python3 ${SCRIPT_DIR}/transcribe.py input.mp4 output.srt

# 音频能量分析（默认保留全部片段）
python3 ${SCRIPT_DIR}/analyze_energy.py input.mp4 energy.json

# 音频能量分析（保留最多10个片段）
python3 ${SCRIPT_DIR}/analyze_energy.py input.mp4 energy.json --max-clips 10

# 生成解说文案提示词（用于有对话的视频）
python3 ${SCRIPT_DIR}/generate_narrator.py \
    --clips output/analysis.json \
    --srt output/subtitles/full.srt \
    --output output/subtitles/narrator.srt

# 视频剪切（每个片段调用一次）
python3 ${SCRIPT_DIR}/cut_video.py input.mp4 00:01:30 00:02:45 output/clips/clip_001.mp4

# 生成 Premiere XML（需要先有 manifest.json）
python3 ${SCRIPT_DIR}/generate_xml.py output/clips output/timeline/project.xml --manifest output/manifest.json --fps 25
```

## 注意事项

1. 大视频文件处理时间较长，显示进度
2. Whisper 模型下载一次后会缓存
3. 建议确保磁盘空间充足
4. 视频片段命名按时间顺序排列
5. **【强制】所有操作必须使用预设脚本** - 禁止自己编写代码或动态生成脚本执行
6. **纯音乐识别** - 自动检测并使用音频能量分析替代语音识别

## 【强制】禁止行为清单

以下行为**严格禁止**：

- ❌ 禁止自己编写 Python/JS/Bash 脚本进行任何分析
- ❌ 禁止手动调用 ffmpeg 进行音频能量分析
- ❌ 禁止修改或扩展预设脚本的功能
- ❌ 禁止创建新的临时脚本文件

## 【强制】允许行为

以下行为**允许**：

- ✅ 只能使用预设脚本的参数和功能
- ✅ 只能使用预设脚本的输入输出格式
- ✅ 只能查看预设脚本生成的提示词文件（供调试参考）
- ✅ 只能使用已存在的分析结果文件（analysis.json、energy.json 等）

---

## 参照格式（详细示例）

以下是实际处理 `inputs/test1.mp4`（《绝命毒师》第一季片段）时生成的详细格式参照：

### 1. analysis.json 详细格式

**【重要】analysis.json 必须包含以下完整字段：**

```json
{
  "analysis_time": "2026-03-17T00:00:00",
  "video_type": "dialogue",
  "video_title": "Breaking Bad - Season 1 Compilation",
  "duration": "00:47:52",
  "summary": "视频整体剧情摘要，200-400字，概括主要剧情线和人物关系",

  "part1_summary": "第一部分详细剧情摘要（400-500字），包含时间范围、主要场景、角色行为、关键对话要点",
  "part2_summary": "第二部分详细剧情摘要",
  "part3_summary": "第三部分详细剧情摘要",
  "part4_summary": "第四部分详细剧情摘要",

  "key_moments": [
    {
      "start": "00:00:00",
      "end": "00:00:45",
      "description": "事件简短描述",
      "importance": "高/中/低",
      "detailed_description": "详细的事件描述，包括具体场景、人物动作、对话内容、情绪等。至少50-100字。**【重要】详细描述的剧情内容必须发生在 start 和 end 指定的时间范围内！**",
      "scene": "场景位置"
    }
  ],

  "characters": [
    {
      "name": "角色名",
      "description": "角色详细介绍，包括身份、性格、背景等",
      "role": "主角/配角/反派/客串",
      "relationships": ["与其他角色的关系"]
    }
  ],

  "themes": [
    "主题1",
    "主题2"
  ],

  "clips": []
}
```

**【重要】key_moments 详细字段说明：**

| 字段 | 必须 | 说明 |
|------|------|------|
| start | ✅ | **开始时间**，格式 HH:MM:SS，表示该情节片段的开始时间 |
| end | ✅ | **结束时间**，格式 HH:MM:SS，表示该情节片段的结束时间 |
| description | ✅ | 简短描述，20-50字 |
| importance | ✅ | 高/中/低，必须有高重要性节点 |
| detailed_description | ✅ | **结构化详细描述**，80-200字，必须包含以下结构化字段：<br>• **人物**：该时间段内出现的所有人物列表<br>• **动作**：每个角色的具体动作描写（转身、皱眉、握拳等）<br>• **对话**：关键对白内容（可用原文或概括）<br>• **场景**：环境、地点、背景细节<br>• **氛围**：情绪基调、气氛描写<br>**【强制】所有内容必须发生在 start 和 end 时间范围内！** |
| scene | ✅ | 场景位置，如"RV内"、"医院"、"街头"等 |

**实际示例（来自 test1.mp4）：**

```json
{
  "start": "00:09:20",
  "end": "00:10:05",
  "description": "Walter高中化学课堂 - 讲授手性化学（chirality）",
  "importance": "高",
  "detailed_description": "Walter在高中讲授化学课，解释'手性'概念——像左右手一样，分子可以是镜像但不能重叠。他用沙利度胺为例，右旋异构体是良药，左旋异构体导致婴儿畸形。这为后续他用化学知识处理尸体做铺垫。**剧情发生在09分20秒到10分05秒之间。**",
  "scene": "高中教室"
},
{
  "start": "00:44:00",
  "end": "00:44:45",
  "description": "Walter承认杀了人 - 'I cooked crystal meth and killed a man'",
  "importance": "高",
  "detailed_description": "关键剧情！Walter终于承认他制毒（cooked crystal meth）而且杀了人。他告诉Jesse，告诉Skyler这些总比承认制毒和杀人要好。这是Walter彻底堕落的时刻。**剧情发生在44分00秒到44分45秒之间。**",
  "scene": "Walter家中"
}
```

**characters 字段说明：**

| 字段 | 必须 | 说明 |
|------|------|------|
| name | ✅ | 角色名 |
| description | ✅ | 50-100字的详细介绍 |
| role | ✅ | 主角/配角/反派/受害者/客串角色 |
| relationships | ✅ | 与其他角色的关系列表 |

### 2. narrator.srt 详细格式

**SRT 字幕格式要求：**

```
序号
开始时间 --> 结束时间
解说文案内容

序号
开始时间 --> 结束时间
解说文案内容
```

**时间戳格式：** `HH:MM:SS,mmm --> HH:MM:SS,mmm`

**解说文案要求：**
- 每个片段 1-3 句话为宜
- 内容要简洁、生动、符合原视频内容
- 使用中文解说

**实际示例（来自 test1.mp4）：**

```
1
00:00:00,000 --> 00:00:20,000
开场，Jesse和另一人刚从一场混乱中脱身，对方询Are you okay? 感谢某人救了他们。Jesse说：你是救命恩人，我们怎么感谢你都不为过。

2
00:00:20,000 --> 00:00:40,000
Jesse描述他们的悲惨处境：他们偏离了主路，车陷进了沟渠。他在开车时看地图，咖啡洒了一裤子。真是噩梦一场。

...

24
00:07:40,000 --> 00:08:00,000
最大发现！Walter解释：氢氟酸不会腐蚀塑料，但会腐蚀金属、岩石、玻璃、陶瓷——浴缸会被腐蚀穿孔！计划彻底失败。

25
00:07:40,000 --> 00:08:00,000
剧集结尾暗示：'If one should fall, the other follows him.' Walter和Jesse命运相连，一损俱损，无法逃脱。
```

### 3. 完整的处理流程参照

**处理 test1.mp4（《绝命毒师》第一季，47分钟）的完整流程：**

```
1. 验证环境 - FFmpeg ✓, Python ✓, faster-whisper ✓

2. 检测字幕 - 发现已存在 output/test1/subtitles/full.srt
   → 跳过语音识别

3. 【直接分析】读取字幕内容，使用自身能力直接分析：

   - 分析第1分段 (00:00:00-00:11:58) 剧情
   - 分析第2分段 (00:11:58-00:23:56) 剧情
   - 分析第3分段 (00:23:56-00:35:54) 剧情
   - 分析第4分段 (00:35:54-00:47:52) 剧情

4. 直接创建 analysis.json，包含：
   - 4个分段的详细剧情摘要（各400-500字）
   - 25个关键情节节点（每个都有详细描述）
   - 6个主要角色介绍和关系图
   - 5个主题分析

5. 【直接生成】根据 analysis.json，直接生成 narrator.srt 解说文案

6. 根据 analysis.json 中的25个关键情节节点创建25段解说文案

7. 视频剪切（待执行）
```

### 4. 关键约束汇总

**生成 analysis.json 时的必须项：**

- ✅ 必须有 video_type 字段（dialogue/instrumental）
- ✅ 必须有 summary 字段（整体剧情摘要）
- ✅ 必须有各分 part_summary 字段（长视频需要）
- ✅ key_moments 必须有 importance="高" 的节点
- ✅ key_moments 必须有 detailed_description 字段（50字以上）
- ✅ key_moments 必须有 scene 字段
- ✅ characters 数组必须包含主要角色
- ✅ 必须有 themes 数组

**生成 narrator.srt 时的必须项：**

- ✅ 序号从1开始，连续编号
- ✅ 时间戳格式为 HH:MM:SS,mmm
- ✅ 解说文案为中文
- ✅ 内容与视频时间点对应

