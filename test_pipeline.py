"""
Dynamic test script for video generation pipeline.
Tests the complete flow including RunPod transcription.

Usage:
    python test_pipeline.py
    python test_pipeline.py --video path/to/video.mp4 --audio path/to/audio.mp3
    python test_pipeline.py --style glow_caption --language en
"""

import asyncio
import argparse
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

from config import settings
from utils.logging import setup_logger
from modules.transcriber import Transcriber
from modules.video_processor import VideoProcessor
from modules.subtitle_renderer import SubtitleRenderer
from modules.face_tracker import FaceTracker

# Setup logger
logger = setup_logger("TestPipeline", settings.outputs_dir / "test_pipeline.log")

# Default test assets (can be overridden via CLI)
DEFAULT_GAMEPLAY_VIDEO = "test_assets/example_gameplay.mp4"
DEFAULT_EXISTING_AUDIO = "outputs/job_20251120_001334/generated_audio.mp3"
DEFAULT_SUBTITLE_STYLE = "simple_caption"
DEFAULT_LANGUAGE = "en"

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Test video generation pipeline with existing assets',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--video', 
        type=str, 
        default=DEFAULT_GAMEPLAY_VIDEO,
        help=f'Path to gameplay video (default: {DEFAULT_GAMEPLAY_VIDEO})'
    )
    
    parser.add_argument(
        '--audio', 
        type=str, 
        default=DEFAULT_EXISTING_AUDIO,
        help=f'Path to existing audio file (default: {DEFAULT_EXISTING_AUDIO})'
    )
    
    parser.add_argument(
        '--style', 
        type=str, 
        default=DEFAULT_SUBTITLE_STYLE,
        choices=['simple_caption', 'glow_caption', 'karaoke_style'],
        help=f'Subtitle style (default: {DEFAULT_SUBTITLE_STYLE})'
    )
    
    parser.add_argument(
        '--language', 
        type=str, 
        default=DEFAULT_LANGUAGE,
        help=f'Transcription language code (default: {DEFAULT_LANGUAGE})'
    )
    
    parser.add_argument(
        '--sample-rate',
        type=int,
        default=5,
        help='YOLO tracking sample rate (frames, default: 5)'
    )
    
    return parser.parse_args()

