from fastapi import FastAPI, HTTPException, status, UploadFile, File, Depends, APIRouter, BackgroundTasks, Response
from fastapi.security import OAuth2PasswordRequestForm
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from pydantic import BaseModel
from pymysql.cursors import DictCursor
from pathlib import Path
from datetime import timedelta
from contextlib import asynccontextmanager
import aiofiles
import os
from dotenv import load_dotenv
from typing import cast
from database import get_db_connection, init_db
from auth import create_access_token, get_current_admin
from rag import run_ingest_pipeline, run_query_pipeline

# bcryptはバイト数制約があるためargon2採用
ph = PasswordHasher()

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()

        default_admin_user = os.getenv("INITIAL_ADMIN_USERNAME")
        default_admin_pass = os.getenv("INITIAL_ADMIN_PASSWORD")

        if default_admin_user and default_admin_pass:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT username FROM users WHERE username = %s", (default_admin_user,))
                    if not cursor.fetchone():
                        hashed_pwd = ph.hash(default_admin_pass)
                        cursor.execute(
                            "INSERT INTO users (username, hashed_password, is_admin) VALUES (%s, %s, True)",
                            (default_admin_user, hashed_pwd)
                        )
                        connection.commit()
            finally:
                connection.close()
    except Exception as e:
        print(e)
    yield

app = FastAPI(lifespan=lifespan)
router = APIRouter()
admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin)]
)

class User(BaseModel):
    username: str
    password: str

class QueryRequest(BaseModel):
    query: str
    doc_id: int | None = None

@router.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello Retrieval-Augmented Generation App"}

@router.post("/register", status_code=status.HTTP_201_CREATED)
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

@router.post("/login", status_code=status.HTTP_200_OK)
def post_login(response: Response, form: OAuth2PasswordRequestForm = Depends()) -> dict[str, str | int | bool]:
    connection = get_db_connection()
    try:
        with connection.cursor(DictCursor) as cursor:
            cursor.execute("SELECT user_id, is_admin, hashed_password FROM users WHERE username = %s", (form.username,))
            result: dict[str, int | bool | str] | None = cursor.fetchone()

            if not result:
                print("User not found in DB")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid userId or password")

            # result["hashed_password"]がNoneのとき500 Internal Server Error
            hashed_password = cast(str, result["hashed_password"])
            try:
                ph.verify(hashed_password, form.password)
            except VerifyMismatchError:
                print(f"Password mismatch for user: {form.username}")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid userId or password")

            token: str = create_access_token({"user_id": int(result["user_id"]), "is_admin": bool(result["is_admin"])}, timedelta(minutes=60))

            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,   # TSからアクセス不可
                max_age=3600,    # 有効期限(秒)
                samesite="lax",  # CSRF対策
                # secure=True      # HTTPS環境のみ送信
            )

        return {"message": "login success"}
    finally:
        connection.close()

@router.post("/query", status_code=status.HTTP_200_OK)
async def ask_question(request: QueryRequest):

    if not request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query text cannot be empty"
            )
    try:
        answer = run_query_pipeline(request.query, request.doc_id)
        return {
            "query": request.query,
            "answer": answer,
            "doc_id": request.doc_id
        }
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during the RAG process."
        )

ALLOWED_EXTENSIONS: set[str] = {".pdf", ".txt", ".md"}
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR: Path = PROJECT_ROOT / "storage" / "upload"

@admin_router.post("/upload/", status_code=status.HTTP_200_OK)
async def upload_file(file: UploadFile = File(...),
                      current_admin: dict[str, int | bool] = Depends(get_current_admin)):
    # filenameが空の場合、FastAPIが422エラーを返すので不要
    # if file.filename is None:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file is not founded")

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

    return {"message": "upload success", "fileName": file.filename}

@admin_router.get("/documents", status_code=status.HTTP_200_OK)
async def get_documents():
    connection = get_db_connection()
    try:
        with connection.cursor(DictCursor) as cursor:
            cursor.execute("SELECT doc_id, filename, status, created_at FROM docs WHERE delete_flg = FALSE")
            rows = cursor.fetchall()
            return rows
    finally:
        connection.close()

@admin_router.post("/documents/{doc_id}/ingest", status_code=status.HTTP_200_OK)
async def ingest_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
) -> dict[str, str | int]:

    connection = get_db_connection()
    try:
        with connection.cursor(DictCursor) as cursor:
            cursor.execute("SELECT user_id, dir_path, filename, status, created_at FROM docs WHERE doc_id = %s", (doc_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Document is not found")

            if row["status"] in ["processing", "injested"]:
                return {"message": f"Document {doc_id} is already {row['status']}", "doc_id": doc_id}

            file_path = Path(row["dir_path"]) / row["filename"]
            cursor.execute("UPDATE docs SET status = 'processing' WHERE doc_id = %s", (doc_id,))
    finally:
        connection.close()

    background_tasks.add_task(run_ingest_pipeline, doc_id, file_path, row["user_id"], row["created_at"])
    return {"message": "Ingestion started", "doc_id": doc_id}

app.include_router(admin_router, prefix="/api")
app.include_router(router, prefix="/api")