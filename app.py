from flask import Flask
from flask_mail import Mail
from flask_login import LoginManager
from config import Config
from db import get_db_connection
from models import Usuario

# Inicializar app
app = Flask(__name__)
app.config.from_object(Config)

# Extensiones
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = "auth.login"

# Importar blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.password import password_bp
from routes.empleados import empleados_bp
from routes.residentes import residentes_bp  # ← AÑADIR ESTA IMPORTACIÓN

# Registrar blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(password_bp)
app.register_blueprint(empleados_bp, url_prefix="/empleados")
app.register_blueprint(residentes_bp, url_prefix="/residentes")  # ← AÑADIR ESTE REGISTRO

# Flask-Login con manejo de errores
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if conn is None:
        print("❌ Error: No se pudo establecer conexión a la BD en load_user")
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuario WHERE id_usuario=%s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        return Usuario(row) if row else None
    except Exception as e:
        print(f"❌ Error en load_user: {e}")
        return None
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    app.run(debug=True)