from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from flask_login import login_required, current_user, logout_user
from invitaciones import crear_invitacion, obtener_invitaciones_activas
from db import get_db_connection
from datetime import datetime
import pdfkit
from io import BytesIO

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/panel_admin")
@login_required
def panel_admin():
    # Verificar que el usuario sea administrador (id_rol = 1)
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta para sumar todos los consumos registrados desde enero 2024
        metricas_query = """
            SELECT SUM(cantidad_registrada) as consumo_total
            FROM (
                SELECT cantidad_registrada FROM consumo_agua WHERE fecha_registro >= '2024-01-01'
                UNION ALL
                SELECT cantidad_registrada FROM consumo_gas WHERE fecha_registro >= '2024-01-01'
                UNION ALL
                SELECT cantidad_registrada FROM consumo_luz WHERE fecha_registro >= '2024-01-01'
            ) as consumos
        """
        cursor.execute(metricas_query)
        consumo_total = cursor.fetchone()[0] or 0

        cursor.close()
        conn.close()

    except Exception as e:
        print("❌ ERROR EN /panel_admin:", str(e))
        consumo_total = 0

    return render_template("administrador/dashboard_admin.html", consumo_total=consumo_total)
## Eliminada función duplicada finanzas()

@admin_bp.route("/consumos")
@login_required
def consumos():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        current_date = datetime.now().strftime('%Y-%m-%d')
        current_month = datetime.now().strftime('%B %Y')

        def ejecutar_query(query):
            cursor.execute(query)
            columnas = [desc[0] for desc in cursor.description]
            return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]

        # 1. Sensor
        sensores_query = """
            SELECT id_sensor, id_area, id_departamento, num_serie, capacidad, disponibilidad, descripcion
            FROM sensor
            ORDER BY id_departamento, id_sensor
        """
        sensores_data = ejecutar_query(sensores_query)

        metricas_sensores_query = """
            SELECT 
                COUNT(*) as total_sensores,
                COUNT(CASE WHEN disponibilidad = true THEN 1 END) as sensores_activos,
                COUNT(DISTINCT id_departamento) as deptos_con_sensores
            FROM sensor
        """
        cursor.execute(metricas_sensores_query)
        columnas = [desc[0] for desc in cursor.description]
        metricas_sensores = dict(zip(columnas, cursor.fetchone()))

        # 2. Consumo Agua
        agua_query = """
            SELECT 
                id_consumo_agua as id_consumo,
                id_sensor,
                id_departamento,
                cantidad_registrada,
                lectura_inicial,
                lectura_final,
                fecha_registro,
                ROUND(lectura_final - lectura_inicial, 2) as consumo_calculado
            FROM consumo_agua 
            WHERE fecha_registro >= '2024-01-01'
            ORDER BY fecha_registro DESC
            LIMIT 30
        """
        agua_data = ejecutar_query(agua_query)

        # 3. Consumo Gas
        gas_query = """
            SELECT 
                id_consumo_gas as id_consumo,
                id_sensor,
                id_departamento,
                cantidad_registrada,
                lectura_inicial,
                lectura_final,
                fecha_registro,
                ROUND(lectura_final - lectura_inicial, 2) as consumo_calculado
            FROM consumo_gas 
            WHERE fecha_registro >= '2024-01-01'
            ORDER BY fecha_registro DESC
            LIMIT 30
        """
        gas_data = ejecutar_query(gas_query)

        # 4. Consumo Luz
        luz_query = """
            SELECT 
                id_consumo_luz as id_consumo,
                id_sensor,
                id_departamento,
                cantidad_registrada,
                lectura_inicial,
                lectura_final,
                fecha_registro,
                ROUND(lectura_final - lectura_inicial, 2) as consumo_calculado
            FROM consumo_luz 
            WHERE fecha_registro >= '2024-01-01'
            ORDER BY fecha_registro DESC
            LIMIT 30
        """
        luz_data = ejecutar_query(luz_query)

        # Combinar consumos
        todos_consumos = []
        for registro in agua_data:
            registro['servicio'] = 'agua'
            todos_consumos.append(registro)
        for registro in gas_data:
            registro['servicio'] = 'gas'
            todos_consumos.append(registro)
        for registro in luz_data:
            registro['servicio'] = 'luz'
            todos_consumos.append(registro)

        todos_consumos.sort(key=lambda x: x['fecha_registro'], reverse=True)

        # Métricas de consumo
        metricas_consumo_query = """
            SELECT 'agua' as servicio, COUNT(*) as total_registros, SUM(cantidad_registrada) as consumo_total
            FROM consumo_agua WHERE fecha_registro >= '2024-01-01'
            UNION ALL
            SELECT 'gas', COUNT(*), SUM(cantidad_registrada) FROM consumo_gas WHERE fecha_registro >= '2024-01-01'
            UNION ALL
            SELECT 'luz', COUNT(*), SUM(cantidad_registrada) FROM consumo_luz WHERE fecha_registro >= '2024-01-01'
        """
        metricas_consumo = ejecutar_query(metricas_consumo_query)

        def buscar(servicio, campo):
            return next((m[campo] for m in metricas_consumo if m['servicio'] == servicio), 0)

        agua = {
            "costo": 320,
            "variacion": -15,
            "consumo_total": buscar('agua', 'consumo_total'),
            "registros": buscar('agua', 'total_registros')
        }
        gas = {
            "costo": 180,
            "variacion": -5,
            "consumo_total": buscar('gas', 'consumo_total'),
            "registros": buscar('gas', 'total_registros')
        }
        luz = {
            "costo": 240,
            "variacion": -8,
            "consumo_total": buscar('luz', 'consumo_total'),
            "registros": buscar('luz', 'total_registros')
        }

        cursor.close()
        conn.close()

    except Exception as e:
        print("❌ ERROR EN /consumos:", str(e))
        flash(f"Error al cargar datos: {str(e)}", "danger")
        sensores_data = []
        todos_consumos = []
        metricas_sensores = None
        agua = {"costo": 0, "variacion": 0, "consumo_total": 0, "registros": 0}
        gas = {"costo": 0, "variacion": 0, "consumo_total": 0, "registros": 0}
        luz = {"costo": 0, "variacion": 0, "consumo_total": 0, "registros": 0}

    return render_template("administrador/consumos.html",
        agua=agua,
        gas=gas,
        luz=luz,
        sensores=sensores_data,
        consumos=todos_consumos,
        metricas_sensores=metricas_sensores,
        current_date=current_date,
        current_month=current_month
    )

