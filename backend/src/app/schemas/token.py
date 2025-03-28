
from pydantic import BaseModel


class ValidateToken(BaseModel):
    token: str
    utility: str