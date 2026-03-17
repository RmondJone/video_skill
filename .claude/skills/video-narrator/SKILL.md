---
name: video-narrator
description: 视频解说生成器 - 用户粘贴视频路径即可自动处理，进行语音识别、AI解说文案生成、视频片段剪切，导出PR可编辑的文件（视频片段+SRT字幕+XML时间线）。当用户提供视频文件路径、提到视频解说、视频剪辑、字幕生成、视频切片、语音转文字、需要导出PR/Adobe Premiere文件时使用此技能。
---

# 视频解说生成器技能

用户提供本地视频文件路径，自动完成语音识别、AI 解说文案生成、视频片段剪切，导出 PR 可编辑的文件。

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

### 步骤 1.5: 检测字幕是否存在（新增）

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
- 默认检测路径：`output/subtitles/full.srt`
- 如果用户指定了输出目录，则检测 `用户指定目录/subtitles/full.srt`

**处理方式：**

1. **字幕不存在**：正常执行步骤 2（语音识别）

2. **字幕已存在**：询问用户选择
   ```
   检测到已有字幕文件: output/subtitles/full.srt

   请选择处理方式：
   1. 跳过识别（使用现有字幕）
   2. 重新识别（覆盖现有字幕）
   ```

**用户交互示例：**
```
检测到已有字幕文件: output/subtitles/full.srt

请选择处理方式：
1. 跳过识别 - 使用现有字幕继续后续步骤（推荐）
2. 重新识别 - 覆盖现有字幕重新进行语音识别
3. 指定新目录 - 指定其他输出目录

请回复数字或选项：
```

**跳过识别时：**
- 直接使用现有 `full.srt` 字幕文件
- 继续执行后续步骤（剧情分析、解说文案生成、视频剪切等）

**参数支持（可选）：**

用户也可以通过参数直接指定处理方式：

| 参数 | 说明 |
|------|------|
| `--skip-asr` | 直接跳过语音识别，使用现有字幕 |
| `--force-asr` | 强制重新执行语音识别 |

**命令示例：**
```bash
# 使用 --skip-if-exists 参数自动跳过已有字幕
python3 .claude/skills/video-narrator/scripts/transcribe.py input.mp4 output/subtitles/full.srt --skip-if-exists
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

### 步骤 2.5: 检测是否为纯音乐（新增步骤）

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

### 步骤 3: 情况 A - 有对话/旁白视频处理流程

**重要规则：**
- **有对话/旁白的视频**：禁用音频能量分析！必须基于字幕内容分析
- **纯音乐/无旁白视频**：使用音频能量分析

#### 情况 A: 有旁白/对话视频（必须按顺序执行）

当检测到视频包含对话/旁白时（识别片段数 >= 10 或文字数 >= 50），执行以下流程：

**步骤 3.1: 【必须】使用 generate_story_summary.py 脚本生成剧情摘要和关键情节分析**

【关键】必须使用 `generate_story_summary.py` 脚本生成提示词，然后发送给 LLM 分析：

```bash
# 运行剧情摘要和关键情节分析脚本
python3 .claude/skills/video-narrator/scripts/generate_story_summary.py \
    --srt output/subtitles/full.srt \
    --output output/analysis.json

# 强制分段模式（无论视频长短都分多段处理）
python3 .claude/skills/video-narrator/scripts/generate_story_summary.py \
    --srt output/subtitles/full.srt \
    --output output/analysis.json \
    --mode long

# 短视频模式（不分段）
python3 .claude/skills/video-narrator/scripts/generate_story_summary.py \
    --srt output/subtitles/full.srt \
    --output output/analysis.json \
    --mode short
