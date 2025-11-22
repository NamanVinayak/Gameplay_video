from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

class Settings(BaseSettings):
    # Base Paths
    base_dir: Path = Path(__file__).parent
    static_dir: Path = base_dir / "static"
    outputs_dir: Path = base_dir / "outputs"
    modules_dir: Path = base_dir / "modules"
    
    # API Keys
    openai_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    llm_model: Optional[str] = "google/gemini-2.5-flash"
    
    # RunPod Configuration
    runpod_api_key: Optional[str] = None # Default/Chatterbox Key
    runpod_endpoint_id: Optional[str] = None # For TTS (Chatterbox)
    
    runpod_whisper_api_key: Optional[str] = None # Specific key for Whisper (if different)
    runpod_whisper_endpoint_id: Optional[str] = None # For Transcription (WhisperX)
    
    # Processing Settings
    subtitle_fps: int = 30
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
settings.outputs_dir.mkdir(exist_ok=True)
