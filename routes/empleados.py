from flask import Blueprint, render_template, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from db import get_db_connection

empleados_bp = Blueprint("empleados", __name__)

def get_id_empleado():
    """Obtener el id_empleado del usuario actual"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_empleado FROM empleado WHERE id_usuario = %s", (current_user.id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error obteniendo id_empleado: {e}")
        return None

# ================================
# DASHBOARD DEL EMPLEADO - CON GRÁFICOS
# ================================
@empleados_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.id_rol != 2:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        id_empleado = get_id_empleado()
        if not id_empleado:
            flash("No se encontró información del empleado.", "danger")
            return redirect(url_for("auth.login"))

        conn = get_db_connection()
        cursor = conn.cursor()

        # Datos del empleado logueado
        cursor.execute("""
            SELECT u.nombre, u.ap_paterno, u.ap_materno, e.puesto, e.fecha_contratacion
            FROM usuario u
            JOIN empleado e ON u.id_usuario = e.id_usuario
            WHERE e.id_empleado = %s
        """, (id_empleado,))
        empleado_data = cursor.fetchone()

        if not empleado_data:
            flash("No se encontraron datos del empleado.", "danger")
            return render_template("empleado/dashboard.html")

        # Total de tickets asignados
        cursor.execute("SELECT COUNT(*) FROM ticket WHERE id_empleado = %s", (id_empleado,))
        total_tickets = cursor.fetchone()[0]

        # Tickets pendientes
        cursor.execute("""
            SELECT COUNT(*) FROM ticket 
            WHERE id_empleado = %s AND estado IN ('abierto', 'en_progreso')
        """, (id_empleado,))
        tickets_pendientes = cursor.fetchone()[0]

        # Total de mantenimientos
        cursor.execute("SELECT COUNT(*) FROM mantenimiento WHERE id_empleado = %s", (id_empleado,))
        total_mantenimientos = cursor.fetchone()[0]

        # =====================
        # DATOS PARA GRÁFICOS DE CONSUMO
        # =====================
        
        # Consumo de AGUA del mes actual
        cursor.execute("""
            SELECT COALESCE(SUM(cantidad_registrada), 0) 
            FROM consumo_agua 
            WHERE DATE_PART('month', fecha_registro) = DATE_PART('month', CURRENT_DATE)
            AND DATE_PART('year', fecha_registro) = DATE_PART('year', CURRENT_DATE)
        """)
        consumo_agua_actual = float(cursor.fetchone()[0] or 0)

        # Consumo de LUZ del mes actual
        cursor.execute("""
            SELECT COALESCE(SUM(cantidad_registrada), 0) 
            FROM consumo_luz 
            WHERE DATE_PART('month', fecha_registro) = DATE_PART('month', CURRENT_DATE)
            AND DATE_PART('year', fecha_registro) = DATE_PART('year', CURRENT_DATE)
        """)
        consumo_luz_actual = float(cursor.fetchone()[0] or 0)

        # Consumo de GAS del mes actual
        cursor.execute("""
            SELECT COALESCE(SUM(cantidad_registrada), 0) 
            FROM consumo_gas 
            WHERE DATE_PART('month', fecha_registro) = DATE_PART('month', CURRENT_DATE)
            AND DATE_PART('year', fecha_registro) = DATE_PART('year', CURRENT_DATE)
        """)
        consumo_gas_actual = float(cursor.fetchone()[0] or 0)

        # Consumos de los últimos 6 meses para gráficos
        cursor.execute("""
            SELECT 
                TO_CHAR(fecha_registro, 'YYYY-MM') as mes,
                SUM(cantidad_registrada) as consumo
            FROM consumo_agua 
            WHERE fecha_registro >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY TO_CHAR(fecha_registro, 'YYYY-MM')
            ORDER BY mes
        """)
        agua_mensual = cursor.fetchall()

        cursor.execute("""
            SELECT 
                TO_CHAR(fecha_registro, 'YYYY-MM') as mes,
                SUM(cantidad_registrada) as consumo
            FROM consumo_luz 
            WHERE fecha_registro >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY TO_CHAR(fecha_registro, 'YYYY-MM')
            ORDER BY mes
        """)
        luz_mensual = cursor.fetchall()

        cursor.execute("""
            SELECT 
                TO_CHAR(fecha_registro, 'YYYY-MM') as mes,
                SUM(cantidad_registrada) as consumo
            FROM consumo_gas 
            WHERE fecha_registro >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY TO_CHAR(fecha_registro, 'YYYY-MM')
            ORDER BY mes
        """)
        gas_mensual = cursor.fetchall()

        cursor.close()
        conn.close()

        # Preparar datos para gráficos
        consumos_mensuales = {
            'agua': [{'mes': row[0], 'consumo': float(row[1] or 0)} for row in agua_mensual],
            'luz': [{'mes': row[0], 'consumo': float(row[1] or 0)} for row in luz_mensual],
            'gas': [{'mes': row[0], 'consumo': float(row[1] or 0)} for row in gas_mensual]
        }

        # Pasar datos al template
        empleado_dict = {
            'nombre': empleado_data[0] or '',
            'ap_paterno': empleado_data[1] or '',
            'ap_materno': empleado_data[2] or '',
            'puesto': empleado_data[3] or '',
            'fecha_contratacion': empleado_data[4] or ''
        }

        return render_template(
            "empleado/dashboard.html",
            empleado=empleado_dict,
            total_tickets=total_tickets,
            tickets_pendientes=tickets_pendientes,
            total_mantenimientos=total_mantenimientos,
            consumo_agua=consumo_agua_actual,
            consumo_luz=consumo_luz_actual,
            consumo_gas=consumo_gas_actual,
            consumos_mensuales=consumos_mensuales
        )

    except Exception as e:
        print(f"❌ Error cargando dashboard: {e}")
        # Pasar valores por defecto para evitar errores en el template
        empleado_dict = {
            'nombre': '',
            'ap_paterno': '',
            'ap_materno': '',
            'puesto': '',
            'fecha_contratacion': ''
        }
        return render_template(
            "empleado/dashboard.html",
            empleado=empleado_dict,
            total_tickets=0,
            tickets_pendientes=0,
            total_mantenimientos=0,
            consumo_agua=0,
            consumo_luz=0,
            consumo_gas=0,
            consumos_mensuales={'agua': [], 'luz': [], 'gas': []}
        )

# ================================
# TICKETS - CONSULTA CORREGIDA (usando tabla 'area')
# ================================
@empleados_bp.route("/tickets")
@login_required
def tickets():
    if current_user.id_rol != 2:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        id_empleado = get_id_empleado()
        if not id_empleado:
            flash("No se encontró información del empleado.", "danger")
            return render_template("empleado/tickets.html", tickets=[])

        conn = get_db_connection()
        cursor = conn.cursor()

        # CONSULTA CORREGIDA - Usa 'area' en lugar de 'area_comun'
        cursor.execute("""
            SELECT 
                t.id_ticket, 
                t.descripcion, 
                t.prioridad, 
                t.estado,
                TO_CHAR(t.fecha_emision, 'DD/MM/YYYY HH24:MI') as fecha_emision,
                TO_CHAR(t.fecha_finalizacion, 'DD/MM/YYYY HH24:MI') as fecha_finalizacion,
                a.nombre as area
            FROM ticket t
            JOIN area a ON t.id_area = a.id_area
            WHERE t.id_empleado = %s
            ORDER BY 
                CASE 
                    WHEN t.estado = 'en_progreso' THEN 1
                    WHEN t.estado = 'abierto' THEN 2
                    WHEN t.estado = 'cerrado' THEN 3
                    WHEN t.estado = 'cancelado' THEN 4
                    ELSE 5
                END,
                CASE 
                    WHEN t.prioridad = 'urgente' THEN 1
                    WHEN t.prioridad = 'alta' THEN 2
                    WHEN t.prioridad = 'media' THEN 3
                    WHEN t.prioridad = 'baja' THEN 4
                    ELSE 5
                END,
                t.fecha_emision DESC
        """, (id_empleado,))
        tickets = cursor.fetchall()

        cursor.close()
        conn.close()

        print(f"✅ Tickets encontrados: {len(tickets)}")
        return render_template("empleado/tickets.html", tickets=tickets)
        
    except Exception as e:
        print(f"❌ Error obteniendo tickets: {e}")
        flash("Error al cargar los tickets.", "danger")
        return render_template("empleado/tickets.html", tickets=[])

# ================================
# MANTENIMIENTOS - CONSULTA CORREGIDA (usando tabla 'area')
# ================================
@empleados_bp.route("/mantenimientos")
@login_required
def mantenimientos():
    if current_user.id_rol != 2:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        id_empleado = get_id_empleado()
        if not id_empleado:
            flash("No se encontró información del empleado.", "danger")
            return render_template("empleado/mantenimientos.html", mantenimientos=[])

        conn = get_db_connection()
        cursor = conn.cursor()

        # CONSULTA CORREGIDA - Usa 'area' en lugar de 'area_comun'
        cursor.execute("""
            SELECT 
                m.id_mantenimiento, 
                m.descripcion, 
                TO_CHAR(m.fecha_programada, 'DD/MM/YYYY'), 
                m.estado, 
                a.nombre as area
            FROM mantenimiento m
            JOIN area a ON m.id_area = a.id_area
            WHERE m.id_empleado = %s
            ORDER BY 
                CASE m.estado
                    WHEN 'en_proceso' THEN 1
                    WHEN 'programado' THEN 2
                    WHEN 'completado' THEN 3
                    ELSE 4
                END,
                m.fecha_programada DESC
        """, (id_empleado,))
        mantenimientos = cursor.fetchall()

        cursor.close()
        conn.close()

        print(f"✅ Mantenimientos encontrados: {len(mantenimientos)}")
        return render_template("empleado/mantenimientos.html", mantenimientos=mantenimientos)

    except Exception as e:
        print(f"❌ Error obteniendo mantenimientos: {e}")
        flash("Error al cargar los mantenimientos.", "danger")
        return render_template("empleado/mantenimientos.html", mantenimientos=[])

# ================================
# ENDPOINT PARA DATOS DE CONSUMO (AJAX)
# ================================
# En empleados.py - Mejorar el endpoint api_consumos
@empleados_bp.route("/api/consumos")
@login_required
def api_consumos():
    """Endpoint para obtener datos de consumo para gráficos"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Consumos del último año para gráficos detallados
        cursor.execute("""
            SELECT 
                TO_CHAR(fecha_registro, 'YYYY-MM') as mes,
                'agua' as tipo,
                SUM(cantidad_registrada) as consumo
            FROM consumo_agua 
            WHERE fecha_registro >= CURRENT_DATE - INTERVAL '1 year'
            GROUP BY TO_CHAR(fecha_registro, 'YYYY-MM')
            
            UNION ALL
            
            SELECT 
                TO_CHAR(fecha_registro, 'YYYY-MM') as mes,
                'luz' as tipo,
                SUM(cantidad_registrada) as consumo
            FROM consumo_luz 
            WHERE fecha_registro >= CURRENT_DATE - INTERVAL '1 year'
            GROUP BY TO_CHAR(fecha_registro, 'YYYY-MM')
            
            UNION ALL
            
            SELECT 
                TO_CHAR(fecha_registro, 'YYYY-MM') as mes,
                'gas' as tipo,
                SUM(cantidad_registrada) as consumo
            FROM consumo_gas 
            WHERE fecha_registro >= CURRENT_DATE - INTERVAL '1 year'
            GROUP BY TO_CHAR(fecha_registro, 'YYYY-MM')
            
            ORDER BY mes, tipo
        """)
        consumos = cursor.fetchall()

        # También obtener consumos actuales del mes
        cursor.execute("""
            SELECT 
                COALESCE(SUM(cantidad_registrada), 0) as consumo_agua
            FROM consumo_agua 
            WHERE DATE_PART('month', fecha_registro) = DATE_PART('month', CURRENT_DATE)
            AND DATE_PART('year', fecha_registro) = DATE_PART('year', CURRENT_DATE)
        """)
        agua_actual = cursor.fetchone()[0]

        cursor.execute("""
            SELECT 
                COALESCE(SUM(cantidad_registrada), 0) as consumo_luz
            FROM consumo_luz 
            WHERE DATE_PART('month', fecha_registro) = DATE_PART('month', CURRENT_DATE)
            AND DATE_PART('year', fecha_registro) = DATE_PART('year', CURRENT_DATE)
        """)
        luz_actual = cursor.fetchone()[0]

        cursor.execute("""
            SELECT 
                COALESCE(SUM(cantidad_registrada), 0) as consumo_gas
            FROM consumo_gas 
            WHERE DATE_PART('month', fecha_registro) = DATE_PART('month', CURRENT_DATE)
            AND DATE_PART('year', fecha_registro) = DATE_PART('year', CURRENT_DATE)
        """)
        gas_actual = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        # Organizar datos para gráficos
        datos_grafico = {}
        for mes, tipo, consumo in consumos:
            if mes not in datos_grafico:
                datos_grafico[mes] = {'mes': mes, 'agua': 0, 'luz': 0, 'gas': 0}
            datos_grafico[mes][tipo] = float(consumo or 0)

        return jsonify({
            'success': True,
            'data': list(datos_grafico.values()),
            'actual': {
                'agua': float(agua_actual or 0),
                'luz': float(luz_actual or 0),
                'gas': float(gas_actual or 0)
            }
        })

    except Exception as e:
        print(f"❌ Error en API consumos: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ================================
# REPORTES
# ================================
@empleados_bp.route("/reportes")
@login_required
def reportes():
    if current_user.id_rol != 2:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        id_empleado = get_id_empleado()
        if not id_empleado:
            flash("No se encontró información del empleado.", "danger")
            return render_template("empleado/reportes.html", reporte_tickets=[], reporte_mantenimientos=[])

        conn = get_db_connection()
        cursor = conn.cursor()

        # Tickets agrupados por estado
        cursor.execute("""
            SELECT estado, COUNT(*) 
            FROM ticket 
            WHERE id_empleado = %s 
            GROUP BY estado
        """, (id_empleado,))
        reporte_tickets = cursor.fetchall()

        # Mantenimientos agrupados por estado
        cursor.execute("""
            SELECT estado, COUNT(*) 
            FROM mantenimiento 
            WHERE id_empleado = %s 
            GROUP BY estado
        """, (id_empleado,))
        reporte_mantenimientos = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "empleado/reportes.html",
            reporte_tickets=reporte_tickets,
            reporte_mantenimientos=reporte_mantenimientos
        )

    except Exception as e:
        print(f"❌ Error generando reportes: {e}")
        flash("Error al generar los reportes.", "danger")
        return render_template("empleado/reportes.html")

