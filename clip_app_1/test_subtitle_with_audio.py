import json
import subprocess
from pathlib import Path
from gtts import gTTS
from modules.subtitle_renderer import SubtitleRenderer
from modules.transliterator import UniversalTransliterator
from utils.helpers import setup_logger

def create_hindi_audio(text: str, output_path: Path):
    """Create Hindi audio using gTTS"""
    tts = gTTS(text=text, lang='hi', slow=False)
    tts.save(str(output_path))
    print(f"Created audio at {output_path}")

def create_video_from_audio(audio_path: Path, output_path: Path):
    """Create a video with black background matching audio duration"""
    # Get audio duration
    cmd = [
        'ffprobe', 
        '-v', 'error', 
        '-show_entries', 'format=duration', 
        '-of', 'default=noprint_wrappers=1:nokey=1', 
        str(audio_path)
    ]
    duration = float(subprocess.check_output(cmd).decode().strip())
    
    # Create video
    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'lavfi',
        '-i', f'color=c=black:s=1080x1920:r=30:d={duration}',
        '-i', str(audio_path),
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-pix_fmt', 'yuv420p',
        '-shortest',
        str(output_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Created video at {output_path}")
    return duration

def main():
    # Setup
    base_dir = Path(__file__).parent
    test_dir = base_dir / "test_output_audio"
    test_dir.mkdir(exist_ok=True)
    
    # Hindi text
    hindi_text = "नमस्ते दोस्तों, स्वागत है मेरे व्लॉग में. आज हम बात करेंगे एआई के बारे में."
    
    # 1. Create Audio
    audio_path = test_dir / "test_audio.mp3"
    create_hindi_audio(hindi_text, audio_path)
    
    # 2. Create Video
    video_path = test_dir / "test_video.mp4"
    duration = create_video_from_audio(audio_path, video_path)
    
    # 3. Create Transcript (Mocking WhisperX output for this known text)
    # We'll estimate timings roughly for this test
    transcript = {
        "language": "hi",
        "segments": [
            {
                "text": hindi_text,
                "words": [
                    {"text": "नमस्ते", "start": 0.0, "end": 0.6},
                    {"text": "दोस्तों", "start": 0.6, "end": 1.2},
                    {"text": "स्वागत", "start": 1.4, "end": 1.9},
                    {"text": "है", "start": 1.9, "end": 2.1},
                    {"text": "मेरे", "start": 2.1, "end": 2.4},
                    {"text": "व्लॉग", "start": 2.4, "end": 2.9},
                    {"text": "में", "start": 2.9, "end": 3.2},
                    {"text": "आज", "start": 3.8, "end": 4.1},
                    {"text": "हम", "start": 4.1, "end": 4.3},
                    {"text": "बात", "start": 4.3, "end": 4.6},
                    {"text": "करेंगे", "start": 4.6, "end": 5.0},
                    {"text": "एआई", "start": 5.0, "end": 5.5},
                    {"text": "के", "start": 5.5, "end": 5.7},
                    {"text": "बारे", "start": 5.7, "end": 6.0},
                    {"text": "में", "start": 6.0, "end": 6.3}
                ]
            }
        ]
    }
    
    # 4. Transliterate (using our new LLM-based transliterator, or fallback if no key)
    # Since we might not want to burn tokens or depend on key here, let's mock the Hinglish result
    # to match what we expect from the LLM.
    
    # Mocking the "text_roman" addition
    transcript['segments'][0]['text_roman'] = "Namaste doston swagat hai mere vlog mein Aaj hum baat karenge AI ke baare mein"
    
    words = transcript['segments'][0]['words']
    roman_words = ["Namaste", "doston", "swagat", "hai", "mere", "vlog", "mein", "Aaj", "hum", "baat", "karenge", "AI", "ke", "baare", "mein"]
    
    for i, word in enumerate(words):
        if i < len(roman_words):
            word['text_roman'] = roman_words[i]
            
    # Save transcript
    transcript_path = test_dir / "transcript_romanized.json"
    with open(transcript_path, 'w', encoding='utf-8') as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
        
    # 5. Render Subtitles
    renderer = SubtitleRenderer(test_dir)
    print("Rendering subtitles...")
    
    overlay_path = renderer.render_subtitles_for_clip(
        romanized_words=words,
        clip_duration=duration,
        style_name="glow_caption"
    )
    
    # 6. Composite
    print("Compositing...")
    final_path = test_dir / "final_test_with_audio.mp4"
    cmd = [
        'ffmpeg',
        '-y',
        '-i', str(video_path),
        '-i', str(overlay_path),
        '-filter_complex', '[0:v][1:v]overlay=0:0',
        '-c:v', 'libx264',
        '-c:a', 'copy',
        str(final_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    
    print(f"\nTest Complete! Video saved to: {final_path}")

if __name__ == "__main__":
    main()
