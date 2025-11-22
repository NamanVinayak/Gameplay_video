import json
from pathlib import Path
from typing import Dict, List
from utils.helpers import setup_logger


class UniversalTransliterator:
    """
    Handles transliteration of text (e.g., Hindi -> Roman English)
    Now supports skipping transliteration for English.
    
    This converts Hindi text like "मैं जा रहा हूं" to "main jaa rahaa hoon"
    (not translation, but phonetic representation in Latin script).

    Note: This uses ITRANS romanization scheme which is widely used for
    Indic scripts.
    """




    def __init__(self, job_folder: Path, api_key: str = None, model: str = None):
        self.job_folder = job_folder
        self.logger = setup_logger("Transliterator", job_folder / "processing.log")
        self.api_key = api_key
        self.model = model

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM for transliteration"""
        if not self.api_key:
            self.logger.warning("No API key provided for Hinglish generation, falling back to original text")
            return None

        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/VinVideo/clip_app",
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a helpful assistant that converts Hindi Devanagari text to Hinglish (Roman script). Keep the words exactly the same, just write them in English letters. Do not translate. Example: 'नमस्ते दोस्तों' -> 'Namaste doston'. Output ONLY the converted text."
                },
                {"role": "user", "content": prompt}
            ]
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content'].strip()
            except Exception as e:
                self.logger.error(f"LLM call failed: {e}")
                return None

    async def transliterate_transcript(self, transcript: Dict) -> Dict:
        """
        Add 'text_roman' field to transcript using LLM for natural Hinglish
        """
        self.logger.info("Starting transliteration...")
        
        language = transcript.get('language', '')
        self.logger.info(f"Detected language: {language}")

        # If English, just copy text to text_roman
        if language == 'en':
            self.logger.info("Language is English, skipping transliteration")
            if 'text' in transcript:
                transcript['text_roman'] = transcript['text']
            
            for segment in transcript.get('segments', []):
                if 'text' in segment:
                    segment['text_roman'] = segment['text']
                for word in segment.get('words', []):
                    if 'text' in word:
                        word['text_roman'] = word['text']
            return transcript

        # For Hindi (or others), use LLM to generate Hinglish
        # We will process segment by segment to maintain context but keep it manageable
        
        for i, segment in enumerate(transcript.get('segments', [])):
            original_text = segment.get('text', '')
            if not original_text:
                continue

            self.logger.info(f"Transliterating segment {i+1}/{len(transcript['segments'])}")
            
            # Call LLM for the whole segment
            hinglish_text = await self._call_llm(original_text)
            
            if hinglish_text:
                segment['text_roman'] = hinglish_text
                
                # Now we need to map words. This is tricky because word counts might not match.
                # Simple approach: Split hinglish text by space and assign to words.
                # If counts mismatch, we fallback to original text for remaining words.
                
                hinglish_words = hinglish_text.split()
                original_words = segment.get('words', [])
                
                import string
                for j, word in enumerate(original_words):
                    if j < len(hinglish_words):
                        # Clean punctuation from the hinglish word to match the "word" concept
                        clean_word = hinglish_words[j].strip(string.punctuation)
                        word['text_roman'] = clean_word if clean_word else hinglish_words[j]
                    else:
                        # Fallback
                        word['text_roman'] = word.get('text', '')
            else:
                # Fallback if LLM fails
                segment['text_roman'] = original_text
                for word in segment.get('words', []):
                    word['text_roman'] = word.get('text', '')

        self.logger.info("Transliteration complete")
        
        # Save romanized transcript
        output_path = self.job_folder / "transcript_romanized.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)
            
        return transcript


class FallbackTransliterator:
    """
    Fallback transliterator using indic-transliteration library

    This is a lighter alternative if ai4bharat-transliteration is not available.
    Uses rule-based transliteration instead of ML model.

    To use this, install: pip install indic-transliteration
    """

    def __init__(self, job_folder: Path):
        self.job_folder = job_folder
        self.logger = setup_logger(
            "FallbackTransliterator",
            job_folder / "processing.log"
        )

        try:
            from indic_transliteration import sanscript
            from indic_transliteration.sanscript import transliterate
            self.sanscript = sanscript
            self.transliterate = transliterate
            self.logger.info("indic-transliteration loaded successfully")
        except ImportError as e:
            self.logger.error("indic-transliteration not installed")
            raise ImportError(
                "indic-transliteration package required. "
                "Run: pip install indic-transliteration"
            ) from e

    def transliterate_transcript(self, transcript_data: Dict) -> Dict:
        """Same interface as HindiTransliterator"""
        self.logger.info("Starting transcript transliteration (fallback method)...")

        romanized_data = {
            'text': transcript_data.get('text', ''),
            'text_roman': '',
            'segments': [],
            'language': transcript_data.get('language', 'hi')
        }

        # Transliterate full text
        if romanized_data['text']:
            romanized_data['text_roman'] = self._transliterate_text(
                romanized_data['text']
            )

        # Process segments and words
        for segment in transcript_data.get('segments', []):
            romanized_segment = segment.copy()

            if 'text' in segment:
                romanized_segment['text_roman'] = self._transliterate_text(
                    segment['text']
                )

            if 'words' in segment:
                romanized_words = []
                for word in segment['words']:
                    romanized_word = word.copy()
                    word_text = word.get('word', word.get('text', ''))

                    if word_text:
                        romanized_word['text_roman'] = self._transliterate_text(
                            word_text
                        )

                    romanized_words.append(romanized_word)

                romanized_segment['words'] = romanized_words

            romanized_data['segments'].append(romanized_segment)

        # Save romanized transcript
        output_path = self.job_folder / "transcript_romanized.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(romanized_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Romanized transcript saved to {output_path}")

        return romanized_data

    def _transliterate_text(self, text: str) -> str:
        """Transliterate using rule-based method"""
        if not text or not text.strip():
            return ""

        try:
            # Use ITRANS scheme for romanization
            romanized = self.transliterate(
                text,
                self.sanscript.DEVANAGARI,
                self.sanscript.ITRANS
            )
            return romanized
        except Exception as e:
            self.logger.error(f"Transliteration failed for '{text}': {e}")
            return text
