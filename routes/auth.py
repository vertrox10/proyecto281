from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from jwt_decorators import jwt_required
from werkzeug.security import check_password_hash, generate_password_hash
from db import get_db_connection
from models import Usuario
from utils import generar_captcha, es_correo_valido, es_contrasena_valida, es_telefono_valido
from invitaciones import crear_invitacion, validar_codigo, marcar_codigo_como_usado
import datetime
import os
import secrets
import random
import uuid
from jwt_utils import create_jwt_token

auth_bp = Blueprint("auth", __name__)

# =============================================================================
# CONFIGURACIÓN Y UTILIDADES
# =============================================================================

# Diccionario temporal para almacenar CAPTCHAs (en producción usa Redis)
captcha_storage = {}

def limpiar_captchas_expirados():
    """Limpia CAPTCHAs antiguos del almacenamiento temporal"""
    current_time = datetime.datetime.now()
    expired_keys = [
        key for key, value in captcha_storage.items()
        if (current_time - value['timestamp']).total_seconds() > 600  # 10 minutos
    ]
    for key in expired_keys:
        captcha_storage.pop(key, None)

# =============================================================================
# ENDPOINTS PARA API MÓVIL
# =============================================================================

@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    """Login para aplicación móvil"""
    try:
        print("🔍 INICIANDO API LOGIN...")
        data = request.get_json()
        
        print(f"🔍 Datos recibidos: {data}")
        
        if not data:
            print("❌ No se recibieron datos JSON")
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos JSON'
            }), 400
        
        correo = data.get("correo")
        password = data.get("password")
        captcha_usuario = data.get("captcha", "")
        captcha_id = data.get("captcha_id", "")

        print(f"🔍 DEBUG API Login - Correo: {correo}")
        print(f"🔍 DEBUG CAPTCHA - ID: {captcha_id}, Usuario: {captcha_usuario}")

        # Validar CAPTCHA para móvil
        if captcha_id and captcha_id != 'local':
            print(f"🔍 Validando CAPTCHA: {captcha_id}")
            print(f"📊 CAPTCHAs en almacenamiento: {list(captcha_storage.keys())}")
            
            captcha_data = captcha_storage.get(captcha_id)
            if not captcha_data:
                print("❌ CAPTCHA expirado o no encontrado")
                return jsonify({
                    'success': False,
                    'message': 'CAPTCHA expirado o no encontrado'
                }), 401
            
            captcha_text = captcha_data['text']
            print(f"🔍 CAPTCHA esperado: {captcha_text}, Usuario: {captcha_usuario}")
            
            if captcha_usuario.strip().upper() != captcha_text.strip().upper():
                print("❌ CAPTCHA incorrecto")
                return jsonify({
                    'success': False,
                    'message': 'CAPTCHA incorrecto'
                }), 401
            
            # Eliminar CAPTCHA después de usar
            captcha_storage.pop(captcha_id, None)
            print("✅ CAPTCHA validado y eliminado")

        print("🔍 Conectando a la base de datos...")
        # Buscar usuario en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuario WHERE correo=%s", (correo,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            print("❌ Usuario no encontrado")
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404

        print(f"🔍 Usuario encontrado: {row}")
        
        # Crear objeto Usuario
        usuario = Usuario(row)
        
        print(f"🔍 Verificando contraseña para: {usuario.correo}")
        # Verificar contraseña
        if not check_password_hash(usuario.contrasena, password):
            print("❌ Contraseña incorrecta")
            return jsonify({
                'success': False,
                'message': 'Contraseña incorrecta'
            }), 401

        print("🔍 Generando token...")
        
        # ✅ CORREGIDO: Generar token con la estructura correcta
        identity_data = {
            'user_id': usuario.id,
            'correo': usuario.correo,
            'id_rol': usuario.id_rol,
            'nombre': usuario.nombre
        }
        
        print("🔍 Generando token MANUAL...")
        token = create_jwt_token(
            user_id=usuario.id,
            correo=usuario.correo, 
            id_rol=usuario.id_rol,
            nombre=usuario.nombre
        )
        print(f"✅ Token generado: {token[:50]}...")
        
        # Datos del usuario para la respuesta
        user_data = {
            'id_usuario': usuario.id,
            'nombre': usuario.nombre,
            'ap_paterno': usuario.ap_paterno,
            'ap_materno': usuario.ap_materno,
            'correo': usuario.correo,
            'telefono': getattr(usuario, 'telefono', 'No disponible'),
            'id_rol': usuario.id_rol
        }

        print(f"✅ Login exitoso - Usuario: {usuario.correo}, Rol: {usuario.id_rol}")

        response_data = {
            'success': True,
            'message': 'Login exitoso',
            'token': token,
            'user': user_data
        }
        
        print(f"✅ Enviando respuesta: {response_data}")
        return jsonify(response_data), 200

    except Exception as e:
        print(f"❌ ERROR CRÍTICO en api_login: {str(e)}")
        import traceback
        print(f"📋 Traceback completo: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'message': f'Error del servidor: {str(e)}'
        }), 500

