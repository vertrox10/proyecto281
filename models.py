from flask_login import UserMixin

class Usuario(UserMixin):
    def __init__(self, datos):
        self.id = datos[0]            # id_usuario
        self.nombre = datos[1]        # nombre
        self.ap_paterno = datos[2]    # ap_paterno
        self.ap_materno = datos[3]    # ap_materno
        self.correo = datos[4]        # correo
        self.contrasena = datos[6]    # contrasena
        self.id_rol = datos[7]        # id_rol

    def get_id(self):
        return str(self.id)
