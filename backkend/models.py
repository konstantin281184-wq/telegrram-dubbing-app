from pydantic import BaseModel

class DubbingRequest(BaseModel):
    voice: str = "default"
    speed: float = 1.0
