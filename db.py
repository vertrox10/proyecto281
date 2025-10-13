import pg8000.dbapi
import ssl

def get_db_connection():
    try:
        ssl_context = ssl.create_default_context()
        conn = pg8000.dbapi.connect(
            host="ep-billowing-boat-adtj0hh6-pooler.c-2.us-east-1.aws.neon.tech",
            database="bdedificio",
            user="neondb_owner",
            password="npg_qxZSRobC4y7L",
            port=5432,
            ssl_context=ssl_context  # requerido por Neon
        )
        return conn
    except Exception as e:
        print(f"❌ Error al conectar a PostgreSQL: {e}")
        return None

