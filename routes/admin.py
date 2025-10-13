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
    # Verificación de rol
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    try:
        # Obtener fecha actual
        current_date = datetime.now().strftime('%Y-%m-%d')
        current_month = datetime.now().strftime('%B %Y')
        
        # CONSULTA CORREGIDA - BUSCAR DATOS DE 2024
        consumo_query = """
            SELECT 
                id_consumo,
                id_sensor,
                id_departamento,
                cantidad_registrada,
                lectura_inicial,
                lectura_final,
                fecha_registro,
                id_usuario,
                ROUND(lectura_final - lectura_inicial, 2) as consumo_calculado
            FROM consumos 
            WHERE fecha_registro >= '2024-01-01'  -- ¡BUSCAR DESDE ENERO 2024!
            ORDER BY fecha_registro DESC, id_departamento
            LIMIT 100
        """
        
        # Ejecutar consulta
        sensores_data = db.session.execute(consumo_query).fetchall()
        
        # Calcular métricas agregadas para el dashboard (también corregir fecha)
        metricas_query = """
            SELECT 
                COUNT(DISTINCT id_departamento) as total_departamentos,
                COUNT(DISTINCT id_sensor) as total_sensores,
                ROUND(AVG(cantidad_registrada), 2) as consumo_promedio,
                SUM(cantidad_registrada) as consumo_total_mes
            FROM consumos 
            WHERE fecha_registro >= '2024-01-01'  -- ¡CORREGIDO!
        """
        
        metricas = db.session.execute(metricas_query).fetchone()
        
        # Datos para servicios
        agua = {
            "costo": 320, 
            "variacion": -15,
            "consumo_total": metricas.consumo_total_mes if metricas else 0,
            "departamentos_activos": metricas.total_departamentos if metricas else 0
        }
        
        gas = {
            "costo": 180, 
            "variacion": -5,
            "consumo_total": 0,
            "departamentos_activos": 0
        }
        
        luz = {
            "costo": 240, 
            "variacion": -8,
            "consumo_total": 0,
            "departamentos_activos": 0
        }

        # DEBUG: Ver cuántos registros encontramos
        print(f"📊 Registros encontrados: {len(sensores_data)}")

    except Exception as e:
        flash(f"Error al cargar datos de consumo: {str(e)}", "danger")
        # Datos por defecto en caso de error
        agua = {"costo": 0, "variacion": 0, "consumo_total": 0, "departamentos_activos": 0}
        gas = {"costo": 0, "variacion": 0, "consumo_total": 0, "departamentos_activos": 0}
        luz = {"costo": 0, "variacion": 0, "consumo_total": 0, "departamentos_activos": 0}
        sensores_data = []
        metricas = None

    # Renderizar template
    return render_template("administrador/consumos.html",
        agua=agua,
        gas=gas,
        luz=luz,
        sensores=sensores_data,
        metricas=metricas,
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