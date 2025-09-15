from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_bcrypt import Bcrypt

# Inicializar app
app = Flask(__name__)
app.secret_key = "supersecreto"  # Necesario para manejar sesiones

# Configuración Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'   # Cambia si usas otro proveedor
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tu_correo@gmail.com'  # 👈 tu correo
app.config['MAIL_PASSWORD'] = 'tu_password_app'      # 👈 contraseña de aplicación
app.config['MAIL_DEFAULT_SENDER'] = 'tu_correo@gmail.com'

mail = Mail(app)
bcrypt = Bcrypt(app)
s = URLSafeTimedSerializer(app.secret_key)


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


# 🔹 Página principal (login)
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form["correo"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuario WHERE correo=%s", (correo,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user["contrasena"], password):
            session["usuario"] = user["nombre"]
            flash("¡Bienvenido " + user["nombre"] + "!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Usuario o contraseña incorrectos", "danger")

        cursor.close()
        conn.close()

    return render_template("login.html")


# 🔹 Registro
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form["nombre"]
        ap_paterno = request.form["ap_paterno"]
        ap_materno = request.form["ap_materno"]
        correo = request.form["correo"]
        telefono = request.form["telefono"]
        password = request.form["password"]

        id_rol = 2  # rol fijo ejemplo usuario

        hashed = bcrypt.generate_password_hash(password).decode("utf-8")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usuario (nombre, ap_paterno, ap_materno, correo, telefono, contrasena, id_rol)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (nombre, ap_paterno, ap_materno, correo, telefono, hashed, id_rol))

        conn.commit()
        cursor.close()
        conn.close()

        flash("Usuario registrado con éxito. Ahora inicia sesión.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# 🔹 Dashboard (solo logueado)
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


# 🔹 Olvidé mi contraseña
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        correo = request.form["correo"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuario WHERE correo=%s", (correo,))
        user = cursor.fetchone()

        if user:
            token = s.dumps(correo, salt="reset-password")
            link = url_for("reset_password", token=token, _external=True)

            msg = Message("Recupera tu contraseña", recipients=[correo])
            msg.body = f"Hola {user['nombre']}, haz clic en el siguiente enlace para cambiar tu contraseña:\n{link}"
            mail.send(msg)

            flash("Se envió un enlace a tu correo para recuperar la contraseña.", "info")
        else:
            flash("Ese correo no está registrado.", "danger")

        cursor.close()
        conn.close()

    return render_template("forgot_password.html")


# 🔹 Resetear contraseña
@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        correo = s.loads(token, salt="reset-password", max_age=3600)
    except (SignatureExpired, BadSignature):
        flash("El enlace es inválido o ha expirado.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        nueva_contra = request.form["password"]
        hashed = bcrypt.generate_password_hash(nueva_contra).decode("utf-8")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuario SET contrasena=%s WHERE correo=%s", (hashed, correo))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Tu contraseña ha sido actualizada. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html")


if __name__ == "__main__":
    app.run(debug=True)
