from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status

load_dotenv()
SECRET_KEY: str =os.getenv("SECRET_KEY")
ALGORITHM: str =os.getenv("ALGORITHM")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# dataは{"user_id":, "is_admin":}
def create_access_token(data: dict[str, int | bool], expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 現在のユーザーを判別する関数
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, int | bool]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="can't validate credentials")

def get_current_admin(current_user: dict[str, int | bool] = Depends(get_current_user)) -> dict[str, int | bool]:
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="need an admin permission"
        )
    return current_user