# ================================
# PERFIL
# ================================
@empleados_bp.route("/perfil")
@login_required
def perfil():
    if current_user.id_rol != 2:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        id_empleado = get_id_empleado()
        if not id_empleado:
            flash("No se encontró información del empleado.", "danger")
            return redirect(url_for("empleados.dashboard"))

        conn = get_db_connection()
        cursor = conn.cursor()

        # Consultar datos del empleado
        cursor.execute("""
            SELECT e.id_empleado, e.puesto, e.salario, e.fecha_contratacion,
                   u.nombre, u.ap_paterno, u.ap_materno, u.correo, u.telefono
            FROM empleado e
            JOIN usuario u ON e.id_usuario = u.id_usuario
            WHERE e.id_empleado = %s
        """, (id_empleado,))
        empleado_data = cursor.fetchone()
        
        # Obtener estadísticas
        cursor.execute("""
            SELECT COUNT(*) FROM ticket 
            WHERE id_empleado = %s AND estado = 'cerrado'
        """, (id_empleado,))
        tickets_completados = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM mantenimiento 
            WHERE id_empleado = %s AND estado = 'completado'
        """, (id_empleado,))
        mantenimientos_realizados = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM ticket 
            WHERE id_empleado = %s AND estado IN ('abierto', 'en_progreso')
        """, (id_empleado,))
        tickets_pendientes = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()

        # Convertir tupla a diccionario para mejor acceso en template
        empleado_dict = {
            'id_empleado': empleado_data[0],
            'puesto': empleado_data[1],
            'salario': empleado_data[2],
            'fecha_contratacion': empleado_data[3],
            'nombre': empleado_data[4],
            'ap_paterno': empleado_data[5],
            'ap_materno': empleado_data[6],
            'correo': empleado_data[7],
            'telefono': empleado_data[8]
        }
        
        return render_template('empleado/perfil.html',
                            empleado=empleado_dict,
                            tickets_completados=tickets_completados,
                            mantenimientos_realizados=mantenimientos_realizados,
                            tickets_pendientes=tickets_pendientes)
    
    except Exception as e:
        print(f"❌ Error cargando perfil: {e}")
        flash("Error al cargar el perfil.", "danger")
        return redirect(url_for("empleados.dashboard"))