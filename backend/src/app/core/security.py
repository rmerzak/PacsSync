import bcrypt

from .config import settings

from datetime import datetime, timedelta, timezone, UTC
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import jwt
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Any
from fastapi import HTTPException, Request
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM


def get_password_hash(password: str) -> str:
    hashed_password: str = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    return hashed_password


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    correct_password: bool = bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    return correct_password

async def send_email(email, body, subject):
    sender_email = f"{settings.EMAIL_SENDER}"
    smtp_host = f"{settings.SMTP_HOST}"
    smtp_port = 587
    smtp_username = f"{settings.SMTP_USERNAME}"
    smtp_password = f"{settings.SMTP_PASSWORD}"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = subject
    message.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, email, message.as_string())
    except Exception as e:
        print(f"Failed to send verification email: {str(e)}")

async def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.exceptions.InvalidTokenError as e:
        return None

def generate_email_verification_token(email: str, expires_delta: timedelta | None = None)-> str:
    if expires_delta:
        expire = datetime.now(UTC).replace(tzinfo=None) + expires_delta
    else:
        expire = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
    to_encode = {"sub": email}
    to_encode.update({"exp": expire, "utility": "EMAIL_VERIFICATION"})

    encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def createAccessToken(data: dict[str:Any], tokenType :str ,expireDate: timedelta | None = None) -> str:
    to_encode = data.copy()
    if (expireDate):
        expire = datetime.now(UTC).replace(tzinfo=None) + expireDate
    else:
        if tokenType == "REFRESH_TOKEN":
            expireDate = timedelta(days = settings.REFRESH_TOKEN_EXPIRE_DAYS)
        elif tokenType == "EMAIL_VERIFICATION":
            expireDate = timedelta(hours = settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
        expire = datetime.now(UTC).replace(tzinfo=None) + expireDate
    to_encode.update({"exp":expire})

    encoded_jwt : str = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    
    return encoded_jwt


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(status_code=403, detail="Invalid token or expired token.")
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")
    def verify_jwt(self, jwt_token: str):
        is_token_valid: bool = False
        try:
            payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=403, detail="Token has expired")
        except jwt.JWTError:
            raise HTTPException(status_code=403, detail="Invalid token")
        if payload:
            is_token_valid = True
        return is_token_valid