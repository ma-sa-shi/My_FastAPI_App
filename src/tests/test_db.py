# root@ac429ecbc2df:/app# python3 -m tests.test_db
# {'doc_id': 1, 'user_id': 1, 'dir_path': 'storage/upload',
# 'filename': 'test.txt', 'status': 'completed',
# 'extracted_text': 'こんにちは、ITエンジニアです。\n今はテストを実施中です。',
# 'created_at': datetime.datetime(2026, 4, 17, 16, 29, 38), 'delete_flg': 0}
from database import get_db_connection
from pymysql.cursors import DictCursor

conn = get_db_connection()
try:
    with conn.cursor(DictCursor) as cursor:
        cursor.execute("SELECT * FROM docs")
        for row in cursor.fetchall():
            print(row)
        cursor.execute("SELECT @@global.time_zone, @@session.time_zone, NOW()")
        row = cursor.fetchone()
        print(row)
finally:
    conn.close()

