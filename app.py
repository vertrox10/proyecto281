from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecreto"  # Necesario para manejar sesiones


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


# 🔹 Login
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

        cursor.close()
        conn.close()

        if user and check_password_hash(user["contrasena"], password):
            session["usuario"] = user["nombre"]
            flash(f"¡Bienvenido {user['nombre']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Usuario o contraseña incorrectos", "danger")

    return render_template("login.html")


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
@app.route("/forgot_password")
def forgot_password():
    return "<h1>Página de recuperación de contraseña en construcción 🔧</h1>"


if __name__ == "__main__":
    app.run(debug=True)
