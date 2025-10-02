from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify, abort
from flask_mail import Mail, Message
from flask_login import LoginManager, login_required, login_user, logout_user, current_user, UserMixin
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import random, string, secrets, datetime, re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from invitaciones import crear_invitacion, validar_codigo, marcar_codigo_como_usado
from db import get_db_connection
from flask_mail import Mail, Message
from flask_login import LoginManager, login_required, login_user, logout_user, current_user, UserMixin
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import random, string, secrets, datetime, re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from invitaciones import crear_invitacion, validar_codigo, marcar_codigo_como_usado
from db import get_db_connection
from models import Usuario





app = Flask(__name__)
app.secret_key = "supersecreto"  # Necesario para manejar sesiones

# Rutas vacías para las secciones del menú
@app.route('/finanzas')
@login_required
def finanzas():
    return render_template('finanzas.html')

@app.route('/consumos')
@login_required
def consumos():
    return render_template('consumos.html')

@app.route('/reservas')
@login_required
def reservas():
    return render_template('reservas.html')

@app.route('/tickets')
@login_required
def tickets():
    return render_template('tickets.html')

# Ruta para cambiar el rol de un usuario
@app.route('/cambiar_rol', methods=['POST'])
@login_required
def cambiar_rol():
    id_usuario = request.form.get('id_usuario')
    nuevo_rol = request.form.get('nuevo_rol')
    if not id_usuario or not nuevo_rol:
        flash('Datos incompletos para cambiar el rol.', 'danger')
        return redirect(url_for('usuarios'))
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuario SET id_rol = %s WHERE id_usuario = %s", (nuevo_rol, id_usuario))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Rol actualizado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al actualizar el rol: {e}', 'danger')
    return redirect(url_for('usuarios'))

# Ruta para usuarios (debe ir después de crear app)
@app.route('/usuarios')
@login_required
def usuarios():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_usuario, nombre, ap_paterno, ap_materno, correo, telefono, id_rol FROM usuario WHERE id_rol = 2")
    empleados = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('usuarios.html', empleados=empleados)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'vc3070934@gmail.com'   # 👉 tu correo
app.config['MAIL_PASSWORD'] = 'fpnn mqpy itgk edhf'  # 👉 tu contraseña o app password
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # 👈 nombre de tu vista de login



mail = Mail(app)


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuario WHERE id_usuario = %s", (user_id,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()
    if data:
        return Usuario(data)  # 👈 asegúrate de tener esta clase definida
    return None

@app.route('/enviar_invitacion', methods=['POST'])
@login_required
def enviar_invitacion():
    if current_user.id_rol != 1:
        abort(403)

    correo = request.form['correo']
    rol_destino = 'empleado'  # 👈 fijo para empleados
    codigo = crear_invitacion(rol_destino)

    mensaje = Message(
        subject="Invitación para registrarte",
        recipients=[correo],
        body=f"""
Hola,

Has sido invitado a registrarte como empleado en la plataforma.
Usa el siguiente código de invitación: {codigo}

Ingresa a: http://localhost:5000/register
""")
    mail.send(mensaje)
    from invitaciones import obtener_invitaciones_activas
    codigos = obtener_invitaciones_activas()
    return render_template("dashboard_admin.html", usuario=current_user, codigos=codigos)



# 🔹 Generar Captcha aleatorio
def generar_captcha():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

# 🔹 Ruta para generar captcha en imagen
@app.route("/captcha")
def captcha():
    captcha_text = session.get("captcha", generar_captcha())
    session["captcha"] = captcha_text  # asegurar que esté en sesión

    # Crear imagen
    img = Image.new("RGB", (150, 60), color=(255, 255, 255))
    d = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 36)  # 👈 usa Arial (asegúrate que exista)
    except:
        font = ImageFont.load_default()

    d.text((10, 10), captcha_text, font=font, fill=(0, 0, 0))

    # Guardar en memoria
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return send_file(buffer, mimetype="image/png")


