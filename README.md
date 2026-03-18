# Video Narrator - 视频解说生成器

[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE) [![Commercial](https://img.shields.io/badge/Commercial%20License-Required-orange.svg)](#-license) [![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org) [![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-orange.svg)](https://ffmpeg.org) [![Whisper](https://img.shields.io/badge/Whisper-faster--whisper-red)](https://github.com/SYSTRAN/faster-whisper)

用户粘贴本地视频文件路径，自动完成语音识别、AI 解说文案生成、视频片段剪切，导出 Adobe Premiere 可编辑的文件。

## ✨ 功能特点

- **🤖 AI 智能分析** - 利用 Claude 直接生成解说文案，无需 API Key
- **🎙️ 语音识别** - 使用 faster-whisper 进行本地语音转文字
- **🎵 智能识别** - 自动区分旁白视频和纯音乐视频
- **✂️ 视频剪切** - 基于 AI 分析精准剪切精彩片段
- **📺 专业导出** - 生成 Premiere XML、EDL 时间线、SRT 字幕

## ❌ Without Video Narrator

手动处理视频解说需要：

- ❌ 手动听写语音，耗时耗力
- ❌ 手动标记时间点，容易出错
- ❌ 逐个剪切视频片段，效率低下
- ❌ 手动调整导出参数，流程繁琐

## ✅ With Video Narrator

自动化处理流程，一键完成：

- ✅ 语音自动识别，无需手动听写
- ✅ AI 智能分析精彩片段
- ✅ 自动剪切视频片段
- ✅ 直接导出 Premiere 可编辑文件

## 🚀 快速开始

### 1. 安装视频解说生成器技能

**方式一：使用 npx 一键安装（推荐）**

```bash
# 一键安装技能
npx skills add RmondJone/video-skill --skill video-narrator --global
```

**方式二：手动安装**

```bash
# 创建本地技能目录
mkdir -p ~/.claude/skills

# 复制技能文件夹
cp -r .claude/skills/video-narrator ~/.claude/skills/

# 验证安装
ls ~/.claude/skills/video-narrator
```

**方式三：通过 find-skills 这个技能安装**

```bash
/find-skills 帮我安装 video-narrator这个技能
```

> [!TIP]
> 安装后，Claude Code 会自动识别 `video-narrator` 技能。当你有视频文件需要处理时，AI 会自动调用此技能。

### 2. 安装依赖

```bash
# 安装 ffmpeg (macOS)
brew install ffmpeg

# 安装 faster-whisper
pip install faster-whisper
```

### 使用方式

**方式一：直接粘贴视频文件路径**
```
处理一下这个视频 /path/to/video.mp4
```

**方式二：指定输出目录**
```
处理 /path/to/video.mp4，输出到 /path/to/output/
```

> [!TIP]
> **零配置**：AI 文案生成直接利用 Claude 自身能力，无需任何 API Key！

## 📋 处理流程

```
视频输入 → 语音识别 → 类型检测 → 精彩片段识别 → AI文案生成 → 视频剪切 → 导出文件
```

### 1. 语音识别 (ASR)
使用 faster-whisper 识别视频中的语音，输出完整文字稿和 SRT 字幕文件。

### 2. 自动检测视频类型

| 检测条件 | 判定结果 |
|---------|---------|
| 识别文字 < 50 字 | 纯音乐视频 |
| 识别片段 < 10 个 | 纯音乐视频 |
| 平均每片段 < 5 字 | 纯音乐视频 |

### 3. 精彩片段识别

| 视频类型 | 处理方式 |
|---------|---------|
| 有旁白/对话 | 基于语音内容识别精彩片段 |
| 纯音乐/无旁白 | 基于音频能量分析识别高潮部分 |

### 4. AI 解说文案生成
直接使用当前 Claude 会话生成专业解说文案，保持与时间戳对应关系。

### 5. 视频导出

```
output/
├── clips/              # 剪切后的视频片段
│   ├── clip_001.mp4
│   ├── clip_002.mp4
├── subtitles/          # 字幕文件
│   └── full.srt
├── timeline/           # 时间线文件
│   ├── project.xml     # Premiere XML
│   └── project.edl     # EDL 时间线
└── manifest.json      # 素材清单
```

## 🛠️ 脚本工具

技能提供以下独立脚本，可单独使用：

| 脚本 | 用途 | 命令示例 |
|-----|------|---------|
| `transcribe.py` | 语音识别 | `python scripts/transcribe.py input.mp4 output.srt --model base` |
| `analyze_energy.py` | 音频能量分析 | `python scripts/analyze_energy.py input.mp4 energy.json` |
| `cut_video.py` | 视频剪切 | `python scripts/cut_video.py input.mp4 00:01:30 00:02:45 output.mp4` |
| `generate_xml.py` | Premiere XML | `python scripts/generate_xml.py clips/ timeline/project.xml` |
| `generate_edl.py` | EDL 时间线 | `python scripts/generate_edl.py clips/ timeline/project.edl` |

## ⚙️ 配置说明

通过环境变量配置（可选）：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `WHISPER_MODEL` | Whisper 模型大小 | base |
| `MIN_CLIP_DURATION` | 片段最小时长(秒) | 10 |
| `MAX_CLIP_DURATION` | 片段最大时长(秒) | 120 |
| `ENERGY_THRESHOLD` | 音频能量阈值(百分位) | 75 |

## 💡 使用示例

### 示例 1: 处理有旁白的视频

```
用户: @处理一下这个视频 /Users/guohanlin/videos/demo.mp4

响应:
1. ✓ 正在验证视频文件...
2. ✓ 正在进行语音识别...
3. ✓ 检测到视频包含语音内容
4. ✓ 正在生成解说文案...
5. ✓ 正在识别精彩片段...
6. ✓ 正在剪切视频...
7. ✓ 正在生成导出文件...

完成! 导出文件已保存到 outputs/
```

### 示例 2: 处理纯音乐视频

```
用户: @处理一下这个音乐视频 /Users/guohanlin/videos/music.mp4

响应:
1. ✓ 正在验证视频文件...
2. ✓ 正在进行语音识别...
3. ⚠️ 检测为纯音乐视频（语音识别结果 < 50 字）
4. ✓ 正在使用音频能量分析识别精彩片段...
5. ✓ 正在生成音乐解说文案...
6. ✓ 正在剪切视频...
7. ✓ 正在生成导出文件...
```

## ⚠️ 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| 视频文件不存在 | 提示用户检查文件路径 |
| FFmpeg 不可用 | 提示安装 FFmpeg |
| Whisper 模型失败 | 提供手动下载指引 |
| 音频分析失败 | 回退到默认剪切策略 |
| 磁盘空间不足 | 提示清理空间 |
| 视频格式不支持 | 提示转换格式 |

## 📌 注意事项

1. 大视频文件处理时间较长，请耐心等待
2. Whisper 模型下载一次后会缓存，无需重复下载
3. 建议确保磁盘空间充足
4. 视频片段命名按时间顺序排列

## 📄 License

### 双协议模式

本项目采用 **双协议模式**：

| 使用场景 | 许可证 | 说明 |
|---------|--------|------|
| 个人 / 非商业用途 | MIT | 免费使用 |
| 商业使用 | 商业许可证 | 需要付费授权 |

> [!IMPORTANT]
> **个人用途免费，商业用途需授权**。将本项目用于商业产品前，请联系作者获取商业授权。

### 协议详情

- **个人/非商业用途**：可免费使用本项目，包括个人学习、研究、创作等非商业目的的使用
- **商业使用**：包括但不限于将本项目集成到商业产品中、商业项目中、用于收费服务等

### 商业授权

如需商业授权，请联系作者获取报价和授权条款。

---

*本协议符合开源精神，在保障作者权益的同时，让更多人能体验和使用本项目。*
