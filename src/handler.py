"""
RunPod Handler for TTS Service
"""

import runpod
from loguru import logger
from typing import Union, List

from .schemas import OpenAISpeechRequest
from .services.audio import AudioService
from .services.tts_model import TTSModel
from .services.tts_service import TTSService

# Initialize services
tts_service = None

async def initialize():
    """Initialize the TTS model and service"""
    logger.info("Initializing TTS model...")
    await TTSModel.setup()
    logger.info("TTS model initialized successfully")
    return TTSService()

async def process_voices(voice_input: Union[str, List[str]]) -> str:
    """Process voice input into a combined voice, handling both string and list formats"""
    if isinstance(voice_input, str):
        voices = [v.strip() for v in voice_input.split("+") if v.strip()]
    else:
        voices = voice_input

    if not voices:
        raise ValueError("No voices provided")

    # Check if all voices exist
    available_voices = await tts_service.list_voices()
    for voice in voices:
        if voice not in available_voices:
            raise ValueError(
                f"Voice '{voice}' not found. Available voices: {', '.join(sorted(available_voices))}"
            )

    return voices[0] if len(voices) == 1 else await tts_service.combine_voices(voices=voices)

async def create_speech(request: dict):
    """Generate speech from text"""
    try:
        request = OpenAISpeechRequest(**request)
        voice_to_use = await process_voices(request.voice)

        async for chunk in tts_service.generate_audio_stream(
            text=request.input,
            voice=voice_to_use,
            speed=request.speed,
            output_format=request.response_format,
        ):
            yield chunk

    except ValueError as e:
        logger.error(f"Invalid request: {str(e)}")
        raise ValueError({"error": "Invalid request", "message": str(e)})
    except Exception as e:
        logger.error(f"Error generating speech: {str(e)}")
        raise Exception({"error": "Server error", "message": str(e)})

async def handler(job):
    """RunPod handler function"""
    global tts_service
    if tts_service is None:
        tts_service = await initialize()
        
    request = job.input
    request["stream"] = True
    async for chunk in await create_speech(request):
        yield chunk

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler}) 