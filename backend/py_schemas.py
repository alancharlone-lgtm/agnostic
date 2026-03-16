from pydantic import BaseModel
from typing import Optional

class BaseAgentRequest(BaseModel):
    user_id: str
    session_id: str
    text_input: Optional[str] = None
    audio_base64: Optional[str] = None
    image_base64: Optional[str] = None

class IndustrialAgentRequest(BaseAgentRequest):
    machine_id: Optional[str] = None
    
class ResidentialAgentRequest(BaseAgentRequest):
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
