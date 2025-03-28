from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from datetime import datetime
from enum import Enum
from pydantic import validator
class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class SexualPreference(str, Enum):
    MALE = "male"
    FEMALE = "female"
    BOTH = "both"

class User(BaseModel):
    id: Optional[UUID] = Field(default=None)
    username: str = Field(..., max_length=255)
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = Field(None, unique=True, max_length=255)
    password: Optional[str] = Field(None, max_length=255)
    gender: Optional[str] = Field(None, max_length=255)
    sexual_preferences: Optional[str]
    interests: Optional[List[str]]
    pictures: Optional[str]
    fame_rating: Optional[float]
    location: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float]
    address: Optional[str] = Field(None, max_length=255)
    age: Optional[int]
    bio: Optional[str]
    is_verified: bool = Field(default=False)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    reset_password_expires: Optional[datetime]
    reset_password_token: Optional[str] = Field(default='')

class UserCreate(BaseModel):
    username: str = Field(..., max_length=255)
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = Field(None, unique=True, max_length=255)
    password: Optional[str] = Field(None, max_length=255)

class UserCreateInternal(UserCreate):
    pass

class UserLogin(BaseModel):
    username: str
    password: str

class ProfileUpdate(BaseModel):
    gender: Optional[Gender]
    sexual_preferences: Optional[SexualPreference]
    bio: Optional[str]
    interests: Optional[str]
    email: str