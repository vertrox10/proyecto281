# models.py
from flask_login import UserMixin

class Usuario(UserMixin):
    def __init__(self, datos):
        self.id = datos["id_usuario"]
        self.nombre = datos["nombre"]
        self.ap_paterno = datos["ap_paterno"]
        self.ap_materno = datos["ap_materno"]
        self.correo = datos["correo"]
        self.id_rol = datos["id_rol"]

    def get_id(self):
        return str(self.id)