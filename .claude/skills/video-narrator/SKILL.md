---
name: video-narrator
description: 视频解说生成器 - 用户@出要处理的视频，自动进行语音识别、AI解说文案生成、视频片段剪切，导出PR可编辑的文件（视频片段+SRT字幕+XML时间线）。当用户提到视频解说、视频剪辑、字幕生成、视频切片、语音转文字、需要导出PR/Adobe Premiere文件时使用此技能。
---

# 视频解说生成器技能

用户 @ 出本地视频文件路径，自动完成语音识别、AI 解说文案生成、视频片段剪切，导出 PR 可编辑的文件。

## 触发条件

用户满足以下任一条件时使用此技能：
- 用户 @ 出视频文件并要求生成解说
- 用户提到"视频解说"、"语音转文字"、"字幕生成"
- 用户要求"视频切片"、"导出PR文件"
- 用户需要将视频导出为 Premiere/Final Cut 可编辑的格式

## 输入要求

从用户消息中提取视频文件路径，确保：
1. 视频文件存在且为支持的格式（mp4, mov, avi, mkv, webm）
2. 提取输出目录（用户指定或默认）

## 处理流程

### 步骤 1: 验证环境依赖

检查以下工具是否可用：
1. **FFmpeg** - 视频处理
2. **faster-whisper** - 语音识别
3. **Python** - 运行环境

如果缺少依赖，提示用户安装：
```bash
# 安装 ffmpeg (macOS)
brew install ffmpeg

# 安装 faster-whisper
pip install faster-whisper
```

### 步骤 2: 语音识别 (ASR)

使用 faster-whisper 识别视频中的语音：

```bash
# 运行语音识别脚本
python scripts/transcribe.py input.mp4 output.srt --model base
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

### 步骤 3: 根据类型选择处理方式

#### 情况 A: 有旁白/对话 → 原有流程

1. 将语音识别结果发送给当前 LLM
2. 生成解说文案
3. 基于文案内容识别精彩片段

#### 情况 B: 纯音乐/无旁白 → 音频能量分析（新增）

当判定为纯音乐时，使用**音频能量分析**识别精彩片段：

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

1. 将视频按固定时间窗口分割（如 5 秒一段）
2. 计算每段的平均音频能量
3. 筛选能量最高的片段（通常是高潮部分）
4. 合并相邻高能量片段
5. 输出片段时间戳列表

```python
def find_highlight_segments(energies, threshold_percentile=75):
    """从音频能量数据中识别高能量片段"""

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

    return final_segments
```

### 步骤 4: AI 解说文案生成

**不需要配置任何外部 API Key！直接使用当前 Claude 会话生成文案。**

将语音识别结果发送给当前 LLM，让它根据以下要求生成解说文案：
1. 阅读语音转写的文字稿
2. 根据用户需求（如风格、长度、重点）生成解说文案
3. 保持与时间戳的对应关系
4. 输出时标注每个段落对应的视频时间点

**提示词示例：**
```
我已完成了视频的语音识别，以下是转写结果：

[粘贴语音转写内容]

请根据以下要求生成视频解说文案：
- 风格：[幽默/专业/亲切/正式]
- 重点：[描述用户想强调的内容]
- 总时长：约 X 分钟

请生成适合配音的解说文案，并在每个段落前标注对应的时间点。
```

**纯音乐视频的解说文案：**

如果步骤 2.5 判定为纯音乐，解说文案应该描述音乐情绪和结构：

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

使用 FFmpeg 按时间戳剪切视频：

```bash
# 运行视频剪切脚本
python scripts/cut_video.py input.mp4 00:01:30 00:02:45 output_clip.mp4
```

### 步骤 6: 生成导出文件

#### 目录结构
```
output/
├── clips/              # 剪切后的视频片段
│   ├── clip_001.mp4
│   ├── clip_002.mp4
├── subtitles/          # 字幕文件
│   ├── full.srt       # 完整字幕
│   └── highlights.srt # 精彩片段字幕
├── timeline/          # 时间线文件
│   └── project.xml    # Premiere XML
└── manifest.json      # 素材清单
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
用户: @处理一下这个视频 /Users/guohanlin/videos/demo.mp4

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
用户: @处理一下这个音乐视频 /Users/guohanlin/videos/music.mp4

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
用户: @处理 /Users/guohanlin/videos/demo.mp4，输出到 /Users/guohanlin/output/
```

## 配置说明

### 环境变量 (可选)

| 变量名 | 必填 | 说明 | 默认值 |
|--------|------|------|--------|
| WHISPER_MODEL | 否 | Whisper 模型大小 | base |
| MIN_CLIP_DURATION | 否 | 片段最小时长(秒) | 10 |
| MAX_CLIP_DURATION | 否 | 片段最大时长(秒) | 120 |
| ENERGY_THRESHOLD | 否 | 音频能量阈值(百分位) | 75 |

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

技能提供以下辅助脚本（位于 `scripts/` 目录）：

1. **transcribe.py** - 语音识别脚本
2. **cut_video.py** - 视频剪切脚本
3. **generate_xml.py** - Premiere XML 生成脚本
4. **generate_edl.py** - EDL 时间线生成脚本
5. **analyze_energy.py** - 音频能量分析脚本（新增）

使用方式：
```bash
# 语音识别
python scripts/transcribe.py input.mp4 output.srt

# 音频能量分析（新增）
python scripts/analyze_energy.py input.mp4 energy.json

# 视频剪切
python scripts/cut_video.py input.mp4 00:01:30 00:02:45 output.mp4

# 生成 XML
python scripts/generate_xml.py clips/ timeline/project.xml
```

## 注意事项

1. 大视频文件处理时间较长，显示进度
2. Whisper 模型下载一次后会缓存
3. 建议确保磁盘空间充足
4. 视频片段命名按时间顺序排列
5. **AI 文案生成零配置** - 直接利用当前 LLM 能力，无需 API Key
6. **纯音乐识别** - 自动检测并使用音频能量分析替代语音识别
