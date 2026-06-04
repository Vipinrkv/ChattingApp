# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\routes\user_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import get_current_user as get_current_user_dep
from app.core.firebase import get_firebase_uid
from app.database.connection import get_db_session
from app.models.user import User
from app.services.user_service import UserService, UsernameAlreadyTakenError
from app.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    firebase_uid: str = Depends(get_firebase_uid),
    session: AsyncSession = Depends(get_db_session),
):
    """Register a new user with Firebase UID"""
    result = await UserService.create_user_if_not_exists(session, firebase_uid, user_data)
    if not result.success:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.error['message'])
    return result.data


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(get_current_user_dep),
):
    """Get current user profile"""
    return current_user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Update user profile"""
    if str(current_user.id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update another user",
        )

    user = await UserService.update_user(session, user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.get("", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """List all other registered users for chat discovery"""
    users = await UserService.get_all_users(session, str(current_user.id))
    return users


@router.get("/search", response_model=list[UserResponse])
async def search_users(
    q: str,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    return await UserService.search_users(session, q, str(current_user.id), limit=50)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Get user by ID"""
    user = await UserService.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
