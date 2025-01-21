"""
FastAPI OpenAI Compatible API
"""

import runpod

from .routers.openai_compatible import create_speech


async def handler(job):
    request = job.input
    # Set stream to True to ensure streaming response
    request["stream"] = True
    response = await create_speech(request)
    
    # Return the streaming response content
    async for chunk in response.body_iterator:
        yield chunk



if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
