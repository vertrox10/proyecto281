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

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(password_bp)


# Flask-Login
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuario WHERE id_usuario=%s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return Usuario(row) if row else None


if __name__ == "__main__":
    app.run(debug=True)
