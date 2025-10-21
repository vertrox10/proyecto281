from flask import Flask
from flask_mail import Mail
from config import Config
from routes.auth import auth_bp
from routes.admin import admin_bp  # <- Importar el blueprint de admin

mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Inicializar Flask-Mail
    mail.init_app(app)
    
    # Configuración de Flask-Login (si no la tienes)
    from models import Usuario
    from flask_login import LoginManager
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    
    @login_manager.user_loader
    def load_user(user_id):
        from db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuario WHERE id_usuario = %s", (user_id,))
        user_row = cursor.fetchone()
        cursor.close()
        conn.close()
        if user_row:
            return Usuario(user_row)
        return None
    
    # Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)  # <- Registrar el blueprint de admin
    
    return app