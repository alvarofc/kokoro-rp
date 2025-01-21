import torch

if torch.cuda.is_available():
    from .tts_gpu import TTSGPUModel as TTSModel
else:
    from .tts_cpu import TTSCPUModel as TTSModel

__all__ = ["TTSModel"]
