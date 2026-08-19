import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import create_session_token
from app.db import get_db
from app.services import sessions
from app.services.appleAuth import verify_apple_token
from app.services.users import upsert_apple_user

router = APIRouter(prefix="/auth", tags=["auth"])


class AppleSignInRequest(BaseModel):
    identity_token: str
    # Apple gives the name to the APP (not the token) on first sign-in only,
    # so the client passes it along here if it has it.
    full_name: str | None = None


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/apple", response_model=TokenPairResponse)
def apple_sign_in(body: AppleSignInRequest, db: Session = Depends(get_db)):
    try:
        claims = verify_apple_token(body.identity_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWKClientError:
        raise HTTPException(status_code=503, detail="Could not reach Apple, try again")

    user = upsert_apple_user(
        db,
        apple_sub=claims["sub"],
        email=claims.get("email"),
        full_name=body.full_name,
    )

    return TokenPairResponse(
        access_token=create_session_token(user.id),
        refresh_token=sessions.create_session(user.id),
    )


@router.post("/refresh", response_model=TokenPairResponse)
def refresh(body: RefreshRequest):
    rotated = sessions.rotate_session(body.refresh_token)
    if rotated is None:
        raise HTTPException(status_code=401, detail="Session expired, sign in again")
    user_id, new_refresh_token = rotated
    return TokenPairResponse(
        access_token=create_session_token(user_id),
        refresh_token=new_refresh_token,
    )


@router.post("/logout", status_code=204)
def logout(body: RefreshRequest):
    sessions.revoke_session(body.refresh_token)
