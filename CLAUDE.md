# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 Claude Code 技能项目，用于**视频解说生成**。用户通过 @ 方式指定本地视频文件，技能自动完成语音识别、AI 解说文案生成、视频片段剪切，导出 PR (Adobe Premiere) 可编辑的文件。

## 项目结构

```
video_skill/
├── skills/
│   └── video-narrator/           # 视频解说生成器技能
│       ├── SKILL.md              # 技能定义文件
│       └── scripts/              # Python 处理脚本
│           ├── transcribe.py     # 语音识别 (faster-whisper)
│           ├── cut_video.py      # 视频剪切 (FFmpeg)
│           ├── generate_xml.py   # Premiere XML 生成
│           ├── generate_edl.py   # EDL 时间线生成
│           └── process_video.py  # 主处理流程
└── docs/
    └── superpowers/
        └── specs/                # 设计文档
            └── 2026-03-16-video-narrator-design.md
```

## 常用命令

### 安装依赖

```bash
# 安装 ffmpeg (macOS)
brew install ffmpeg

# 安装 faster-whisper
pip install faster-whisper
```

### 使用脚本

```bash
# 语音识别
python skills/video-narrator/scripts/transcribe.py input.mp4 output.srt

# 视频剪切
python skills/video-narrator/scripts/cut_video.py input.mp4 00:01:30 00:02:45 output.mp4

# 生成 XML 时间线
python skills/video-narrator/scripts/generate_xml.py clips/ timeline/project.xml
```

## 技术栈

- **Python 3**: 核心处理逻辑
- **FFmpeg**: 视频处理和剪切
- **faster-whisper**: 本地语音识别 (支持 tiny/base/small/medium/large 模型)
- **AI API**: 支持 OpenAI API、Anthropic API 及兼容 OpenAI 格式的 API

## 配置说明

通过环境变量配置：

| 变量名 | 说明 |
|--------|------|
| `OPENAI_API_KEY` | OpenAI API Key |
| `OPENAI_BASE_URL` | OpenAI API 基础 URL |
| `ANTHROPIC_API_KEY` | Anthropic API Key |
| `WHISPER_MODEL` | Whisper 模型大小 (默认 base) |

## 技能触发条件

当用户满足以下任一条件时使用 `video-narrator` 技能：
- 用户 @ 出视频文件并要求生成解说
- 用户提到"视频解说"、"语音转文字"、"字幕生成"
- 用户要求"视频切片"、"导出 PR 文件"
- 用户需要将视频导出为 Premiere/Final Cut 可编辑的格式

## 输出文件结构

```
output/
├── clips/              # 剪切后的视频片段
├── subtitles/          # SRT 字幕文件
├── timeline/           # Premiere XML/EDL 时间线
└── manifest.json       # 素材清单
```
