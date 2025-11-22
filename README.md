# Gameplay Video Generator

A powerful tool for generating gameplay videos with AI-generated scripts, voiceovers, and subtitles.

## Features

- **AI Script Generation**: Uses Google Gemini (or other LLMs) to generate engaging scripts.
- **Text-to-Speech**: Supports ElevenLabs and RunPod (Chatterbox) for high-quality voiceovers.
- **Automatic Transcription**: Uses WhisperX for accurate word-level timestamps.
- **Dynamic Subtitles**: Generates stylish subtitles with "Hinglish" support.
- **Video Processing**: Automatically cuts gameplay footage to match audio duration.
- **Web Interface**: Simple UI for easy interaction.

## Getting Started

For detailed setup instructions, including environment variables and API keys, please refer to [ENV_SETUP.md](ENV_SETUP.md).

### Quick Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure Environment**:
    Copy `.env.example` to `.env` and add your API keys.

3.  **Run the Application**:
    ```bash
    python main.py
    ```

## Testing

A sample video and audio file are included in `test_assets/`. You can run the test script to verify your setup:

```bash
python test_gen.py
```

This script uses `test_assets/example_gameplay.mp4` and `test_assets/generated_audio.mp3` to test the pipeline without using API credits for TTS.
