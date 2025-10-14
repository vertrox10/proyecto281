from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from db import get_db_connection
from models import Usuario
from utils import generar_captcha, es_correo_valido, es_contrasena_valida, es_telefono_valido
from invitaciones import crear_invitacion, validar_codigo, marcar_codigo_como_usado

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/", methods=["GET", "POST"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
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
                    return redirect(url_for("auth.ingresar_base"))
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
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/register/residente", methods=["GET", "POST"])
def register_residente():
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
    return render_template("seleccionar_registro.html")

@auth_bp.route("/verificar_codigo/<rol>", methods=["GET", "POST"])
def verificar_codigo(rol):
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
    data = request.get_json()
    captcha_usuario = data.get("captcha", "")
    captcha_sesion = session.get("captcha", "")
    valido = captcha_usuario.strip().upper() == captcha_sesion.strip().upper()
    return jsonify({"valido": valido})

@auth_bp.route("/residente/ingresar_base")
@login_required
def ingresar_base():
    if current_user.id_rol != 3:
        flash("Acceso solo para residentes.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("residente/ingresar_base.html")

@auth_bp.route("/residente/guardar_base", methods=["POST"])
@login_required
def residente_guardar_base():
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
            return render_template("empleado/register_empleado.html", user_data=request.form)  # <- CORREGIDO
        
        if password != confirm_password:
            print("❌ Contraseñas no coinciden")
            flash("Las contraseñas no coinciden.", "danger")
            return render_template("empleado/register_empleado.html", user_data=request.form)  # <- CORREGIDO
        
        # Validar contraseña
        if not es_contrasena_valida(password):
            print("❌ Contraseña no válida")
            flash("La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial.", "danger")
            return render_template("empleado/register_empleado.html", user_data=request.form)  # <- CORREGIDO
        
        # Validar correo
        if not es_correo_valido(correo):
            print("❌ Correo no válido")
            flash("El correo electrónico no es válido.", "danger")
            return render_template("empleado/register_empleado.html", user_data=request.form)  # <- CORREGIDO
        
        # Validar teléfono
        if not es_telefono_valido(telefono):
            print("❌ Teléfono no válido")
            flash("El número de teléfono no es válido.", "danger")
            return render_template("empleado/register_empleado.html", user_data=request.form)  # <- CORREGIDO
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            print("✅ Conexión a BD establecida")
            
            # Verificar si el correo ya existe
            cursor.execute("SELECT id_usuario FROM usuario WHERE correo = %s", (correo,))
            if cursor.fetchone():
                print("❌ Correo ya existe")
                flash("El correo electrónico ya está registrado.", "danger")
                return render_template("empleado/register_empleado.html", user_data=request.form)  # <- CORREGIDO
            
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
            return render_template("empleado/register_empleado.html", user_data=request.form)  # <- CORREGIDO
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
            print("🔚 Conexión cerrada")
    
    # GET request - mostrar formulario vacío
    return render_template("empleado/register_empleado.html")  # <- CORREGIDO

@auth_bp.route("/register/admin", methods=["GET", "POST"])
def register_admin():
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

