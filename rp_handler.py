"""
Standalone RunPod Handler for TTS Service
"""

import runpod
from enum import Enum
from typing import Union, List, Literal
from loguru import logger
from pydantic import Field, BaseModel

# Schema definitions
class OpenAISpeechRequest(BaseModel):
    model: Literal["tts-1", "tts-1-hd", "kokoro"] = "kokoro"
    input: str = Field(..., description="The text to generate audio for")
    voice: str = Field(
        default="af",
        description="The voice to use for generation. Can be a base voice or a combined voice name.",
    )
    response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = Field(
        default="mp3",
        description="The format to return audio in.",
    )
    speed: float = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="The speed of the generated audio.",
    )
    stream: bool = Field(
        default=True,
        description="If true, audio will be streamed as it's generated.",
    )

# Import services after schema to avoid circular imports
from api.src.services.audio import AudioService
from api.src.services.tts_model import TTSModel
from api.src.services.tts_service import TTSService

# Initialize model and services
async def initialize():
    """Initialize the TTS model and service"""
    logger.info("Initializing TTS model...")
    await TTSModel.setup()
    logger.info("TTS model initialized successfully")
    return TTSService()

# Initialize services
tts_service = None

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

    # If single voice, return it directly
    if len(voices) == 1:
        return voices[0]

    # Otherwise combine voices
    return await tts_service.combine_voices(voices=voices)

async def create_speech(request: dict):
    """Generate speech from text"""
    try:
        # Convert dict to OpenAISpeechRequest
        request = OpenAISpeechRequest(**request)
        
        # Process voice combination and validate
        voice_to_use = await process_voices(request.voice)

        # Stream audio chunks as they're generated
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
    # Set stream to True to ensure streaming response
    request["stream"] = True
    async for chunk in await create_speech(request):
        yield chunk

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler}) 