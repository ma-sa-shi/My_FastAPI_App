from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
from fastapi import Depends, HTTPException, status, Cookie

load_dotenv()
SECRET_KEY: str =os.getenv("SECRET_KEY", "")
ALGORITHM: str =os.getenv("ALGORITHM", "")

# dataは{"user_id":, "is_admin":}
def create_access_token(data: dict[str, int | bool | datetime], expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 現在のユーザーを判別する関数
def get_current_user(access_token: str | None = Cookie(None)) -> dict[str, int | bool]:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="can't validate credentials")

def get_current_admin(current_user: dict[str, int | bool] = Depends(get_current_user)) -> dict[str, int | bool]:
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="need an admin permission"
        )
    return current_user