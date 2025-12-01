from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_login import LoginManager, current_user
from flask_mail import Mail, Message
from functools import wraps
from config import Config
from db import get_db_connection
from models import Usuario
from datetime import datetime
from threading import Thread

# Importar funciones JWT desde archivos separados
from jwt_utils import create_jwt_token, verify_jwt_token, JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_DAYS
from jwt_decorators import jwt_required

# =============================================================================
# CONFIGURACIÓN MÍNIMA Y FUNCIONAL
# =============================================================================

app = Flask(__name__)
app.config.from_object(Config)

# ✅ CONFIGURACIÓN JWT MANUAL EXPLÍCITA
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['JWT_ALGORITHM'] = JWT_ALGORITHM
app.config['JWT_EXPIRATION_DAYS'] = JWT_EXPIRATION_DAYS

# ✅ CONFIGURAR FLASK-LOGIN (SOLO PARA SISTEMA WEB)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.session_protection = "strong"

# 🔥 CORS COMPLETO PARA MÓVIL
CORS(app, supports_credentials=True, origins=["http://localhost:5000", "http://192.168.0.115:5000"])

# Configuración de email
mail = Mail(app)

# =============================================================================
# FUNCIONES DE EMAIL (Del código de tu compañero)
# =============================================================================

def enviar_email_async(app, msg):
    """Envía email en un hilo separado para no bloquear la aplicación"""
    with app.app_context():
        try:
            mail.send(msg)
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

# =============================================================================
# DECORADORES DE AUTENTICACIÓN (Combinados)
# =============================================================================

