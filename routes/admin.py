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
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    conn = None
    cursor = None
    current_date = datetime.now().strftime('%Y-%m-%d')
    current_month = datetime.now().strftime('%B %Y')
    
    try:
        conn = get_db_connection()
        if conn is None:
            flash("❌ Error de conexión a la base de datos", "danger")
            return render_template("administrador/consumos.html",
                agua={"costo": 0, "variacion": 0, "consumo_total": 0, "departamentos_activos": 0},
                gas={"costo": 0, "variacion": 0, "consumo_total": 0, "departamentos_activos": 0},
                luz={"costo": 0, "variacion": 0, "consumo_total": 0, "departamentos_activos": 0},
                sensores=[],
                metricas=None,
                current_date=current_date,
                current_month=current_month
            )
        
        cursor = conn.cursor()

        # CONSUMO DE AGUA
        cursor.execute("""
            SELECT 
                'agua' as tipo,
                id_consumo_agua as id_consumo,
                fecha_registro,
                cantidad_registrada,
                lectura_inicial,
                lectura_final,
                ROUND(lectura_final - lectura_inicial, 2) as consumo_calculado
            FROM consumo_agua 
            WHERE fecha_registro >= '2024-01-01'
            ORDER BY fecha_registro DESC 
            LIMIT 30
        """)
        agua_data = cursor.fetchall()

        # CONSUMO DE LUZ
        cursor.execute("""
            SELECT 
                'luz' as tipo,
                id_consumo_luz as id_consumo,
                fecha_registro,
                cantidad_registrada,
                lectura_inicial,
                lectura_final,
                ROUND(lectura_final - lectura_inicial, 2) as consumo_calculado
            FROM consumo_luz 
            WHERE fecha_registro >= '2024-01-01'
            ORDER BY fecha_registro DESC 
            LIMIT 30
        """)
        luz_data = cursor.fetchall()

        # CONSUMO DE GAS
        cursor.execute("""
            SELECT 
                'gas' as tipo,
                id_consumo_gas as id_consumo,
                fecha_registro,
                cantidad_registrada,
                lectura_inicial,
                lectura_final,
                ROUND(lectura_final - lectura_inicial, 2) as consumo_calculado
            FROM consumo_gas 
            WHERE fecha_registro >= '2024-01-01'
            ORDER BY fecha_registro DESC 
            LIMIT 30
        """)
        gas_data = cursor.fetchall()

        # Combinar todos los datos
        sensores_data = agua_data + luz_data + gas_data

        # CALCULAR MÉTRICAS PARA AGUA (este mes)
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT id_consumo_agua) as total_registros,
                COALESCE(SUM(cantidad_registrada), 0) as consumo_total,
                COALESCE(AVG(cantidad_registrada), 0) as consumo_promedio,
                COUNT(DISTINCT fecha_registro) as dias_con_registro
            FROM consumo_agua 
            WHERE fecha_registro >= DATE_TRUNC('month', CURRENT_DATE)
        """)
        metricas_agua = cursor.fetchone()

        # CALCULAR MÉTRICAS PARA LUZ (este mes)
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT id_consumo_luz) as total_registros,
                COALESCE(SUM(cantidad_registrada), 0) as consumo_total,
                COALESCE(AVG(cantidad_registrada), 0) as consumo_promedio,
                COUNT(DISTINCT fecha_registro) as dias_con_registro
            FROM consumo_luz 
            WHERE fecha_registro >= DATE_TRUNC('month', CURRENT_DATE)
        """)
        metricas_luz = cursor.fetchone()

        # CALCULAR MÉTRICAS PARA GAS (este mes)
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT id_consumo_gas) as total_registros,
                COALESCE(SUM(cantidad_registrada), 0) as consumo_total,
                COALESCE(AVG(cantidad_registrada), 0) as consumo_promedio,
                COUNT(DISTINCT fecha_registro) as dias_con_registro
            FROM consumo_gas 
            WHERE fecha_registro >= DATE_TRUNC('month', CURRENT_DATE)
        """)
        metricas_gas = cursor.fetchone()

        # Obtener total de departamentos
        cursor.execute("SELECT COUNT(*) FROM departamento")
        total_departamentos = cursor.fetchone()[0]

        # Crear objeto metricas
        metricas = type('Metricas', (), {
            'total_departamentos': total_departamentos,
            'total_registros': len(sensores_data),
            'agua_total': metricas_agua[1] if metricas_agua else 0,
            'luz_total': metricas_luz[1] if metricas_luz else 0,
            'gas_total': metricas_gas[1] if metricas_gas else 0,
            'agua_promedio': metricas_agua[2] if metricas_agua else 0,
            'luz_promedio': metricas_luz[2] if metricas_luz else 0,
            'gas_promedio': metricas_gas[2] if metricas_gas else 0
        })()

        print(f"📊 Registros encontrados - Agua: {len(agua_data)}, Luz: {len(luz_data)}, Gas: {len(gas_data)}")

    except Exception as e:
        print(f"❌ Error al cargar datos de consumo: {e}")
        flash(f"Error al cargar datos de consumo: {str(e)}", "danger")
        sensores_data = []
        metricas = None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # Preparar datos para template con métricas reales
    agua = {
        "costo": 320, 
        "variacion": -15,
        "consumo_total": metricas.agua_total if metricas else 0,
        "consumo_promedio": metricas.agua_promedio if metricas else 0,
        "departamentos_activos": metricas.total_departamentos if metricas else 0
    }
    
    gas = {
        "costo": 180, 
        "variacion": -5,
        "consumo_total": metricas.gas_total if metricas else 0,
        "consumo_promedio": metricas.gas_promedio if metricas else 0,
        "departamentos_activos": metricas.total_departamentos if metricas else 0
    }
    
    luz = {
        "costo": 240, 
        "variacion": -8,
        "consumo_total": metricas.luz_total if metricas else 0,
        "consumo_promedio": metricas.luz_promedio if metricas else 0,
        "departamentos_activos": metricas.total_departamentos if metricas else 0
    }

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

    conn = get_db_connection()
    cursor = conn.cursor()

    # Consulta de empleados
    cursor.execute("SELECT id_usuario, nombre, ap_paterno FROM usuario WHERE id_rol = 2")
    empleados = [dict(id_usuario=row[0], nombre=row[1], ap_paterno=row[2]) for row in cursor.fetchall()]

    # Consulta de residentes
    cursor.execute("SELECT id_usuario, nombre, ap_paterno FROM usuario WHERE id_rol = 3")
    residentes = [dict(id_usuario=row[0], nombre=row[1], ap_paterno=row[2]) for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return render_template("administrador/finanzas.html", empleados=empleados, residentes=residentes)

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
        cursor.execute("SELECT correo FROM usuario WHERE id_usuario = %s", (id_usuario,))
        result = cursor.fetchone()

        if result is None:
            flash("⚠️ Usuario no encontrado.", "warning")
            cursor.close()
            conn.close()
            return redirect(url_for("admin.dashboard_finanzas"))

        email = result[0]
        cursor.close()
        conn.close()

        # Crear versión HTML del mensaje para mejor presentación
        mensaje_html = f"""
        <html>
            <body>
                <div style="font-family: Arial, sans-serif; line-height: 1.6;">
                    {mensaje.replace('\n', '<br>')}
                </div>
            </body>
        </html>
        """

        # Usar la función de envío de email
        from flask import current_app
        if hasattr(current_app, 'enviar_email'):
            exito = current_app.enviar_email(
                destinatario=email,
                asunto="Cobros registrados - Administración",
                cuerpo=mensaje,
                html=mensaje_html
            )
            
            if exito:
                flash("📨 Mensaje enviado al residente correctamente", "success")
            else:
                flash("❌ Error al enviar el mensaje", "danger")
        else:
            flash("❌ Servicio de email no disponible", "danger")

        return redirect(url_for("admin.dashboard_finanzas"))

    except Exception as e:
        print("Error al enviar mensaje:", str(e))
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
@login_required
def reportes_mensuales():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            flash("❌ Error de conexión a la base de datos", "danger")
            return render_template("administrador/reporte.html",
                                 reportes_mensuales=[],
                                 deudas_info=(0, 0, 0, 0))

        cursor = conn.cursor()

        # Reportes financieros mensuales - usando tabla PAGO
        cursor.execute("""
            SELECT 
                TO_CHAR(fecha_pago, 'YYYY-MM') as mes,
                COUNT(*) as total_pagos,
                SUM(monto) as total_monto,
                metodo,
                COUNT(DISTINCT id_usuario) as usuarios_unicos
            FROM pago 
            WHERE estado = 'completado'
            GROUP BY TO_CHAR(fecha_pago, 'YYYY-MM'), metodo
            ORDER BY mes DESC, total_monto DESC
        """)
        reportes_mensuales = cursor.fetchall()

        # Deudas pendientes - usando tabla DEUDA
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT d.id_usuario) as total_deudores,
                COALESCE(SUM(d.monto), 0) as deuda_total,
                COALESCE(AVG(d.monto), 0) as deuda_promedio,
                COUNT(d.id_deuda) as total_deudas_pendientes
            FROM deuda d
            WHERE d.estado = 'pendiente'
        """)
        deudas_row = cursor.fetchone()

        # Normalizar a diccionario con valores por defecto
        if deudas_row is None:
            deudas_dict = {
                'total_deudores': 0,
                'deuda_total': 0.0,
                'deuda_promedio': 0.0,
                'total_deudas_pendientes': 0,
            }
        else:
            # deudas_row expected: (total_deudores, deuda_total, deuda_promedio, total_deudas_pendientes)
            deuda_total_val = float(deudas_row[1]) if deudas_row[1] is not None else 0.0
            deuda_promedio_val = float(deudas_row[2]) if deudas_row[2] is not None else 0.0
            deudas_dict = {
                'total_deudores': int(deudas_row[0]) if deudas_row[0] is not None else 0,
                'deuda_total': deuda_total_val,
                'deuda_promedio': deuda_promedio_val,
                'total_deudas_pendientes': int(deudas_row[3]) if deudas_row[3] is not None else 0,
            }

        # Renderizar con los datos obtenidos (deudas_info ahora es un dict)
        return render_template("administrador/reporte.html",
                             reportes_mensuales=reportes_mensuales,
                             deudas_info=deudas_dict)
    except Exception as e:
        print(f"❌ Error al cargar reportes: {e}")
        flash(f"❌ Error al cargar reportes: {str(e)}", "danger")
        # IMPORTANTE: Renderizar la plantilla incluso con error
        empty_deudas = {
            'total_deudores': 0,
            'deuda_total': 0.0,
            'deuda_promedio': 0.0,
            'total_deudas_pendientes': 0,
        }
        return render_template("administrador/reporte.html",
                             reportes_mensuales=[],
                             deudas_info=empty_deudas)
    finally:
        # Asegurar que se cierren las conexiones
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@admin_bp.route("/deudas")
@login_required
def gestionar_deudas():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener deudas pendientes de usuarios - usando tabla DEUDA
        cursor.execute("""
            SELECT 
                u.id_usuario,
                u.nombre,
                u.ap_paterno,
                u.ap_materno,
                u.correo,
                COALESCE(SUM(d.monto), 0) as deuda_total,
                COUNT(d.id_deuda) as deudas_pendientes,
                MAX(d.fecha_creacion) as fecha_creacion_max
            FROM usuario u
            JOIN deuda d ON u.id_usuario = d.id_usuario 
            WHERE d.estado = 'pendiente'
            GROUP BY u.id_usuario, u.nombre, u.ap_paterno, u.ap_materno, u.correo
            HAVING COALESCE(SUM(d.monto), 0) > 0
            ORDER BY deuda_total DESC
        """)
        deudas = cursor.fetchall()
        
        # Estadísticas generales de deudas
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT d.id_usuario) as total_deudores,
                COALESCE(SUM(d.monto), 0) as deuda_general_total,
                AVG(d.monto) as deuda_promedio,
                COUNT(d.id_deuda) as total_deudas_pendientes
            FROM deuda d
            WHERE d.estado = 'pendiente'
        """)
        estadisticas = cursor.fetchone()
        
        cursor.close()
        conn.close()

        return render_template("administrador/reporte.html", 
                     deudas=deudas,
                     estadisticas_deudas=estadisticas)
    except Exception as e:
        print(f"❌ Error al cargar las deudas: {e}")
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
        conceptos = request.form.getlist("concepto[]")
        montos = request.form.getlist("monto[]")
        
        conceptos_lista = []
        for i in range(len(conceptos)):
            if conceptos[i] and montos[i]:
                try:
                    monto = float(montos[i])
                    # Generar identificador único para evitar el constraint
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    identificador_unico = f"{conceptos[i]}_{timestamp}_{i}"
                    conceptos_lista.append((conceptos[i], monto, identificador_unico))
                except ValueError:
                    continue

        if not conceptos_lista:
            flash("❌ No se proporcionaron conceptos válidos", "warning")
            return redirect(url_for("admin.dashboard_finanzas"))

        conn = get_db_connection()
        cursor = conn.cursor()

        for concepto, monto, identificador in conceptos_lista:
            cursor.execute("""
                INSERT INTO deuda (id_usuario, identificador, monto, estado, fecha_creacion)
                VALUES (%s, %s, %s, 'pendiente', CURRENT_DATE)
            """, (id_usuario, identificador, monto))

        conn.commit()
        cursor.close()
        conn.close()

        flash("✅ Cobros registrados correctamente", "success")
        return redirect(url_for("admin.dashboard_finanzas"))

    except Exception as e:
        print(f"❌ Error al registrar cobros: {e}")
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
        
        # Marcar todas las deudas pendientes del usuario como pagadas
        cursor.execute("""
            UPDATE deuda 
            SET estado = 'pagado', 
                fecha_pago = CURRENT_DATE
            WHERE id_usuario = %s 
                AND estado = 'pendiente'
        """, (id_usuario,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("✅ Deudas marcadas como pagadas correctamente", "success")
        return redirect(url_for("admin.gestionar_deudas"))
        
    except Exception as e:
        print(f"❌ Error al marcar como pagado: {e}")
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

        # Consulta de deudas agrupadas por usuario
        cursor.execute("""
            SELECT 
                u.nombre,
                u.ap_paterno,
                u.ap_materno,
                u.correo,
                COUNT(d.id_deuda) AS cantidad_deudas,
                SUM(d.monto) AS deuda_total
            FROM usuario u
            JOIN deuda d ON u.id_usuario = d.id_usuario
            WHERE d.estado = 'pendiente'
            GROUP BY u.id_usuario, u.nombre, u.ap_paterno, u.ap_materno, u.correo
            HAVING SUM(d.monto) > 0
            ORDER BY deuda_total DESC
        """)
        deudas = cursor.fetchall()

        cursor.close()
        conn.close()

        # Renderizar plantilla para PDF
        return render_template("administrador/reporte_deudas_pdf.html",
                               deudas=deudas,
                               fecha_reporte=datetime.now().strftime("%d/%m/%Y"))

    except Exception as e:
        flash(f"❌ Error al generar reporte PDF: {str(e)}", "danger")
        return redirect(url_for("admin.dashboard_finanzas"))
    
@admin_bp.route("/debug-deuda")
@login_required
def debug_deuda():
    """Ver la estructura de la tabla deuda"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'deuda'
            ORDER BY ordinal_position
        """)
        estructura = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        resultado = "<h1>Estructura de tabla DEUDA:</h1><ul>"
        for col in estructura:
            resultado += f"<li>{col[0]} - {col[1]} - {col[2]} - {col[3]}</li>"
        resultado += "</ul>"
        
        return resultado
    except Exception as e:
        return f"Error: {str(e)}"



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
