from fastapi import APIRouter

from .users import router as users_router
from .authentication import router as auth_router
from .posts import router as posts_router
from .dicom_net import router as dicom_net_router
router = APIRouter(prefix="/v1")

router.include_router(users_router)
router.include_router(auth_router)
router.include_router(posts_router)
router.include_router(dicom_net_router)
