#!/usr/bin/env python3
"""
Premiere XML 时间线生成脚本
生成 Adobe Premiere 可以导入的 XML 时间线文件

正确的 Premiere XML 格式参考:
- 根元素直接是 <sequence>，无 <project> 包装
- 需要完整的 <format> 和 <samplecharacteristics>
- 音频使用双轨道 stereo 结构
- 路径使用 / 格式
"""
import argparse
import json
import sys
import os
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


def create_xml_project(clips, output_path, fps=30, manifest_dir=''):
    """创建 Premiere XML 项目（正确格式）"""
    # 根元素 - 直接是 sequence，无 project 包装
    xmeml = Element('xmeml')
    xmeml.set('version', '5')

    # Sequence - 添加 explodedTracks 属性
    sequence = SubElement(xmeml, 'sequence')
    sequence.set('explodedTracks', 'true')
    SubElement(sequence, 'name').text = 'Video Narrator Export'

    # 计算总时长（帧）
    total_duration_frames = sum(c['duration'] * fps for c in clips)
    SubElement(sequence, 'duration').text = str(total_duration_frames)

    # Rate
    rate = SubElement(sequence, 'rate')
    SubElement(rate, 'timebase').text = str(fps)
    SubElement(rate, 'ntsc').text = 'FALSE'

    # Media
    media = SubElement(sequence, 'media')

    # Video 部分
    video = SubElement(media, 'video')
    video_format = SubElement(video, 'format')
    video_samples = SubElement(video_format, 'samplecharacteristics')
    SubElement(video_samples, 'width').text = '1920'
    SubElement(video_samples, 'height').text = '1080'
    SubElement(video_samples, 'pixelaspectratio').text = 'square'
    video_rate = SubElement(video_samples, 'rate')
    SubElement(video_rate, 'timebase').text = str(fps)
    SubElement(video_rate, 'ntsc').text = 'FALSE'

    video_track = SubElement(video, 'track')

    # 添加每个视频片段
    time_position = 0
    for i, clip in enumerate(clips, 1):
        duration_frames = clip['duration'] * fps

        # Video clipitem
        video_item = SubElement(video_track, 'clipitem')
        video_item.set('id', f"clipitem-{i}")

        clip_name = clip.get('output_file', clip.get('name', f"Clip {i}"))

        # 解析 clip 路径：如果是相对路径，基于 manifest.json 所在目录解析
        if not os.path.isabs(clip_name):
            if manifest_dir:
                clip_abs_path = os.path.join(manifest_dir, clip_name)
            else:
                clip_abs_path = os.path.abspath(clip_name)
        else:
            clip_abs_path = clip_name

        SubElement(video_item, 'name').text = os.path.basename(clip_name).replace('.mp4', '')
        SubElement(video_item, 'enabled').text = 'TRUE'
        SubElement(video_item, 'start').text = str(time_position)
        SubElement(video_item, 'end').text = str(time_position + duration_frames)
        SubElement(video_item, 'in').text = '0'
        SubElement(video_item, 'out').text = str(duration_frames)

        # File reference
        file = SubElement(video_item, 'file')
        file.set('id', f"file-{i}")
        file_name = os.path.basename(clip_name)
        SubElement(file, 'name').text = file_name
        SubElement(file, 'pathurl').text = clip_abs_path

        # File timecode
        file_tc = SubElement(file, 'timecode')
        SubElement(file_tc, 'string').text = '00:00:00:00'
        SubElement(file_tc, 'displayformat').text = 'NDF'
        file_tc_rate = SubElement(file_tc, 'rate')
        SubElement(file_tc_rate, 'timebase').text = str(fps)
        SubElement(file_tc_rate, 'ntsc').text = 'FALSE'

        # File rate
        file_rate = SubElement(file, 'rate')
        SubElement(file_rate, 'timebase').text = str(fps)
        SubElement(file_rate, 'ntsc').text = 'FALSE'

        SubElement(file, 'duration').text = ''

        # File media (video + audio)
        file_media = SubElement(file, 'media')
        file_video = SubElement(file_media, 'video')
        file_video_samples = SubElement(file_video, 'samplecharacteristics')
        file_video_rate = SubElement(file_video_samples, 'rate')
        SubElement(file_video_rate, 'timebase').text = str(fps)
        SubElement(file_video_rate, 'ntsc').text = 'FALSE'
        SubElement(file_video_samples, 'width').text = '1920'
        SubElement(file_video_samples, 'height').text = '1080'
        SubElement(file_video_samples, 'pixelaspectratio').text = 'square'

        file_audio = SubElement(file_media, 'audio')
        file_audio_samples = SubElement(file_audio, 'samplecharacteristics')
        SubElement(file_audio_samples, 'depth').text = '16'
        SubElement(file_audio_samples, 'samplerate').text = '44100'
        SubElement(file_audio, 'channelcount').text = '2'

        # Compositemode
        SubElement(video_item, 'compositemode').text = 'normal'

        # Link elements (video + 2 audio)
        link1 = SubElement(video_item, 'link')
        SubElement(link1, 'linkclipref').text = f"clipitem-{i}"
        SubElement(link1, 'mediatype').text = 'video'
        SubElement(link1, 'trackindex').text = '1'
        SubElement(link1, 'clipindex').text = str(i)

        link2 = SubElement(video_item, 'link')
        SubElement(link2, 'linkclipref').text = f"clipitem-{i * 2 + 1}"
        SubElement(link2, 'mediatype').text = 'audio'
        SubElement(link2, 'trackindex').text = '1'
        SubElement(link2, 'clipindex').text = str(i)

        link3 = SubElement(video_item, 'link')
        SubElement(link3, 'linkclipref').text = f"clipitem-{i * 2 + 2}"
        SubElement(link3, 'mediatype').text = 'audio'
        SubElement(link3, 'trackindex').text = '2'
        SubElement(link3, 'clipindex').text = str(i)

        time_position += duration_frames

    # Audio 部分
    audio = SubElement(media, 'audio')
    SubElement(audio, 'numOutputChannels').text = '2'

    audio_format = SubElement(audio, 'format')
    audio_samples = SubElement(audio_format, 'samplecharacteristics')
    SubElement(audio_samples, 'depth').text = '16'
    SubElement(audio_samples, 'samplerate').text = '44100'

    # Audio track 1 (stereo left)
    audio_track1 = SubElement(audio, 'track')
    audio_track1.set('totalExplodedTrackCount', '2')
    audio_track1.set('premiereTrackType', 'Stereo')
    audio_track1.set('currentExplodedTrackIndex', '0')
    SubElement(audio_track1, 'outputchannelindex').text = '1'

    # Audio track 2 (stereo right)
    audio_track2 = SubElement(audio, 'track')
    audio_track2.set('totalExplodedTrackCount', '2')
    audio_track2.set('premiereTrackType', 'Stereo')
    audio_track2.set('currentExplodedTrackIndex', '1')
    SubElement(audio_track2, 'outputchannelindex').text = '2'

    # 添加音频 clipitem
    time_position = 0
    for i, clip in enumerate(clips, 1):
        duration_frames = clip['duration'] * fps
        clip_name = clip.get('output_file', clip.get('name', f"Clip {i}"))
        clip_base_name = os.path.basename(clip_name).replace('.mp4', '')

        # Audio track 1 clipitem
        audio_item1 = SubElement(audio_track1, 'clipitem')
        audio_item1.set('id', f"clipitem-{i * 2 + 1}")
        audio_item1.set('premiereChannelType', 'stereo')
        SubElement(audio_item1, 'name').text = clip_base_name
        SubElement(audio_item1, 'enabled').text = 'TRUE'
        SubElement(audio_item1, 'start').text = str(time_position)
        SubElement(audio_item1, 'end').text = str(time_position + duration_frames)
        SubElement(audio_item1, 'in').text = '0'
        SubElement(audio_item1, 'out').text = str(duration_frames)
        audio_file1 = SubElement(audio_item1, 'file')
        audio_file1.set('id', f"file-{i}")
        audio_source1 = SubElement(audio_item1, 'sourcetrack')
        SubElement(audio_source1, 'mediatype').text = 'audio'
        SubElement(audio_source1, 'trackindex').text = '1'

        # Audio track 2 clipitem
        audio_item2 = SubElement(audio_track2, 'clipitem')
        audio_item2.set('id', f"clipitem-{i * 2 + 2}")
        audio_item2.set('premiereChannelType', 'stereo')
        SubElement(audio_item2, 'name').text = clip_base_name
        SubElement(audio_item2, 'enabled').text = 'TRUE'
        SubElement(audio_item2, 'start').text = str(time_position)
        SubElement(audio_item2, 'end').text = str(time_position + duration_frames)
        SubElement(audio_item2, 'in').text = '0'
        SubElement(audio_item2, 'out').text = str(duration_frames)
        audio_file2 = SubElement(audio_item2, 'file')
        audio_file2.set('id', f"file-{i}")
        audio_source2 = SubElement(audio_item2, 'sourcetrack')
        SubElement(audio_source2, 'mediatype').text = 'audio'
        SubElement(audio_source2, 'trackindex').text = '2'

        time_position += duration_frames

    # Write XML
    xml_str = tostring(xmeml, encoding='unicode')
    xml_pretty = minidom.parseString(xml_str).toprettyxml(indent='  ')

    # 修复 XML 声明
    xml_pretty = "<?xml version='1.0' encoding='utf-8'?>\n" + xml_pretty

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_pretty)

    print(f"Premiere XML 已生成: {output_path}")


