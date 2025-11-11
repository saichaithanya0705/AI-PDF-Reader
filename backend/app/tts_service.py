"""
Text-to-Speech Service for Adobe Hackathon
Supports Azure TTS with fallback options
"""

import os
import asyncio
import tempfile
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import requests
from pathlib import Path

# Optional Azure import
try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    speechsdk = None
    AZURE_AVAILABLE = False
    print("⚠️ Azure Speech SDK not available. TTS features will be limited.")


class TTSProvider(ABC):
    """Abstract base class for TTS providers"""
    
    @abstractmethod
    async def generate_audio(self, text: str, voice: str = None) -> bytes:
        pass


class AzureTTSProvider(TTSProvider):
    def __init__(self):
        if not AZURE_AVAILABLE:
            raise ImportError("Azure Speech SDK is not installed. Install with: pip install azure-cognitiveservices-speech")
        
        self.api_key = os.getenv('AZURE_TTS_KEY')
        self.region = os.getenv('AZURE_TTS_REGION', 'eastasia')  # Use direct region from env

        if not self.api_key:
            raise ValueError("Azure TTS API key not provided")

        print(f"🔊 Azure TTS Config: Region={self.region}, Key={self.api_key[:10]}...")

        try:
            # Configure speech service
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.api_key,
                region=self.region
            )

            # Set default voice
            self.speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"

            # Set audio format to ensure compatibility
            self.speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
            )

            print(f"✅ Azure TTS initialized successfully")

        except Exception as e:
            print(f"❌ Azure TTS initialization failed: {e}")
            raise
    
    def _extract_region_from_endpoint(self, endpoint: str) -> str:
        """Extract region from Azure endpoint URL"""
        try:
            # Azure TTS endpoints typically follow pattern: https://{region}.tts.speech.microsoft.com/
            if 'tts.speech.microsoft.com' in endpoint:
                region = endpoint.split('//')[1].split('.')[0]
                return region
            return 'eastus'  # fallback
        except:
            return 'eastus'
    
    async def generate_audio(self, text: str, voice: str = None) -> bytes:
        """Generate audio from text using Azure TTS"""
        try:
            print(f"🔊 Azure TTS: Generating audio for {len(text)} characters")
            print(f"🔊 Voice: {voice or self.speech_config.speech_synthesis_voice_name}")

            if voice:
                self.speech_config.speech_synthesis_voice_name = voice

            # Limit text length for TTS
            if len(text) > 5000:
                text = text[:5000] + "..."
                print(f"🔊 Truncated text to 5000 characters")

            # Create synthesizer following exact ChatGPT example format
            # ✅ Ensure this is not None and use_default_speaker=True as in example
            audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=audio_config  # Following ChatGPT example exactly
            )

            # Generate speech using async method
            print(f"🔊 Starting Azure TTS synthesis...")

            # Use the async method properly
            def synthesize_speech():
                return synthesizer.speak_text_async(text).get()

            result = await asyncio.to_thread(synthesize_speech)

            print(f"🔊 Azure TTS result: {result.reason}")

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print(f"✅ Azure TTS success: {len(result.audio_data)} bytes")
                return result.audio_data
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = speechsdk.CancellationDetails(result)
                error_msg = f"TTS canceled: {cancellation_details.reason}"
                if cancellation_details.error_details:
                    error_msg += f" - {cancellation_details.error_details}"
                print(f"❌ Azure TTS canceled: {error_msg}")
                raise Exception(error_msg)
            else:
                raise Exception(f"TTS failed: {result.reason}")

        except Exception as e:
            print(f"❌ Azure TTS error: {str(e)}")
            raise Exception(f"Azure TTS error: {str(e)}")


class GoogleTTSProvider(TTSProvider):
    """Fallback TTS provider using Google TTS"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_TTS_API_KEY')
        if not self.api_key:
            raise ValueError("Google TTS API key not provided")
    
    async def generate_audio(self, text: str, voice: str = None) -> bytes:
        """Generate audio using Google TTS API"""
        try:
            url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.api_key}"
            
            payload = {
                "input": {"text": text},
                "voice": {
                    "languageCode": "en-US",
                    "name": voice or "en-US-Wavenet-D",
                    "ssmlGender": "NEUTRAL"
                },
                "audioConfig": {
                    "audioEncoding": "MP3"
                }
            }
            
            response = await asyncio.to_thread(
                requests.post,
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Decode base64 audio
            import base64
            audio_data = base64.b64decode(data['audioContent'])
            return audio_data
            
        except Exception as e:
            raise Exception(f"Google TTS error: {str(e)}")


class LocalTTSProvider(TTSProvider):
    """Local TTS provider for development/fallback"""
    
    async def generate_audio(self, text: str, voice: str = None) -> bytes:
        """Generate simple audio file (placeholder for local TTS)"""
        # This is a placeholder - in a real implementation, you might use
        # libraries like pyttsx3 or espeak for local TTS
        
        # For now, return a minimal WAV file header (silence)
        # This ensures the API doesn't fail even without TTS service
        wav_header = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x22\x56\x00\x00\x44\xac\x00\x00\x02\x00\x10\x00data\x00\x08\x00\x00'
        silence_data = b'\x00' * 2048  # 2KB of silence
        return wav_header + silence_data


def get_tts_provider() -> TTSProvider:
    """Factory function to get the appropriate TTS provider"""
    provider_type = os.getenv('TTS_PROVIDER', 'azure').lower()
    
    try:
        if provider_type == 'azure':
            return AzureTTSProvider()
        elif provider_type == 'google':
            return GoogleTTSProvider()
        else:
            # Fallback to local TTS
            return LocalTTSProvider()
    except Exception as e:
        print(f"Warning: Failed to initialize {provider_type} TTS provider: {e}")
        print("Falling back to local TTS provider")
        return LocalTTSProvider()


class TTSService:
    """Main TTS service class"""
    
    def __init__(self):
        self.provider = get_tts_provider()
    
    async def generate_podcast(self, content: str, title: str = "Podcast") -> bytes:
        """Generate a podcast-style audio from content"""
        
        # Create podcast script
        podcast_script = f"""
        Welcome to your AI-powered document podcast. 
        
        Today we're exploring: {title}
        
        {content}
        
        This concludes our brief exploration. Thank you for listening to your AI document companion.
        """
        
        # Limit content length for reasonable audio duration (2-5 minutes)
        max_chars = 1000  # Roughly 2-3 minutes of speech
        if len(podcast_script) > max_chars:
            podcast_script = podcast_script[:max_chars] + "... and much more to explore in the full document."
        
        return await self.provider.generate_audio(podcast_script)
    
    async def generate_insight_audio(self, insight_text: str) -> bytes:
        """Generate audio for a specific insight"""
        return await self.provider.generate_audio(insight_text)
    
    async def save_audio_file(self, audio_data: bytes, filename: str = None) -> str:
        """Save audio data to a temporary file and return the path"""
        if not filename:
            filename = f"audio_{asyncio.get_event_loop().time()}.wav"
        
        # Create temp directory if it doesn't exist
        temp_dir = Path("data/temp_audio")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = temp_dir / filename
        
        with open(file_path, 'wb') as f:
            f.write(audio_data)
        
        return str(file_path)
