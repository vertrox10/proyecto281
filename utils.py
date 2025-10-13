import random, string, re

def generar_captcha():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=5))

def es_correo_valido(correo):
    patron = r"^[\w\.-]+@([\w\.-]+)$"
    match = re.match(patron, correo)
    return match and match.group(1).lower() in ["gmail.com", "outlook.com"]

def es_telefono_valido(telefono):
    return re.fullmatch(r"\d{7,15}", telefono) is not None

def es_contrasena_valida(password):
    return (len(password) >= 8 and 
            re.search(r"[A-Z]", password) and 
            re.search(r"[a-z]", password) and 
            re.search(r"[0-9]", password))