def load_clips_from_manifest(manifest_path):
    """从素材清单加载片段信息"""
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    # 返回 (clips, manifest_dir)
    manifest_dir = os.path.dirname(os.path.abspath(manifest_path))
    return manifest.get('clips', []), manifest_dir


def load_clips_from_dir(clips_dir):
    """从目录加载片段信息（需要手动指定时间）"""
    clips = []
    clip_files = sorted([f for f in os.listdir(clips_dir) if f.endswith(('.mp4', '.mov', '.avi'))])

    print("警告: 请提供包含时间信息的 manifest.json 文件", file=sys.stderr)
    return []


def main():
    parser = argparse.ArgumentParser(description='生成 Premiere XML 时间线')
    parser.add_argument('clips_dir', help='视频片段目录')
    parser.add_argument('output', help='输出 XML 文件路径')
    parser.add_argument('--manifest', help='素材清单 JSON 文件路径')
    parser.add_argument('--fps', type=int, default=30, help='帧率 (默认 30)')

    args = parser.parse_args()

    # 加载片段信息
    manifest_dir = ''
    if args.manifest:
        clips, manifest_dir = load_clips_from_manifest(args.manifest)
    else:
        # 尝试查找 manifest.json
        manifest_path = os.path.join(os.path.dirname(args.clips_dir), 'manifest.json')
        if os.path.exists(manifest_path):
            clips, manifest_dir = load_clips_from_manifest(manifest_path)
        else:
            clips = load_clips_from_dir(args.clips_dir)
            manifest_dir = ''
            if not clips:
                print("错误: 请提供 manifest.json 文件指定片段时间信息", file=sys.stderr)
                sys.exit(1)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)

    # 生成 XML
    create_xml_project(clips, args.output, args.fps, manifest_dir)


if __name__ == '__main__':
    main()
