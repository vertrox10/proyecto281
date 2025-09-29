import mysql.connector
from mysql.connector import Error

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="123456",
            database="bdedificio"
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print("❌ Error al conectar:", e)
        return None