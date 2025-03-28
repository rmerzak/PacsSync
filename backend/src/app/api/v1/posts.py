import fastapi

from fastapi import Depends, File, UploadFile, HTTPException
from app.core.security import JWTBearer
from app.core.config import settings
import cloudinary
import cloudinary.uploader
cloudinary.config(
    cloud_name = settings.CLOUDINARY_CLOUD_NAME,
    api_key = settings.CLOUDINARY_API_KEY,
    api_secret= settings.CLOUDINARY_API_SECRET
)

router = fastapi.APIRouter(tags=["posts"],prefix="/posts")





@router.get("/posts")
async def get_posts():
    return {"data": "posts"}


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    # Check if the uploaded file is an image
    allowed_formats = ["image/jpeg", "image/png", "image/gif"]
    if file.content_type not in allowed_formats:
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    try:
        # Upload the file to Cloudinary
        result = cloudinary.uploader.upload(file.file)
        
        # Return the Cloudinary URL of the uploaded image
        return {
            "message": "Image uploaded successfully",
            "url": result["secure_url"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))