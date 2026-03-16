# Video Narrator - 视频解说生成器

用户 @ 出本地视频文件路径，自动完成语音识别、AI 解说文案生成、视频片段剪切，导出 Adobe Premiere 可编辑的文件。

## 功能特点

- **语音识别**: 使用 faster-whisper 进行本地语音转文字
- **AI 解说文案**: 利用当前 Claude 会话生成解说文案（无需 API Key）
- **智能片段识别**:
  - 有旁白视频：基于语音内容识别精彩片段
  - 纯音乐视频：基于音频能量分析识别高潮部分
- **专业导出**: 生成 Premiere XML、EDL 时间线、SRT 字幕

## 触发条件

满足以下任一条件时自动触发此技能：
- 用户 @ 出视频文件并要求生成解说
- 用户提到"视频解说"、"语音转文字"、"字幕生成"
- 用户要求"视频切片"、"导出 PR 文件"
- 用户需要将视频导出为 Premiere/Final Cut 可编辑的格式

## 使用方法

### 方式一：直接 @ 视频文件

```
@处理一下这个视频 /path/to/video.mp4
```

### 方式二：指定输出目录

```
@处理 /path/to/video.mp4，输出到 /path/to/output/
```

## 环境依赖

首次使用前请确保安装以下依赖：

```bash
# 安装 ffmpeg (macOS)
brew install ffmpeg

# 安装 faster-whisper
pip install faster-whisper
```

## 处理流程

### 1. 语音识别 (ASR)
- 使用 faster-whisper 识别视频中的语音
- 输出完整文字稿和 SRT 字幕文件

### 2. 自动检测视频类型

**智能判断逻辑：**
- 识别文字 < 50 字 → 判定为**纯音乐视频**
- 识别片段 < 10 个 → 判定为**纯音乐视频**
- 平均每片段 < 5 字 → 判定为**纯音乐视频**

### 3. 精彩片段识别

| 视频类型 | 处理方式 |
|---------|---------|
| 有旁白/对话 | 基于语音内容识别精彩片段 |
| 纯音乐/无旁白 | 基于音频能量分析识别高潮部分 |

### 4. AI 解说文案生成

**重要：无需配置任何 API Key！**

直接使用当前 Claude 会话生成专业解说文案：
- 阅读语音转写内容
- 根据需求生成解说文案
- 保持与时间戳对应关系

### 5. 视频剪切

按时间戳剪切视频片段，输出 MP4 文件

### 6. 生成导出文件

```
output/
├── clips/              # 剪切后的视频片段
│   ├── clip_001.mp4
│   ├── clip_002.mp4
├── subtitles/          # 字幕文件
│   ├── full.srt        # 完整字幕
├── timeline/           # 时间线文件
│   ├── project.xml     # Premiere XML
│   └── project.edl    # EDL 时间线
└── manifest.json      # 素材清单
```

## 脚本工具

技能提供以下独立脚本：

### 语音识别
```bash
python scripts/transcribe.py input.mp4 output.srt --model base
```

### 音频能量分析
```bash
python scripts/analyze_energy.py input.mp4 energy.json
```

### 视频剪切
```bash
python scripts/cut_video.py input.mp4 00:01:30 00:02:45 output.mp4
```

### 生成 Premiere XML
```bash
python scripts/generate_xml.py clips/ timeline/project.xml
```

### 生成 EDL 时间线
```bash
python scripts/generate_edl.py clips/ timeline/project.edl
```

## 配置说明

通过环境变量配置（可选）：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| WHISPER_MODEL | Whisper 模型大小 | base |
| MIN_CLIP_DURATION | 片段最小时长(秒) | 10 |
| MAX_CLIP_DURATION | 片段最大时长(秒) | 120 |
| ENERGY_THRESHOLD | 音频能量阈值(百分位) | 75 |

## 使用示例

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

完成!
- 视频类型: 纯音乐（无旁白）
- 精彩片段: 基于音频能量分析识别
```

## 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| 视频文件不存在 | 提示用户检查文件路径 |
| FFmpeg 不可用 | 提示安装 FFmpeg |
| Whisper 模型失败 | 提供手动下载指引 |
| 音频分析失败 | 回退到默认剪切策略 |
| 磁盘空间不足 | 提示清理空间 |
| 视频格式不支持 | 提示转换格式 |

## 注意事项

1. 大视频文件处理时间较长，请耐心等待
2. Whisper 模型下载一次后会缓存，无需重复下载
3. 建议确保磁盘空间充足
4. 视频片段命名按时间顺序排列
5. **AI 文案生成零配置** - 直接利用 Claude 能力，无需 API Key
6. **纯音乐智能识别** - 自动检测并使用音频能量分析
