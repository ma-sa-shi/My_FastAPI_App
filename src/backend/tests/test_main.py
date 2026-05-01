import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from pathlib import Path
from main import app, User
from auth import get_current_admin


@pytest.fixture(autouse=True)
def mock_google_genai(mocker):
    return mocker.patch("rag.genai.Client")


client = TestClient(app)


# GET /api/のテスト
class TestRootEndpoint:
    def test_read_root_success(self):
        response = client.get("/api/")
        assert response.status_code == 200
        assert response.json() == {
            "message": "Hello Retrieval-Augmented Generation App"
        }


# POST /api/registerのテスト
class TestRegisterEndpoint:
    # 正常系:ユーザー登録テスト
    # main.get_db_connectionをmockに替える
    def test_register_success(self, mocker: MockerFixture):
        mock_get_db = mocker.patch("main.get_db_connection")
        mock_connection = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()

        mock_get_db.return_value = mock_connection
        # __enter__はwith conn.cursor() as cursor:で呼ばれるメソッド
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        user_data = {"username": "testuser", "password": "testpassword"}
        response = client.post("/api/register", json=user_data)
        assert response.status_code == 201
        assert response.json()["message"] == "register success"
        assert response.json()["username"] == "testuser"

        # executeの回数が2回の場合、SELECT、INSERTが呼ばれている
        assert mock_cursor.execute.call_count == 2
        mock_connection.commit.assert_called_once()

    # 異常系:usernameがDBに登録済みの場合のテスト
    def test_register_user_exists(self, mocker: MockerFixture):
        mock_get_db = mocker.patch("main.get_db_connection")
        mock_connection = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()

        mock_get_db.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "username": "testuser"
        }  # ユーザーが既に存在

        user_data = {"username": "testuser", "password": "testpassword"}
        response = client.post("/api/register", json=user_data)

        assert response.status_code == 400
        assert response.json()["detail"] == "username already exists"