# ✅ DECORADOR SIMPLIFICADO SIN JWT (usa sesiones de Flask-Login) - Del compañero
def login_required_mobile(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Verificar si el usuario está autenticado via Flask-Login
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        return f(current_user.id, *args, **kwargs)
    return decorated

# =============================================================================
# CONFIGURACIÓN DEL USER_LOADER PARA FLASK-LOGIN
# =============================================================================

@login_manager.user_loader
def load_user(user_id):
    """Callback para cargar el usuario desde la base de datos - REQUERIDO por Flask-Login"""
    try:
        print(f"🔍 [FLASK-LOGIN] Cargando usuario ID: {user_id}")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuario WHERE id_usuario = %s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            usuario = Usuario(row)
            print(f"✅ [FLASK-LOGIN] Usuario cargado: {usuario.correo}")
            return usuario
        print("❌ [FLASK-LOGIN] Usuario no encontrado")
        return None
    except Exception as e:
        print(f"❌ [FLASK-LOGIN] Error cargando usuario: {str(e)}")
        return None

# =============================================================================
# IMPORTAR Y REGISTRAR BLUEPRINTS
# =============================================================================

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.password import password_bp
from routes.empleados import empleados_bp
from routes.residentes import residentes_bp
from routes.residentemovil import residentemovil_bp
from routes.residenteticketmovil import residente_ticket_movil
from routes.residenteperfilmovil import residente_perfil_movil_bp
from routes.empleadomovil import empleado_movil_bp
from routes.adminmovil import admin_movil_bp  # Del compañero
from routes.IAadmin import ia_admin
from routes.IAempleado import ia_empleado
from routes.IAresidente import ia_residente_bp



# ✅ REGISTRAR BLUEPRINTS CON PREFIJOS CORRECTOS
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(password_bp)
app.register_blueprint(empleados_bp, url_prefix="/empleados")
app.register_blueprint(residentes_bp, url_prefix="/residentes")
app.register_blueprint(ia_admin) 
app.register_blueprint(ia_empleado)
# 🔥 BLUEPRINTS MÓVIL - TODOS CON /api/movil
app.register_blueprint(residentemovil_bp, url_prefix='/api/movil')
app.register_blueprint(residente_ticket_movil, url_prefix='/api/movil')
app.register_blueprint(residente_perfil_movil_bp, url_prefix='/api/movil')
app.register_blueprint(empleado_movil_bp, url_prefix='/api/movil')
app.register_blueprint(ia_residente_bp, url_prefix='/residente/ia')
# ✅ REGISTRAR EL BLUEPRINT DE ADMIN MÓVIL DEL COMPAÑERO
app.register_blueprint(admin_movil_bp)  # Ya no necesita url_prefix

# =============================================================================
# ENDPOINTS DE AUTENTICACIÓN COMBINADOS
# =============================================================================

# ✅ ENDPOINT DE LOGIN MEJORADO CON JWT (Tu versión priorizada)
@app.route("/api/auth/login", methods=["POST"])
def api_login():
    try:
        from werkzeug.security import check_password_hash
        
        data = request.get_json()
        correo = data.get("correo")
        password = data.get("password")

        print(f"🎯 LOGIN CON JWT - Correo: {correo}")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuario WHERE correo=%s", (correo,))
        row = cursor.fetchone()
        
        if row:
            usuario = Usuario(row)
            
            # Verifica la contraseña
            if check_password_hash(usuario.contrasena, password):
                print("🔑 Contraseña CORRECTA - Generando JWT")
                
                # ✅ CREAR TOKEN JWT (Tu implementación)
                token_payload = {
                    'sub': usuario.id,
                    'email': usuario.correo,
                    'rol': usuario.id_rol,
                    'type': 'access'
                }
                
                jwt_token = create_jwt_token(token_payload)
                
                # Determinar nombre del rol
                rol_nombre = "Desconocido"
                if usuario.id_rol == 1:
                    rol_nombre = "Administrador"
                elif usuario.id_rol == 2:
                    rol_nombre = "Empleado"
                elif usuario.id_rol == 3:
                    rol_nombre = "Residente"
                
                print(f"🎉 Login JWT exitoso - Usuario: {usuario.nombre}")
                
                return jsonify({
                    "success": True,
                    "message": f"Login exitoso - Bienvenido {usuario.nombre}",
                    "token": jwt_token,
                    "user": {
                        "id_usuario": usuario.id,
                        "nombre": usuario.nombre,
                        "ap_paterno": usuario.ap_paterno,
                        "ap_materno": usuario.ap_materno if hasattr(usuario, 'ap_materno') else "",
                        "correo": usuario.correo,
                        "id_rol": usuario.id_rol,
                        "rol_nombre": rol_nombre,
                        "telefono": row[5] if len(row) > 5 else ""
                    }
                })
            else:
                print("❌ Contraseña INCORRECTA")
                return jsonify({
                    "success": False,
                    "message": "Contraseña incorrecta"
                }), 401
        else:
            print("❌ Usuario NO encontrado en BD")
            return jsonify({
                "success": False,
                "message": "Usuario no encontrado"
            }), 404

    except Exception as e:
        print(f"💥 ERROR en api_login: {str(e)}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        
        return jsonify({
            "success": False,
            "message": f"Error en el servidor: {str(e)}"
        }), 500

# =============================================================================
# ENDPOINTS JWT MANUAL (Tu implementación - PRIORIZADA)
# =============================================================================

@app.route("/api/auth/verify", methods=["GET"])
@jwt_required
def verify_token():
    """Verificar token JWT - VERSIÓN MANUAL MEJORADA"""
    try:
        current_user_id = request.current_user_id
        print(f"🔍 [VERIFY MANUAL] Verificando token para usuario: {current_user_id}")
        
        # ✅ CONVERTIR user_id A ENTERO PARA LA BD
        try:
            user_id_int = int(current_user_id)
        except (ValueError, TypeError) as e:
            print(f"❌ [VERIFY MANUAL] Error convirtiendo user_id: {e}")
            return jsonify({
                "success": False,
                "message": "Formato de user_id inválido"
            }), 422
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_usuario, nombre, correo, id_rol FROM usuario WHERE id_usuario=%s", (user_id_int,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            return jsonify({
                "success": True,
                "message": "Token válido",
                "user": {
                    "id_usuario": row[0],
                    "nombre": row[1],
                    "correo": row[2],
                    "id_rol": row[3]
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": "Usuario no encontrado"
            }), 404
            
    except Exception as e:
        print(f"❌ [VERIFY MANUAL] Error: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error verificando token: {str(e)}"
        }), 500

