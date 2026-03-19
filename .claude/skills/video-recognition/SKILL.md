---
name: video-recognition
description: 视频画面解说生成器 - 用户粘贴视频路径即可自动处理，进行场景检测、关键帧提取、画面分析，生成风格化解说文案（SRT/TXT格式）。当用户提供无声视频、需要画面解说、提到风格化解说时使用此技能。
---

# 视频画面解说生成器技能

用户提供本地视频文件路径，自动完成场景检测、关键帧提取、画面分析，生成风格化解说文案。

**【核心约束】**
- **时间轴严格对齐**：字幕结束时间 = 视频总时长
- **每2秒一句紧凑字幕**：时间紧凑，内容分配均匀
- **场景分析JSON包含详细描述**：供生成多行字幕使用

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

### 步骤 3: 获取视频信息

**【自动执行】** 使用 ffprobe 获取视频实际总时长：
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 input.mp4
```

### 步骤 4: 场景检测

```bash
python3 .claude/skills/video-recognition/scripts/detect_scenes.py input.mp4 output/scenes.json --threshold 30
```

### 步骤 5: 关键帧提取

```bash
python3 .claude/skills/video-recognition/scripts/extract_keyframes.py input.mp4 output/scenes.json output/keyframes/ --max-frames 5
```

### 步骤 6: 画面描述生成

**【核心】使用 Claude 自身能力分析关键帧：**
1. 读取关键帧图片
2. 分析每个场景的画面内容
3. **生成详细的场景描述文本**，包含多个短句供生成字幕使用

**【重要】场景描述JSON格式要求：**
```json
{
  "video_path": "input.mp4",
  "video_duration": 871,
  "descriptions": [
    {
      "scene_index": 0,
      "time": "00:00:00",
      "description": "场景详细描述，包含多个短句。用逗号、句号等标点分割成独立的短句，便于生成2秒一句的紧凑字幕。"
    }
  ]
}
```

### 步骤 7: 叙事串联 + 风格化

**【核心改进】每2秒一句紧凑字幕：**

```bash
python3 .claude/skills/video-recognition/scripts/generate_narrator.py \
    output/descriptions.json output/narrator \
    --style 风趣幽默 --format both \
    --duration 871 --sentence-duration 2.0
```

**时间轴计算规则：**
- 视频总时长 = ffprobe 实际获取的时长
- 每句字幕时长 = 2秒（可配置）
- 字幕数量 = 总时长 / 每句时长
- 末个字幕结束时间 = 视频总时长

## 输出文件结构

```
output/<视频名>/
├── scenes.json          # 场景检测结果
├── keyframes/           # 关键帧图片
│   ├── scene_001.jpg
│   ├── scene_002.jpg
├── descriptions.json    # 画面描述（含详细描述）
├── narrator.srt         # 解说字幕（SRT格式，每2秒一句）
└── narrator.txt         # 解说文案（TXT格式）
```

## 字幕生成规则

**【核心】每2秒一句紧凑字幕：**

| 视频时长 | 字幕数量 | 每句时长 |
|----------|----------|----------|
| 5分钟 | ~150句 | 2秒 |
| 10分钟 | ~300句 | 2秒 |
| 15分钟 | ~450句 | 2秒 |

**描述文本分割规则：**
- 按中文标点（，。！？；）分割成独立短句
- 每个短句对应一个2秒的字幕条目
- 内容按场景时间比例均匀分配

## 使用示例

### 示例 1: 基本使用
```
用户: 处理一下这个无声视频 /Users/guohanlin/videos/demo.mp4

技能响应:
1. 正在验证环境...
2. 正在获取视频信息... 视频总时长: 14:31
3. 请选择解说风格...
4. 正在检测场景...
5. 正在提取关键帧...
6. 正在分析画面...
7. 正在生成解说文案（每2秒一句）...
8. 时间轴验证通过

完成! 解说文案已保存到:
- narrator.srt (436句紧凑字幕)
- narrator.txt
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
4. **generate_narrator.py** - 叙事串联 + 风格化脚本（每2秒一句）
5. **process_video.py** - 主流程编排脚本

**脚本完整路径：**
```bash
# 脚本基础路径
SCRIPT_DIR=".claude/skills/video-recognition/scripts"

# 一键执行完整流程（推荐）
python3 ${SCRIPT_DIR}/process_video.py input.mp4 output/ --style 风趣幽默

# 分步执行
# 步骤 1: 场景检测
python3 ${SCRIPT_DIR}/detect_scenes.py input.mp4 output/scenes.json

# 步骤 2: 关键帧提取
python3 ${SCRIPT_DIR}/extract_keyframes.py input.mp4 output/scenes.json output/keyframes/

# 步骤 3: 生成描述模板
python3 ${SCRIPT_DIR}/describe_scenes.py output/keyframes/keyframes.json output/descriptions.json

# 步骤 4: 生成解说文案（每2秒一句紧凑字幕）
python3 ${SCRIPT_DIR}/generate_narrator.py \
    output/descriptions.json output/narrator \
    --style 风趣幽默 --format both \
    --duration 871 --sentence-duration 2.0
```

## 故障排除

### 问题：字幕时间轴对不上
**原因**：descriptions.json 中没有 video_duration 字段
**解决**：确保 --duration 参数正确传递

### 问题：字幕数量太少
**原因**：场景描述分割的短句数量不够
**解决**：在 descriptions.json 的 description 字段中使用更多标点分割短句

### 问题：每句时长太长/太短
**解决**：使用 --sentence-duration 参数调整，默认2秒
