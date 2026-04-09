from fastapi import FastAPI, HTTPException, status, UploadFile, File
from passlib.context import CryptContext
from pydantic import BaseModel
from pathlib import Path
from database import get_db_connection, init_db
from auth import create_access_token

app = FastAPI()
init_db()
# bcryptはバイト数制約があるためargon2採用
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto") 

class User(BaseModel):
    username: str
    is_admin: bool
    password: str

@app.get("/")
def read_root():
    return {"message": "Hello Retrieval-Augmented Generation App"}

@app.post("/register", status_code=status.HTTP_201_CREATED)
def post_register(user: User):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 登録済みか確認するSQL
            check_sql = "SELECT username FROM users WHERE username = %s"
            cursor.execute(check_sql, (user.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="username already exists")
            hashed_pwd = pwd_context.hash(user.password)
            sql = "INSERT INTO users (username, is_admin, hashed_password) VALUES (%s, %s, %s)"
            cursor.execute(sql, (user.username, user.is_admin, hashed_pwd))
            connection.commit()
        return {"message": "register success", "username": user.username, "is_admin": user.is_admin}
    finally:
        connection.close()

@app.post("/login", status_code=status.HTTP_200_OK)
def post_login(user: User):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT user_id, is_admin, hashed_password FROM users WHERE username = %s"
            cursor.execute(sql, (user.username,))
            result = cursor.fetchone()
            if not result or not pwd_context.verify(user.password, result['hashed_password']):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid userId or password")
            token = create_access_token({"user_id": result["user_id"], "is_admin": bool(result["is_admin"])})
        return {"message": "Login success", "access_token": token, "token_type": "bearer", "user_id": result['user_id'], "is_admin": bool(result["is_admin"]), "username": user.username}
    finally:
        connection.close()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
UPLOAD_DIR = "./storage/upload/"
@app.post("/upload/", status_code=status.HTTP_200_OK)
async def upload_file(user_id: int, file: UploadFile = File(...)):
    # ディレクトリ作成
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    # 拡張子チェック
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Extention {ext} is not allowed. Only {', '.join(ALLOWED_EXTENSIONS)} is permitted"
        )

    file_path = Path(UPLOAD_DIR) / file.filename

    # ファイル保存
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"{str(e)}")
    finally:
        await file.close()
    # DBにメタデータ保存
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO docs (user_id, dir_path, filename) VALUES (%s, %s, %s)"
            cursor.execute(sql, (user_id, UPLOAD_DIR, file.filename))
            connection.commit()
    finally:
        connection.close()

    return {"messege": "upload success", "fileName": file.filename}