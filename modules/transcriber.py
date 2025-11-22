import httpx
import json
from pathlib import Path
from typing import Dict, List, Optional
from utils.logging import setup_logger


async def upload_audio_to_tmpfiles(audio_path: Path, logger) -> str:
    """
    Upload audio file to tmpfiles.org and return public URL
    
    tmpfiles.org provides free temporary file hosting (1 hour expiry)
    """
    logger.info("Uploading audio to tmpfiles.org for public access...")
    
    async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
        with open(audio_path, 'rb') as f:
            files = {'file': (audio_path.name, f, 'audio/wav')}
            
            # Upload to tmpfiles.org
            response = await client.post(
                'https://tmpfiles.org/api/v1/upload',
                files=files
            )
            
            logger.info(f"tmpfiles.org response status: {response.status_code}")
            
            response.raise_for_status()
            
            try:
                result = response.json()
            except Exception as e:
                logger.error(f"Failed to parse JSON: {e}")
                raise Exception(f"tmpfiles.org returned invalid JSON: {response.text[:200]}")
                
            if result.get('status') != 'success':
                raise Exception(f"tmpfiles.org upload failed: {result}")
                
            # tmpfiles.org returns URL like "https://tmpfiles.org/1234/file.wav"
            # We need to convert it to direct download URL: "https://tmpfiles.org/dl/1234/file.wav"
            url = result['data']['url']
            
            # Convert to direct download URL
            if 'tmpfiles.org/' in url:
                # Change https://tmpfiles.org/ABC/file.wav to https://tmpfiles.org/dl/ABC/file.wav
                url = url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')
                
            logger.info(f"Audio uploaded successfully to: {url}")
            return url


class Transcriber:
    """Handles audio transcription using WhisperX on RunPod"""

    def __init__(self, api_key: str, endpoint: str, job_folder: Path):
        self.api_key = api_key
        self.endpoint = endpoint
        self.job_folder = job_folder
        self.logger = setup_logger(
            "Transcriber",
            job_folder / "processing.log"
        )

    async def transcribe(self, audio_path: Path, audio_url: str = None, initial_prompt: Optional[str] = None, language: str = None) -> Dict:
        """
        Send audio to WhisperX and get transcript with timestamps
        """
        self.logger.info(f"Sending audio to WhisperX: {audio_path.name}")

        async with httpx.AsyncClient(timeout=600.0) as client:
            try:
                # Send transcription request using /runsync
                self.logger.info("Starting transcription job...")

                # Build full RunPod URL
                # If endpoint is just an ID, prepend the base URL
                if not self.endpoint.startswith('http'):
                    endpoint = f"https://api.runpod.ai/v2/{self.endpoint}/runsync"
                else:
                    # Make endpoint use /runsync for synchronous processing
                    endpoint = self.endpoint
                    if not endpoint.endswith('/runsync'):
                        if endpoint.endswith('/run'):
                            endpoint = endpoint[:-4] + '/runsync'
                        else:
                            endpoint = endpoint.rstrip('/') + '/runsync'

                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }

                # Upload audio to tmpfiles.org if no URL provided
                if not audio_url:
                    audio_url = await upload_audio_to_tmpfiles(audio_path, self.logger)

                self.logger.info(f"Using audio URL: {audio_url}")

                # Build payload according to kodxana/whisperx-worker spec
                input_payload = {
                    'audio_file': audio_url,
                    'batch_size': 64,
                    'align_output': True,
                    'diarization': False  # Disabled - requires Hugging Face auth
                }
                
                # Only add language if specified (otherwise auto-detect)
                if language:
                    input_payload['language'] = language
                    self.logger.info(f"Language forced to: {language}")
                else:
                    self.logger.info("Language set to auto-detect")

                payload = {
                    'input': input_payload
                }
                if initial_prompt:
                    payload['input']['initial_prompt'] = initial_prompt

                self.logger.info(f"Sending request to: {endpoint}")

                response = await client.post(
                    endpoint,
                    headers=headers,
                    json=payload
                )

                # Log response for debugging
                self.logger.info(f"Response status: {response.status_code}")

                response.raise_for_status()
                result = response.json()

                self.logger.info("Transcription received from WhisperX")

                # Parse WhisperX response
                transcript_data = self._parse_whisperx_response(result)

                # Save transcript as JSON
                transcript_path = self.job_folder / "transcript.json"
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    json.dump(transcript_data, f, ensure_ascii=False, indent=2)

                # Save as SRT
                srt_path = self.job_folder / "transcript.srt"
                self._save_as_srt(transcript_data['segments'], srt_path)

                # Save word-level timestamps for subtitle generation
                self.save_word_timestamps(transcript_data)

                self.logger.info(f"Transcript saved to {transcript_path}")
                return transcript_data

            except Exception as e:
                self.logger.error(f"Transcription error: {e}")
                raise

    def _parse_whisperx_response(self, response: Dict) -> Dict:
        """
        Parse WhisperX response into standardized format with word-level timestamps
        """
        # Common WhisperX response format
        if 'output' in response:
            data = response['output']
        elif 'result' in response:
            data = response['result']
        else:
            data = response

        # Extract segments with word-level data
        segments = data.get('segments', [])

        # Log whether word-level timestamps are present
        has_words = any('words' in seg for seg in segments)
        if has_words:
            self.logger.info("Word-level timestamps detected in WhisperX response")
        else:
            self.logger.warning("No word-level timestamps found. Check align_output=True in request")

        return {
            'text': data.get('text', ''),
            'segments': segments,
            'language': data.get('language', 'hi')
        }

    def _save_as_srt(self, segments: List[Dict], srt_path: Path):
        """Convert segments to SRT subtitle format"""
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, 1):
                start = self._format_srt_time(segment['start'])
                end = self._format_srt_time(segment['end'])
                text = segment['text'].strip()

                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")

    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        """Format seconds as SRT timestamp (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def save_word_timestamps(self, transcript_data: Dict) -> Path:
        """
        Save word-level timestamps to separate JSON file for subtitle processing
        """
        word_data = {
            'language': transcript_data.get('language', 'hi'),
            'full_text': transcript_data.get('text', ''),
            'words': []
        }

        word_count = 0
        for segment in transcript_data.get('segments', []):
            if 'words' in segment:
                # Extract words from this segment
                for word_info in segment['words']:
                    # Handle different possible word formats from WhisperX
                    word_text = word_info.get('word', word_info.get('text', ''))

                    word_data['words'].append({
                        'text': word_text,
                        'start': word_info.get('start', 0.0),
                        'end': word_info.get('end', 0.0),
                        'segment_id': segment.get('id', 0)
                    })
                    word_count += 1

        # Save word-level timestamps
        words_path = self.job_folder / "transcript_words.json"
        with open(words_path, 'w', encoding='utf-8') as f:
            json.dump(word_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Saved {word_count} word-level timestamps to {words_path}")

        if word_count == 0:
            self.logger.warning(
                "No word-level timestamps found! Subtitle generation may not work properly."
            )

        return words_path