# 🔹 Login
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form["correo"]
        password = request.form["password"]
        captcha_usuario = request.form["captcha"]

        # Verificar captcha (insensible a mayúsculas)
        if captcha_usuario.upper() != session.get("captcha", ""):
            flash("Captcha incorrecto ❌. Intenta de nuevo.", "danger")
            session["captcha"] = generar_captcha()  # regenerar captcha
            return render_template("login.html", captcha_text=session["captcha"])

        conn = get_db_connection()
        if not conn:
            flash("Error de conexión con la base de datos.", "danger")
            return render_template("login.html", captcha_text=session["captcha"])

        cursor = conn.cursor(dictionary=True)
        user = None

        try:
            cursor.execute("SELECT * FROM usuario WHERE correo=%s", (correo,))
            user = cursor.fetchone()
        except Error as e:
            print("❌ Error en login:", e)
            flash("Error al consultar usuario.", "danger")
        finally:
            cursor.close()
            conn.close()

        if user and check_password_hash(user["contrasena"], password):
            usuario_obj = Usuario(user)
            login_user(usuario_obj)
            flash(f"¡Bienvenido {user['nombre']}!", "success")
            return redirect(url_for("panel_admin"))
        else:
            flash("Usuario o contraseña incorrectos", "danger")

    # Generar captcha para GET o primer acceso
    session["captcha"] = generar_captcha()
    return render_template("login.html", captcha_text=session["captcha"])


# 🔹 Registro
def es_correo_valido(correo):
    patron = r"^[\w\.-]+@([\w\.-]+)$"
    match = re.match(patron, correo)
    if not match:
        return False

    dominio = match.group(1).lower()
    dominios_permitidos = ["gmail.com", "outlook.com"]

    return dominio in dominios_permitidos


@app.route("/register", methods=["GET", "POST"])
def register():
    # Solo permitir acceso si el código está en sesión
    codigo_invitacion = session.get("codigo_invitacion")
    if not codigo_invitacion:
        return redirect(url_for("verificar_codigo"))

    if request.method == "POST":
        nombre = request.form["nombre"]
        ap_paterno = request.form["ap_paterno"]
        ap_materno = request.form["ap_materno"]
        correo = request.form["correo"].lower().strip()
        telefono = request.form["telefono"]
        password = request.form["password"]

        if not es_correo_valido(correo):
            flash("Formato de correo inválido ❌", "danger")
            return redirect(url_for("register"))
        if not es_contrasena_valida(password):
            flash("La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula y un número ❌", "danger")
            return redirect(url_for("register"))
        if not es_telefono_valido(telefono):
            flash("El teléfono debe contener solo números (7 a 15 dígitos) ❌", "danger")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        if not conn:
            flash("Error de conexión con la base de datos.", "danger")
            return redirect(url_for("register"))

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT 1 FROM usuario WHERE correo = %s", (correo,))
            if cursor.fetchone():
                flash("Este correo ya está registrado ❌", "danger")
                return redirect(url_for("register"))
            cursor.close()

            # Validar el código de invitación
            from invitaciones import validar_codigo, marcar_codigo_como_usado
            invitacion = validar_codigo(codigo_invitacion)
            if not invitacion or invitacion["rol_destino"] != "empleado":
                flash("Código inválido o no autorizado ❌", "danger")
                return redirect(url_for("verificar_codigo"))
            id_rol = 2  # Rol empleado

            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usuario (nombre, ap_paterno, ap_materno, correo, telefono, contrasena, id_rol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (nombre, ap_paterno, ap_materno, correo, telefono, hashed_password, id_rol))

            conn.commit()
            flash("Usuario registrado con éxito ✅. Ahora inicia sesión.", "success")
            marcar_codigo_como_usado(codigo_invitacion)
            session.pop("codigo_invitacion", None)

        except Error as e:
            print("❌ Error en register:", e)
            flash("Error al registrar: " + str(e), "danger")

        finally:
            if cursor: cursor.close()
            if conn: conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")

def es_telefono_valido(telefono):
    return re.fullmatch(r"\d{7,15}", telefono) is not None

def es_contrasena_valida(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):  # Mayúscula
        return False
    if not re.search(r"[a-z]", password):  # Minúscula
        return False
    if not re.search(r"[0-9]", password):  # Número
        return False
    return True