```

**分段处理说明（针对长视频 > 15分钟）：**

脚本支持自动分段处理长视频，解决 LLM 上下文长度限制问题：

- **自动检测**：当视频时长超过 15 分钟时，自动将字幕分为多个段落
- **分段模式** (`--mode` 参数)：
  - `auto` (默认)：自动检测，超过 15 分钟自动分段
  - `short`：强制不分段，适用于短视频
  - `long`：强制分段，无论视频多长都分为多段处理

**脚本输出：**

短视频（< 15分钟）：
- `output/analysis_prompt.txt` - 发送给 LLM 的提示词
- `output/analysis.json` - 分析结果占位文件

长视频（> 15分钟）：
- `output/analysis_prompt_p1.txt` - 第一分段提示词
- `output/analysis_prompt_p2.txt` - 第二分段提示词（如果需要）
- `output/analysis_prompt_summary.txt` - 汇总提示词（包含所有分段的时间点）
- `output/analysis.json` - 最终分析结果

**分段分析工作流程（长视频）：**

1. 脚本自动检测视频时长，生成 1-3 个分段提示词
2. 将每个分段提示词发送给 LLM，获取该时段的关键情节
3. 将所有分段的分析结果汇总，生成完整连贯的剧情分析
4. 将最终结果填入 `analysis.json`

脚本会生成提示词，包含：
1. 视频大致剧情/内容摘要要求（200字左右）
2. 关键情节节点格式要求（时间点 | 事件描述 | 重要程度）

**步骤 3.2: 【必须】LLM 分析并输出关键情节节点**

将生成的提示词（`analysis_prompt.txt`）发送给当前 LLM，让它分析并生成：

1. **视频大致剧情/内容摘要**（100-500字）
2. **关键情节节点**（每个节点包含：时间点、事件描述、重要程度高/中/低）

LLM 输出格式要求：
```
1. 剧情摘要：xxxxx

2. 关键情节节点：
00:05:30 | 主角发现重要线索 | 高
00:10:15 | 发生激烈冲突 | 高
00:15:45 | 情节转折 | 中
...
```

**步骤 3.3: 【必须】根据 LLM 输出的关键情节创建片段**

手动将 LLM 输出的关键情节节点填入 `analysis.json`，格式如下：

```json
{
  "analysis_time": "2026-01-01T00:00:00",
  "video_type": "dialogue",
  "key_moments": [
    {
      "time": "00:05:30",
      "description": "主角发现重要线索",
      "importance": "高",
      "start_seconds": 330
    },
    {
      "time": "00:10:15",
      "description": "发生激烈冲突",
      "importance": "高",
      "start_seconds": 615
    }
  ],
  "clips": []
}
```

然后基于这些关键情节节点筛选视频片段：
1. 筛选"重要程度"为"高"的片段
2. 如需补充，可筛选"重要程度"为"中"的片段
3. 每个片段前后扩展 2-5 秒作为缓冲
4. **【关键】必须按时间顺序排序**，不是按能量排序

**步骤 3.4: 【必须】使用 generate_narrator.py 脚本生成解说文案**

必须使用 `generate_narrator.py` 脚本生成提示词，然后发送给 LLM 生成解说文案：

```bash
# 运行解说文案生成脚本
python3 .claude/skills/video-narrator/scripts/generate_narrator.py \
    --clips output/analysis.json \
    --srt output/subtitles/full.srt \
    --output output/subtitles/narrator.srt
```

脚本输出：
- `output/subtitles/narrator_prompt.txt` - 发送给 LLM 的解说文案生成提示词

脚本会生成提示词，包含：
1. 视频剧情摘要（从 analysis.json 中读取）
2. 所有片段的时间范围和描述
3. 每个片段相关的原始字幕
4. 输出格式要求

**步骤 3.5: 【必须】LLM 生成解说文案**

将生成的提示词（`narrator_prompt.txt`）发送给当前 LLM，让它根据以下要求生成解说文案：

```
请根据以下信息，为每个视频片段生成解说文案：

1. 首先分析完整字幕，生成视频剧情摘要（200字左右）

2. 然后为每个片段生成1-3句解说文案，要求：
   - 简洁、生动、符合原视频内容
   - 保持与原视频内容的相关性
   - 输出格式：
     片段1 | 00:00:10-00:00:25 | [解说文案]
     片段2 | 00:01:30-00:01:45 | [解说文案]
```

**输出：**
- `subtitles/full.srt` - 原始完整字幕
- `subtitles/narrator.srt` - AI 解说文案字幕

### 步骤 3 续: 情况 B - 纯音乐/无旁白视频处理流程

当判定为纯音乐时（识别片段数 < 10 或 文字数 < 50），使用**音频能量分析**识别精彩片段：

**重要：此方法仅用于纯音乐视频！有对话视频禁止使用！**

**方法：使用 FFmpeg 分析音频响度**

```bash
# 使用 ffmpeg 分析音频能量，输出每个片段的 RMS 能量值
ffmpeg -i input.mp4 -af "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=energy.txt" -f null -
```

**或者使用 Python 音频分析：**

```python
import subprocess
import numpy as np

