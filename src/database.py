import pymysql
import os
import time
from dotenv import load_dotenv
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

load_dotenv()

def get_db_connection() -> Connection:
    return pymysql.connect(
        host="rdb",
        user="root",
        password=os.getenv("MYSQL_ROOT_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        port=3306,
        # 取得結果を辞書で受け取るresult = {"id": 1, "name": "shimizu"}
        cursorclass=DictCursor,
        client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS 
    )

def init_db() -> None:
    with open("init.sql", "r") as f:
        sql: str = f.read()

    connection = None
    for i in range(10):
        try:
            connection: Connection = get_db_connection()
            break
        except pymysql.err.OperationalError as e:
            time.sleep(2)

    connection  = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            connection.commit()
    finally:
        connection.close()