from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import shutil
from pathlib import Path
from datetime import datetime
import subprocess
import json

from config import settings
from utils.logging import setup_logger
from modules.voice_generator import VoiceGenerator
from modules.transcriber import Transcriber
from modules.video_processor import VideoProcessor
from modules.subtitle_renderer import SubtitleRenderer
from modules.face_tracker import FaceTracker

# Setup Logger
logger = setup_logger("Main", settings.outputs_dir / "app.log")

# ============================================================================
# TODO - REMAINING TASKS (See TODO.md for full details)
# ============================================================================
# 1. [HIGH PRIORITY] Fix Subtitle Styling Issues
#    - Text effects may not render correctly
#    - Font loading fallbacks to default (Arial-Bold, Impact missing)
#    - Review: modules/subtitle_renderer.py, subtitle_styles/effects/
#    - Test all three styles: simple_caption, glow_caption, karaoke_style
#
# 2. [HIGH PRIORITY] Remove hardcoded API key in test_runpod_direct.py
#    - Security issue: RunPod key exposed in line 7
#    - Load from environment variables instead
#    - Rotate exposed key before production
#
# 3. [MEDIUM] Fix test file hardcoded paths
#    - test_gen.py uses /Users/naman/Downloads/
#    - Change to test_assets/example_gameplay.mp4
#
# 4. [DONE] YOLO Integration - Complete ✅
#    - FaceTracker integrated from clip_app_1
#    - Subject tracking working (tested in clip_app_1)
#    - See INTEGRATION_COMPLETE.md for details
# ============================================================================

app = FastAPI(title="YouTube Automation Tool (Clip App 2)")

# Mount static files
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

class ScriptRequest(BaseModel):
    script: str
    voice_provider: str = "openai" # "openai" or "runpod"
    voice_id: Optional[str] = None # e.g., "alloy" or "cloned_voice_id"
    reference_audio_path: Optional[str] = None # For cloning
    gameplay_video_path: str # Path to background video

@app.get("/")
async def homepage():
    """Serve the web interface"""
    return FileResponse(settings.static_dir / "index.html")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "openai_enabled": bool(settings.openai_api_key),
        "runpod_enabled": bool(settings.runpod_api_key and settings.runpod_endpoint_id)
    }

@app.post("/process_script")
async def process_script(request: ScriptRequest, background_tasks: BackgroundTasks):
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    job_folder = settings.outputs_dir / job_id
    job_folder.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting job {job_id} with provider {request.voice_provider}")

    try:
        # Initialize modules
        voice_gen = VoiceGenerator(settings, job_folder)
        
        # Initialize Transcriber with RunPod Whisper Endpoint
        # Use specific Whisper key if available, otherwise fallback to default
        whisper_key = settings.runpod_whisper_api_key or settings.runpod_api_key
        
        transcriber = Transcriber(
            api_key=whisper_key, 
            endpoint=settings.runpod_whisper_endpoint_id, 
            job_folder=job_folder
        )
        
        # 1. Generate Audio
        logger.info("Step 1: Generating Audio...")
        audio_path = voice_gen.generate_audio(
            text=request.script,
            provider=request.voice_provider,
            voice_id=request.voice_id,
            reference_audio_path=Path(request.reference_audio_path) if request.reference_audio_path else None
        )
        
        # 2. Transcribe Audio (for timestamps)
        logger.info("Step 2: Transcribing Audio for Alignment...")
        # Call transcriber same way as clip_app_1 - pass audio_path directly
        transcript_data = await transcriber.transcribe(audio_path, language="en")
        
        # 3. Process Video
        logger.info("Step 3: Processing Video...")
        video_processor = VideoProcessor(job_folder)
        
        # Get audio duration
        def get_duration(path):
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(path)]
            return float(subprocess.check_output(cmd).strip())
            
        audio_duration = get_duration(audio_path)
        
        # Cut video to match audio duration
        gameplay_path = Path(request.gameplay_video_path)
        if not gameplay_path.exists():
            raise FileNotFoundError(f"Gameplay video not found: {gameplay_path}")

        # Track face/subject position using YOLO
        logger.info("Step 3a: Tracking subject position with YOLO...")
        face_tracker = FaceTracker(job_folder)

        # Convert duration to end timestamp
        hours = int(audio_duration // 3600)
        minutes = int((audio_duration % 3600) // 60)
        seconds = int(audio_duration % 60)
        end_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        tracking_data = face_tracker.track_faces_in_clip(
            video_path=gameplay_path,
            start_time="00:00:00",
            end_time=end_time,
            sample_rate=5  # Sample every 5 frames
        )

        face_x = tracking_data['face_center_x']
        face_y = tracking_data['face_center_y']
        width = tracking_data['source_width']
        height = tracking_data['source_height']

        logger.info(f"Subject detected at: ({face_x}, {face_y})")

        # Create base video clip with face-centered crop
        logger.info("Step 3b: Creating vertical clip...")
        base_video_path = job_folder / "base_video.mp4"
        video_processor.create_vertical_clip(
            video_path=gameplay_path,
            start_time="00:00:00",
            duration=audio_duration,
            face_x=face_x,
            face_y=face_y,
            source_width=width,
            source_height=height,
            output_name="base_video.mp4"
        )
        
        # Merge Audio and Video
        merged_video_path = job_folder / "merged_video.mp4"
        video_processor.merge_audio_video(base_video_path, audio_path, merged_video_path)
        
        # 4. Render Subtitles
        logger.info("Step 4: Rendering Subtitles...")
        subtitle_renderer = SubtitleRenderer(job_folder)
        
        # We need 'words' from transcript_data
        # Transcriber saves them to 'transcript_words.json', but we can also extract from return value
        # The Transcriber.transcribe returns the full WhisperX response
        # We need to convert it to the format SubtitleRenderer expects
        
        # Helper to extract words
        words = []
        for seg in transcript_data.get('segments', []):
            if 'words' in seg:
                for w in seg['words']:
                    words.append({
                        'text': w.get('word', w.get('text', '')),
                        'start': w['start'],
                        'end': w['end']
                    })
        
        # Render
        subtitle_overlay = subtitle_renderer.render_subtitles_for_clip(
            romanized_words=words, # It expects 'text_roman' but 'text' works too if no transliteration needed
            clip_duration=audio_duration,
            style_name="simple_caption" # Default style
        )
        
        # Composite
        final_output_path = job_folder / "final_video.mp4"
        video_processor.composite_subtitles(merged_video_path, subtitle_overlay, final_output_path)
        
        logger.info(f"Job Complete! Output: {final_output_path}")
        
        return {
            "job_id": job_id, 
            "status": "completed", 
            "output_url": f"/outputs/{job_id}/final_video.mp4"
        }
        
    except Exception as e:
        logger.error(f"Job failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/outputs/{job_id}/{filename}")
async def get_output(job_id: str, filename: str):
    file_path = settings.outputs_dir / job_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
