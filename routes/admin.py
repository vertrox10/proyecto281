from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user, logout_user
from invitaciones import crear_invitacion, obtener_invitaciones_activas
from db import get_db_connection  # <- Importar la conexión a la BD
from datetime import datetime

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/panel_admin")
@login_required
def panel_admin():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    ahora = datetime.now()

    # Simulación de ingresos totales (puedes reemplazar con consulta real)
    ingresos_totales = 25000.0
    consumo_total = 0.0  # o el valor real si lo tienes
    return render_template("administrador/dashboard_admin.html",
                       ahora=ahora,
                       ingresos_totales=ingresos_totales,
                       consumo_total=consumo_total)

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
        sensores_data = cursor.fetchall()

        
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(consumo_query)
        sensores_data = cursor.fetchall()
        cursor.close()
        conn.close()

        
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


@admin_bp.route("/dashboard_finanzas")
@login_required
def dashboard_finanzas():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    empleados = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id_usuario, nombre, ap_paterno
            FROM usuario
            WHERE id_rol = 2
        """)
        empleados_raw = cursor.fetchall()

        empleados = [
            {'id_usuario': emp[0], 'nombre': emp[1], 'ap_paterno': emp[2]}
            for emp in empleados_raw
        ]

        cursor.close()
        conn.close()

    except Exception as e:
        flash(f"Error al cargar empleados: {str(e)}", "danger")
        # No intentes usar cursor aquí, ya que puede no existir

    return render_template("administrador/finanzas.html", empleados=empleados)

@admin_bp.route("/dashboard-finanzas")
@login_required
def finanzas():
    return render_template("administrador/dashboard_finanzas.html")


@admin_bp.route("/pagar_empleado", methods=["POST"])
@login_required
def pagar_empleado():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    try:
        id_usuario = int(request.form.get("id_usuario"))
        monto = request.form.get("monto")

        try:
            monto = float(monto)
        except (TypeError, ValueError):
            monto = 1800.00  # Sueldo fijo por defecto

        metodo = request.form.get("metodo")
        nro_trans = request.form.get("nro_trans")
        estado = "completado"
        fecha_pago = datetime.now().date()

        conn = get_db_connection()
        cursor = conn.cursor()

        # ✅ Insertar y obtener el ID generado
        cursor.execute("""
            INSERT INTO pago (id_usuario, monto, metodo, nro_trans, estado, fecha_pago, pagado_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_pago
        """, (id_usuario, monto, metodo, nro_trans, estado, fecha_pago, current_user.id))
        nuevo_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()

        flash(f"✅ Pago realizado: Bs {monto:.2f}", "success")
        return redirect(url_for("admin.ver_comprobante", id_pago=nuevo_id))

    except Exception as e:
        flash(f"❌ Error al registrar el pago: {str(e)}", "danger")
        return redirect(url_for("admin.dashboard_finanzas"))
    

@admin_bp.route("/enviar_mensaje_residente", methods=["POST"])
@login_required
def enviar_mensaje_residente():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    try:
        id_usuario = int(request.form.get("id_usuario"))
        mensaje = request.form.get("mensaje")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM usuario WHERE id_usuario = %s", (id_usuario,))
        email = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        # Aquí puedes usar Flask-Mail o tu sistema de envío
        enviar_email(destinatario=email, asunto="Cobros registrados", cuerpo=mensaje)

        flash("📨 Mensaje enviado al residente", "success")
        return redirect(url_for("admin.dashboard_finanzas"))

    except Exception as e:
        flash(f"❌ Error al enviar mensaje: {str(e)}", "danger")
        return redirect(url_for("admin.dashboard_finanzas"))

@admin_bp.route("/comprobante")
@login_required
def ver_comprobantes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id_pago, u.nombre, u.ap_paterno, p.monto, p.metodo, p.nro_trans, p.fecha_pago, p.estado
        FROM pago p
        JOIN usuario u ON p.id_usuario = u.id_usuario
        ORDER BY p.fecha_pago DESC
    """)
    comprobantes = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("administrador/comprobante.html", comprobantes=comprobantes)


@admin_bp.route('/comprobante/<int:id_pago>')
@login_required
def ver_comprobante(id_pago):
    """Muestra un comprobante individual por su id_pago."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id_pago, u.nombre, u.ap_paterno, u.ap_materno, p.monto, p.metodo, p.nro_trans, p.fecha_pago, p.estado
            FROM pago p
            JOIN usuario u ON p.id_usuario = u.id_usuario
            WHERE p.id_pago = %s
        """, (id_pago,))
        pago = cursor.fetchone()
        cursor.close()
        conn.close()

        if not pago:
            flash('Comprobante no encontrado.', 'warning')
            return redirect(url_for('admin.ver_comprobantes'))

        return render_template('administrador/comprobante_detalle.html', pago=pago)
    except Exception as e:
        flash(f'Error al cargar comprobante: {str(e)}', 'danger')
        return redirect(url_for('admin.ver_comprobantes'))


@admin_bp.route("/reportes")
def reportes_mensuales():  # Mostrar totales por mes, método, etc.
    return render_template("administrador/reporte.html")



