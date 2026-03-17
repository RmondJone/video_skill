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

### 步骤 3: 情况 A - 有对话/旁白视频处理流程

**【强制规则】所有剧情摘要、关键情节分析、解说文案生成等需要 AI 分析的操作，必须通过预设脚本完成，禁止自己生成脚本或动态创建代码执行。**

**重要规则：**
- **有对话/旁白的视频**：禁用音频能量分析！必须基于字幕内容分析
- **纯音乐/无旁白视频**：使用音频能量分析

#### 情况 A: 有旁白/对话视频（必须按顺序执行）

当检测到视频包含对话/旁白时（识别片段数 >= 10 或文字数 >= 50），执行以下流程：

**步骤 3.1: 【必须】使用 generate_story_summary.py 脚本生成剧情摘要和关键情节分析**

【强制】必须使用 `generate_story_summary.py` 脚本生成提示词，该脚本会生成 `analysis_prompt.txt` 文件，然后自动完成分析：

```bash
# 运行剧情摘要和关键情节分析脚本（短视频 < 15分钟）
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

**【重要】脚本执行流程：**
1. 脚本自动读取字幕文件
2. 脚本自动生成分析提示词并保存到 `analysis_prompt.txt`
3. **【禁止】不允许手动将提示词发送给 LLM 或自己编写代码生成分析结果**
4. 脚本运行完成后，检查是否生成了 `analysis.json` 文件
   - 如果已存在有效的 `analysis.json`，说明已有分析结果，直接使用
   - 如果不存在，需要使用预设的分析结果文件或重新运行脚本

**分段处理说明（针对长视频 > 15分钟）：**

脚本支持自动分段处理长视频，解决上下文长度限制问题：

- **自动检测**：当视频时长超过 15 分钟时，自动将字幕分为多个段落
- **分段模式** (`--mode` 参数)：
  - `auto` (默认)：自动检测，超过 15 分钟自动分段
  - `short`：强制不分段，适用于短视频
  - `long`：强制分段，无论视频多长都分为多段处理

**脚本输出：**

短视频（< 15分钟）：
- `output/analysis_prompt.txt` - 发送给 LLM 的提示词（仅供查看）
- `output/analysis.json` - 分析结果（如果已有则使用，否则需要预先准备）

长视频（> 15分钟）：
- `output/analysis_prompt_p1.txt` - 第一分段提示词
- `output/analysis_prompt_p2.txt` - 第二分段提示词（如果需要）
- `output/analysis_prompt_summary.txt` - 汇总提示词（包含所有分段的时间点）
- `output/analysis.json` - 最终分析结果

**【关键约束】禁止行为：**
- ❌ 禁止自己编写 Python/JS 代码生成分析结果
- ❌ 禁止手动将 prompt 发送给 LLM 并自己填入结果
- ❌ 禁止修改或扩展预设脚本的功能
- ✅ 只能使用预设脚本的参数和功能
- ✅ 如果需要分析结果，必须使用已存在的 analysis.json 或通过脚本重新生成

**步骤 3.2: 【必须】使用 analysis.json 中的关键情节创建片段**

检查脚本生成的 `analysis.json` 文件，使用其中的关键情节节点：

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

**步骤 3.3: 【必须】使用 generate_narrator.py 脚本生成解说文案**

必须使用 `generate_narrator.py` 脚本生成解说文案：

```bash
# 运行解说文案生成脚本
python3 .claude/skills/video-narrator/scripts/generate_narrator.py \
    --clips output/analysis.json \
    --srt output/subtitles/full.srt \
    --output output/subtitles/narrator.srt
```

**【强制】脚本执行规则：**
- 脚本会自动生成 `narrator_prompt.txt` 提示词文件
- **【禁止】不允许手动将提示词发送给 LLM**
- 脚本运行后检查是否生成了有效的 `narrator.srt` 文件
  - 如果已存在，使用该文件
  - 如果不存在，需要使用预设的模板或重新运行脚本

**步骤 3.4: 视频剪切**

与原步骤 5 相同，使用 cut_video.py 脚本。

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

### 步骤 4: 纯音乐视频解说文案（特殊处理）

**仅适用于步骤 2.5 判定为纯音乐的视频！**

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
5. **【强制】所有操作必须使用预设脚本** - 禁止自己编写代码或动态生成脚本执行
6. **纯音乐识别** - 自动检测并使用音频能量分析替代语音识别

## 【强制】禁止行为清单

以下行为**严格禁止**：

- ❌ 禁止自己编写 Python/JS/Bash 脚本进行任何分析
- ❌ 禁止手动调用 ffmpeg 进行音频能量分析
- ❌ 禁止将提示词手动发送给 LLM 并自己填入结果
- ❌ 禁止修改或扩展预设脚本的功能
- ❌ 禁止创建新的临时脚本文件

## 【强制】允许行为

以下行为**允许**：

- ✅ 只能使用预设脚本的参数和功能
- ✅ 只能使用预设脚本的输入输出格式
- ✅ 只能查看预设脚本生成的提示词文件（供调试参考）
- ✅ 只能使用已存在的分析结果文件（analysis.json、energy.json 等）
