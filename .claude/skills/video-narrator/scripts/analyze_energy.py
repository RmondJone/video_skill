#!/usr/bin/env python3
"""
音频能量分析脚本 - 用于纯音乐视频的精彩片段识别
通过分析音频能量（响度）来识别视频中的高潮/精彩部分
"""
import argparse
import json
import os
import subprocess
import sys
import numpy as np
from datetime import datetime


def get_video_duration(video_path):
    """获取视频时长"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def analyze_audio_rms(video_path, window_sec=3):
    """
    使用 volumedetect 分析音频 RMS 能量
    """
    duration = get_video_duration(video_path)
    energies = []
    current_time = 0

    print(f"正在分析音频能量 (每{window_sec}秒一个采样点)...")

    while current_time < duration:
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(current_time),
            '-t', str(window_sec),
            '-i', video_path,
            '-af', 'volumedetect',
            '-f', 'null', '-'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # 解析 mean_volume 和 max_volume (注意是下划线)
        mean_vol = -40.0
        max_vol = -40.0

        for line in result.stderr.split('\n'):
            if 'mean_volume:' in line:
                try:
                    mean_vol = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                except:
                    mean_vol = -40.0
            if 'max_volume:' in line:
                try:
                    max_vol = float(line.split('max_volume:')[1].split('dB')[0].strip())
                except:
                    max_vol = -40.0

        # 转换能量值 (0-1范围)
        # mean_volume 通常在 -40dB 到 -10dB 之间
        # max_volume 通常在 -30dB 到 0dB 之间
        # 使用 max_volume 作为主要能量指标，因为它更能反映高潮部分
        energy = max(0, min(1, (max_vol + 40) / 40))

        energies.append({
            'time': current_time,
            'energy': energy,
            'mean_volume_db': mean_vol,
            'max_volume_db': max_vol
        })

        current_time += window_sec
        print(f"\r分析进度: {current_time:.1f}s / {duration:.1f}s (能量: {energy:.2f})", end='', flush=True)

    print()
    return energies


def find_highlight_segments(energies, threshold_percentile=75, min_duration=5, merge_gap=3):
    """从音频能量数据中识别高能量片段"""
    if not energies:
        return []

    energy_values = [e['energy'] for e in energies]
    threshold = np.percentile(energy_values, threshold_percentile)

    print(f"能量阈值: {threshold:.2f} (第 {threshold_percentile}% 百分位)")

    # 计算窗口大小
    window_size = energies[1]['time'] - energies[0]['time'] if len(energies) > 1 else 3

    # 找出高能量区域
    highlight_ranges = []
    in_highlight = False
    start_time = 0

    for i, e in enumerate(energies):
        if e['energy'] >= threshold and not in_highlight:
            in_highlight = True
            start_time = e['time']
        elif e['energy'] < threshold and in_highlight:
            in_highlight = False
            end_time = energies[i-1]['time'] + window_size
            duration = end_time - start_time
            if duration >= min_duration:
                highlight_ranges.append({
                    'start': start_time,
                    'end': end_time,
                    'duration': duration,
                    'avg_energy': np.mean([x['energy'] for x in energies if start_time <= x['time'] < end_time])
                })

    # 处理最后的高能量区域
    if in_highlight:
        end_time = energies[-1]['time'] + window_size
        duration = end_time - start_time
        if duration >= min_duration:
            highlight_ranges.append({
                'start': start_time,
                'end': end_time,
                'duration': duration,
                'avg_energy': np.mean([e['energy'] for e in energies if start_time <= e['time'] < end_time])
            })

    # 合并相邻片段
    if highlight_ranges:
        highlight_ranges = merge_adjacent_ranges(highlight_ranges, merge_gap)

    # 按能量排序
    highlight_ranges.sort(key=lambda x: x['avg_energy'], reverse=True)

    return highlight_ranges


def merge_adjacent_ranges(ranges, gap_threshold):
    """合并相邻的高能量区域"""
    if not ranges:
        return []

    ranges.sort(key=lambda x: x['start'])
    merged = [ranges[0]]

    for current in ranges[1:]:
        last = merged[-1]
        if current['start'] - last['end'] <= gap_threshold:
            new_start = last['start']
            new_end = max(last['end'], current['end'])
            new_duration = new_end - new_start
            total_energy = last['avg_energy'] * last['duration'] + current['avg_energy'] * current['duration']
            new_avg_energy = total_energy / new_duration if new_duration > 0 else 0

            merged[-1] = {
                'start': new_start,
                'end': new_end,
                'duration': new_duration,
                'avg_energy': new_avg_energy
            }
        else:
            merged.append(current)

    return merged


def format_timestamp(seconds):
    """将秒数格式化为 HH:MM:SS"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def save_results(energies, highlights, output_path):
    """保存分析结果"""
    result = {
        'analysis_time': datetime.now().isoformat(),
        'total_duration': energies[-1]['time'] if energies else 0,
        'energy_data': energies,
        'highlights': [
            {
                'id': f"clip_{i+1:03d}",
                'start_time': format_timestamp(h['start']),
                'end_time': format_timestamp(h['end']),
                'start_seconds': h['start'],
                'end_seconds': h['end'],
                'duration': round(h['duration'], 1),
                'energy_level': 'high' if h['avg_energy'] > 0.7 else 'medium'
            }
            for i, h in enumerate(highlights)
        ]
    }

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


def main():
    parser = argparse.ArgumentParser(description='音频能量分析 - 识别纯音乐视频的精彩片段')
    parser.add_argument('input', help='输入视频文件路径')
    parser.add_argument('output', help='输出 JSON 文件路径')
    parser.add_argument('--window', type=int, default=3, help='分析窗口大小(秒, 默认3)')
    parser.add_argument('--threshold', type=int, default=75, help='能量阈值百分位(默认75)')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"视频时长: {get_video_duration(args.input):.1f}秒")

    # 分析能量
    energies = analyze_audio_rms(args.input, args.window)

    if not energies:
        print("错误: 无法分析音频能量", file=sys.stderr)
        sys.exit(1)

    print(f"分析完成，共 {len(energies)} 个数据点")

    # 打印能量分布
    energy_vals = [e['energy'] for e in energies]
    max_vals = [e['max_volume_db'] for e in energies]
    print(f"能量范围: {min(energy_vals):.2f} - {max(energy_vals):.2f}, 平均: {np.mean(energy_vals):.2f}")
    print(f"最大音量范围: {min(max_vals):.1f}dB - {max(max_vals):.1f}dB")

    # 识别精彩片段
    print("正在识别精彩片段...")
    highlights = find_highlight_segments(
        energies,
        threshold_percentile=args.threshold,
        min_duration=5,
        merge_gap=3
    )

    print(f"识别到 {len(highlights)} 个精彩片段")

    # 保存结果
    result = save_results(energies, highlights, args.output)

    # 打印精彩片段
    print("\n精彩片段列表:")
    for i, h in enumerate(result['highlights'], 1):
        print(f"  {i}. {h['start_time']} - {h['end_time']} (时长: {h['duration']}秒, 能量等级: {h['energy_level']})")

    print(f"\n结果已保存到: {args.output}")


if __name__ == '__main__':
    main()
