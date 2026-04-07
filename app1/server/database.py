import pymysql
import os
import time
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return pymysql.connect(
        host="rdb",
        user="root",
        password=os.getenv("MYSQL_ROOT_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        port=3306,
        # 取得結果を辞書で受け取るresult = {"id": 1, "name": "shimizu"}
        cursorclass=pymysql.cursors.DictCursor,
        client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS 
    )

def init_db():
    with open("init.sql", "r") as f:
        sql = f.read()

    connection = None
    for i in range(10):
        try:
            connection = get_db_connection()
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