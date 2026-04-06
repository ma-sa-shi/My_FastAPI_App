from fastapi import FastAPI, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel
import pymysql
import os

app = FastAPI()

# 計算に時間がかかるbcryt採用、deprecatedなアルゴリズム自動更新
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") 

def get_db_connection():
    return pymysql.connect(
        host="rdb",
        user="root",
        password=os.getenv("MYSQL_ROOT_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        port=3306,
        # 取得結果を辞書で受け取るresult = {"id": 1, "name": "tanaka"}
        cursorclass=pymysql.cursors.DictCursor 
    )

class User(BaseModel):
    userId: str
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
            check_sql = "SELECT userId FROM users WHERE userId = %s"
            cursor.execute(check_sql, (user.userId,))
            if cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
            hashed_pwd = pwd_context.hash(user.password)
            sql = "INSERT INTO users (userId, password) VALUES (%s, %s)"
            cursor.execute(sql, (user.userId, hashed_pwd))
            connection.commit()
        return {"message": "register success", "user": user.userId}
    finally:
        connection.close()

@app.post("/login", status_code=status.HTTP_200_OK)
def post_login(user: User):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT password FROM users WHERE userId = %s"
            cursor.execute(sql, (user.userId,))
            result = cursor.fetchone()
            if not result or not pwd_context.verify(user.password, result['password']):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid userId or password")
        return {"message": "Login success",  "user": user.userId}
    finally:
        connection.close()