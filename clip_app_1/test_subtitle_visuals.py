import json
import subprocess
from pathlib import Path
from modules.subtitle_renderer import SubtitleRenderer
from utils.helpers import setup_logger

def create_dummy_video(path: Path, duration: int = 10):
    """Create a black video of specified duration"""
    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'lavfi',
        '-i', f'color=c=black:s=1080x1920:r=30:d={duration}',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        str(path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Created dummy video at {path}")

def create_mock_transcript(job_folder: Path):
    """Create a mock Hinglish transcript"""
    
    # "Namaste doston, swagat hai mere vlog mein. Aaj hum baat karenge AI ke baare mein."
    # (Hello friends, welcome to my vlog. Today we will talk about AI.)
    
    mock_data = {
        "language": "hi",
        "segments": [
            {
                "words": [
                    {"text": "नमस्ते", "text_roman": "Namaste", "start": 0.5, "end": 1.0},
                    {"text": "दोस्तों", "text_roman": "doston", "start": 1.1, "end": 1.5},
                    {"text": ",", "text_roman": ",", "start": 1.5, "end": 1.6},
                    {"text": "स्वागत", "text_roman": "swagat", "start": 1.8, "end": 2.2},
                    {"text": "है", "text_roman": "hai", "start": 2.3, "end": 2.5},
                    {"text": "मेरे", "text_roman": "mere", "start": 2.6, "end": 2.9},
                    {"text": "व्लॉग", "text_roman": "vlog", "start": 3.0, "end": 3.4},
                    {"text": "में", "text_roman": "mein", "start": 3.5, "end": 3.8},
                    {"text": ".", "text_roman": ".", "start": 3.8, "end": 3.9}
                ]
            },
            {
                "words": [
                    {"text": "आज", "text_roman": "Aaj", "start": 4.5, "end": 4.8},
                    {"text": "हम", "text_roman": "hum", "start": 4.9, "end": 5.1},
                    {"text": "बात", "text_roman": "baat", "start": 5.2, "end": 5.5},
                    {"text": "करेंगे", "text_roman": "karenge", "start": 5.6, "end": 6.0},
                    {"text": "AI", "text_roman": "AI", "start": 6.1, "end": 6.5},
                    {"text": "के", "text_roman": "ke", "start": 6.6, "end": 6.8},
                    {"text": "बारे", "text_roman": "baare", "start": 6.9, "end": 7.2},
                    {"text": "में", "text_roman": "mein", "start": 7.3, "end": 7.6},
                    {"text": ".", "text_roman": ".", "start": 7.6, "end": 7.7}
                ]
            }
        ]
    }
    
    # Save as transcript_romanized.json (which SubtitleRenderer prioritizes)
    path = job_folder / "transcript_romanized.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(mock_data, f, ensure_ascii=False, indent=2)
    print(f"Created mock transcript at {path}")

def main():
    # Setup test environment
    base_dir = Path(__file__).parent
    test_dir = base_dir / "test_output"
    test_dir.mkdir(exist_ok=True)
    
    # Create dummy video
    video_path = test_dir / "test_video.mp4"
    create_dummy_video(video_path)
    
    # Create mock transcript
    create_mock_transcript(test_dir)
    
    # Initialize renderer
    renderer = SubtitleRenderer(test_dir)
    
    # Load words from transcript
    transcript_path = test_dir / "transcript_romanized.json"
    with open(transcript_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    words = []
    for segment in data.get('segments', []):
        for word in segment.get('words', []):
            words.append({
                'text': word.get('text_roman', word.get('text', '')),
                'start': word.get('start', 0),
                'end': word.get('end', 0)
            })
            
    print(f"Loaded {len(words)} words for rendering")
    
    # Render subtitles (creates transparent overlay)
    print("Rendering subtitle overlay...")
    overlay_path = renderer.render_subtitles_for_clip(
        romanized_words=words,
        clip_duration=10.0,
        style_name="glow_caption" # Test the glow style
    )
    
    # Composite onto video
    print("Compositing onto video...")
    output_path = test_dir / "final_test_output.mp4"
    
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-i', str(overlay_path),
        '-filter_complex', '[0:v][1:v]overlay=0:0',
        '-c:v', 'libx264',
        '-y',
        str(output_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    
    print("\nTest Complete!")
    print(f"Output video saved to: {output_path}")

if __name__ == "__main__":
    main()
