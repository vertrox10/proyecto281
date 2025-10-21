import pg8000.dbapi
import ssl
import os

def get_db_connection():
    try:
        ssl_context = ssl.create_default_context()
        
        # Usar variables de entorno para mayor seguridad
        host = os.environ.get('DB_HOST', "ep-billowing-boat-adtj0hh6-pooler.c-2.us-east-1.aws.neon.tech")
        database = os.environ.get('DB_NAME', "bdedificio")
        user = os.environ.get('DB_USER', "neondb_owner")
        password = os.environ.get('DB_PASSWORD', "npg_qxZSRobC4y7L")
        
        print(f"🔌 Intentando conectar a: {host}, BD: {database}, Usuario: {user}")
        
        conn = pg8000.dbapi.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=5432,
            ssl_context=ssl_context
        )
        
        print("✅ Conexión a PostgreSQL establecida exitosamente")
        return conn
        
    except Exception as e:
        print(f"❌ Error crítico al conectar a PostgreSQL: {e}")
        return None