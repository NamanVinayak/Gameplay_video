import requests
from pathlib import Path
from typing import Optional, Dict
from openai import OpenAI
from elevenlabs.client import ElevenLabs
from utils.logging import setup_logger

class VoiceGenerator:
    """
    Handles Text-to-Speech generation using OpenAI or RunPod (Chatterbox)
    """
    
    def __init__(self, config, job_folder: Path):
        self.config = config
        self.job_folder = job_folder
        self.logger = setup_logger("VoiceGenerator", job_folder / "processing.log")
        
        # Initialize OpenAI client if key is present
        self.openai_client = None
        if config.openai_api_key:
            self.openai_client = OpenAI(api_key=config.openai_api_key)
        
        # Initialize ElevenLabs client if key is present
        self.elevenlabs_client = None
        if config.elevenlabs_api_key:
            self.elevenlabs_client = ElevenLabs(api_key=config.elevenlabs_api_key)
            
    def generate_audio(
        self, 
        text: str, 
        provider: str = "openai", 
        voice_id: str = "alloy",
        reference_audio_path: Optional[Path] = None
    ) -> Path:
        """
        Generate audio from text using specified provider
        
        Args:
            text: Text to speak
            provider: "openai" or "runpod"
            voice_id: Voice ID (OpenAI: alloy, echo, etc. | RunPod: predefined voice filename)
            reference_audio_path: Path to reference audio for cloning (RunPod only)
            
        Returns:
            Path to generated audio file
        """
        self.logger.info(f"Generating audio using {provider} with voice {voice_id}")
        
        output_path = self.job_folder / "generated_audio.mp3"
        
        if provider == "openai":
            return self._generate_openai(text, voice_id, output_path)
        elif provider == "elevenlabs":
            return self._generate_elevenlabs(text, voice_id, output_path)
        elif provider == "runpod":
            return self._generate_runpod(text, voice_id, reference_audio_path, output_path)
        else:
            raise ValueError(f"Unknown provider: {provider}")
            
    def _generate_openai(self, text: str, voice_id: str, output_path: Path) -> Path:
        """Generate using OpenAI TTS"""
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")
            
        try:
            response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice=voice_id,
                input=text
            )
            
            response.stream_to_file(output_path)
            self.logger.info(f"OpenAI audio saved to {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"OpenAI TTS failed: {e}")
            raise
    
    def _generate_elevenlabs(self, text: str, voice_id: str, output_path: Path) -> Path:
        """Generate using ElevenLabs TTS"""
        if not self.elevenlabs_client:
            raise ValueError("ElevenLabs API key not configured")
        
        # Default voice if none provided
        if not voice_id:
            voice_id = "JBFqnCBsd6RMkjVDRZzb"  # George - Natural and clear
        
        try:
            self.logger.info(f"Generating ElevenLabs audio with voice {voice_id}")
            
            # Generate audio using ElevenLabs SDK
            audio_generator = self.elevenlabs_client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            
            # Write audio to file
            with open(output_path, 'wb') as f:
                for chunk in audio_generator:
                    f.write(chunk)
            
            self.logger.info(f"ElevenLabs audio saved to {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"ElevenLabs TTS failed: {e}")
            raise
            
    def _generate_runpod(
        self, 
        text: str, 
        voice_id: Optional[str], 
        reference_audio_path: Optional[Path], 
        output_path: Path
    ) -> Path:
        """Generate using RunPod Chatterbox"""
        if not self.config.runpod_api_key or not self.config.runpod_endpoint_id:
            raise ValueError("RunPod credentials not configured")
            
        # Use /run endpoint (not /runsync) as per Chatterbox documentation
        endpoint_url = f"https://api.runpod.ai/v2/{self.config.runpod_endpoint_id}/run"
        
        headers = {
            "Authorization": f"Bearer {self.config.runpod_api_key}",
            "Content-Type": "application/json"
        }
        
        # Construct payload based on Chatterbox API documentation
        input_data = {
            "text": text,
            "output_format": "wav",
            "split_text": True,
            "chunk_size": 120,
            "temperature": 0.7,
            "exaggeration": 0.5,
            "cfg_weight": 3.0,
            "seed": -1,
            "speed_factor": 1.0,
            "language": "en"
        }
        
        # Handle Voice Cloning vs Predefined
        if reference_audio_path and reference_audio_path.exists():
            # Voice Cloning
            self.logger.info(f"Using voice cloning with reference: {reference_audio_path.name}")
            input_data["voice_mode"] = "clone"
            input_data["reference_audio_filename"] = reference_audio_path.name
            # Note: For voice cloning, the reference audio needs to be uploaded to the server first
            # This is a limitation we'll need to address later
        else:
            # Predefined Voice
            input_data["voice_mode"] = "predefined"
            if voice_id:
                input_data["predefined_voice_id"] = voice_id
            
        payload = {
            "input": input_data
        }
        
        try:
            self.logger.info(f"Sending request to RunPod: {endpoint_url}")
            response = requests.post(endpoint_url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            self.logger.info(f"RunPod response: {result}")
            
            # RunPod /run endpoint returns a job ID, we need to poll for results
            # Or use /runsync for synchronous response
            # Let's try /runsync instead for simplicity
            if "id" in result:
                job_id = result["id"]
                self.logger.info(f"Job submitted: {job_id}. Polling for results...")
                
                # Poll for results
                status_url = f"https://api.runpod.ai/v2/{self.config.runpod_endpoint_id}/status/{job_id}"
                max_attempts = 150  # 150 attempts * 2 seconds = 5 minutes max (for cold starts)
                
                for attempt in range(max_attempts):
                    import time
                    time.sleep(2)
                    
                    status_response = requests.get(status_url, headers=headers)
                    status_response.raise_for_status()
                    status_result = status_response.json()
                    
                    status = status_result.get("status")
                    self.logger.info(f"Job status: {status}")
                    
                    if status == "COMPLETED":
                        output = status_result.get("output")
                        if not output:
                            raise ValueError(f"No output in completed job: {status_result}")
                        
                        # Download audio from output
                        if isinstance(output, str) and output.startswith("http"):
                            audio_data = requests.get(output).content
                        elif isinstance(output, dict) and "audio_url" in output:
                            audio_data = requests.get(output["audio_url"]).content
                        elif isinstance(output, dict) and "audio_base64" in output:
                            import base64
                            audio_data = base64.b64decode(output["audio_base64"])
                        else:
                            raise ValueError(f"Unknown output format: {output}")
                        
                        # Save audio
                        with open(output_path, 'wb') as f:
                            f.write(audio_data)
                        
                        self.logger.info(f"Audio saved to {output_path}")
                        return output_path
                        
                    elif status == "FAILED":
                        error = status_result.get("error", "Unknown error")
                        raise ValueError(f"RunPod job failed: {error}")
                    
                    # Continue polling if IN_QUEUE or IN_PROGRESS
                
                raise TimeoutError(f"Job {job_id} did not complete within timeout")
            else:
                raise ValueError(f"Unexpected response format: {result}")
                
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"RunPod TTS failed: {e}")
            raise
