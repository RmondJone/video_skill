---
name: video-recognition
description: 视频画面解说生成器 - 用户粘贴视频路径即可自动处理，进行场景检测、关键帧提取、画面分析，生成风格化解说文案（SRT/TXT格式）。当用户提供无声视频、需要画面解说、提到风格化解说时使用此技能。
---

# 视频画面解说生成器技能

用户提供本地视频文件路径，自动完成场景检测、关键帧提取、画面分析，生成风格化解说文案。

**【重要】参考资料存放在 references 文件夹中：**

- `.claude/skills/video-recognition/references/scenes_example.json` - 场景检测输出示例
- `.claude/skills/video-recognition/references/narrator_example.txt` - 解说文案输出示例

---

## 触发条件

用户满足以下任一条件时使用此技能：
- 用户粘贴了本地视频文件路径并要求画面解说
- 用户提到"无声视频解说"、"画面分析"、"纯视觉解说"
- 用户提到需要风格化解说（风趣幽默、技术硬核、理性科普、解压治愈、温馨感人）

**注意：无需用户使用 @ 触发，只需用户提供视频文件路径即可自动识别并处理。**

## 输入要求

从用户消息中提取视频文件路径，确保：
1. 视频文件存在且为支持的格式（mp4, mov, avi, mkv, webm）
2. 提取输出目录（用户指定或默认）

## 处理流程

### 步骤 1: 验证环境依赖（自动执行）

**自动检查以下工具是否可用，无需用户同意：**
1. **FFmpeg** - 视频处理和关键帧提取
2. **PySceneDetect** - 场景检测
3. **Python** - 运行环境

如果缺少依赖，自动提示用户安装并执行安装命令：
```bash
# 检查并安装 ffmpeg (macOS)
which ffmpeg || brew install ffmpeg

# 检查并安装 PySceneDetect
python3 -c "import scenedetect" 2>/dev/null || pip install scenedetect
```

### 步骤 2: 选择解说风格

**必须询问用户选择解说风格：**

```
请选择解说风格（直接回复数字或风格名）：
1. 风趣幽默（默认）- 轻松调侃的语气，画外音风格
2. 技术硬核 - 专业术语、深度分析
3. 理性科普 - 客观陈述、逻辑清晰
4. 解压治愈 - 柔和舒缓、放松心情
5. 温馨感人 - 情感充沛、温暖人心
```

**风格说明：**

| 风格 | 说明 | 适用场景 |
|------|------|----------|
| 风趣幽默（默认）| 轻松调侃的语气，画外音风格 | 日常vlog、娱乐内容 |
| 技术硬核 | 专业术语、深度分析 | 科技、编程、工业 |
| 理性科普 | 客观陈述、逻辑清晰 | 知识讲解、教育 |
| 解压治愈 | 柔和舒缓、放松心情 | ASMR、冥想，自然 |
| 温馨感人 | 情感充沛、温暖人心 | 亲情、友情、励志 |

### 步骤 3: 场景检测

```bash
python3 .claude/skills/video-recognition/scripts/detect_scenes.py input.mp4 output/scenes.json --threshold 30
```

### 步骤 4: 关键帧提取

```bash
python3 .claude/skills/video-recognition/scripts/extract_keyframes.py input.mp4 output/scenes.json output/keyframes/ --max-frames 5
```

### 步骤 5: 画面描述生成

**【核心】使用 Claude 自身能力分析关键帧：**
1. 读取关键帧图片
2. 分析每个场景的画面内容
3. 生成场景描述文本

### 步骤 6: 叙事串联 + 风格化

**【核心】使用 Claude 自身能力生成连贯解说文案：**
1. 串联所有场景描述
2. 应用用户选择的风格
3. 生成最终解说文案

### 步骤 7: 输出解说文案

```bash
python3 .claude/skills/video-recognition/scripts/generate_narrator.py output/descriptions.json output/narrator --style 幽默 --format both
```

## 输出文件结构

```
output/<视频名>/
├── scenes.json          # 场景检测结果
├── keyframes/           # 关键帧图片
│   ├── scene_001.jpg
│   ├── scene_002.jpg
├── descriptions.json    # 画面描述
├── narrator.srt         # 解说文案（SRT格式）
└── narrator.txt         # 解说文案（TXT格式）
```

## 使用示例

### 示例 1: 基本使用
```
用户: 处理一下这个无声视频 /Users/guohanlin/videos/demo.mp4

技能响应:
1. 正在验证环境...
2. 请选择解说风格...
3. 正在检测场景...
4. 正在提取关键帧...
5. 正在分析画面...
6. 正在生成解说文案...

完成! 解说文案已保存到: /Users/guohanlin/videos/demo_output/
```

### 示例 2: 指定风格
```
用户: 处理 /Users/guohanlin/videos/demo.mp4，风格选技术硬核
```

## 依赖说明

| 工具 | 说明 | 安装方式 |
|------|------|----------|
| ffmpeg | 视频处理、关键帧提取 | `brew install ffmpeg` |
| PySceneDetect | 场景检测 | `pip install scenedetect` |

**注意：不需要配置任何外部 AI API Key！**

解说文案生成直接使用 Claude 自身的能力。

## 脚本工具

**所有脚本位于 `.claude/skills/video-recognition/scripts/` 目录**

1. **detect_scenes.py** - 场景检测脚本
2. **extract_keyframes.py** - 关键帧提取脚本
3. **describe_scenes.py** - 画面描述生成脚本
4. **generate_narrator.py** - 叙事串联 + 风格化脚本
5. **process_video.py** - 主流程编排脚本

**脚本完整路径：**
```bash
# 脚本基础路径
SCRIPT_DIR=".claude/skills/video-recognition/scripts"

# 场景检测
python3 ${SCRIPT_DIR}/detect_scenes.py input.mp4 output/scenes.json

# 关键帧提取
python3 ${SCRIPT_DIR}/extract_keyframes.py input.mp4 output/scenes.json output/keyframes/

# 生成描述模板
python3 ${SCRIPT_DIR}/describe_scenes.py output/keyframes/keyframes.json output/descriptions.json

# 生成解说文案
python3 ${SCRIPT_DIR}/generate_narrator.py output/descriptions.json output/narrator --style 风趣幽默 --format both

# 一键执行完整流程
python3 ${SCRIPT_DIR}/process_video.py input.mp4 output/ --style 风趣幽默
```