def analyze_audio_energy(video_path, output_path="energy.txt"):
    """分析视频音频能量，输出每个时间段的能量值"""

    # 使用 ffprobe 获取音频流信息
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-print_format', 'json',
        '-show_format', '-show_streams',
        video_path
    ]

    # 使用 ffmpeg 提取音频并分析
    cmd = [
        'ffmpeg', '-i', video_path,
        '-af', 'compand=gain=-6,astats=metadata=1:reset=1',
        '-f', 'null', '-'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # 解析输出，提取 RMS 能量值
    # 返回: [(timestamp, energy), ...]
    energies = []
    for line in result.stderr.split('\n'):
        if 'RMS_level' in line:
            # 解析时间和能量值
            pass

    return energies
```

**精彩片段识别逻辑：**

1. 将视频按固定时间窗口分割（如 3-5 秒一段）
2. 计算每段的平均音频能量
3. 筛选能量最高的片段（通常是高潮部分）
4. 合并相邻高能量片段
5. 输出片段时间戳列表

**重要：默认保留所有识别出的高能片段，不进行数量限制！**

```python
def find_highlight_segments(energies, threshold_percentile=75, max_clips=None):
    """从音频能量数据中识别高能量片段

    Args:
        energies: 音频能量数据列表
        threshold_percentile: 能量阈值百分位（默认75，即能量最高的25%）
        max_clips: 最大保留片段数，None表示保留全部

    Returns:
        高能量片段列表
    """

    # 计算能量阈值（高于 75% 的片段）
    threshold = np.percentile(energies, threshold_percentile)

    # 标记高能量区域
    highlight_timestamps = []
    for i, (timestamp, energy) in enumerate(energies):
        if energy >= threshold:
            highlight_timestamps.append(timestamp)

    # 合并相邻片段（间隔小于 3 秒）
    merged = merge_adjacent_segments(highlight_timestamps, gap_threshold=3)

    # 过滤过短片段（小于 5 秒）
    final_segments = [s for s in merged if s['duration'] >= 5]

    # 按能量排序（从高到低）
    final_segments.sort(key=lambda x: x['avg_energy'], reverse=True)

    # 如果设置了最大片段数限制，则截取
    if max_clips is not None and max_clips > 0:
        final_segments = final_segments[:max_clips]

    return final_segments
```

### 步骤 4: 纯音乐视频解说文案（特殊处理）

**仅适用于步骤 2.5 判定为纯音乐的视频！**

如果判定为纯音乐，解说文案应该描述音乐情绪和结构，而不是基于字幕内容：

```
这是一首纯音乐视频，没有对话或旁白。

音乐结构分析：
- 00:00 - 00:48: 前奏/引入部分，情绪渐进
- 00:48 - 01:42: 第一次副歌，能量上升
- 01:56 - 02:13: 高潮段落，情绪最高点
- 02:17 - 02:52: 尾声，情感回落

建议解说文案：
"这是一段充满活力的音乐..."
```

### 步骤 5: 视频剪切

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

**重要：必须为每个精彩片段分别调用一次脚本！**

### 步骤 6: 生成导出文件

**必须使用脚本！** 先生成 manifest.json，然后调用 generate_xml.py 和 generate_edl.py 脚本。

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

#### 步骤 6.3: 生成 EDL 时间线

**必须使用脚本！**

```bash
python3 .claude/skills/video-narrator/scripts/generate_edl.py <manifest.json路径> <输出EDL路径> --fps <帧率>

# 示例：
python3 .claude/skills/video-narrator/scripts/generate_edl.py output/manifest.json output/timeline/project.edl --fps 25
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
│   ├── project.xml     # Premiere XML
│   └── project.edl     # EDL 时间线
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

**4. EDL 时间线 (CMX 3600)**
```
TITLE: Video Narrator Export
FCM: NON-DROP FRAME

001  001      V     C        00:00:10:00 00:00:25:00 00:00:00:00 00:00:15:00
002  002      V     C        00:01:30:00 00:02:45:00 00:00:15:00 00:00:30:00
```

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

### 示例 1: 有旁白的视频
```
用户: 处理一下这个视频 /Users/guohanlin/videos/demo.mp4

技能响应:
1. 正在验证视频文件...
2. 正在进行语音识别...
3. 检测到视频包含语音内容
4. 正在生成解说文案...
5. 正在识别精彩片段...
6. 正在剪切视频...
7. 正在生成导出文件...

完成! 导出文件已保存到: /Users/guohanlin/videos/demo_output/
```

### 示例 2: 纯音乐视频（新增）
```
用户: 处理一下这个音乐视频 /Users/guohanlin/videos/music.mp4

技能响应:
1. 正在验证视频文件...
2. 正在进行语音识别...
3. ⚠️ 检测到为纯音乐视频（语音识别结果少于50字）
4. 正在使用音频能量分析识别精彩片段...
5. 正在生成音乐解说文案...
6. 正在剪切视频...
7. 正在生成导出文件...

完成! 导出文件已保存到: /Users/guohanlin/videos/music_output/
- 视频类型: 纯音乐（无旁白）
- 精彩片段: 基于音频能量分析识别
```

### 示例 3: 指定输出目录
```
用户: 处理 /Users/guohanlin/videos/demo.mp4，输出到 /Users/guohanlin/output/
```

### 示例 4: 自定义片段数量
```
用户: 处理 /Users/guohanlin/videos/demo.mp4，保留10个片段

技能响应:
1. 正在验证环境...
2. 正在语音识别...
3. 正在分析音频能量...
4. 识别到 25 个高能片段，按要求保留前 10 个
5. 正在剪切视频...
6. 正在生成导出文件...

完成! 保留10个精彩片段
```

### 示例 5: 保留全部片段
```
用户: 处理 /Users/guohanlin/videos/demo.mp4，保留全部片段

技能响应:
1. 正在验证环境...
2. 正在语音识别...
3. 正在分析音频能量...
4. 识别到 25 个高能片段，全部保留
5. 正在剪切视频...
6. 正在生成导出文件...

完成! 保留全部25个精彩片段
```

## 配置说明

### 用户自定义选项

在调用技能时可以指定以下参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| --max-clips | 最大保留片段数量，0或省略表示保留全部 | 全部保留 |
| --energy-threshold | 音频能量阈值(百分位)，越高越严格 | 75 |
| --skip-asr | 跳过语音识别，使用现有字幕 | 否 |
| --force-asr | 强制重新执行语音识别 | 否 |

**使用示例：**
```
用户: 处理视频 /Users/guohanlin/videos/demo.mp4，保留10个片段
用户: 处理视频 /Users/guohanlin/videos/demo.mp4，保留全部片段
用户: 处理视频 /Users/guohanlin/videos/demo.mp4 --max-clips 5
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
2. **generate_story_summary.py** - 剧情摘要和关键情节分析脚本（有对话视频）
3. **cut_video.py** - 视频剪切脚本
4. **generate_xml.py** - Premiere XML 生成脚本
5. **generate_edl.py** - EDL 时间线生成脚本
6. **analyze_energy.py** - 音频能量分析脚本（纯音乐视频）
7. **generate_narrator.py** - 解说文案生成脚本（有对话视频）

**脚本完整路径：**
```bash
# 脚本基础路径
SCRIPT_DIR=".claude/skills/video-narrator/scripts"

# 语音识别
python3 ${SCRIPT_DIR}/transcribe.py input.mp4 output.srt

# 剧情摘要和关键情节分析（用于有对话视频）
python3 ${SCRIPT_DIR}/generate_story_summary.py \
    --srt output/subtitles/full.srt \
    --output output/analysis.json

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

# 生成 EDL（需要先有 manifest.json）
python3 ${SCRIPT_DIR}/generate_edl.py output/manifest.json output/timeline/project.edl --fps 25
```

## 注意事项

1. 大视频文件处理时间较长，显示进度
2. Whisper 模型下载一次后会缓存
3. 建议确保磁盘空间充足
4. 视频片段命名按时间顺序排列
5. **AI 文案生成零配置** - 直接利用当前 LLM 能力，无需 API Key
6. **纯音乐识别** - 自动检测并使用音频能量分析替代语音识别
7. 识别语音、剪切视频、生成XML 文件等操作必须使用SKILL 自带脚本执行
