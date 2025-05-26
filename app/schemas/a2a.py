from pydantic import BaseModel
from typing import Dict, Any, Optional, List


class A2ATaskContext(BaseModel):
    user_id: Optional[str] = None
    # Otros campos de contexto que puedan ser necesarios
    # Ejemplo: session_id: Optional[str] = None


class A2ATaskRequest(BaseModel):
    input: str
    context: Optional[A2ATaskContext] = None


class A2AProcessRequest(BaseModel):
    user_input: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    kwargs: Optional[Dict[str, Any]] = None


class A2AResponse(BaseModel):
    response: str
    artifacts: Optional[List[Any]] = None
