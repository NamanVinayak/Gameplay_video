# Environment Setup Guide

This guide details the environment variables and configuration required to run the `clip_app_2` video generation tool.

## Prerequisites

- Python 3.10+
- FFmpeg installed and available in system PATH
- Git

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/NamanVinayak/Gameplay_video.git
   cd Gameplay_video
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   ```

## Environment Variables

The application uses a `.env` file to manage configuration. Below is a list of all supported variables.

### API Keys (Required for specific features)

| Variable | Description | Required For |
|----------|-------------|--------------|
| `OPENAI_API_KEY` | OpenAI API Key | Script generation, TTS (if using OpenAI) |
| `ELEVENLABS_API_KEY` | ElevenLabs API Key | High-quality TTS (if using ElevenLabs) |
| `OPENROUTER_API_KEY` | OpenRouter API Key | Alternative LLM provider |
| `RUNPOD_API_KEY` | RunPod API Key | WhisperX transcription, Chatterbox TTS |

### RunPod Configuration (For Serverless GPU Processing)

| Variable | Description |
|----------|-------------|
| `RUNPOD_ENDPOINT_ID` | Endpoint ID for TTS (Chatterbox) |
| `RUNPOD_WHISPER_ENDPOINT_ID` | Endpoint ID for WhisperX Transcription |
| `RUNPOD_WHISPER_API_KEY` | Specific key for Whisper (optional, defaults to RUNPOD_API_KEY) |

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL` | `google/gemini-2.5-flash` | Model to use for script generation |
| `SUBTITLE_FPS` | `30` | Frames per second for subtitle generation |

## Directory Structure

The application expects the following structure (created automatically):

- `outputs/`: Generated videos and intermediate files
- `static/`: Static assets for the web interface
- `modules/`: Core logic modules
- `test_assets/`: Sample media for testing

## Testing

To verify your setup, you can run the test generation script using the included sample video:

```bash
python test_gen.py
```