# 🔹 Dashboard
@app.route("/dashboard")
def dashboard():
    if "usuario" in session:
        return render_template("dashboard_admin.html", usuario=session["usuario"])
    else:
        return redirect(url_for("login"))

# 🔹 Panel Admin
@app.route("/panel_admin")
@login_required
def panel_admin():
    from invitaciones import obtener_invitaciones_activas
    codigos = obtener_invitaciones_activas()
    return render_template("dashboard_admin.html", usuario=current_user, codigos=codigos)


# 🔹 Logout
@app.route("/logout")
def logout():
    session.pop("usuario", None)
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("login"))


# 🔹 Recuperación de contraseña
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        correo = request.form["correo"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuario WHERE correo=%s", (correo,))
        user = cursor.fetchone()

        if user:
            token = secrets.token_urlsafe(32)
            expiration = datetime.datetime.now() + datetime.timedelta(hours=1)

            cursor.execute("""
                UPDATE usuario 
                SET reset_token=%s, token_expiration=%s
                WHERE correo=%s
            """, (token, expiration, correo))
            conn.commit()

            reset_url = url_for("reset_password", token=token, _external=True)

            msg = Message("Recuperación de contraseña",
                          sender=app.config["MAIL_USERNAME"],
                          recipients=[correo])
            msg.body = f"Hola {user['nombre']},\n\nUsa este enlace para restablecer tu contraseña:\n{reset_url}\n\nEste enlace expira en 1 hora."
            mail.send(msg)

            flash("Se ha enviado un enlace de recuperación a tu correo.", "success")
        else:
            flash("Correo no encontrado.", "danger")

        cursor.close()
        conn.close()

    return render_template("forgot_password.html")

@app.route('/generar_invitacion', methods=['POST'])
@login_required
def generar_invitacion():
    if current_user.id_rol != 1:
        abort(403)
    rol_destino = request.form['rol_destino']
    codigo = crear_invitacion(rol_destino)
    flash(f"Código generado: {codigo} para rol {rol_destino}", "success")
    return redirect('/panel_admin')

# 🔹 Restablecer contraseña
@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuario WHERE reset_token=%s", (token,))
    user = cursor.fetchone()

    if not user:
        flash("Token inválido.", "danger")
        return redirect(url_for("forgot_password"))

    if datetime.datetime.now() > user["token_expiration"]:
        flash("El enlace ha expirado.", "danger")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        new_password = request.form["password"]
        hashed_password = generate_password_hash(new_password)

        cursor.execute("""
            UPDATE usuario 
            SET contrasena=%s, reset_token=NULL, token_expiration=NULL
            WHERE id_usuario=%s
        """, (hashed_password, user["id_usuario"]))
        conn.commit()

        flash("Tu contraseña ha sido cambiada con éxito.", "success")
        return redirect(url_for("login"))

    cursor.close()
    conn.close()
    return render_template("reset_password.html")

@app.route("/verificar_captcha", methods=["POST"])
def verificar_captcha():
    data = request.get_json()
    captcha_ingresado = data.get("captcha", "")
    captcha_correcto = session.get("captcha", "")

    return jsonify({"valido": captcha_ingresado == captcha_correcto})


# 🔹 Verificar código de invitación antes del registro
@app.route('/verificar_codigo', methods=['GET', 'POST'])
def verificar_codigo():
    if request.method == 'POST':
        codigo = request.form['codigo'].strip()
        from invitaciones import validar_codigo
        invitacion = validar_codigo(codigo)
        if invitacion:
            session['codigo_invitacion'] = codigo
            return redirect(url_for('register'))
        else:
            flash('Código inválido o ya usado ❌', 'danger')
    return render_template('verificar_codigo.html')

@app.route('/empleados')
@login_required
def empleados():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT nombre, ap_paterno, ap_materno, correo, telefono FROM usuario WHERE id_rol = 2")
    empleados = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('empleados.html', empleados=empleados)

if __name__ == "__main__":
    app.run(debug=True)

