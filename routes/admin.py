from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user, logout_user
from invitaciones import crear_invitacion, obtener_invitaciones_activas
from db import get_db_connection  # <- Importar la conexión a la BD

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/panel_admin")
@login_required
def panel_admin():
    # Verificar que el usuario sea administrador (id_rol = 1)
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    return render_template("administrador/dashboard_admin.html")

@admin_bp.route("/finanzas")
@login_required
def finanzas():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("administrador/finanzas.html")

@admin_bp.route("/consumos")
@login_required
def consumos():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("administrador/consumos.html")

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

        # Obtener empleados
        cursor.execute("""
            SELECT u.id_usuario, u.nombre, u.ap_paterno, u.ap_materno,
                   u.correo, u.telefono, u.id_rol
            FROM usuario u
            WHERE u.id_rol != 3  -- Suponiendo que rol 3 es residente
            ORDER BY u.id_rol, u.nombre
        """)
        empleados = cursor.fetchall()

        empleados_list = []
        for user in empleados:
            empleados_list.append({
                'tipo': 'Empleado',
                'id': user[0],
                'nombre': user[1],
                'ap_paterno': user[2],
                'ap_materno': user[3],
                'correo': user[4],
                'telefono': user[5],
                'id_rol': user[6],
                'piso': None,
                'departamento': None,
                'fecha_ingreso': None
            })

        # Obtener residentes
        cursor.execute("""
            SELECT r.id, r.nombre, r.ap_paterno, r.ap_materno,
                   r.piso, r.nro_departamento, r.fecha_ingreso
            FROM residente r
            ORDER BY r.piso, r.nro_departamento
        """)
        residentes = cursor.fetchall()

        residentes_list = []
        for r in residentes:
            residentes_list.append({
                'tipo': 'Residente',
                'id': r[0],
                'nombre': r[1],
                'ap_paterno': r[2],
                'ap_materno': r[3],
                'correo': None,
                'telefono': None,
                'id_rol': 3,  # Asumiendo que 3 es residente
                'piso': r[4],
                'departamento': r[5],
                'fecha_ingreso': r[6]
            })

        cursor.close()
        conn.close()

        usuarios_combinados = empleados_list + residentes_list

        return render_template("administrador/usuarios.html", usuarios=usuarios_combinados)

    except Exception as e:
        print(f"Error obteniendo usuarios y residentes: {str(e)}")
        flash("Error al cargar los datos.", "danger")
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