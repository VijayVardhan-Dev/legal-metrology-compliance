from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import AuthCredentials, AuthResponse, AuthUserResponse, RegisterRequest


router = APIRouter()


def user_response(user: User) -> AuthUserResponse:
	return AuthUserResponse(
		id=user.id,
		email=user.email,
		role=user.role,
		is_active=user.is_active,
		created_at=user.created_at,
	)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
	existing = db.query(User).filter(User.email == payload.email).first()
	if existing:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="An account with this email already exists",
		)

	user = User(
		username=payload.email,
		email=payload.email,
		hashed_password=hash_password(payload.password),
		role="inspector",
		is_active=True,
	)
	db.add(user)
	db.commit()
	db.refresh(user)
	return AuthResponse(user=user_response(user), message="Account created successfully")


@router.post("/login", response_model=AuthResponse)
def login(payload: AuthCredentials, db: Session = Depends(get_db)):
	user = db.query(User).filter(User.email == payload.email).first()
	if not user or not user.is_active or not verify_password(payload.password, user.hashed_password):
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid email or password",
		)
	return AuthResponse(user=user_response(user), message="Login successful")
