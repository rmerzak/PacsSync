from app.services.base_service import BaseService
from app.repository.user_repository import UserRepository
from app.schemas.users import UserLogin
from app.core.security import createAccessToken, verify_password, get_password_hash,verify_token
from app.core.config import settings
from app.core.responce import error_response, success_response
from fastapi import Response, status
from datetime import timedelta
from app.schemas.users import UserCreateInternal
from app.core.security import generate_email_verification_token, send_email
from app.services.auth_interface import IAuthService
front_url_prefix = settings.FRONT_URL
template_env = settings.EMAIL_TEMPLATES_ENV
verify_template = settings.EMAIL_TEMPLATES["verify_email"]

class AuthServiceImp(BaseService, IAuthService):
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        super().__init__(user_repository)
    async def close_scoped_session(self):
        await self.user_repository.close_session()

    async def login(self, user: UserLogin, response: Response):
        existing_user = await self.user_repository.get_user_by_username(user.username)
        if not existing_user:
            return error_response("Invalid credentials", "Invalid username or password", status_code=400)
        if not await verify_password(user.password, existing_user["password"]):
            return error_response("Invalid credentials", "Invalid username or password", status_code=400)
        
        access_token = await createAccessToken(
            {"sub": existing_user['email'], "utility": "ACCESS_TOKEN"}, 
            "ACCESS_TOKEN", 
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        refresh_token = await createAccessToken(
            {"sub": existing_user['email'], "utility": "REFRESH_TOKEN"}, 
            "REFRESH_TOKEN"
        )
        
        max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        response.set_cookie(
            key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="Lax", max_age=max_age
        )

        return success_response({
            "message": "Login successful", 
            "data": {"access_token": access_token, "token_type": "bearer"}
        }, status_code=200)

    async def register(self, user):
        existing_user = await self.user_repository.get_user_by_username(user.username)
        if existing_user:
            return error_response("User already exists", "User with this username already exists", status_code=400)
        existing_email = await self.user_repository.get_user_by_email(user.email)
        if existing_email:
            return error_response("Email already exists", "User with this email already exists", status_code=400)
        user_internal_dict = user.model_dump()
        user_internal_dict["password"] = get_password_hash(user_internal_dict["password"])
        user_internal_dict["is_verified"] = False

        user_internal = UserCreateInternal(**user_internal_dict)
        created_user = await self.user_repository.create_user_internal(user_internal)
        created_user_dict = dict(created_user)  # Convert Record to dict

        verification_token = generate_email_verification_token(user_internal.email)
        template = template_env.get_template(verify_template)
        verification_link = f"{front_url_prefix}/verifyEmail?token={verification_token}"
        body = template.render(
            username=user_internal.username,
            email=user_internal.email,
            verification_link=verification_link,
        )
    
        await send_email(email=user_internal.email, body=body, subject="Email Verification")

        return success_response({"message": "User created successfully", "data": created_user_dict}, status_code=status.HTTP_201_CREATED)

    async def resend_email_verification(self, email: str):
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            return error_response("User not found", "User with this email not found", status_code=status.HTTP_404_NOT_FOUND)
        verification_token = generate_email_verification_token(user["email"])
        template = template_env.get_template(verify_template)
        verification_link = f"{front_url_prefix}/verifyEmail?token={verification_token}"
        body = template.render(
            username=user["username"],
            email=user["email"],
            verification_link=verification_link,
        )
        await send_email(email=user["email"], body=body, subject="Email Verification")
        return success_response({"message": "Verification email sent"}, status_code=status.HTTP_200_OK)

    async def verify_email(self, token: str, response: Response):
        payload = await verify_token(token)
        if not payload or payload["utility"] != "EMAIL_VERIFICATION":
            return error_response("Invalid token", "Invalid or expired token", status_code=status.HTTP_400_BAD_REQUEST)
        email = payload["sub"]
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            return error_response("User not found", "User with this email not found", status_code=status.HTTP_404_NOT_FOUND)
        if user["is_verified"]:
            return error_response("Email already verified", "Email already verified", status_code=status.HTTP_400_BAD_REQUEST)
        
        await self.user_repository.update_user_verification(email)

        accessExpireToken = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        accessToken = await createAccessToken({"sub": user['email'], "utility": "ACCESS_TOKEN"}, "ACCESS_TOKEN", accessExpireToken)
        refreshToken = await createAccessToken({"sub": user['email'], "utility": "REFRESH_TOKEN"}, "REFRESH_TOKEN")
        max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        response.set_cookie(
            key="refresh_token", value=refreshToken, httponly=True, secure=True, samesite="Lax", max_age=max_age
        )

        return success_response({"message": "Email verified successfully", "data": {"access_token": accessToken, "token_type": "bearer"}}, status_code=status.HTTP_200_OK)

    async def request_password_reset(self, email: str):
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            return error_response("User not found", "User with this email not found", status_code=status.HTTP_404_NOT_FOUND)
        reset_token = await createAccessToken(
            {"sub": user['email'], "utility": "PASSWORD_RESET"}, 
            "ACCESS_TOKEN", 
            timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        )
        template = template_env.get_template(settings.EMAIL_TEMPLATES["reset_password"])
        reset_link = f"{front_url_prefix}/resetPassword?token={reset_token}"
        body = template.render(
            username=user["username"],
            email=user["email"],
            reset_link=reset_link,
        )
        await send_email(email=user["email"], body=body, subject="Password Reset")
        return success_response({"message": "Password reset email sent"}, status_code=status.HTTP_200_OK)

    async def verify_token(self, token: str):
        payload = await verify_token(token)
        if not payload or payload["utility"] != token.utility:
            return error_response("Invalid token", "Invalid or expired token", status_code=status.HTTP_400_BAD_REQUEST)
        return success_response({"message": "Token verified successfully", "data": payload}, status_code=status.HTTP_200_OK)
