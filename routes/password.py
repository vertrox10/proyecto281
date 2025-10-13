from flask import Blueprint, render_template, request, flash, url_for
from flask_mail import Message
from db import get_db_connection
import secrets, datetime

password_bp = Blueprint("password", __name__)

@password_bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        # lógica de recuperación
        # Importa mail aquí para evitar el import circular
        from app import mail
        # ...tu código para enviar el mail...
        pass
    return render_template("forgot_password.html")