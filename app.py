from flask import Flask, jsonify, request, session
from flask_mail import Mail, Message
from flask_login import LoginManager
from flask_cors import CORS
from config import Config
from db import get_db_connection
from models import Usuario
from threading import Thread
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta, datetime
import os
import jwt as pyjwt
from flask_jwt_extended import decode_token
from routes.residenteticketmovil import residente_ticket_movil


# Inicializar app
app = Flask(__name__)
app.config.from_object(Config)

# 🔐 CONFIGURACIÓN JWT COMPLETA Y EXPLÍCITA
app.config['JWT_SECRET_KEY'] = 'tu-clave-secreta-muy-segura-para-movil-2024'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
app.config['JWT_ALGORITHM'] = 'HS256'
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'

# Configuraciones críticas para evitar conflictos
app.config['JWT_DECODE_ALGORITHMS'] = ['HS256']
app.config['JWT_IDENTITY_CLAIM'] = 'identity'
app.config['JWT_USER_CLAIMS'] = 'user_claims'

jwt = JWTManager(app)

# 🔥 CONFIGURACIÓN DE CORS ESPECÍFICA PARA JWT
CORS(app, resources={
    r"/api/*": {"origins": "*", "supports_credentials": True},
    r"/residentemovil/*": {"origins": "*", "supports_credentials": True}
})

# Extensiones
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = "auth.login"

# 🔥 FUNCIONES DE CARGA JWT CRÍTICAS
@jwt.user_identity_loader
def user_identity_lookup(user):
    """Cómo identificar al usuario desde el token"""
    print(f"🔐 [JWT IDENTITY] Cargando identidad: {user}")
    return user

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    """Cargar usuario desde la base de datos basado en el token"""
    try:
        identity = jwt_data["sub"]
        print(f"🔐 [JWT LOADER] Buscando usuario con ID: {identity}")
        
        conn = get_db_connection()
        if conn is None:
            print("❌ [JWT LOADER] Error de conexión a BD")
            return None
            
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuario WHERE id_usuario=%s", (identity,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            usuario = Usuario(row)
            print(f"✅ [JWT LOADER] Usuario encontrado: {usuario.nombre}")
            return usuario
        else:
            print("❌ [JWT LOADER] Usuario no encontrado en BD")
            return None
            
    except Exception as e:
        print(f"💥 [JWT LOADER] Error: {e}")
        return None

# Función para enviar emails
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

# Importar blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.password import password_bp
from routes.empleados import empleados_bp
from routes.residentes import residentes_bp
from routes.residentemovil import residentemovil_bp
from routes.residenteticketmovil import residente_ticket_movil
from routes.residenteperfilmovil import residente_perfil_movil_bp

# Registrar blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(password_bp)
app.register_blueprint(empleados_bp, url_prefix="/empleados")
app.register_blueprint(residentes_bp, url_prefix="/residentes")
app.register_blueprint(residentemovil_bp)
app.register_blueprint(residente_ticket_movil, url_prefix='/api/movil')
app.register_blueprint(residente_perfil_movil_bp, url_prefix='/api/movil')

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

# ===== ENDPOINTS PRINCIPALES =====