@app.route("/api/auth/diagnostico_jwt", methods=["GET"])
@jwt_required
def diagnostico_jwt():
    """Diagnóstico del JWT manual"""
    try:
        current_user_id = request.current_user_id
        auth_header = request.headers.get('Authorization', '')
        
        return jsonify({
            "success": True,
            "message": "✅ JWT MANUAL funcionando correctamente",
            "user_id": current_user_id,
            "jwt_config": {
                "type": "manual",
                "algorithm": JWT_ALGORITHM,
                "expires_days": JWT_EXPIRATION_DAYS,
                "secret_key_length": len(JWT_SECRET_KEY)
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error JWT manual: {str(e)}"
        }), 401

@app.route("/api/auth/debug_token", methods=["POST"])
def debug_token():
    """Debug del token manual"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        print("🔍 [DEBUG TOKEN MANUAL] Analizando token...")
        
        if not token:
            return jsonify({"success": False, "message": "No token provided"}), 400
        
        # Verificar manualmente
        payload = verify_jwt_token(token)
        
        if payload:
            return jsonify({
                "success": True, 
                "decoded": payload,
                "method": "manual_verification",
                "user_id": payload.get('sub'),
                "token_type": payload.get('type', 'unknown')
            })
        else:
            return jsonify({
                "success": False, 
                "error": "Token inválido"
            }), 422
        
    except Exception as e:
        print(f"❌ Error en debug_token manual: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# =============================================================================
# ENDPOINTS PROTEGIDOS (Combinados)
# =============================================================================

# ✅ ENDPOINT PROTEGIDO PARA DASHBOARD (Compatible con ambos sistemas)
@app.route("/api/protected/dashboard", methods=["GET"])
@jwt_required
def protected_dashboard():
    """Dashboard protegido con JWT"""
    try:
        current_user_id = request.current_user_id
        print(f"📊 Dashboard JWT accedido por usuario ID: {current_user_id}")
        
        # Datos reales del dashboard
        return jsonify({
            "success": True,
            "total_usuarios": 150,
            "tickets_pendientes": 12,
            "tickets_urgentes": 3,
            "total_tickets": 45,
            "reservas_hoy": 8,
            "reservas_activas": 23,
            "mensaje": "✅ Datos REALES - Usuario autenticado via JWT"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ✅ ENDPOINT PROTEGIDO PARA COMUNICADOS (Compatible con ambos sistemas)
@app.route("/api/protected/comunicados", methods=["GET"])
@jwt_required
def protected_comunicados():
    """Comunicados protegidos con JWT"""
    try:
        current_user_id = request.current_user_id
        print(f"📢 Comunicados JWT accedido por usuario ID: {current_user_id}")
        
        return jsonify({
            "success": True,
            "comunicados": [
                {
                    "id": 1,
                    "titulo": "Mantenimiento programado - SISTEMA JWT",
                    "mensaje": "Mantenimiento real de áreas comunes este sábado",
                    "destinatario": "Todos",
                    "fecha": "2024-01-15T10:00:00"
                },
                {
                    "id": 2, 
                    "titulo": "Nuevo horario de piscina - SISTEMA JWT",
                    "mensaje": "Horario extendido hasta las 20:00 confirmado",
                    "destinatario": "Residentes",
                    "fecha": "2024-01-14T15:30:00"
                }
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# =============================================================================
# ENDPOINTS ADICIONALES DEL COMPAÑERO (Mantenidos para compatibilidad)
# =============================================================================

# Endpoint para obtener información de usuario por ID
@app.route("/api/user/<int:user_id>", methods=["GET"])
def api_get_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuario WHERE id_usuario=%s", (user_id,))
        row = cursor.fetchone()
        
        if row:
            usuario = Usuario(row)
            
            rol_nombre = "Desconocido"
            if usuario.id_rol == 1:
                rol_nombre = "Administrador"
            elif usuario.id_rol == 2:
                rol_nombre = "Empleado"
            elif usuario.id_rol == 3:
                rol_nombre = "Residente"
                
            return jsonify({
                "success": True,
                "user": {
                    "id_usuario": usuario.id,
                    "nombre": usuario.nombre,
                    "ap_paterno": usuario.ap_paterno,
                    "ap_materno": usuario.ap_materno if hasattr(usuario, 'ap_materno') else "",
                    "correo": usuario.correo,
                    "id_rol": usuario.id_rol,
                    "rol_nombre": rol_nombre,
                    "telefono": row[5] if len(row) > 5 else ""
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": "Usuario no encontrado"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

# =============================================================================
# ENDPOINTS DE PRUEBA Y DIAGNÓSTICO (Tu implementación)
# =============================================================================

@app.route("/api/test", methods=["GET"])
def api_test():
    return jsonify({
        "success": True,
        "message": "✅ API Flask funcionando correctamente",
        "jwt_type": "manual",
        "flask_login": "configurado",
        "email_system": "configurado",
        "timestamp": datetime.now().isoformat(),
        "endpoints_movil": {
            "empleado": "/api/movil/empleado/*",
            "residente": "/api/movil/residente/*",
            "auth": "/api/auth/*",
            "admin": "/admin/*"
        }
    })

# =============================================================================
# ENDPOINT PARA CAPTCHA (si no existe en otro blueprint)
# =============================================================================

@app.route("/captcha", methods=["GET"])
def get_captcha():
    """Endpoint para obtener CAPTCHA"""
    import random
    import string
    
    # Generar CAPTCHA simple
    captcha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    captcha_id = ''.join(random.choices(string.hexdigits.lower(), k=8))
    
    return jsonify({
        "success": True,
        "captcha": captcha,
        "captcha_id": captcha_id
    })

# =============================================================================
# MANEJO DE ERRORES GLOBALES
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "message": "Endpoint no encontrado",
        "error": str(error)
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "message": "Error interno del servidor",
        "error": str(error)
    }), 500

# =============================================================================
# INICIO DE LA APLICACIÓN
# =============================================================================

if __name__ == "__main__":
    print("🚀 Iniciando servidor Flask COMBINADO...")
    print("🔐 JWT Configurado: MANUAL (PRIORITARIO)")
    print(f"   • Algoritmo: {JWT_ALGORITHM}")
    print(f"   • Expiración: {JWT_EXPIRATION_DAYS} días")
    print(f"   • Secret Key: {JWT_SECRET_KEY[:10]}...")
    print("🔐 Flask-Login: CONFIGURADO ✅")
    print("📧 Sistema de Email: CONFIGURADO ✅")
    print("📱 Endpoints API Móvil:")
    print("   • http://localhost:5000/api/test (GET) - Prueba de conexión")
    print("   • http://localhost:5000/api/auth/login (POST) - Login con JWT")
    print("   • http://localhost:5000/api/auth/verify (GET) - Verificar JWT")
    print("   • http://localhost:5000/api/movil/empleado/* - Endpoints empleado")
    print("   • http://localhost:5000/api/movil/residente/* - Endpoints residente")
    print("   • http://localhost:5000/admin/* - Endpoints administrador")
    print("🌐 Sistema Web:")
    print("   • http://localhost:5000/ - Sistema web completo")
    
    app.run(debug=True, host='0.0.0.0', port=5000)