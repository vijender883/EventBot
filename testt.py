import pymysql

try:
    conn = pymysql.connect(
        host="testdb.cz60eacw4gt2.ap-south-1.rds.amazonaws.com",
        user="admin",
        password="AlphaBeta1212",
        database="mysql",
        port=3306,
        connect_timeout=10
    )
    print("✅ Connected successfully!")
    conn.close()
except Exception as e:
    print("❌ Connection failed:", e)
