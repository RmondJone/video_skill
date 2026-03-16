#!/usr/bin/env python3
"""
EDL 时间线生成脚本
生成 CMX 3600 格式的 EDL 文件，可被多种视频编辑软件导入
"""
import argparse
import json
import sys
import os

def frames_to_timecode(frames, fps=30):
    """将帧数转换为 EDL 时间码格式 HH:MM:SS:FF"""
    hours = frames // (fps * 3600)
    minutes = (frames % (fps * 3600)) // (fps * 60)
    seconds = (frames % (fps * 60)) // fps
    frames_remaining = frames % fps
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames_remaining:02d}"

def timecode_to_frames(tc, fps=30):
    """将时间码转换为帧数"""
    parts = tc.replace(';', ':').split(':')
    if len(parts) == 4:
        h, m, s, f = parts
        return int(h) * fps * 3600 + int(m) * fps * 60 + int(s) * fps + int(f)
    return 0

def parse_timestamp_to_frames(ts, fps=30):
    """解析时间戳字符串为帧数"""
    # 格式: HH:MM:SS 或 HH:MM:SS,mmm
    ts = ts.replace(',', '.')
    parts = ts.split(':')
    if len(parts) == 3:
        h, m, s = parts
        total_seconds = int(h) * 3600 + int(m) * 60 + float(s)
        return int(total_seconds * fps)
    elif len(parts) == 2:
        m, s = parts
        total_seconds = int(m) * 60 + float(s)
        return int(total_seconds * fps)
    return 0

def create_edl(clips, output_path, fps=30, reel_name="VIDEO"):
    """生成 EDL 文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        # 标题
        f.write("TITLE: Video Narrator Export\n")
        f.write(f"FCM: {'DROP FRAME' if fps == 29.97 else 'NON-DROP FRAME'}\n")
        f.write("\n")

        # 记录每个片段
        record_position = 0
        for i, clip in enumerate(clips, 1):
            # 源时间码
            source_in = parse_timestamp_to_frames(clip['start_time'], fps)
            source_out = parse_timestamp_to_frames(clip['end_time'], fps)

            # 目标时间码（record in/out）
            record_in = record_position
            record_out = record_position + clip['duration']

            # 事件号（补零到3位）
            event_num = f"{i:03d}"

            # 轨道类型（视频V 音频A）
            track_type = "V"

            # 转场（无转场 C = Cut）
            transition = "C"

            # 源信息
            source_tc_in = frames_to_timecode(source_in, fps)
            source_tc_out = frames_to_timecode(source_out, fps)

            # 目标信息
            record_tc_in = frames_to_timecode(record_in, fps)
            record_tc_out = frames_to_timecode(record_out, fps)

            # Reel 名称（最多8字符）
            reel = reel_name[:8].ljust(8)

            # 写入 EDL 行
            # 格式: EVENT REEL TRACK TRANS SOURCE_IN SOURCE_OUT RECORD_IN RECORD_OUT
            f.write(f"{event_num}  {reel}      {track_type}     {transition}       {source_tc_in} {source_tc_out} {record_tc_in} {record_tc_out}\n")

            record_position += clip['duration']

    print(f"EDL 文件已生成: {output_path}")

def load_clips_from_manifest(manifest_path):
    """从素材清单加载片段信息"""
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    return manifest.get('clips', [])

def main():
    parser = argparse.ArgumentParser(description='生成 EDL 时间线文件')
    parser.add_argument('manifest', help='素材清单 JSON 文件路径')
    parser.add_argument('output', help='输出 EDL 文件路径')
    parser.add_argument('--fps', type=int, default=30, help='帧率 (default: 30)')
    parser.add_argument('--reel', default='VIDEO', help='Reel 名称 (default: VIDEO)')

    args = parser.parse_args()

    if not os.path.exists(args.manifest):
        print(f"错误: manifest 文件不存在: {args.manifest}", file=sys.stderr)
        sys.exit(1)

    # 加载片段信息
    clips = load_clips_from_manifest(args.manifest)

    if not clips:
        print("警告: manifest 中没有片段信息", file=sys.stderr)
        sys.exit(1)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)

    # 生成 EDL
    create_edl(clips, args.output, args.fps, args.reel)

if __name__ == '__main__':
    main()
