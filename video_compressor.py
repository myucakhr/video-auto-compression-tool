#!/usr/bin/env python3
"""
動画自動圧縮ツール (Mac M3 Pro最適化版 + Cross-Platform Support)
Google NotebookLM用に200MB以下に自動圧縮
"""

import os
import sys
import time
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# 設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TARGET_SIZE_MB = 160
DEFAULT_AUDIO_BITRATE_KBPS = 128
DEFAULT_AUDIO_BITRATE_LONG_KBPS = 64
LONG_VIDEO_THRESHOLD_MIN = 60
SUPPORTED_FORMATS = ('.mp4', '.mov', '.mkv', '.avi', '.webm')

# 色付きログ出力用
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log(message, color=''):
    """タイムスタンプ付きログ出力"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{color}[{timestamp}] {message}{Colors.ENDC}")

def get_video_info(input_path):
    """ffprobeで動画情報を取得（長さ、解像度）"""
    try:
        # 動画の長さを取得
        result = subprocess.run([
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            input_path
        ], capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())

        # 解像度を取得
        result = subprocess.run([
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=s=x:p=0',
            input_path
        ], capture_output=True, text=True, check=True)

        width, height = map(int, result.stdout.strip().split('x'))

        return {
            'duration': duration,
            'width': width,
            'height': height
        }
    except subprocess.CalledProcessError as e:
        log(f"エラー: 動画情報の取得に失敗 - {e}", Colors.FAIL)
        return None
    except ValueError:
        log("エラー: 動画情報を解析できませんでした", Colors.FAIL)
        return None

def check_h264_videotoolbox():
    """h264_videotoolbox (Mac HW加速) が使えるかチェック"""
    try:
        result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True)
        return 'h264_videotoolbox' in result.stdout
    except:
        return False

class VideoCompressor:
    def __init__(self, target_size_mb=DEFAULT_TARGET_SIZE_MB, use_hw_accel=True):
        self.target_size_mb = target_size_mb
        self.use_hw_accel = use_hw_accel and check_h264_videotoolbox()
        self.codec = 'h264_videotoolbox' if self.use_hw_accel else 'libx264'
        log(f"使用コーデック: {self.codec}", Colors.OKBLUE)

    def calculate_target_bitrate(self, duration_sec, audio_bitrate_kbps):
        """目標ファイルサイズから映像ビットレートを計算"""
        total_bitrate_bps = (self.target_size_mb * 8 * 1024 * 1024) / duration_sec
        audio_bitrate_bps = audio_bitrate_kbps * 1024
        video_bitrate_bps = int(total_bitrate_bps - audio_bitrate_bps)
        video_bitrate_kbps = video_bitrate_bps // 1024
        
        MIN_VIDEO_BITRATE = 200
        adjusted_target_size_mb = self.target_size_mb

        if video_bitrate_kbps < MIN_VIDEO_BITRATE:
            # 最小ビットレートで再計算
            required_total_bitrate_bps = (MIN_VIDEO_BITRATE * 1024) + audio_bitrate_bps
            adjusted_target_size_mb = (required_total_bitrate_bps * duration_sec) / (8 * 1024 * 1024)
            video_bitrate_kbps = MIN_VIDEO_BITRATE

        return video_bitrate_kbps, adjusted_target_size_mb

    def compress_segment(self, input_path, output_path, start_time, duration, video_info, audio_bitrate_kbps):
        """動画（またはその一部）を圧縮"""
        video_bitrate_kbps, _ = self.calculate_target_bitrate(duration if duration else video_info['duration'], audio_bitrate_kbps)

        # 解像度調整
        scale_filter = None
        if video_info['duration'] / 60 >= LONG_VIDEO_THRESHOLD_MIN:
            if video_info['height'] > 720:
                scale_filter = "scale=-2:720"

        maxrate_kbps = int(video_bitrate_kbps * 1.1)
        bufsize_kbps = int(video_bitrate_kbps * 2)

        cmd = ['ffmpeg', '-i', input_path]
        if start_time is not None:
            cmd.extend(['-ss', str(start_time)])
        if duration is not None:
            cmd.extend(['-t', str(duration)])

        cmd.extend([
            '-c:v', self.codec,
            '-b:v', f'{video_bitrate_kbps}k',
            '-maxrate', f'{maxrate_kbps}k',
            '-bufsize', f'{bufsize_kbps}k',
        ])
        
        # libx264用のプリセット
        if self.codec == 'libx264':
             cmd.extend(['-preset', 'medium'])

        if scale_filter:
            cmd.extend(['-vf', scale_filter])

        cmd.extend([
            '-c:a', 'aac',
            '-b:a', f'{audio_bitrate_kbps}k',
            '-movflags', '+faststart',
            '-y',
            output_path
        ])

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            log(f"FFmpegエラー: {e.stderr}", Colors.FAIL)
            return False

    def compress(self, input_path, output_dir=None):
        """動画ファイルの圧縮実行（分割処理含む）"""
        if output_dir is None:
            output_dir = os.path.dirname(input_path)
            
        filename = os.path.basename(input_path)
        name_without_ext = os.path.splitext(filename)[0]
        
        video_info = get_video_info(input_path)
        if not video_info:
            return None

        duration = video_info['duration']
        duration_min = duration / 60
        audio_bitrate = DEFAULT_AUDIO_BITRATE_LONG_KBPS if duration_min >= LONG_VIDEO_THRESHOLD_MIN else DEFAULT_AUDIO_BITRATE_KBPS

        # ビットレート計算と分割判定
        video_bitrate_kbps, adjusted_size = self.calculate_target_bitrate(duration, audio_bitrate)
        
        result_paths = []
        
        if adjusted_size > 200: # 200MB超えなら分割
            num_segments = int(adjusted_size / self.target_size_mb) + 1
            segment_duration = duration / num_segments
            
            log(f"長尺のため {num_segments} 分割します", Colors.WARNING)
            
            for i in range(num_segments):
                seg_output = os.path.join(output_dir, f"{name_without_ext}_part{i+1}.mp4")
                if self.compress_segment(input_path, seg_output, i * segment_duration, segment_duration, video_info, audio_bitrate):
                    result_paths.append(seg_output)
        else:
            output_path = os.path.join(output_dir, f"{name_without_ext}_compressed.mp4")
            if self.compress_segment(input_path, output_path, None, None, video_info, audio_bitrate):
                result_paths.append(output_path)
                
        return result_paths
