from fastapi import FastAPI, HTTPException, status, UploadFile, File, Depends, APIRouter 
from fastapi.security import OAuth2PasswordRequestForm
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from pydantic import BaseModel
from pathlib import Path
from datetime import timedelta
from typing import cast
from database import get_db_connection, init_db
from auth import create_access_token, get_current_admin

app = FastAPI()
init_db()
# bcryptはバイト数制約があるためargon2採用
ph = PasswordHasher()

class User(BaseModel):
    username: str
    is_admin: bool
    password: str

@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello Retrieval-Augmented Generation App"}

@app.post("/register", status_code=status.HTTP_201_CREATED)
def post_register(user: User) -> dict[str, str | bool]:
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 登録済みか確認するSQL
            check_sql: str = "SELECT username FROM users WHERE username = %s"
            cursor.execute(check_sql, (user.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="username already exists")
            
            hashed_pwd: str = ph.hash(user.password)
            sql: str = "INSERT INTO users (username, is_admin, hashed_password) VALUES (%s, %s, %s)"
            cursor.execute(sql, (user.username, user.is_admin, hashed_pwd))
            connection.commit()
        return {"message": "register success", "username": user.username, "is_admin": user.is_admin}
    finally:
        connection.close()

@app.post("/login", status_code=status.HTTP_200_OK)
def post_login(form: OAuth2PasswordRequestForm = Depends()) -> dict[str, str | int | bool]:
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql: str = "SELECT user_id, is_admin, hashed_password FROM users WHERE username = %s"
            cursor.execute(sql, (form.username,))
            result: dict[str, int | bool | str] | None = cursor.fetchone()

            if not result:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid userId or password")
            
            # result["hashed_password"]がNoneのとき500 Internal Server Error
            hashed_password = cast(str, result["hashed_password"])
            
            try:
                ph.verify(hashed_password, form.password)
            except VerifyMismatchError:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid userId or password")

            token: str = create_access_token({"user_id": int(result["user_id"]), "is_admin": bool(result["is_admin"])}, timedelta(minutes=60))
        
        return {
            "access_token": token,
            "token_type": "bearer", 
            "user_id": result['user_id'], 
            "is_admin": bool(result["is_admin"]), 
            "username": form.username
            }
    finally:
        connection.close()

admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin)]
)

ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx", ".txt", ".md"}
UPLOAD_DIR: Path = Path("./storage/upload/")
@admin_router.post("/upload/", status_code=status.HTTP_200_OK)
async def upload_file(file: UploadFile = File(...), current_admin: dict[str, int | bool] = Depends(get_current_admin)):
    if file.filename is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file is not founded")

    # ディレクトリ作成
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # 拡張子チェック
    ext: str = Path(file.filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Extention {ext} is not allowed. Only {", ".join(ALLOWED_EXTENSIONS)} is permitted"
        )

    file_path: Path = UPLOAD_DIR / file.filename
    
    # ファイル保存
    try:
        contents: bytes = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=str(e))
    finally:
        await file.close()
    
    # DBにメタデータ保存
    user_id: int = current_admin["user_id"]
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql: str = "INSERT INTO docs (user_id, dir_path, filename) VALUES (%s, %s, %s)"
            cursor.execute(sql, (user_id, str(UPLOAD_DIR), file.filename))
            connection.commit()
    finally:
        connection.close()

    return {"messege": "upload success", "fileName": file.filename}

app.include_router(admin_router)