async def test_full_pipeline(
    gameplay_video: str,
    audio_file: str,
    subtitle_style: str = "simple_caption",
    language: str = "en",
    sample_rate: int = 5
):
    """Test the entire video generation pipeline"""
    
    GAMEPLAY_VIDEO = Path(gameplay_video)
    EXISTING_AUDIO = Path(audio_file)
    
    print("=" * 70)
    print("🎬 TESTING VIDEO GENERATION PIPELINE")
    print("=" * 70)
    print()
    
    # Verify files exist
    if not GAMEPLAY_VIDEO.exists():
        print(f"❌ ERROR: Gameplay video not found: {GAMEPLAY_VIDEO}")
        return False
    
    if not EXISTING_AUDIO.exists():
        print(f"❌ ERROR: Audio file not found: {EXISTING_AUDIO}")
        return False
    
    print(f"✅ Gameplay video: {GAMEPLAY_VIDEO}")
    print(f"✅ Audio file: {EXISTING_AUDIO}")
    print()
    
    # Create job folder
    job_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    job_folder = settings.outputs_dir / job_id
    job_folder.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Output folder: {job_folder}")
    print(f"⚙️  Configuration:")
    print(f"   - Subtitle style: {subtitle_style}")
    print(f"   - Language: {language}")
    print(f"   - Sample rate: {sample_rate} frames")
    print()
    
    # Copy audio to job folder
    audio_path = job_folder / "generated_audio.mp3"
    shutil.copy(EXISTING_AUDIO, audio_path)
    print(f"✅ Copied audio to job folder")
    print()
    
    try:
        # Step 1: Transcribe Audio
        print("-" * 70)
        print("STEP 1: Transcribing audio with WhisperX...")
        print("-" * 70)
        
        whisper_key = settings.runpod_whisper_api_key or settings.runpod_api_key
        transcriber = Transcriber(
            api_key=whisper_key,
            endpoint=settings.runpod_whisper_endpoint_id,
            job_folder=job_folder
        )
        
        transcript_data = await transcriber.transcribe(audio_path, language=language)
        print(f"✅ Transcription complete!")
        
        if transcript_data.get('segments'):
            total_words = sum(len(seg.get('words', [])) for seg in transcript_data['segments'])
            print(f"   Total words: {total_words}")
        print()
        
        # Step 2: Get audio duration
        print("-" * 70)
        print("STEP 2: Getting audio duration...")
        print("-" * 70)
        
        def get_duration(path):
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                   '-of', 'default=noprint_wrappers=1:nokey=1', str(path)]
            return float(subprocess.check_output(cmd).strip())
        
        audio_duration = get_duration(audio_path)
        print(f"✅ Audio duration: {audio_duration:.2f} seconds")
        print()
        
        # Step 3: Track subject
        print("-" * 70)
        print("STEP 3: Tracking subject with YOLO...")
        print("-" * 70)
        
        face_tracker = FaceTracker(job_folder)
        
        hours = int(audio_duration // 3600)
        minutes = int((audio_duration % 3600) // 60)
        seconds = int(audio_duration % 60)
        end_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        tracking_data = face_tracker.track_faces_in_clip(
            video_path=GAMEPLAY_VIDEO,
            start_time="00:00:00",
            end_time=end_time,
            sample_rate=sample_rate
        )
        
        print(f"✅ Subject detected at: ({tracking_data['face_center_x']}, {tracking_data['face_center_y']})")
        print()
        
        # Step 4: Create vertical clip
        print("-" * 70)
        print("STEP 4: Creating vertical clip...")
        print("-" * 70)
        
        video_processor = VideoProcessor(job_folder)
        base_video_path = job_folder / "base_video.mp4"
        
        video_processor.create_vertical_clip(
            video_path=GAMEPLAY_VIDEO,
            start_time="00:00:00",
            duration=audio_duration,
            face_x=tracking_data['face_center_x'],
            face_y=tracking_data['face_center_y'],
            source_width=tracking_data['source_width'],
            source_height=tracking_data['source_height'],
            output_name="base_video.mp4"
        )
        
        print(f"✅ Vertical clip created")
        print()
        
        # Step 5: Merge audio and video
        print("-" * 70)
        print("STEP 5: Merging audio and video...")
        print("-" * 70)
        
        merged_video_path = job_folder / "merged_video.mp4"
        video_processor.merge_audio_video(base_video_path, audio_path, merged_video_path)
        
        print(f"✅ Audio and video merged")
        print()
        
        # Step 6: Render subtitles
        print("-" * 70)
        print("STEP 6: Rendering subtitles...")
        print("-" * 70)
        
        subtitle_renderer = SubtitleRenderer(job_folder)
        
        # Extract words
        words = []
        for seg in transcript_data.get('segments', []):
            if 'words' in seg:
                for w in seg['words']:
                    words.append({
                        'text': w.get('word', w.get('text', '')),
                        'start': w['start'],
                        'end': w['end']
                    })
        
        print(f"📝 Processing {len(words)} words for subtitles...")
        
        subtitle_overlay = subtitle_renderer.render_subtitles_for_clip(
            romanized_words=words,
            clip_duration=audio_duration,
            style_name=subtitle_style
        )
        
        print(f"✅ Subtitles rendered")
        print()
        
        # Step 7: Composite final video
        print("-" * 70)
        print("STEP 7: Compositing final video...")
        print("-" * 70)
        
        final_output_path = job_folder / "final_video.mp4"
        video_processor.composite_subtitles(merged_video_path, subtitle_overlay, final_output_path)
        
        print(f"✅ Final video created")
        print()
        
        # Summary
        print("=" * 70)
        print("✅ TEST COMPLETE!")
        print("=" * 70)
        print()
        print(f"📁 Output folder: {job_folder.absolute()}")
        print(f"🎥 Final video: {final_output_path.absolute()}")
        
        if final_output_path.exists():
            file_size = final_output_path.stat().st_size / (1024 * 1024)
            print(f"📊 File size: {file_size:.2f} MB")
        
        print()
        print("🎉 Ready for your review!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    args = parse_arguments()
    
    success = asyncio.run(test_full_pipeline(
        gameplay_video=args.video,
        audio_file=args.audio,
        subtitle_style=args.style,
        language=args.language,
        sample_rate=args.sample_rate
    ))
    
    exit(0 if success else 1)
