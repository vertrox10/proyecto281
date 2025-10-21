import random
import string
from datetime import datetime, timedelta
from flask_mail import Mail, Message
from db import get_db_connection
from flask import current_app

def generar_codigo_invitacion():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def crear_invitacion(correo_destino, estado=True, dias_expiracion=3):
    codigo = generar_codigo_invitacion()
    fecha_creacion = datetime.now()
    fecha_expiracion = fecha_creacion + timedelta(days=dias_expiracion)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO invitaciones (codigo, correo_destino, estado, fecha_creacion, fecha_expiracion)
        VALUES (%s, %s, %s, %s, %s)
    """, (codigo, correo_destino, estado, fecha_creacion, fecha_expiracion))
    conn.commit()
    cursor.close()
    conn.close()
    
    # Enviar el código por correo
    enviar_codigo_por_correo(correo_destino, codigo, dias_expiracion)
    
    return codigo

def enviar_codigo_por_correo(correo_destino, codigo, dias_expiracion):
    try:
        from flask import current_app
        mail = Mail(current_app)
        
        asunto = "Código de Invitación - Sistema de Residentes"
        mensaje = f"""
        <html>
        <body>
            <h2>Código de Invitación</h2>
            <p>Se ha generado un código de invitación para registrarte en el sistema de residentes.</p>
            
            <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #333; text-align: center;">Tu código de invitación es:</h3>
                <div style="font-size: 24px; font-weight: bold; text-align: center; color: #2c3e50; letter-spacing: 2px;">
                    {codigo}
                </div>
            </div>
            
            <p><strong>Este código expira en {dias_expiracion} días.</strong></p>
            
            <p>Por favor, ingresa este código en el formulario de registro para completar tu inscripción.</p>
            
            <hr>
            <p style="color: #666; font-size: 12px;">
                Este es un mensaje automático, por favor no respondas a este correo.
            </p>
        </body>
        </html>
        """
        
        msg = Message(
            subject=asunto,
            recipients=[correo_destino],
            html=mensaje,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        mail.send(msg)
        print(f"✅ Código enviado a: {correo_destino}")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando correo: {str(e)}")
        return False

def obtener_invitaciones_activas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, codigo, correo_destino, estado, fecha_creacion, fecha_expiracion
        FROM invitaciones
        WHERE estado = true AND fecha_expiracion > NOW()
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    codigos = [
        {
            "id": row[0],
            "codigo": row[1],
            "correo_destino": row[2],
            "estado": row[3],
            "fecha_creacion": row[4],
            "fecha_expiracion": row[5]
        }
        for row in rows
    ]
    return codigos

def validar_codigo(codigo):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, correo_destino, estado, fecha_expiracion
        FROM invitaciones
        WHERE codigo = %s AND estado = true AND fecha_expiracion > NOW()
    """, (codigo,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return {
            "id": row[0],
            "correo_destino": row[1],
            "estado": row[2],
            "fecha_expiracion": row[3]
        }
    return None

def marcar_codigo_como_usado(codigo):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE invitaciones SET estado = false WHERE codigo = %s
    """, (codigo,))
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