@admin_bp.route("/reservas")
@login_required
def reservas():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("administrador/reservas.html")

@admin_bp.route("/tickets")
@login_required
def tickets():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("administrador/tickets.html")

# SOLO UNA RUTA /usuarios - ELIMINAR LA DUPLICADA
@admin_bp.route("/usuarios")
@login_required
def usuarios():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener todos los usuarios y residentes con JOIN para mostrar datos completos
        cursor.execute("""
            SELECT u.id_usuario, u.nombre, u.ap_paterno, u.ap_materno, 
                   u.correo, u.telefono, u.id_rol,
                   r.piso, r.nro_departamento, r.fecha_ingreso
            FROM usuario u
            LEFT JOIN residente r ON u.id_usuario = r.id_usuario
            ORDER BY u.id_rol, u.nombre
        """)
        usuarios = cursor.fetchall()
        
        # Convertir a lista de diccionarios para facilitar el acceso en el template
        usuarios_list = []
        for user in usuarios:
            usuarios_list.append({
                'id_usuario': user[0],
                'nombre': user[1],
                'ap_paterno': user[2],
                'ap_materno': user[3],
                'correo': user[4],
                'telefono': user[5],
                'id_rol': user[6],
                'piso': user[7],
                'nro_departamento': user[8],
                'fecha_ingreso': user[9]
            })
        
        cursor.close()
        conn.close()
        
        return render_template("administrador/usuarios.html", usuarios=usuarios_list)
        
    except Exception as e:
        print(f"Error obteniendo usuarios: {str(e)}")
        flash("Error al cargar los usuarios.", "danger")
        return render_template("administrador/usuarios.html", usuarios=[])


