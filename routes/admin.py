from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user, logout_user
from invitaciones import crear_invitacion, obtener_invitaciones_activas
from db import get_db_connection  # <- Importar la conexión a la BD
from datetime import datetime


admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/panel_admin")
@login_required
def panel_admin():
    # Verificar que el usuario sea administrador (id_rol = 1)
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    return render_template("administrador/dashboard_admin.html")

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

@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))


@admin_bp.route('/finanzas')
@login_required
def dashboard_finanzas():
    return render_template("administrador/finanzas.html")