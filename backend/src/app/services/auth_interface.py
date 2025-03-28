from abc import ABC, abstractmethod
from app.schemas.users import UserCreate, UserLogin
from fastapi import Response

class IAuthService(ABC):
    @abstractmethod
    async def login(self, user: UserLogin, response: Response):
        pass

    @abstractmethod
    async def register(self, user: UserCreate):
        pass

    @abstractmethod
    async def resend_email_verification(self, email: str):
        pass

    @abstractmethod
    async def verify_email(self, token: str, response: Response):
        pass

    @abstractmethod
    async def request_password_reset(self, email: str):
        pass

    @abstractmethod
    async def verify_token(self, token: str):
        pass
    @abstractmethod
    async def close_scoped_session():
        pass