# POST /api/loginのテスト
class TestLoginEndpoint:
    # 正常系:ログイン成功テスト
    def test_login_success(self, mocker: MockerFixture):
        mock_get_db = mocker.patch("main.get_db_connection")
        mock_create_token = mocker.patch("main.create_access_token")
        mock_connection = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_get_db.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        from argon2 import PasswordHasher

        ph = PasswordHasher()
        hashed_password = ph.hash("testpassword")

        mock_cursor.fetchone.return_value = {
            "user_id": 1,
            "is_admin": True,
            "hashed_password": hashed_password,
            "username": "testuser",
        }
        mock_create_token.return_value = "test_token"

        response = client.post(
            "/api/login", data={"username": "testuser", "password": "testpassword"}
        )
        assert response.status_code == 200
        assert response.json() == {"message": "login success"}
        assert response.cookies.get("access_token") == "test_token"

    # 異常系:usernameがDBに無い場合のテスト
    def test_login_user_not_found(self, mocker: MockerFixture):
        mock_get_db = mocker.patch("main.get_db_connection")
        mock_connection = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_get_db.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        response = client.post(
            "/api/login",
            data={"username": "non-existent-user", "password": "testpassword"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid userId or password"

    # 異常系:passwordが異なる場合のテスト
    def test_login_wrong_password(self, mocker: MockerFixture):
        mock_get_db = mocker.patch("main.get_db_connection")
        mock_connection = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_get_db.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        from argon2 import PasswordHasher

        ph = PasswordHasher()
        hashed_password = ph.hash("correctpassword")

        mock_cursor.fetchone.return_value = {
            "user_id": 1,
            "is_admin": False,
            "hashed_password": hashed_password,
        }

        response = client.post(
            "/api/login", data={"username": "testuser", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid userId or password"


# POST /api/queryのテスト
class TestQueryEndpoint:
    # 正常系:doc_idありのテスト
    def test_query_success(self, mocker: MockerFixture):
        mock_run_query = mocker.patch(
            "main.run_query_pipeline", return_value="This is the answer"
        )

        response = client.post(
            "/api/query", json={"query": "What is Python?", "doc_id": 1}
        )
        assert response.status_code == 200
        assert response.json()["query"] == "What is Python?"
        assert response.json()["answer"] == "This is the answer"
        assert response.json()["doc_id"] == 1

    # 正常系:doc_id無しのクエリ
    def test_query_without_doc_id(self, mocker: MockerFixture):
        mocker.patch("main.run_query_pipeline", return_value="Answer without doc_id")

        response = client.post(
            "/api/query", json={"query": "General question"}
        )
        assert response.status_code == 200
        assert response.json()["query"] == "General question"
        assert response.json()["answer"] == "Answer without doc_id"
        assert response.json()["doc_id"] is None

    # 異常系:queryが空の場合のテスト
    def test_query_empty_string(self):
        response = client.post("/api/query", json={"query": "   "})
        assert response.status_code == 400
        assert response.json()["detail"] == "Query text cannot be empty"

    # 異常系:run_query_pipeline内のエラー
    def test_query_error_in_pipeline(self, mocker: MockerFixture):
        mocker.patch("main.run_query_pipeline", side_effect=Exception("Pipeline error"))

        response = client.post("/api/query", json={"query": "Some question"})
        assert response.status_code == 500
        assert (
            "unexpected error occurred during the RAG process"
            in response.json()["detail"]
        )


# POST /admin/upload/のテスト
class TestAdminUploadEndpoint:
    # 正常系:アップロードテスト
    def test_upload_file_success(self, mocker: MockerFixture):
        app.dependency_overrides[get_current_admin] = lambda: {
            "user_id": 1,
            "is_admin": True,
        }
        mock_get_db = mocker.patch("main.get_db_connection")
        mock_connection = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_get_db.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_open = mocker.patch("aiofiles.open", create=True)
        mock_file = mocker.AsyncMock()
        mock_open.return_value.__aenter__.return_value = mock_file
        try:
            response = client.post(
                "/api/admin/upload/",
                files={"file": ("test.txt", b"content", "text/plain")},
            )
            assert response.status_code == 200
            assert response.json()["message"] == "upload success"
            assert response.json()["fileName"] == "test.txt"
        finally:
            app.dependency_overrides.clear()

    """ファイル名が無いファイルをアップロードする場合のテスト"""

    def test_upload_file_no_filename(self):
        app.dependency_overrides[get_current_admin] = lambda: {
            "user_id": 1,
            "is_admin": True,
        }
        try:
            response = client.post(
                "/api/admin/upload/", files={"file": ("", b"content", "text/plain")}
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    # 異常系:許可されていない拡張子でアップロードする場合のテスト
    def test_upload_file_invalid_extension(self):
        app.dependency_overrides[get_current_admin] = lambda: {
            "user_id": 1,
            "is_admin": True,
        }
        try:
            response = client.post(
                "/api/admin/upload/",
                files={"file": ("test.exe", b"content", "application/x-msdownload")},
            )
            assert response.status_code == 415
            assert "not allowed" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    # 異常系:is_admin=Falseのユーザがアップロードする場合のテスト
    def test_upload_requires_admin_privilege(self):
        from fastapi import HTTPException

        def mock_admin_error():
            raise HTTPException(status_code=403, detail="need an admin permission")

        app.dependency_overrides[get_current_admin] = mock_admin_error
        try:
            response = client.post(
                "/api/admin/upload/",
                files={"file": ("test.txt", b"content", "text/plain")},
            )
            assert response.status_code == 403
            assert response.json()["detail"] == "need an admin permission"
        finally:
            app.dependency_overrides.clear()


# POST /admin/api/documents/{doc_id}/ingestのテスト
class TestAdminIngestEndpoint:
    # 正常系:ドキュメント取込みテスト
    def test_ingest_document_success(self, mocker: MockerFixture):
        app.dependency_overrides[get_current_admin] = lambda: {
            "user_id": 1,
            "is_admin": True,
        }
        mock_get_db = mocker.patch("main.get_db_connection")
        mock_connection = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_get_db.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "user_id": 1,
            "dir_path": "./storage/upload/",
            "filename": "test.txt",
            "status": "uploaded",  # Add the missing 'status' key
            "created_at": "2026-01-01",
        }
        mock_pipeline = mocker.patch("main.run_ingest_pipeline")
        try:
            response = client.post("/api/admin/documents/1/ingest")
            assert response.status_code == 200
            assert response.json()["message"] == "Ingestion started"
            assert response.json()["doc_id"] == 1
            mock_pipeline.assert_called_once_with(
                1, Path("./storage/upload/test.txt"), 1, "2026-01-01"
            )
        finally:
            app.dependency_overrides.clear()

    # 異常系:DBに無いドキュメントを取込む場合のテスト
    def test_ingest_document_not_found(self, mocker: MockerFixture):
        app.dependency_overrides[get_current_admin] = lambda: {
            "user_id": 1,
            "is_admin": True,
        }
        mock_get_db = mocker.patch("main.get_db_connection")
        mock_connection = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_get_db.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        try:
            response = client.post("/api/admin/documents/999/ingest")
            assert response.status_code == 404
            assert response.json()["detail"] == "Document is not found"
        finally:
            app.dependency_overrides.clear()

    # 異常系:is_admin=Falseのユーザがアップロードする場合のテスト
    def test_ingest_requires_admin_privilege(self):
        from fastapi import HTTPException

        def mock_admin_error():
            raise HTTPException(status_code=403, detail="need an admin permission")

        app.dependency_overrides[get_current_admin] = mock_admin_error
        try:
            response = client.post("/api/admin/documents/1/ingest")
            assert response.status_code == 403
            assert response.json()["detail"] == "need an admin permission"
        finally:
            app.dependency_overrides.clear()


class TestUserModel:
    def test_user_model_valid(self):
        user = User(username="testuser", password="testpassword")
        assert user.username == "testuser"
        assert user.password == "testpassword"

    def test_user_model_json_schema(self):
        user_data = {"username": "testuser", "password": "testpassword"}
        user = User(**user_data)
        assert user.model_dump() == user_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
