from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import random, string
from flask import send_file
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mail import Mail, Message
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import datetime
from flask import Flask
from flask_mail import Mail
from flask import request, jsonify, session

app = Flask(__name__)
app.secret_key = "supersecreto"  # Necesario para manejar sesiones

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'vc3070934@gmail.com'   # 👉 tu correo
app.config['MAIL_PASSWORD'] = 'fpnn mqpy itgk edhf'  # 👉 tu contraseña o app password
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)
# 🔹 Conexión a la base de datos
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="123456",
            database="bdedificio"
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print("❌ Error al conectar:", e)
        return None


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
            session["usuario"] = user["nombre"]
            flash(f"¡Bienvenido {user['nombre']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Usuario o contraseña incorrectos", "danger")

    # Generar captcha para GET o primer acceso
    session["captcha"] = generar_captcha()
    return render_template("login.html", captcha_text=session["captcha"])


# 🔹 Registro
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            nombre = request.form["nombre"]
            ap_paterno = request.form["ap_paterno"]
            ap_materno = request.form["ap_materno"]
            correo = request.form["correo"]
            telefono = request.form["telefono"]
            password = request.form["password"]

            # Encriptar contraseña
            hashed_password = generate_password_hash(password)

            id_rol = 2  # 👈 Rol por defecto = Usuario

            conn = get_db_connection()
            if not conn:
                flash("Error de conexión con la base de datos.", "danger")
                return redirect(url_for("register"))

            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usuario (nombre, ap_paterno, ap_materno, correo, telefono, contrasena, id_rol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (nombre, ap_paterno, ap_materno, correo, telefono, hashed_password, id_rol))

            conn.commit()
            flash("Usuario registrado con éxito. Ahora inicia sesión.", "success")

        except Error as e:
            print("❌ Error en register:", e)
            flash("Error al registrar: " + str(e), "danger")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# 🔹 Dashboard
@app.route("/dashboard")
def dashboard():
    if "usuario" in session:
        return render_template("dashboard.html", usuario=session["usuario"])
    else:
        return redirect(url_for("login"))


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


if __name__ == "__main__":
    app.run(debug=True)