@admin_bp.route("/deudas")
@login_required
def gestionar_deudas():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener deudas pendientes de usuarios
        cursor.execute("""
            SELECT 
                u.id_usuario,
                u.nombre,
                u.ap_paterno,
                u.ap_materno,
                u.email,
                COALESCE(SUM(r.monto_pendiente), 0) as deuda_total,
                COUNT(r.id_reserva) as reservas_pendientes,
                MAX(r.fecha_vencimiento) as fecha_vencimiento_max
            FROM usuario u
            LEFT JOIN reserva r ON u.id_usuario = r.id_usuario 
                AND r.estado_pago = 'pendiente'
                AND r.monto_pendiente > 0
            WHERE u.id_rol IN (2, 3)  # Residentes y empleados
            GROUP BY u.id_usuario, u.nombre, u.ap_paterno, u.ap_materno, u.email
            HAVING COALESCE(SUM(r.monto_pendiente), 0) > 0
            ORDER BY deuda_total DESC
        """)
        deudas = cursor.fetchall()
        
        # Estadísticas generales de deudas
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT u.id_usuario) as total_deudores,
                COALESCE(SUM(r.monto_pendiente), 0) as deuda_general_total,
                AVG(r.monto_pendiente) as deuda_promedio,
                COUNT(r.id_reserva) as total_reservas_pendientes
            FROM usuario u
            LEFT JOIN reserva r ON u.id_usuario = r.id_usuario 
                AND r.estado_pago = 'pendiente'
                AND r.monto_pendiente > 0
            WHERE u.id_rol IN (2, 3)
        """)
        estadisticas = cursor.fetchone()
        
        cursor.close()
        conn.close()

        return render_template("administrador/reportes.html", 
                             deudas=deudas,
                             estadisticas_deudas=estadisticas)
                             
    except Exception as e:
        flash(f"❌ Error al cargar las deudas: {str(e)}", "danger")
        return redirect(url_for("admin.dashboard_finanzas"))


@admin_bp.route("/registrar_cobros", methods=["POST"])
@login_required
def registrar_cobros():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    try:
        id_usuario = int(request.form.get("id_usuario"))
        conceptos = []
        for i in range(1, 4):
            concepto = request.form.get(f"concepto_{i}")
            monto = request.form.get(f"monto_{i}")
            if concepto and monto:
                try:
                    monto = float(monto)
                    conceptos.append((concepto, monto))
                except ValueError:
                    continue

        conn = get_db_connection()
        cursor = conn.cursor()

        for identificador, monto in conceptos:
            cursor.execute("""
                INSERT INTO deuda (id_usuario, identificador, monto, estado)
                VALUES (%s, %s, %s, 'pendiente')
            """, (id_usuario, identificador, monto))

        conn.commit()
        cursor.close()
        conn.close()

        flash("✅ Cobros registrados correctamente", "success")
        return redirect(url_for("admin.dashboard_finanzas"))

    except Exception as e:
        flash(f"❌ Error al registrar cobros: {str(e)}", "danger")
        return redirect(url_for("admin.dashboard_finanzas"))


@admin_bp.route("/marcar_pagado/<int:id_usuario>", methods=["POST"])
@login_required
def marcar_deuda_pagada(id_usuario):
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Marcar todas las reservas pendientes del usuario como pagadas
        cursor.execute("""
            UPDATE reserva 
            SET estado_pago = 'pagado', 
                monto_pendiente = 0,
                fecha_pago = CURRENT_DATE
            WHERE id_usuario = %s 
                AND estado_pago = 'pendiente'
                AND monto_pendiente > 0
        """, (id_usuario,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("✅ Deudas marcadas como pagadas correctamente", "success")
        return redirect(url_for("admin.gestionar_deudas"))
        
    except Exception as e:
        flash(f"❌ Error al marcar como pagado: {str(e)}", "danger")
        return redirect(url_for("admin.gestionar_deudas"))


@admin_bp.route("/reporte_deudas_pdf")
@login_required
def generar_reporte_deudas_pdf():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 🔍 Consulta de deudas agrupadas por usuario
        cursor.execute("""
            SELECT 
                u.nombre,
                u.ap_paterno,
                u.ap_materno,
                u.email,
                COUNT(d.id_deuda) AS cantidad_deudas,
                SUM(d.monto) AS deuda_total
            FROM usuario u
            JOIN deuda d ON u.id_usuario = d.id_usuario
            WHERE d.estado = 'pendiente'
            GROUP BY u.id_usuario, u.nombre, u.ap_paterno, u.ap_materno, u.email
            HAVING SUM(d.monto) > 0
            ORDER BY deuda_total DESC
        """)
        deudas = cursor.fetchall()

        cursor.close()
        conn.close()

        # 🔐 Renderizar plantilla para PDF
        return render_template("administrador/reporte_deudas_pdf.html",
                               deudas=deudas,
                               fecha_reporte=datetime.now().strftime("%d/%m/%Y"))

    except Exception as e:
        flash(f"❌ Error al generar reporte PDF: {str(e)}", "danger")
        return redirect(url_for("admin.dashboard_finanzas"))



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


@admin_bp.route('/comunicado', endpoint='comunicado')
@login_required
def comunicados():
    return render_template("administrador/comunicado.html")









@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))
