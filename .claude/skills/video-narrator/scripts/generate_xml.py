#!/usr/bin/env python3
"""
Premiere XML 时间线生成脚本
生成 Adobe Premiere 可以导入的 XML 时间线文件
"""
import argparse
import json
import sys
import os
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

def create_xml_project(clips, output_path):
    """创建 Premiere XML 项目"""
    # 根元素
    xmeml = Element('xmeml')
    xmeml.set('version', '5')

    # Project
    project = SubElement(xmeml, 'project')
    SubElement(project, 'name').text = 'Video Narrator Export'

    # Children - Sequence
    children = SubElement(project, 'children')
    sequence = SubElement(children, 'sequence')
    SubElement(sequence, 'name').text = 'Main Sequence'

    # Rate
    rate = SubElement(sequence, 'rate')
    SubElement(rate, 'timebase').text = '30'
    SubElement(rate, 'ntsc').text = 'TRUE'

    # Duration
    SubElement(sequence, 'duration').text = str(sum(c['duration'] for c in clips) * 30)

    # Media
    media = SubElement(sequence, 'media')
    video = SubElement(media, 'video')
    video_track = SubElement(video, 'track')

    # 添加每个片段
    time_position = 0
    for i, clip in enumerate(clips, 1):
        # 解析时间码
        start_tc = clip.get('start_timecode', clip['start_time'])
        end_tc = clip.get('end_timecode', clip['end_time'])

        # Video track item
        video_item = SubElement(video_track, 'clipitem')
        video_item.set('id', f"clipitem-{i}")

        SubElement(video_item, 'name').text = clip.get('name', f"Clip {i}")
        SubElement(video_item, 'enabled').text = 'TRUE'
        SubElement(video_item, 'duration').text = str(clip['duration'] * 30)

        # Start/End (timeline position)
        SubElement(video_item, 'start').text = str(time_position * 30)
        SubElement(video_item, 'end').text = str((time_position + clip['duration']) * 30)

        # In/Out (source position)
        SubElement(video_item, 'in').text = '0'
        SubElement(video_item, 'out').text = str(clip['duration'] * 30)

        # File reference
        file = SubElement(video_item, 'file')
        file.set('id', f"file-{i}")
        SubElement(file, 'name').text = os.path.basename(clip['source_file'])
        pathurl = SubElement(file, 'pathurl')
        pathurl.text = f"file://{os.path.abspath(clip['source_file'])}"

        # Timecode
        tc = SubElement(video_item, 'timecode')
        SubElement(tc, 'string').text = start_tc
        rate_tc = SubElement(tc, 'rate')
        SubElement(rate_tc, 'timebase').text = '30'

        time_position += clip['duration']

    # Audio track (optional)
    audio = SubElement(media, 'audio')
    audio_track = SubElement(audio, 'track')

    # Write XML
    xml_str = tostring(xmeml, encoding='unicode')
    xml_pretty = minidom.parseString(xml_str).toprettyxml(indent='  ')

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_pretty)

    print(f"Premiere XML 已生成: {output_path}")

def load_clips_from_manifest(manifest_path):
    """从素材清单加载片段信息"""
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    return manifest.get('clips', [])

def load_clips_from_dir(clips_dir):
    """从目录加载片段信息（需要手动指定时间）"""
    clips = []
    clip_files = sorted([f for f in os.listdir(clips_dir) if f.endswith(('.mp4', '.mov', '.avi'))])

    # 这里需要从 manifest 或用户提供的时间信息
    # 暂时返回空列表，需要用户指定
    print("警告: 请提供包含时间信息的 manifest.json 文件", file=sys.stderr)
    return []

def main():
    parser = argparse.ArgumentParser(description='生成 Premiere XML 时间线')
    parser.add_argument('clips_dir', help='视频片段目录')
    parser.add_argument('output', help='输出 XML 文件路径')
    parser.add_argument('--manifest', help='素材清单 JSON 文件路径')

    args = parser.parse_args()

    # 加载片段信息
    if args.manifest:
        clips = load_clips_from_manifest(args.manifest)
    else:
        # 尝试查找 manifest.json
        manifest_path = os.path.join(os.path.dirname(args.clips_dir), 'manifest.json')
        if os.path.exists(manifest_path):
            clips = load_clips_from_manifest(manifest_path)
        else:
            clips = load_clips_from_dir(args.clips_dir)
            if not clips:
                print("错误: 请提供 manifest.json 文件指定片段时间信息", file=sys.stderr)
                sys.exit(1)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)

    # 生成 XML
    create_xml_project(clips, args.output)

if __name__ == '__main__':
    main()