@admin_bp.route("/generar_invitacion", methods=["POST"])
@login_required
def generar_invitacion():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    rol_destino = request.form.get("rol_destino")
    # Aquí puedes generar un código y mostrarlo
    codigo = crear_invitacion("", estado=True)  # Sin correo, solo código
    flash(f"Código generado: {codigo}", "success")
    return redirect(url_for("admin.panel_admin"))

@admin_bp.route("/enviar_invitacion", methods=["POST"])
@login_required
def enviar_invitacion():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    correo = request.form.get("correo")
    try:
        codigo = crear_invitacion(correo)
        flash(f"Invitación enviada a {correo}", "success")
    except Exception as e:
        flash(f"Error al enviar invitación: {str(e)}", "danger")
    
    return redirect(url_for("admin.panel_admin"))

@admin_bp.route("/cambiar_rol", methods=["POST"])
@login_required
def cambiar_rol():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Procesar cada usuario del formulario
        for key, value in request.form.items():
            if key.startswith('id_usuario_'):
                index = key.split('_')[2]  # Obtener el índice
                id_usuario = value
                nuevo_rol = request.form.get(f'nuevo_rol_{index}')
                
                if id_usuario and nuevo_rol:
                    # Actualizar el rol en la base de datos
                    cursor.execute("""
                        UPDATE usuario SET id_rol = %s WHERE id_usuario = %s
                    """, (nuevo_rol, id_usuario))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Roles actualizados correctamente.", "success")
        
    except Exception as e:
        conn.rollback()
        print(f"Error actualizando roles: {str(e)}")
        flash("Error al actualizar los roles.", "danger")
    
    return redirect(url_for("admin.usuarios"))

@admin_bp.route("/dashboard_finanzas ", endpoint="dashboard_finanzas")
@login_required
def dashboard_finanzas():
    factura = {
        "id": 101,
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "cliente": "Marcelo G.",
        "servicio": "Consumo eléctrico",
        "total": 1280.50
    }
    return render_template("administrador/finanzas.html", factura=factura)

# Ruta para generar el PDF
@admin_bp.route("/generar_pdf/<int:id>", methods=["POST"])
@login_required
def generar_pdf(id):
    factura = {
        "id": id,
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "cliente": "Marcelo G.",
        "servicio": "Consumo eléctrico",
        "total": 1280.50
    }
    config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
    html = render_template("administrador/factura.html", factura=factura)
    pdf = pdfkit.from_string(html, False, configuration=config)
    return send_file(BytesIO(pdf), download_name=f"factura_{id}.pdf", as_attachment=True)




