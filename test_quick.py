"""
Quick subtitle test - skips transcription, uses existing transcript
"""

import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

from config import settings
from modules.video_processor import VideoProcessor
from modules.subtitle_renderer import SubtitleRenderer
from modules.face_tracker import FaceTracker

# Use existing transcript
EXISTING_TRANSCRIPT = Path("outputs/job_20251120_001334/transcript_words.json")
EXISTING_AUDIO = Path("outputs/job_20251120_001334/generated_audio.mp3")
GAMEPLAY_VIDEO = Path("test_assets/example_gameplay.mp4")

def main():
    print("=" * 70)
    print("🎬 QUICK SUBTITLE TEST (No Transcription)")
    print("=" * 70)
    print()
    
    # Verify files
    if not EXISTING_TRANSCRIPT.exists():
        print(f"❌ ERROR: Transcript not found: {EXISTING_TRANSCRIPT}")
        return False
    
    if not EXISTING_AUDIO.exists():
        print(f"❌ ERROR: Audio not found: {EXISTING_AUDIO}")
        return False
        
    if not GAMEPLAY_VIDEO.exists():
        print(f"❌ ERROR: Video not found: {GAMEPLAY_VIDEO}")
        return False
    
    print(f"✅ Using existing transcript: {EXISTING_TRANSCRIPT}")
    print(f"✅ Audio: {EXISTING_AUDIO}")
    print(f"✅ Video: {GAMEPLAY_VIDEO}")
    print()
    
    # Create output folder
    job_id = f"quick_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    job_folder = settings.outputs_dir / job_id
    job_folder.mkdir(parents=True, exist_ok=True)
    
    # Copy audio
    audio_path = job_folder / "generated_audio.mp3"
    shutil.copy(EXISTING_AUDIO, audio_path)
    
    # Load transcript
    with open(EXISTING_TRANSCRIPT, 'r') as f:
        transcript_data = json.load(f)
    
    # Extract words array
    words = transcript_data.get('words', transcript_data)
    
    print(f"📝 Loaded {len(words)} words from transcript")
    print()
    
    # Get audio duration
    def get_duration(path):
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
               '-of', 'default=noprint_wrappers=1:nokey=1', str(path)]
        return float(subprocess.check_output(cmd).strip())
    
    audio_duration = get_duration(audio_path)
    print(f"⏱️  Audio duration: {audio_duration:.2f} seconds")
    print()
    
    # Track face
    print("-" * 70)
    print("STEP 1: Tracking subject...")
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
        sample_rate=5
    )
    
    print(f"✅ Subject at ({tracking_data['face_center_x']}, {tracking_data['face_center_y']})")
    print()
    
    # Create vertical clip
    print("-" * 70)
    print("STEP 2: Creating vertical clip...")
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
    
    print("✅ Vertical clip created")
    print()
    
    # Merge audio
    print("-" * 70)
    print("STEP 3: Merging audio...")
    print("-" * 70)
    
    merged_video_path = job_folder / "merged_video.mp4"
    video_processor.merge_audio_video(base_video_path, audio_path, merged_video_path)
    
    print("✅ Audio merged")
    print()
    
    # Render subtitles
    print("-" * 70)
    print("STEP 4: Rendering subtitles...")
    print("-" * 70)
    print(f"📝 Font size: 1100px (normal), 1300px (highlighted)")
    print()
    
    subtitle_renderer = SubtitleRenderer(job_folder)
    
    subtitle_overlay = subtitle_renderer.render_subtitles_for_clip(
        romanized_words=words,
        clip_duration=audio_duration,
        style_name="simple_caption"
    )
    
    print("✅ Subtitles rendered")
    print()
    
    # Composite
    print("-" * 70)
    print("STEP 5: Compositing final video...")
    print("-" * 70)
    
    final_output_path = job_folder / "final_video.mp4"
    video_processor.composite_subtitles(merged_video_path, subtitle_overlay, final_output_path)
    
    print("✅ Final video created")
    print()
    
    # Summary
    print("=" * 70)
    print("✅ QUICK TEST COMPLETE!")
    print("=" * 70)
    print()
    print(f"📁 Output: {job_folder.absolute()}")
    print(f"🎥 Video: {final_output_path.absolute()}")
    
    if final_output_path.exists():
        file_size = final_output_path.stat().st_size / (1024 * 1024)
        print(f"📊 Size: {file_size:.2f} MB")
    
    print()
    print("🎉 Check if subtitles are big enough now!")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