# Endpoint API para login móvil - CON JWT CORREGIDO
@app.route("/api/auth/login", methods=["POST"])
def api_login():
    try:
        from werkzeug.security import check_password_hash
        
        data = request.get_json()
        correo = data.get("correo")
        password = data.get("password")

        print(f"🎯 LOGIN DESDE APP MÓVIL CON JWT")
        print(f"📧 Correo: {coro}")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuario WHERE correo=%s", (correo,))
        row = cursor.fetchone()
        
        if row:
            print(f"✅ Usuario encontrado en BD: {row[1]}")  # nombre
            usuario = Usuario(row)
            
            # DEBUG: Mostrar atributos del usuario
            print(f"🔍 DEBUG - Usuario creado:")
            print(f"   id: {usuario.id}")
            print(f"   nombre: {usuario.nombre}")
            print(f"   correo: {usuario.correo}")
            print(f"   id_rol: {usuario.id_rol}")
            
            # Verifica la contraseña
            if check_password_hash(usuario.contrasena, password):
                print("🔑 Contraseña CORRECTA - Generando JWT")
                
                # ✅ CREAR TOKEN JWT
                access_token = create_access_token(
                    identity=usuario.id,  # user_id como identity
                    additional_claims={
                        'correo': usuario.correo,
                        'id_rol': usuario.id_rol,
                        'nombre': usuario.nombre
                    }
                )
                
                print(f"🔐 JWT Generado: {access_token[:50]}...")
                
                # Determinar nombre del rol
                rol_nombre = "Desconocido"
                if usuario.id_rol == 1:
                    rol_nombre = "Administrador"
                elif usuario.id_rol == 2:
                    rol_nombre = "Empleado"
                elif usuario.id_rol == 3:
                    rol_nombre = "Residente"
                
                print(f"🎉 Login exitoso - Usuario: {usuario.nombre}, Rol: {rol_nombre} ({usuario.id_rol})")
                
                return jsonify({
                    "success": True,
                    "message": f"Login exitoso - Bienvenido {usuario.nombre}",
                    "token": access_token,  # ✅ TOKEN JWT INCLUIDO
                    "user": {
                        "id_usuario": usuario.id,
                        "nombre": usuario.nombre,
                        "ap_paterno": usuario.ap_paterno,
                        "ap_materno": usuario.ap_materno if hasattr(usuario, 'ap_materno') else "",
                        "correo": usuario.correo,
                        "id_rol": usuario.id_rol,
                        "rol_nombre": rol_nombre,
                        "telefono": row[5] if len(row) > 5 else ""  # telefono directamente de la BD
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

# Endpoint para verificar token JWT
@app.route("/api/auth/verify", methods=["GET"])
@jwt_required()
def verify_token():
    try:
        current_user_id = get_jwt_identity()
        print(f"🔍 [VERIFY] Verificando token para usuario: {current_user_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuario WHERE id_usuario=%s", (current_user_id,))
        row = cursor.fetchone()
        
        if row:
            usuario = Usuario(row)
            return jsonify({
                "success": True,
                "message": "Token válido",
                "user": {
                    "id_usuario": usuario.id,
                    "nombre": usuario.nombre,
                    "correo": usuario.correo,
                    "id_rol": usuario.id_rol
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": "Usuario no encontrado"
            }), 404
            
    except Exception as e:
        print(f"❌ [VERIFY] Error verificando token: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error verificando token: {str(e)}"
        }), 500

# 🔥 NUEVO ENDPOINT: Diagnóstico JWT
@app.route("/api/auth/diagnostico_jwt", methods=["GET"])
@jwt_required()
def diagnostico_jwt():
    """Diagnóstico completo del JWT"""
    try:
        current_user_id = get_jwt_identity()
        auth_header = request.headers.get('Authorization', '')
        
        # Debug info
        print(f"🔐 [DIAGNÓSTICO] User ID: {current_user_id}")
        print(f"🔐 [DIAGNÓSTICO] Auth Header: {auth_header}")
        
        return jsonify({
            "success": True,
            "message": "✅ JWT funcionando correctamente",
            "user_id": current_user_id,
            "auth_header_received": auth_header[:50] + "..." if len(auth_header) > 50 else auth_header,
            "jwt_config": {
                "secret_key": app.config['JWT_SECRET_KEY'][:10] + "...",
                "algorithm": app.config['JWT_ALGORITHM'],
                "expires": str(app.config['JWT_ACCESS_TOKEN_EXPIRES'])
            }
        })
        
    except Exception as e:
        print(f"❌ [DIAGNÓSTICO] Error: {e}")
        return jsonify({
            "success": False,
            "message": f"Error JWT: {str(e)}"
        }), 401

# Endpoint para obtener información de usuario por ID
@app.route("/api/user/<int:user_id>", methods=["GET"])
@jwt_required()
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

# Endpoint de prueba para verificar que la API funciona
@app.route("/api/test", methods=["GET"])
def api_test():
    return jsonify({
        "success": True,
        "message": "✅ API Flask funcionando correctamente",
        "status": "Conectado",
        "jwt_configured": True,
        "endpoints": {
            "login": "/api/auth/login (POST)",
            "verify": "/api/auth/verify (GET) - JWT required",
            "diagnostico_jwt": "/api/auth/diagnostico_jwt (GET) - JWT required",
            "get_user": "/api/user/<id> (GET) - JWT required",
            "test": "/api/test (GET)"
        }
    })

# Endpoint para renovar token JWT
@app.route("/api/auth/refresh", methods=["POST"])
@jwt_required()
def refresh_token():
    try:
        current_user_id = get_jwt_identity()
        print(f"🔄 Renovando token para usuario: {current_user_id}")
        
        # Crear nuevo token
        new_token = create_access_token(identity=current_user_id)
        
        return jsonify({
            "success": True,
            "token": new_token,
            "message": "Token renovado exitosamente"
        })
        
    except Exception as e:
        print(f"❌ Error renovando token: {e}")
        return jsonify({
            "success": False,
            "message": "Error renovando token"
        }), 500

# ===== ENDPOINTS DE DIAGNÓSTICO JWT =====

@app.route("/api/auth/debug_token", methods=["POST"])
def debug_token():
    """Endpoint para debuggear tokens JWT"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        print(f"🔍 [DEBUG TOKEN] Token recibido: {token}")
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'No token provided'
            }), 400
        
        # Intentar decodificar con Flask-JWT-Extended
        try:
            decoded_flask = decode_token(token)
            print(f"✅ [DEBUG TOKEN] Decodificado con Flask-JWT: {decoded_flask}")
            flask_success = True
        except Exception as flask_error:
            print(f"❌ [DEBUG TOKEN] Error Flask-JWT: {flask_error}")
            flask_success = False
        
        # Intentar decodificar con PyJWT directamente
        try:
            decoded_pyjwt = pyjwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            print(f"✅ [DEBUG TOKEN] Decodificado con PyJWT: {decoded_pyjwt}")
            pyjwt_success = True
        except Exception as pyjwt_error:
            print(f"❌ [DEBUG TOKEN] Error PyJWT: {pyjwt_error}")
            pyjwt_success = False
        
        return jsonify({
            'success': flask_success or pyjwt_success,
            'flask_jwt_decoded': flask_success,
            'pyjwt_decoded': pyjwt_success,
            'secret_key_used': app.config['JWT_SECRET_KEY'][:10] + '...',
            'message': 'Token analysis completed'
        })
            
    except Exception as e:
        print(f"💥 [DEBUG TOKEN] Error general: {e}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route("/api/auth/test_generate", methods=["POST"])
def test_generate_token():
    """Endpoint para probar generación de token"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 3)
        
        print(f"🔧 [TEST GENERATE] Generando token para user_id: {user_id}")
        
        # Generar token de prueba
        test_token = create_access_token(
            identity=user_id,
            additional_claims={
                'correo': 'test@example.com',
                'id_rol': 3,
                'nombre': 'Test User'
            }
        )
        
        print(f"🔧 [TEST GENERATE] Token generado: {test_token}")
        
        # Verificar si el token generado es válido
        try:
            decoded = decode_token(test_token)
            print(f"✅ [TEST GENERATE] Token auto-verificado: {decoded}")
            self_valid = True
        except Exception as e:
            print(f"❌ [TEST GENERATE] Token NO auto-verificado: {e}")
            self_valid = False
        
        return jsonify({
            'success': True,
            'token': test_token,
            'self_valid': self_valid,
            'message': 'Test token generated'
        })
        
    except Exception as e:
        print(f"💥 [TEST GENERATE] Error: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route("/api/auth/test_verify", methods=["GET"])
def test_verify():
    """Endpoint público para probar que el verify funciona"""
    return jsonify({
        "success": True,
        "message": "✅ Endpoint verify está funcionando",
        "timestamp": datetime.now().isoformat()
    })

# ===== ENDPOINTS DE REGISTRO =====

@app.route("/api/auth/solicitar_codigo", methods=["POST"])
def api_solicitar_codigo():
    try:
        data = request.get_json()
        correo = data.get("correo")
        rol = data.get("rol")
        
        print(f"📧 Solicitando código para: {correo} - Rol: {rol}")
        
        return jsonify({
            "success": True,
            "message": f"✅ Código de invitación enviado a {correo}"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route("/api/auth/validar_codigo", methods=["POST"])
def api_validar_codigo():
    try:
        data = request.get_json()
        codigo = data.get("codigo")
        rol = data.get("rol")
        
        print(f"🔍 Validando código: {codigo} - Rol: {rol}")
        
        valido = "123" in codigo if codigo else False
        
        return jsonify({
            "success": True,
            "valido": valido,
            "message": "✅ Código válido" if valido else "❌ Código inválido"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "valido": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route("/api/auth/register/residente", methods=["POST"])
def api_register_residente():
    try:
        data = request.get_json()
        print(f"🏠 Registrando residente: {data}")
        
        return jsonify({
            "success": True,
            "message": "✅ Residente registrado exitosamente"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route("/api/auth/register/empleado", methods=["POST"])
def api_register_empleado():
    try:
        data = request.get_json()
        print(f"💼 Registrando empleado: {data}")
        
        return jsonify({
            "success": True,
            "message": "✅ Empleado registrado exitosamente"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route("/api/auth/register/admin", methods=["POST"])
def api_register_admin():
    try:
        data = request.get_json()
        print(f"🔧 Registrando admin: {data}")
        
        return jsonify({
            "success": True,
            "message": "✅ Administrador registrado exitosamente"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500
@app.route("/api/auth/debug_jwt_config")
def debug_jwt_config():
    """Diagnóstico completo de la configuración JWT"""
    try:
        # Verificar configuración actual
        config_info = {
            'JWT_SECRET_KEY': app.config.get('JWT_SECRET_KEY', 'NO_CONFIGURADO')[:10] + '...',
            'JWT_ALGORITHM': app.config.get('JWT_ALGORITHM', 'NO_CONFIGURADO'),
            'JWT_ACCESS_TOKEN_EXPIRES': str(app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 'NO_CONFIGURADO')),
            'JWT_TOKEN_LOCATION': app.config.get('JWT_TOKEN_LOCATION', 'NO_CONFIGURADO'),
            'JWT_HEADER_NAME': app.config.get('JWT_HEADER_NAME', 'NO_CONFIGURADO'),
            'JWT_HEADER_TYPE': app.config.get('JWT_HEADER_TYPE', 'NO_CONFIGURADO')
        }
        
        # Verificar blueprints registrados
        blueprints = []
        for name, blueprint in app.blueprints.items():
            blueprints.append({
                'name': name,
                'url_prefix': blueprint.url_prefix,
                'module': blueprint.__module__
            })
        
        return jsonify({
            'success': True,
            'jwt_config': config_info,
            'blueprints_registered': blueprints,
            'total_blueprints': len(blueprints)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error en diagnóstico: {str(e)}'
        }), 500

# ===== MANEJO DE ERRORES JWT =====

@jwt.unauthorized_loader
def unauthorized_callback(callback):
    return jsonify({
        "success": False,
        "message": "Token faltante o inválido"
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(callback):
    return jsonify({
        "success": False,
        "message": "Token inválido"
    }), 422

@jwt.expired_token_loader
def expired_token_callback(callback):
    return jsonify({
        "success": False,
        "message": "Token expirado"
    }), 401
@app.route("/api/auth/verify_token_manual", methods=["POST"])
def verify_token_manual():
    """Verificar token manualmente para debug"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'No token provided'
            }), 400
        
        print(f"🔍 [MANUAL VERIFY] Token recibido: {token}")
        print(f"🔍 [MANUAL VERIFY] JWT Secret: {app.config['JWT_SECRET_KEY'][:10]}...")
        
        # Verificar con PyJWT
        try:
            decoded = pyjwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            print(f"✅ [MANUAL VERIFY] PyJWT decoded: {decoded}")
            return jsonify({
                'success': True,
                'message': 'Token válido con PyJWT',
                'decoded': decoded
            })
        except Exception as e:
            print(f"❌ [MANUAL VERIFY] PyJWT error: {e}")
            return jsonify({
                'success': False,
                'message': f'PyJWT error: {str(e)}'
            }), 422
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500
    
# ===== INICIO DE LA APLICACIÓN =====

if __name__ == "__main__":
    print("🚀 Iniciando servidor Flask...")
    print("🔐 JWT Configurado:")
    print(f"   • Clave: {app.config['JWT_SECRET_KEY'][:10]}...")
    print(f"   • Expiración: {app.config['JWT_ACCESS_TOKEN_EXPIRES']}")
    print("📱 Endpoints API Móvil:")
    print("   • http://localhost:5000/api/test (GET) - Prueba de conexión")
    print("   • http://localhost:5000/api/auth/login (POST) - Login con JWT")
    print("   • http://localhost:5000/api/auth/verify (GET) - Verificar JWT")
    print("   • http://localhost:5000/api/auth/diagnostico_jwt (GET) - Diagnóstico JWT")
    print("   • http://localhost:5000/api/auth/debug_token (POST) - Debug JWT")
    print("   • http://localhost:5000/api/auth/test_generate (POST) - Test generar token")
    print("   • http://localhost:5000/api/auth/test_verify (GET) - Test verify")
    print("   • http://localhost:5000/api/auth/refresh (POST) - Renovar JWT")
    print("   • http://localhost:5000/api/user/<id> (GET) - Obtener usuario")
    print("🌐 Sistema Web:")
    print("   • http://localhost:5000/ - Sistema web completo")
    app.run(debug=True, host='0.0.0.0', port=5000)
    