@auth_bp.route("/captcha", methods=["GET"])
def api_captcha():
    """API para generar CAPTCHA"""
    try:
        captcha = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=6))
        captcha_id = str(uuid.uuid4())[:8]
        
        # ✅ CORREGIDO: GUARDAR EL CAPTCHA EN EL ALMACENAMIENTO
        captcha_storage[captcha_id] = {
            'text': captcha,
            'timestamp': datetime.datetime.now()
        }
        
        print(f"✅ CAPTCHA generado: {captcha}, ID: {captcha_id}")
        print(f"📊 CAPTCHAs almacenados: {len(captcha_storage)}")
        
        return jsonify({
            'success': True,
            'captcha': captcha,
            'captcha_id': captcha_id
        })
        
    except Exception as e:
        print(f"❌ Error generando CAPTCHA: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@auth_bp.route("/api/auth/validate_captcha", methods=["POST"])
def api_validate_captcha():
    """Validar CAPTCHA independientemente para móvil"""
    try:
        data = request.get_json()
        user_input = data.get('user_input', '')
        captcha_id = data.get('captcha_id', '')
        
        if not captcha_id:
            return jsonify({
                'success': False,
                'valid': False,
                'message': 'ID de CAPTCHA requerido'
            }), 400
        
        # Buscar el CAPTCHA en el almacenamiento
        captcha_data = captcha_storage.get(captcha_id)
        
        if not captcha_data:
            return jsonify({
                'success': False,
                'valid': False,
                'message': 'CAPTCHA expirado o no encontrado'
            }), 404
        
        captcha_text = captcha_data['text']
        is_valid = user_input.strip().upper() == captcha_text.strip().upper()
        
        # Eliminar el CAPTCHA después de validar (usar una sola vez)
        if captcha_id in captcha_storage:
            captcha_storage.pop(captcha_id)
        
        return jsonify({
            'success': True,
            'valid': is_valid,
            'message': 'CAPTCHA válido' if is_valid else 'CAPTCHA inválido'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al validar CAPTCHA: {str(e)}'
        }), 500

@auth_bp.route("/api/auth/register/residente", methods=["POST"])
def api_register_residente():
    """Registro de residente para aplicación móvil"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos JSON'
            }), 400
        
        # Obtener datos del JSON
        nombre = data.get("nombre")
        ap_paterno = data.get("ap_paterno")
        ap_materno = data.get("ap_materno")
        correo = data.get("correo")
        telefono = data.get("telefono")
        piso = data.get("piso")
        nro_departamento = data.get("nro_departamento")
        password = data.get("password")
        
        print(f"🔍 DEBUG API Register - Datos recibidos:")
        print(f"Nombre: {nombre}, Correo: {correo}, Departamento: {nro_departamento}-{piso}")
        
        # Validaciones básicas
        if not all([nombre, ap_paterno, correo, telefono, piso, nro_departamento, password]):
            missing = [field for field in ['nombre', 'ap_paterno', 'correo', 'telefono', 'piso', 'nro_departamento', 'password'] if not data.get(field)]
            return jsonify({
                'success': False,
                'message': f'Campos obligatorios faltantes: {", ".join(missing)}'
            }), 400
        
        # Validar contraseña
        if not es_contrasena_valida(password):
            return jsonify({
                'success': False,
                'message': 'La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial.'
            }), 400
        
        # Validar correo
        if not es_correo_valido(correo):
            return jsonify({
                'success': False,
                'message': 'El correo electrónico no es válido.'
            }), 400
        
        # Validar teléfono
        if not es_telefono_valido(telefono):
            return jsonify({
                'success': False,
                'message': 'El número de teléfono no es válido.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si el correo ya existe
        cursor.execute("SELECT id_usuario FROM usuario WHERE correo = %s", (correo,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'El correo electrónico ya está registrado.'
            }), 400
        
        # Verificar si el departamento ya está ocupado
        cursor.execute("""
            SELECT id_usuario FROM residente 
            WHERE piso = %s AND nro_departamento = %s
        """, (piso, nro_departamento))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Este departamento ya tiene un residente registrado.'
            }), 400
        
        # Hash de la contraseña
        hashed_password = generate_password_hash(password)
        
        # Insertar nuevo usuario
        cursor.execute("""
            INSERT INTO usuario 
            (nombre, ap_paterno, ap_materno, correo, telefono, contrasena, id_rol)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_usuario
        """, (nombre, ap_paterno, ap_materno, correo, telefono, hashed_password, 3))
        
        id_usuario = cursor.fetchone()[0]
        
        # Insertar en tabla RESIDENTE
        cursor.execute("""
            INSERT INTO residente (id_usuario, nro_departamento, piso, fecha_ingreso)
            VALUES (%s, %s, %s, CURRENT_DATE)
        """, (id_usuario, nro_departamento, piso))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Registro exitoso. Ahora puedes iniciar sesión.'
        }), 201
        
    except Exception as e:
        print(f"❌ ERROR en api_register_residente: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        return jsonify({
            'success': False,
            'message': f'Error al registrar: {str(e)}'
        }), 500

@auth_bp.route("/api/auth/solicitar_codigo", methods=["POST"])
def api_solicitar_codigo():
    """Solicitar código de invitación para móvil"""
    try:
        data = request.get_json()
        correo = data.get("correo")
        rol = data.get("rol")
        
        if not correo or not rol:
            return jsonify({
                'success': False,
                'message': 'Correo y rol son obligatorios'
            }), 400
        
        # Usar tu función existente de invitaciones
        codigo_generado = crear_invitacion(correo)
        
        return jsonify({
            'success': True,
            'message': f'Código de invitación enviado a {correo}',
            'codigo': codigo_generado  # Solo para testing, en producción no enviar
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al enviar código: {str(e)}'
        }), 500

@auth_bp.route("/api/auth/validar_codigo", methods=["POST"])
def api_validar_codigo():
    """Validar código de invitación para móvil"""
    try:
        data = request.get_json()
        codigo = data.get("codigo")
        rol = data.get("rol")
        
        if not codigo:
            return jsonify({
                'success': False,
                'message': 'Código es obligatorio'
            }), 400
        
        resultado = validar_codigo(codigo)
        
        if resultado and resultado["estado"] == True:
            return jsonify({
                'success': True,
                'valido': True,
                'message': 'Código válido. Puedes continuar con el registro.'
            }), 200
        else:
            return jsonify({
                'success': True,  # La petición fue exitosa pero el código es inválido
                'valido': False,
                'message': 'Código inválido o expirado.'
            }), 200
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al validar código: {str(e)}'
        }), 500

@auth_bp.route("/api/auth/test", methods=["POST"])
def api_test_auth():
    """Endpoint simple de prueba"""
    try:
        return jsonify({
            'success': True,
            'message': 'API de auth funcionando correctamente',
            'timestamp': datetime.datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# =============================================================================
# ENDPOINTS ORIGINALES PARA SISTEMA WEB
# =============================================================================

@auth_bp.route("/", methods=["GET", "POST"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login para sistema web"""
    if request.method == "POST":
        correo = request.form.get("correo")
        password = request.form.get("password")
        captcha_usuario = request.form.get("captcha", "")
        captcha_sesion = session.get("captcha", "")

        # Verificar CAPTCHA en backend
        if captcha_usuario.strip().upper() != captcha_sesion.strip().upper():
            flash("CAPTCHA incorrecto.", "danger")
            session["captcha"] = generar_captcha()
            return render_template("login.html", captcha_text=session["captcha"])

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuario WHERE correo=%s", (correo,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            usuario = Usuario(row)
            # Verifica la contraseña
            if check_password_hash(usuario.contrasena, password):
                login_user(usuario)
                flash("Usuario y contraseña correctos.", "success")
                # Redirige según el rol
                if usuario.id_rol == 3:  # Residente
                    return redirect(url_for("residentes.dashboard"))
                elif usuario.id_rol == 2:  # Empleado
                   return redirect(url_for("empleados.dashboard"))
                elif usuario.id_rol == 1:  # Administrador
                    return redirect(url_for("admin.panel_admin"))
                else:
                    flash("Rol no reconocido.", "danger")
            else:
                flash("Contraseña incorrecta.", "danger")
        else:
            flash("Usuario no encontrado.", "danger")

        session["captcha"] = generar_captcha()
        return render_template("login.html", captcha_text=session["captcha"])

    session["captcha"] = generar_captcha()
    return render_template("login.html", captcha_text=session["captcha"])

@auth_bp.route("/logout")
def logout():
    """Cerrar sesión"""
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/register/residente", methods=["GET", "POST"])
def register_residente():
    """Registro de residente para sistema web"""
    if request.method == "POST":
        # Obtener datos del formulario
        nombre = request.form.get("nombre")
        ap_paterno = request.form.get("ap_paterno")
        ap_materno = request.form.get("ap_materno")
        correo = request.form.get("correo")
        telefono = request.form.get("telefono")
        piso = request.form.get("piso")
        nro_departamento = request.form.get("nro_departamento")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        print(f"🔍 DEBUG - Datos recibidos:")
        print(f"Nombre: {nombre}")
        print(f"Ap Paterno: {ap_paterno}") 
        print(f"Ap Materno: {ap_materno}")
        print(f"Correo: {correo}")
        print(f"Teléfono: {telefono}")
        print(f"Piso: {piso}")
        print(f"Departamento: {nro_departamento}")
        print(f"Password: {'*' * len(password) if password else 'None'}")
        
        # Validaciones básicas
        if not all([nombre, ap_paterno, correo, telefono, piso, nro_departamento, password]):
            missing = [field for field in ['nombre', 'ap_paterno', 'correo', 'telefono', 'piso', 'nro_departamento', 'password'] if not request.form.get(field)]
            print(f"❌ Campos faltantes: {missing}")
            flash("Todos los campos son obligatorios.", "danger")
            return render_template("residente/register_residente.html", 
                                 user_data=request.form)
        
        if password != confirm_password:
            print("❌ Contraseñas no coinciden")
            flash("Las contraseñas no coinciden.", "danger")
            return render_template("residente/register_residente.html", 
                                 user_data=request.form)
        
        # Validar contraseña
        if not es_contrasena_valida(password):
            print("❌ Contraseña no válida")
            flash("La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial.", "danger")
            return render_template("residente/register_residente.html", 
                                 user_data=request.form)
        
        # Validar correo
        if not es_correo_valido(correo):
            print("❌ Correo no válido")
            flash("El correo electrónico no es válido.", "danger")
            return render_template("residente/register_residente.html", 
                                 user_data=request.form)
        
        # Validar teléfono
        if not es_telefono_valido(telefono):
            print("❌ Teléfono no válido")
            flash("El número de teléfono no es válido.", "danger")
            return render_template("residente/register_residente.html", 
                                 user_data=request.form)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            print("✅ Conexión a BD establecida")
            
            # Verificar si el correo ya existe
            cursor.execute("SELECT id_usuario FROM usuario WHERE correo = %s", (correo,))
            if cursor.fetchone():
                print("❌ Correo ya existe")
                flash("El correo electrónico ya está registrado.", "danger")
                return render_template("residente/register_residente.html", 
                                     user_data=request.form)
            
            print("✅ Correo no existe en BD")
            
            # Verificar si el departamento ya está ocupado en la tabla RESIDENTE
            cursor.execute("""
                SELECT id_usuario FROM residente 
                WHERE piso = %s AND nro_departamento = %s
            """, (piso, nro_departamento))
            if cursor.fetchone():
                print("❌ Departamento ya ocupado")
                flash("Este departamento ya tiene un residente registrado.", "danger")
                return render_template("residente/register_residente.html", 
                                     user_data=request.form)
            
            print("✅ Departamento disponible")
            
            # Hash de la contraseña
            hashed_password = generate_password_hash(password)
            print("✅ Contraseña hasheada")
            
            # Insertar nuevo usuario en tabla USUARIO (sin piso y nro_departamento)
            print("🔄 Intentando INSERT en usuario...")
            cursor.execute("""
                INSERT INTO usuario 
                (nombre, ap_paterno, ap_materno, correo, telefono, contrasena, id_rol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id_usuario
            """, (nombre, ap_paterno, ap_materno, correo, telefono, hashed_password, 3))
            
            # Obtener el ID del usuario insertado
            id_usuario = cursor.fetchone()[0]
            print(f"✅ Usuario insertado con ID: {id_usuario}")
            
            # Insertar en tabla RESIDENTE con los datos de departamento
            print("🔄 Intentando INSERT en residente...")
            cursor.execute("""
                INSERT INTO residente (id_usuario, nro_departamento, piso, fecha_ingreso)
                VALUES (%s, %s, %s, CURRENT_DATE)
            """, (id_usuario, nro_departamento, piso))
            
            print("✅ Registro en tabla residente exitoso")
            
            conn.commit()
            print("✅ Commit realizado - Registro COMPLETADO")
            flash("Registro exitoso. Ahora puedes iniciar sesión.", "success")
            return redirect(url_for("auth.login"))
            
        except Exception as e:
            print(f"❌ ERROR en registro: {str(e)}")
            import traceback
            print(f"📋 Traceback completo: {traceback.format_exc()}")
            if 'conn' in locals():
                conn.rollback()
            flash(f"Error al registrar: {str(e)}", "danger")
            return render_template("residente/register_residente.html", 
                                 user_data=request.form)
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
            print("🔚 Conexión cerrada")
    
    # GET request - mostrar formulario vacío
    return render_template("residente/register_residente.html")

@auth_bp.route("/seleccionar_registro")
def seleccionar_registro():
    """Seleccionar tipo de registro"""
    return render_template("seleccionar_registro.html")

@auth_bp.route("/verificar_codigo/<rol>", methods=["GET", "POST"])
def verificar_codigo(rol):
    """Verificar código de invitación"""
    if request.method == "POST":
        accion = request.form.get("accion")
        correo = request.form.get("correo")
        codigo = request.form.get("codigo")

        if accion == "solicitar" and correo:
            try:
                codigo_generado = crear_invitacion(correo)
                flash(f"✅ Código de invitación enviado a {correo}", "success")
            except Exception as e:
                flash(f"Error al enviar el código: {str(e)}", "danger")
                
        elif accion == "validar" and codigo:
            resultado = validar_codigo(codigo)
            if resultado and resultado["estado"] == True:
                marcar_codigo_como_usado(codigo)
                flash("✅ Código válido. Puedes continuar con el registro.", "success")
                
                print(f"🔍 DEBUG - Rol recibido: {rol}")
                
                # USAR LOS NOMBRES EXACTOS DE TU BD
                if rol == "empleado":
                    print("🔄 Redirigiendo a registro empleado")
                    return redirect(url_for("auth.register_empleado"))
                elif rol == "Administrador":  # ← CON MAYÚSCULA
                    print("🔄 Redirigiendo a registro admin")
                    return redirect(url_for("auth.register_admin"))
                else:
                    flash(f"Rol no válido: {rol}", "danger")
                    return redirect(url_for("auth.seleccionar_registro"))
            else:
                flash("❌ Código inválido o expirado.", "danger")

    return render_template("verificar_codigo.html", rol=rol)

@auth_bp.route("/verificar_captcha", methods=["POST"])
def verificar_captcha():
    """Verificar CAPTCHA para sistema web"""
    data = request.get_json()
    captcha_usuario = data.get("captcha", "")
    captcha_sesion = session.get("captcha", "")
    valido = captcha_usuario.strip().upper() == captcha_sesion.strip().upper()
    return jsonify({"valido": valido})

@auth_bp.route("/residente/ingresar_base")
@login_required
def ingresar_base():
    """Ingresar base para residentes"""
    if current_user.id_rol != 3:
        flash("Acceso solo para residentes.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("residente/ingresar_bae.html")

@auth_bp.route("/residente/guardar_base", methods=["POST"])
@login_required
def residente_guardar_base():
    """Guardar base para residentes"""
    if current_user.id_rol != 3:
        flash("Acceso solo para residentes.", "danger")
        return redirect(url_for("auth.login"))
    # Aquí va la lógica para guardar la base
    nombre_base = request.form.get("nombre_base")
    descripcion = request.form.get("descripcion")
    fecha = request.form.get("fecha")
    # ...guardar en la base de datos...
    flash("Base guardada correctamente.", "success")
    return redirect(url_for("auth.ingresar_base"))

@auth_bp.route("/register/empleado", methods=["GET", "POST"])
def register_empleado():
    """Registro de empleado para sistema web"""
    if request.method == "POST":
        # Obtener datos del formulario
        nombre = request.form.get("nombre")
        ap_paterno = request.form.get("ap_paterno")
        ap_materno = request.form.get("ap_materno")
        correo = request.form.get("correo")
        telefono = request.form.get("telefono")
        puesto = request.form.get("puesto")
        salario = request.form.get("salario")
        fecha_contratacion = request.form.get("fecha_contratacion")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        print(f"🔍 DEBUG - Registro empleado:")
        print(f"Puesto: {puesto}, Salario: {salario}, Fecha: {fecha_contratacion}")
        
        # Validaciones básicas
        if not all([nombre, ap_paterno, correo, telefono, puesto, salario, fecha_contratacion, password]):
            missing = [field for field in ['nombre', 'ap_paterno', 'correo', 'telefono', 'puesto', 'salario', 'fecha_contratacion', 'password'] if not request.form.get(field)]
            print(f"❌ Campos faltantes: {missing}")
            flash("Todos los campos son obligatorios.", "danger")
            return render_template("empleado/register_empleado.html", user_data=request.form)
        
        if password != confirm_password:
            print("❌ Contraseñas no coinciden")
            flash("Las contraseñas no coinciden.", "danger")
            return render_template("empleado/register_empleado.html", user_data=request.form)
        
        # Validar contraseña
        if not es_contrasena_valida(password):
            print("❌ Contraseña no válida")
            flash("La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial.", "danger")
            return render_template("empleado/register_empleado.html", user_data=request.form)
        
        # Validar correo
        if not es_correo_valido(correo):
            print("❌ Correo no válido")
            flash("El correo electrónico no es válido.", "danger")
            return render_template("empleado/register_empleado.html", user_data=request.form)
        
        # Validar teléfono
        if not es_telefono_valido(telefono):
            print("❌ Teléfono no válido")
            flash("El número de teléfono no es válido.", "danger")
            return render_template("empleado/register_empleado.html", user_data=request.form)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            print("✅ Conexión a BD establecida")
            
            # Verificar si el correo ya existe
            cursor.execute("SELECT id_usuario FROM usuario WHERE correo = %s", (correo,))
            if cursor.fetchone():
                print("❌ Correo ya existe")
                flash("El correo electrónico ya está registrado.", "danger")
                return render_template("empleado/register_empleado.html", user_data=request.form)
            
            print("✅ Correo no existe en BD")
            
            # Hash de la contraseña
            hashed_password = generate_password_hash(password)
            print("✅ Contraseña hasheada")
            
            # Insertar nuevo usuario en tabla USUARIO (id_rol = 2 para empleados)
            print("🔄 Intentando INSERT en usuario...")
            cursor.execute("""
                INSERT INTO usuario 
                (nombre, ap_paterno, ap_materno, correo, telefono, contrasena, id_rol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id_usuario
            """, (nombre, ap_paterno, ap_materno, correo, telefono, hashed_password, 2))
            
            # Obtener el ID del usuario insertado
            id_usuario = cursor.fetchone()[0]
            print(f"✅ Usuario insertado con ID: {id_usuario}")
            
            # Insertar en tabla EMPLEADO
            print("🔄 Intentando INSERT en empleado...")
            cursor.execute("""
                INSERT INTO empleado (id_usuario, puesto, salario, fecha_contratacion)
                VALUES (%s, %s, %s, %s)
            """, (id_usuario, puesto, salario, fecha_contratacion))
            
            print("✅ Registro en tabla empleado exitoso")
            
            conn.commit()
            print("✅ Commit realizado - Registro COMPLETADO")
            flash("✅ Empleado registrado exitosamente.", "success")
            return redirect(url_for("auth.login"))
            
        except Exception as e:
            print(f"❌ ERROR en registro empleado: {str(e)}")
            import traceback
            print(f"📋 Traceback completo: {traceback.format_exc()}")
            if 'conn' in locals():
                conn.rollback()
            flash(f"Error al registrar empleado: {str(e)}", "danger")
            return render_template("empleado/register_empleado.html", user_data=request.form)
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
            print("🔚 Conexión cerrada")
    
    # GET request - mostrar formulario vacío
    return render_template("empleado/register_empleado.html")

@auth_bp.route("/register/admin", methods=["GET", "POST"])
def register_admin():
    """Registro de administrador para sistema web"""
    if request.method == "POST":
        # Obtener datos del formulario
        nombre = request.form.get("nombre")
        ap_paterno = request.form.get("ap_paterno")
        ap_materno = request.form.get("ap_materno")
        correo = request.form.get("correo")
        telefono = request.form.get("telefono")
        cargo = request.form.get("cargo")
        fecha_asignacion = request.form.get("fecha_asignacion")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        print(f"🔍 DEBUG - Registro administrador:")
        print(f"Cargo: {cargo}, Fecha: {fecha_asignacion}")
        
        # Validaciones básicas
        if not all([nombre, ap_paterno, correo, telefono, cargo, fecha_asignacion, password]):
            missing = [field for field in ['nombre', 'ap_paterno', 'correo', 'telefono', 'cargo', 'fecha_asignacion', 'password'] if not request.form.get(field)]
            print(f"❌ Campos faltantes: {missing}")
            flash("Todos los campos son obligatorios.", "danger")
            return render_template("administrador/register_admin.html", user_data=request.form)
        
        if password != confirm_password:
            print("❌ Contraseñas no coinciden")
            flash("Las contraseñas no coinciden.", "danger")
            return render_template("administrador/register_admin.html", user_data=request.form)
        
        # Validar contraseña
        if not es_contrasena_valida(password):
            print("❌ Contraseña no válida")
            flash("La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial.", "danger")
            return render_template("administrador/register_admin.html", user_data=request.form)
        
        # Validar correo
        if not es_correo_valido(correo):
            print("❌ Correo no válido")
            flash("El correo electrónico no es válido.", "danger")
            return render_template("administrador/register_admin.html", user_data=request.form)
        
        # Validar teléfono
        if not es_telefono_valido(telefono):
            print("❌ Teléfono no válido")
            flash("El número de teléfono no es válido.", "danger")
            return render_template("administrador/register_admin.html", user_data=request.form)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            print("✅ Conexión a BD establecida")
            
            # Verificar si el correo ya existe
            cursor.execute("SELECT id_usuario FROM usuario WHERE correo = %s", (correo,))
            if cursor.fetchone():
                print("❌ Correo ya existe")
                flash("El correo electrónico ya está registrado.", "danger")
                return render_template("admin/register_admin.html", user_data=request.form)
            
            print("✅ Correo no existe en BD")
            
            # Hash de la contraseña
            hashed_password = generate_password_hash(password)
            print("✅ Contraseña hasheada")
            
            # Insertar nuevo usuario en tabla USUARIO (id_rol = 1 para administradores)
            print("🔄 Intentando INSERT en usuario...")
            cursor.execute("""
                INSERT INTO usuario 
                (nombre, ap_paterno, ap_materno, correo, telefono, contrasena, id_rol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id_usuario
            """, (nombre, ap_paterno, ap_materno, correo, telefono, hashed_password, 1))
            
            # Obtener el ID del usuario insertado
            id_usuario = cursor.fetchone()[0]
            print(f"✅ Usuario insertado con ID: {id_usuario}")
            
            # Insertar en tabla ADMINISTRADOR
            print("🔄 Intentando INSERT en administrador...")
            cursor.execute("""
                INSERT INTO administrador (id_usuario, cargo, fecha_asignacion)
                VALUES (%s, %s, %s)
            """, (id_usuario, cargo, fecha_asignacion))
            
            print("✅ Registro en tabla administrador exitoso")
            
            conn.commit()
            print("✅ Commit realizado - Registro COMPLETADO")
            flash("✅ Administrador registrado exitosamente.", "success")
            return redirect(url_for("auth.login"))
            
        except Exception as e:
            print(f"❌ ERROR en registro administrador: {str(e)}")
            import traceback
            print(f"📋 Traceback completo: {traceback.format_exc()}")
            if 'conn' in locals():
                conn.rollback()
            flash(f"Error al registrar administrador: {str(e)}", "danger")
            return render_template("administrador/register_admin.html", user_data=request.form)
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
            print("🔚 Conexión cerrada")
    
    # GET request - mostrar formulario vacío
    return render_template("administrador/register_admin.html")