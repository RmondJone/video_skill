# 视频解说生成器技能设计文档

## 概述

创建一个 Claude Code 技能，用户可以通过 @ 方式指定本地视频文件，自动完成以下工作：

1. **语音识别**：使用 faster-whisper 将视频中的语音转为文字
2. **AI 解说文案生成**：基于语音文字，使用 AI 生成解说文案（支持多种 API 配置）
3. **精彩片段识别**：自动识别视频中的精彩片段
4. **视频剪切**：按时间戳剪切视频片段
5. **导出 PR 可编辑文件**：输出视频片段 + SRT 字幕 + XML/EDL 时间线 + PR 项目文件

## 核心功能

### 1. 输入处理
- 支持用户通过 @ 方式提供视频文件路径
- 支持常见视频格式：mp4, mov, avi, mkv, webm
- 验证视频文件存在且可读

### 2. 语音转文字 (ASR)
- 使用 faster-whisper 进行本地语音识别
- 支持多种模型：tiny, base, small, medium, large
- 输出 SRT 格式字幕文件

### 3. AI 解说文案生成
- 支持多种 AI API 配置：
  - OpenAI API (GPT-4o, GPT-4o-mini)
  - Anthropic API (Claude)
  - 兼容 OpenAI 格式的 API (Ollama, DeepSeek, etc.)
- 根据语音文字生成解说文案
- 生成带时间戳的 SRT 字幕文件

### 4. 精彩片段识别
- 基于语音识别结果识别有内容的片段
- 可配置片段最小/最大时长
- 生成片段时间戳列表

### 5. 视频剪切
- 使用 FFmpeg 按时间戳剪切视频
- 输出独立的视频片段文件
- 保持原始视频质量

### 6. 导出文件格式

#### 输出文件结构
```
output/
├── clips/              # 剪切后的视频片段
│   ├── clip_001.mp4
│   ├── clip_002.mp4
│   └── ...
├── subtitles/          # 字幕文件
│   ├── full.srt       # 完整字幕
│   └── highlights.srt # 精彩片段字幕
├── timeline/          # 时间线文件
│   └── project.xml    # Premiere XML
├── assets/            # 素材清单
│   └── manifest.json  # 素材信息
└── project/          # PR 项目文件
    └── prproj/       # (如需要)
```

#### 支持的导出格式
- **独立视频片段**：MP4 (H.264)
- **SRT 字幕文件**：标准 SRT 格式
- **XML 时间线**：Adobe Premiere XML 格式
- **EDL 时间线**：CMX 3600 EDL 格式
- **素材清单**：JSON 格式记录所有素材路径和时长

## 技术架构

### 依赖工具
- **FFmpeg**：视频处理
- **faster-whisper**：语音识别
- **Python**：核心处理逻辑

### 配置管理
- AI API 配置通过环境变量或配置文件
- 支持多个 AI 服务商配置

## 用户交互流程

1. 用户 @ 出视频文件路径
2. 技能解析视频文件
3. 使用 faster-whisper 识别语音，生成初始 SRT
4. 调用 AI API 生成解说文案
5. 识别精彩片段时间戳
6. 使用 FFmpeg 剪切视频片段
7. 生成导出文件（视频片段 + SRT + XML/EDL）
8. 显示导出结果和素材清单

## 配置项

### 必需配置
- `FFMPEG_PATH`：FFmpeg 可执行文件路径
- `WHISPER_MODEL`：使用的 Whisper 模型大小

### AI API 配置（至少配置一项）
- `OPENAI_API_KEY` + `OPENAI_BASE_URL`
- `ANTHROPIC_API_KEY`
- 其他兼容 OpenAI 格式的 API

### 可选配置
- `DEFAULT_WHISPER_MODEL`：默认 whisper 模型 (default: base)
- `MIN_CLIP_DURATION`：片段最小时长 (default: 10s)
- `MAX_CLIP_DURATION`：片段最大时长 (default: 120s)
- `OUTPUT_DIR`：默认输出目录

## 错误处理

- 视频文件不存在：提示用户检查文件路径
- FFmpeg 不可用：提示安装 FFmpeg
- Whisper 模型下载失败：提供手动下载指引
- AI API 调用失败：提示检查 API 配置
- 磁盘空间不足：提示清理空间

## 验收标准

1. 用户提供视频路径后，技能自动完成全流程
2. 输出的视频片段可被 Premiere 正常导入
3. SRT 字幕时间戳与视频同步
4. XML 时间线包含所有片段和字幕信息
5. 支持配置多种 AI 服务商
