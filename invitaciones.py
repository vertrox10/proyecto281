import random
import string
from flask import flash
from db import get_db_connection
def generar_codigo_invitacion():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def crear_invitacion(rol_destino):
    codigo = generar_codigo_invitacion()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO invitaciones (codigo, rol_destino)
        VALUES (%s, %s)
    """, (codigo, rol_destino))
    conn.commit()
    cursor.close()
    conn.close()
    return codigo

def obtener_invitaciones_activas():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM invitaciones WHERE usado = FALSE")
    codigos = cursor.fetchall()
    cursor.close()
    conn.close()
    return codigos

def validar_codigo(codigo):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT rol_destino FROM invitaciones WHERE codigo = %s AND usado = FALSE", (codigo,))
    invitacion = cursor.fetchone()
    cursor.close()
    conn.close()
    return invitacion

def marcar_codigo_como_usado(codigo):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE invitaciones SET usado = TRUE WHERE codigo = %s", (codigo,))
    conn.commit()
    cursor.close()
    conn.close()

def eliminar_invitacion(codigo):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM invitaciones WHERE codigo = %s", (codigo,))
    conn.commit()
    cursor.close()
    conn.close()



