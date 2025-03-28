from abc import ABC, abstractmethod
from fastapi import Response
from app.schemas.users import ProfileUpdate
from fastapi import UploadFile, File
from typing import List

class IUserService(ABC):
    @abstractmethod
    async def update_profile(self, profile_data: ProfileUpdate, profile_picture: UploadFile = File(...), additional_pictures: List[UploadFile] = File([])):
        pass
    @abstractmethod
    async def close_scoped_session():
        pass