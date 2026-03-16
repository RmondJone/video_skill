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

### 步骤 3: AI 解说文案生成 (关键改进)

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

### 步骤 4: 精彩片段识别

基于语音识别结果和生成的文案，识别精彩片段：

1. 筛选高能量/信息密度高的段落
2. 根据片段时间戳提取
3. 合并相邻片段
4. 输出片段时间戳列表

可以询问用户想保留哪些片段，或者让 LLM 根据内容重要性推荐。

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
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="5">
  <project>
    <name>Video Narrator Export</name>
    <children>
      <sequence>
        <name>Main Sequence</name>
        <rate><timebase>30</timebase></rate>
        <media>
          <video>
            <track>
              <!-- 片段信息 -->
            </track>
          </video>
        </media>
      </sequence>
    </children>
  </project>
</xmeml>
```

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
  "clips": [
    {
      "id": "clip_001",
      "source_file": "input.mp4",
      "start_time": "00:01:30",
      "end_time": "00:02:45",
      "duration": 75,
      "output_file": "clips/clip_001.mp4"
    }
  ],
  "subtitles": [
    {
      "file": "subtitles/full.srt",
      "type": "full"
    },
    {
      "file": "subtitles/highlights.srt",
      "type": "highlights"
    }
  ]
}
```

## 使用示例

### 示例 1: 基本使用
```
用户: @处理一下这个视频 /Users/guohanlin/videos/demo.mp4

技能响应:
1. 正在验证视频文件...
2. 正在使用 faster-whisper 进行语音识别...
3. [将转写结果发送给当前 LLM] 正在生成解说文案...
4. 正在识别精彩片段...
5. 正在剪切视频...
6. 正在生成导出文件...

完成! 导出文件已保存到: /Users/guohanlin/videos/demo_output/

├── clips/
│   ├── clip_001.mp4 (01:30 - 02:45)
│   ├── clip_002.mp4 (05:10 - 06:30)
│   └── ...
├── subtitles/
│   ├── full.srt
│   └── highlights.srt
├── timeline/
│   └── project.xml
└── manifest.json
```

### 示例 2: 指定输出目录
```
用户: @处理 /Users/guohanlin/videos/demo.mp4，输出到 /Users/guohanlin/output/
```

### 示例 3: 指定解说风格
```
用户: @处理 /Users/guohanlin/videos/demo.mp4，解说风格要幽默风趣
```

## 配置说明

### 环境变量 (可选)

| 变量名 | 必填 | 说明 | 默认值 |
|--------|------|------|--------|
| WHISPER_MODEL | 否 | Whisper 模型大小 | base |
| MIN_CLIP_DURATION | 否 | 片段最小时长(秒) | 10 |
| MAX_CLIP_DURATION | 否 | 片段最大时长(秒) | 120 |

**重要：不需要配置任何 AI API Key！**

AI 文案生成直接使用当前 Claude 会话的能力，无需外部 API。

## 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| 视频文件不存在 | 提示用户检查文件路径 |
| FFmpeg 不可用 | 提示安装 FFmpeg |
| Whisper 模型失败 | 提供手动下载指引 |
| 磁盘空间不足 | 提示清理空间 |
| 视频格式不支持 | 提示转换格式 |

## 脚本工具

技能提供以下辅助脚本（位于 `scripts/` 目录）：

1. **transcribe.py** - 语音识别脚本
2. **cut_video.py** - 视频剪切脚本
3. **generate_xml.py** - Premiere XML 生成脚本
4. **generate_edl.py** - EDL 时间线生成脚本

使用方式：
```bash
# 语音识别
python scripts/transcribe.py input.mp4 output.srt

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
