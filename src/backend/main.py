from fastapi import FastAPI, HTTPException, status, UploadFile, File, Depends, APIRouter, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from pydantic import BaseModel
from pymysql.cursors import DictCursor
from pathlib import Path
from datetime import timedelta
import aiofiles
from typing import cast
from database import get_db_connection, init_db
from auth import create_access_token, get_current_admin
from rag import run_ingest_pipeline, run_query_pipeline


app = FastAPI()
init_db()
# bcryptはバイト数制約があるためargon2採用
ph = PasswordHasher()

class User(BaseModel):
    username: str
    password: str

@app.get("/api/")
def read_root() -> dict[str, str]:
    return {"message": "Hello Retrieval-Augmented Generation App"}

@app.post("/api/register", status_code=status.HTTP_201_CREATED)
def post_register(user: User) -> dict[str, str | bool]:
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 登録済みか確認するSQL
            cursor.execute("SELECT username FROM users WHERE username = %s", (user.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="username already exists")

            hashed_pwd: str = ph.hash(user.password)
            cursor.execute("INSERT INTO users (username, hashed_password) VALUES (%s, %s)", (user.username, hashed_pwd))
            connection.commit()
        return {"message": "register success", "username": user.username}
    finally:
        connection.close()

@app.post("/api/login", status_code=status.HTTP_200_OK)
def post_login(form: OAuth2PasswordRequestForm = Depends()) -> dict[str, str | int | bool]:
    connection = get_db_connection()
    try:
        with connection.cursor(DictCursor) as cursor:
            cursor.execute("SELECT user_id, is_admin, hashed_password FROM users WHERE username = %s", (form.username,))
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

@app.post("/api/query", status_code=status.HTTP_200_OK)
async def ask_question(query: str, doc_id: int | None =None):

    if not query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query text cannot be empty"
            )
    try:
        answer = run_query_pipeline(query, doc_id)
        return {
            "query": query,
            "answer": answer,
            "doc_id": doc_id
        }
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during the RAG process."
        )

ALLOWED_EXTENSIONS: set[str] = {".pdf", ".txt", ".md"}
UPLOAD_DIR: Path = Path("./storage/upload/")
@admin_router.post("/upload/", status_code=status.HTTP_200_OK)
async def upload_file(file: UploadFile = File(...),
                      current_admin: dict[str, int | bool] = Depends(get_current_admin)):
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
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(contents)
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
            cursor.execute("INSERT INTO docs (user_id, dir_path, filename) VALUES (%s, %s, %s)", (user_id, str(UPLOAD_DIR), file.filename))
            connection.commit()
    finally:
        connection.close()

    return {"messege": "upload success", "fileName": file.filename}

@admin_router.post("/api/documents/{doc_id}/ingest", status_code=status.HTTP_200_OK)
async def ingest_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
):

    connection = get_db_connection()
    try:
        with connection.cursor(DictCursor) as cursor:
            cursor.execute("SELECT user_id, dir_path, filename, created_at FROM docs WHERE doc_id = %s", (doc_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Document is not found")

            file_path = Path(row["dir_path"]) / row["filename"]
            cursor.execute("UPDATE docs SET status = 'processing' WHERE doc_id = %s", (doc_id,))
    finally:
        connection.close()

    background_tasks.add_task(run_ingest_pipeline, doc_id, file_path, row["user_id"], row["created_at"])
    return {"messege": "Ingestion started", "doc_id": doc_id}

app.include_router(admin_router)