def enviar_comunicado_emails(titulo, mensaje, destinatarios):
    """Envía el comunicado usando Flask-Mail"""
    try:
        # 1. Obtener correos destino desde BD
        correos_destino = obtener_correos_destinatarios(destinatarios)
        
        if not correos_destino:
            return {'success': False, 'error': 'No se encontraron correos destino para los destinatarios seleccionados'}
        
        # 2. Crear mensaje con Flask-Mail
        msg = Message(
            subject=f"📢 Comunicado: {titulo}",
            recipients=correos_destino,
            html=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ 
                        font-family: 'Arial', sans-serif; 
                        margin: 0; 
                        padding: 0; 
                        background: #f5f5f5;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background: white;
                    }}
                    .header {{ 
                        background: #2c3e50; 
                        color: white; 
                        padding: 30px 20px;
                        text-align: center;
                    }}
                    .content {{ 
                        padding: 30px 20px; 
                        line-height: 1.6;
                        color: #333;
                    }}
                    .message-box {{
                        background: #f8f9fa;
                        padding: 20px;
                        border-left: 4px solid #4caf50;
                        margin: 20px 0;
                    }}
                    .footer {{ 
                        background: #34495e;
                        color: #bdc3c7; 
                        padding: 20px;
                        text-align: center;
                        font-size: 12px;
                    }}
                    .destinatarios {{
                        background: #e3f2fd;
                        padding: 10px 15px;
                        border-radius: 5px;
                        margin: 15px 0;
                        font-size: 14px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📢 Comunicado Residencial</h1>
                        <p>Administración del Edificio</p>
                    </div>
                    
                    <div class="content">
                        <h2>{titulo}</h2>
                        
                        <div class="destinatarios">
                            <strong>Para:</strong> {', '.join([d.capitalize() for d in destinatarios])}
                        </div>
                        
                        <div class="message-box">
                            {mensaje.replace(chr(10), '<br>')}
                        </div>
                        
                        <p><em>Este es un mensaje automático, por favor no responda a este correo.</em></p>
                    </div>
                    
                    <div class="footer">
                        <p>Comunicado enviado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}</p>
                        <p>© 2024 Administración del Edificio. Todos los derechos reservados.</p>
                    </div>
                </div>
            </body>
            </html>
            """
        )
        
        # 3. Enviar email
        mail.send(msg)
        
        print(f"✅ Email enviado a {len(correos_destino)} destinatarios")
        
        return {
            'success': True, 
            'enviados': len(correos_destino),
            'correos': correos_destino
        }
        
    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        return {'success': False, 'error': str(e)}
    


def obtener_correos_destinatarios(destinatarios):
    """Obtiene correos usando tu conexión PostgreSQL directa"""
    correos = []
    conn = None
    
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # Residentes
        if 'residente' in destinatarios:
            cursor.execute("""
                SELECT u.correo 
                FROM residente r 
                JOIN usuarios u ON r.id_usuario = u.id_usuario 
                WHERE r.activo = true AND u.correo IS NOT NULL
            """)
            residentes_emails = [row[0] for row in cursor.fetchall()]
            correos.extend(residentes_emails)
            print(f"👨‍👩‍👧‍👦 {len(residentes_emails)} residentes encontrados")
        
        # Empleados  
        if 'empleado' in destinatarios:
            cursor.execute("""
                SELECT u.correo 
                FROM empleado e 
                JOIN usuarios u ON e.id_usuario = u.id_usuario 
                WHERE e.activo = true AND u.correo IS NOT NULL
            """)
            empleados_emails = [row[0] for row in cursor.fetchall()]
            correos.extend(empleados_emails)
            print(f"👷 {len(empleados_emails)} empleados encontrados")
        
        # Eliminar duplicados y limpiar
        correos = list(set([email.strip().lower() for email in correos if email]))
        
        print(f"📧 Total de correos únicos: {len(correos)}")
        return correos
        
    except Exception as e:
        print(f"❌ Error en obtener_correos_destinatarios: {e}")
        return []
    finally:
        if conn:
            conn.close()
    
    
@admin_bp.route('/comunicado', methods=['GET', 'POST'])
def comunicado():
    if request.method == 'POST':
        titulo = request.form['titulo']
        mensaje = request.form['mensaje']
        destinatarios = request.form.getlist('destinatarios')  # ['residentes', 'empleados']
        
        # Validar que se seleccionó al menos un destinatario
        if not destinatarios:
            flash('❌ Debes seleccionar al menos un destinatario', 'error')
            return redirect('/comunicado')
        
        # Validar que hay título y mensaje
        if not titulo.strip() or not mensaje.strip():
            flash('❌ El título y mensaje son obligatorios', 'error')
            return redirect('/comunicado')
        
        # Enviar emails
        resultado = enviar_comunicado_emails(titulo, mensaje, destinatarios)
        
        if resultado['success']:
            flash(f'✅ Comunicado enviado a {resultado["enviados"]} destinatarios', 'success')
        else:
            flash(f'❌ Error: {resultado["error"]}', 'error')
        
        return redirect('/comunicado')
    
    return render_template('administrador/comunicado.html')





@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))




