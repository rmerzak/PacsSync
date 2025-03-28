import fastapi
from app.schemas.users import UserCreate, UserLogin
from app.schemas.token import ValidateToken
from fastapi import Request, Response, Depends
from app.core.config import settings
from app.core.container import  Container
from dependency_injector.wiring import Provide
from datetime import timedelta
from app.core.middleware import inject
front_url_prefix = settings.FRONT_URL
template_env = settings.EMAIL_TEMPLATES_ENV
verify_template = settings.EMAIL_TEMPLATES["verify_email"]
from app.core.responce import error_response, success_response
from app.core.security import JWTBearer
from app.services.auth_interface import IAuthService

router = fastapi.APIRouter(tags=["auth"], prefix="/auth")



@router.post("/register", status_code=201)
@inject
async def register(request: Request, user: UserCreate, service: IAuthService = Depends(Provide[Container.auth_service])):
    result = await service.register(user)
    return result

@router.post("/login", status_code=201)
@inject
async def login(request: Request,response:Response, user: UserLogin, service: IAuthService = Depends(Provide[Container.auth_service])):
    result = await service.login(user, response)
    return result

@router.post("/resendEmailVerification")
@inject
async def resend_email_verification(request: Request, email: str, service: IAuthService = Depends(Provide[Container.auth_service])):
    result = await service.resend_email_verification(email)
    return result

@router.get("/verifyEmail")
@inject
async def verify_email(response: Response, request: Request, token: str, service: IAuthService = Depends(Provide[Container.auth_service])):
    result = await service.verify_email(token, response)
    return result

@router.post("/requestPasswordReset")
@inject
async def request_password_reset(request: Request, email: str, service: IAuthService = Depends(Provide[Container.auth_service])):
    result = await service.request_password_reset(email)
    return result

@router.post("/resetPassword",dependencies=[Depends(JWTBearer())])
@inject
async def reset_password(request: Request, new_password: str,token:str, service: IAuthService = Depends(Provide[Container.auth_service])):
    result = await service.reset_password(token, new_password)
    return result

@router.post("/verifyToken")
@inject
async def verify_token_api(request: Request, token: ValidateToken, service: IAuthService = Depends(Provide[Container.auth_service])):
    result = await service.verify_token(token)
    return result