# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A FastAPI-based video automation tool that generates short-form gameplay videos with AI-generated voiceovers and animated subtitles. The application processes scripts through a pipeline: text-to-speech → transcription → video processing → subtitle rendering.

## Development Commands

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Running the Application
```bash
# Start the FastAPI server
python main.py
# Server runs on http://localhost:8000

# Alternative with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Test with sample video (uses test_assets/example_gameplay.mp4)
python test_gen.py

# Test RunPod connection directly
python test_runpod_direct.py
```

## Architecture

### Processing Pipeline
The application follows a sequential 4-step pipeline (main.py:48-159):

1. **Voice Generation** (`VoiceGenerator`) - Converts script text to speech audio
2. **Transcription** (`Transcriber`) - Generates word-level timestamps using WhisperX
3. **Video Processing** (`VideoProcessor`) - Crops/cuts gameplay footage to match audio duration
4. **Subtitle Rendering** (`SubtitleRenderer`) - Creates animated subtitle overlays

### Core Modules

**modules/voice_generator.py**
- Supports multiple TTS providers: OpenAI, ElevenLabs, RunPod (Chatterbox)
- RunPod uses async job polling (max 5 minutes for cold starts)
- Outputs: `generated_audio.mp3`

**modules/transcriber.py**
- Uses WhisperX on RunPod for word-level timestamps
- Uploads audio to tmpfiles.org for RunPod access (1-hour expiry)
- Must use `/runsync` endpoint for synchronous processing
- Outputs: `transcript.json`, `transcript.srt`, `transcript_words.json`
- Critical: `align_output=True` required for word-level timestamps

**modules/video_processor.py**
- FFmpeg-based video operations
- `create_vertical_clip()`: Crops to 9:16 (1080x1920) centered on face position
- `merge_audio_video()`: Mixes TTS (100%) with gameplay audio (10% ducking)
- `composite_subtitles()`: Overlays transparent subtitle video using ProRes 4444

**modules/subtitle_renderer.py**
- Frame-by-frame subtitle generation (default 30fps)
- Loads styles from `subtitle_styles/styles.json`
- Three rendering modes: outline, glow, karaoke
- Uses VinVideo text effects (`subtitle_styles/effects/`)
- Word window shows 3 words at a time with highlight tracking
- Outputs: `subtitle_frames/` → `subtitles_overlay.mov` (ProRes 4444 for transparency)

### Configuration

**config.py**
- Uses `pydantic-settings` for env var management
- Automatically creates `outputs/` directory
- Supports separate RunPod keys for TTS vs Whisper

**subtitle_styles/styles.json**
- Three preset styles: simple_caption, glow_caption, karaoke_style
- Each style defines: typography, colors, effects, layout margins
- Bottom margin: 450px (safe zone for mobile platforms)

## Important Technical Details

### FFmpeg Requirements
- FFmpeg must be in system PATH
- ProRes codec required for transparent subtitle overlay
- Video dimensions must be divisible by 2 for H.264 encoding

### API Integrations

**RunPod Endpoints**
- TTS (Chatterbox): Uses `/run` endpoint with status polling
- WhisperX: Uses `/runsync` for synchronous transcription
- Audio must be publicly accessible URL (handled via tmpfiles.org upload)

**ElevenLabs**
- Default voice: "JBFqnCBsd6RMkjVDRZzb" (George)
- Model: eleven_multilingual_v2
- Output format: mp3_44100_128

### Video Processing Flow
1. Gameplay video cropped to 9:16 vertical format (centered)
2. Duration matched to TTS audio length
3. Audio mixing: gameplay (10%) + TTS (100%)
4. Subtitle frames rendered as transparent PNG sequence
5. PNGs encoded to ProRes 4444 video
6. Subtitle overlay composited onto final video

### Common Patterns

**Job Folder Structure**
Each API request creates a timestamped job folder:
```
outputs/job_YYYYMMDD_HHMMSS/
├── generated_audio.mp3
├── transcript.json
├── transcript_words.json
├── base_video.mp4
├── merged_video.mp4
├── subtitle_frames/
│   └── frame_000000.png...
├── subtitles_overlay.mov
├── final_video.mp4
└── processing.log
```

**Error Handling**
- All modules log to `{job_folder}/processing.log`
- RunPod TTS polls for max 5 minutes (150 attempts × 2s)
- Subtitle rendering falls back to simple text on effect failures
- Video audio mixing has fallback if stream detection fails

### Subtitle Word Timing
The subtitle renderer handles gaps between words (up to 1.5s) by keeping the last word visible. This prevents flashing during natural speech pauses (subtitle_renderer.py:180-238).
