import fastapi
from app.schemas.users import UserCreate, UserCreateInternal
from fastapi import Request, Response, status, Depends, HTTPException, File, UploadFile
from app.core.security import get_password_hash, generate_email_verification_token, send_email, verify_token, createAccessToken
from app.core.config import settings
from datetime import timedelta
from app.core.security import JWTBearer
from app.core.responce import error_response, success_response
from app.schemas.users import ProfileUpdate
from typing import List
from app.services.user_interface import IUserService
from app.core.container import Container
from dependency_injector.wiring import Provide
from app.core.middleware import inject
template_env = settings.EMAIL_TEMPLATES_ENV
verify_template = settings.EMAIL_TEMPLATES["verify_email"]
router = fastapi.APIRouter(tags=["users"], prefix="/users")


@router.put("/update-profile")
@inject
async def update_profile( 
    profile_data: ProfileUpdate = Depends(),
    profile_picture: UploadFile = File(...),
    additional_pictures: List[UploadFile] = File([]),
    service: IUserService = Depends(Provide[Container.user_service]),
    # current_user: User = Depends(get_current_user)
    ):
    #must fix the interests and pass te email from current_user
    if profile_data.interests:
        interests_list = [i.strip() for i in profile_data.interests.split(",")]
    else:
        interests_list = []
    result = await service.update_profile(profile_data, profile_picture, additional_pictures)
    return result