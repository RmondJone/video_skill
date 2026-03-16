#!/usr/bin/env python3
"""
语音识别脚本 - 使用 faster-whisper 进行语音转文字
"""
import argparse
import sys
import os
from faster_whisper import WhisperModel

def generate_srt(segments, output_path):
    """生成 SRT 字幕文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments, 1):
            start = format_time(segment.start)
            end = format_time(segment.end)
            text = segment.text.strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

def format_time(seconds):
    """将秒数转换为 SRT 时间格式 HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def main():
    parser = argparse.ArgumentParser(description='语音识别 - 将视频语音转为 SRT 字幕')
    parser.add_argument('input', help='输入视频文件路径')
    parser.add_argument('output', help='输出 SRT 文件路径')
    parser.add_argument('--model', default='base', choices=['tiny', 'base', 'small', 'medium', 'large'],
                        help='Whisper 模型大小 (default: base)')
    parser.add_argument('--device', default='cpu', choices=['cpu', 'cuda'],
                        help='运行设备 (default: cpu)')
    parser.add_argument('--compute-type', default='int8', choices=['int8', 'int8_float16', 'float16'],
                        help='计算类型 (default: int8)')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"加载 Whisper {args.model} 模型...")
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    print(f"正在识别: {args.input}")
    segments, info = model.transcribe(args.input, beam_size=5)

    print(f"检测到的语言: {info.language} (概率: {info.language_probability:.2f})")
    print(f"正在生成字幕文件: {args.output}")

    # 将 segments 转换为列表以支持多次迭代
    segment_list = list(segments)
    generate_srt(segment_list, args.output)

    print(f"完成! 识别了 {len(segment_list)} 个片段")
    print(f"输出文件: {args.output}")

if __name__ == '__main__':
    main()
