from flask import Flask
from flask_mail import Mail, Message
from flask_login import LoginManager
from config import Config
from db import get_db_connection
from models import Usuario
from threading import Thread

# Inicializar app
app = Flask(__name__)
app.config.from_object(Config)

# Extensiones
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = "auth.login"

# Función para enviar emails
def enviar_email_async(app, msg):
    """Envía email en un hilo separado para no bloquear la aplicación"""
    with app.app_context():
        try:
            mail.send(msg)  # Ahora mail está definido en este contexto
            print("✅ Email enviado exitosamente")
        except Exception as e:
            print(f"❌ Error enviando email: {str(e)}")

def enviar_email(destinatario, asunto, cuerpo, html=None):
    """
    Envía un email usando Flask-Mail
    """
    try:
        # Crear el mensaje
        msg = Message(
            subject=asunto,
            recipients=[destinatario],
            body=cuerpo,
            html=html,
            sender=app.config.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')
        )
        
        # Enviar en un hilo separado
        Thread(target=enviar_email_async, args=(app, msg)).start()
        
        return True
        
    except Exception as e:
        print(f"❌ Error preparando email: {str(e)}")
        return False

# Hacerla disponible globalmente
app.enviar_email = enviar_email

# Importar blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.password import password_bp
from routes.empleados import empleados_bp
from routes.residentes import residentes_bp

# Registrar blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(password_bp)
app.register_blueprint(empleados_bp, url_prefix="/empleados")
app.register_blueprint(residentes_bp, url_prefix="/residentes")

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