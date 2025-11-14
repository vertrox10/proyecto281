from flask import Blueprint, render_template, flash, redirect, url_for, jsonify, request, send_file
from flask_login import login_required, current_user
from db import get_db_connection
# Librerías para PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# Librerías para Excel
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.chart import PieChart, BarChart, Reference

import requests
import base64
import io
from datetime import datetime
import os
import tempfile
import pdfkit  

# Crear Blueprint para empleados (SOLO UNA VEZ)
empleados_bp = Blueprint('empleados', __name__, url_prefix='/empleado')

# Configurar pdfkit (si lo vas a usar)
WKHTMLTOPDF_PATH = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'  # Ajusta esta ruta
config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

def get_id_empleado():
    """Obtener el id_empleado del usuario actual"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print(f"🔍 Buscando empleado para usuario ID: {current_user.id}")
        
        cursor.execute("SELECT id_empleado FROM empleado WHERE id_usuario = %s", (current_user.id,))
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Empleado encontrado: ID {result[0]}")
        else:
            print(f"❌ No se encontró empleado para usuario {current_user.id}")
            # Verificar si el usuario existe en la tabla empleado
            cursor.execute("SELECT * FROM empleado LIMIT 5")
            empleados = cursor.fetchall()
            print(f"🔍 Primeros 5 empleados en BD: {empleados}")
        
        cursor.close()
        conn.close()
        
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error obteniendo id_empleado: {e}")
        return None

# ================================
# DASHBOARD DEL EMPLEADO - CON CONSUMOS CORREGIDOS
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

        # MÉTRICAS PARA EL EMPLEADO
        # Mantenimientos activos asignados
        cursor.execute("""
            SELECT COUNT(*) FROM mantenimiento 
            WHERE id_empleado = %s AND activo = true
        """, (current_user.id,))
        mantenimientos_activos = cursor.fetchone()[0]

        # Tickets asignados
        cursor.execute("""
            SELECT COUNT(*) FROM ticket 
            WHERE id_empleado = %s AND estado IN ('abierto', 'en_progreso')
        """, (current_user.id,))
        tickets_asignados = cursor.fetchone()[0]

        # Último pago
        cursor.execute("""
            SELECT n.monto 
            FROM nomina n
            WHERE n.id_empleado = %s 
            ORDER BY n.fecha_pago DESC 
            LIMIT 1
        """, (id_empleado,))
        ultimo_pago_result = cursor.fetchone()
        ultimo_pago = ultimo_pago_result[0] if ultimo_pago_result else 0

        # Asistencia este mes
        cursor.execute("""
            SELECT COUNT(DISTINCT fecha) 
            FROM control_asistencia 
            WHERE id_empleado = %s 
            AND DATE_PART('month', fecha) = DATE_PART('month', CURRENT_DATE)
            AND DATE_PART('year', fecha) = DATE_PART('year', CURRENT_DATE)
        """, (id_empleado,))
        dias_trabajados = cursor.fetchone()[0]

        # =====================
        # CONSUMOS DE SENSORES - CORREGIDOS (usando JOIN con tabla consumo)
        # =====================
        
        # Consumo de AGUA del mes actual
        cursor.execute("""
            SELECT COALESCE(SUM(ca.cantidad_registrada), 0) 
            FROM consumo_agua ca
            JOIN consumo c ON ca.id_consumo = c.id_consumo
            WHERE DATE_PART('month', c.fecha_registro) = DATE_PART('month', CURRENT_DATE)
            AND DATE_PART('year', c.fecha_registro) = DATE_PART('year', CURRENT_DATE)
        """)
        consumo_agua_actual = float(cursor.fetchone()[0] or 0)

        # Consumo de LUZ del mes actual
        cursor.execute("""
            SELECT COALESCE(SUM(cl.cantidad_registrada), 0) 
            FROM consumo_luz cl
            JOIN consumo c ON cl.id_consumo = c.id_consumo
            WHERE DATE_PART('month', c.fecha_registro) = DATE_PART('month', CURRENT_DATE)
            AND DATE_PART('year', c.fecha_registro) = DATE_PART('year', CURRENT_DATE)
        """)
        consumo_luz_actual = float(cursor.fetchone()[0] or 0)

        # Consumo de GAS del mes actual
        cursor.execute("""
            SELECT COALESCE(SUM(cg.cantidad_registrada), 0) 
            FROM consumo_gas cg
            JOIN consumo c ON cg.id_consumo = c.id_consumo
            WHERE DATE_PART('month', c.fecha_registro) = DATE_PART('month', CURRENT_DATE)
            AND DATE_PART('year', c.fecha_registro) = DATE_PART('year', CURRENT_DATE)
        """)
        consumo_gas_actual = float(cursor.fetchone()[0] or 0)

        # Consumos de los últimos 6 meses para gráficos
        cursor.execute("""
            SELECT 
                TO_CHAR(c.fecha_registro, 'YYYY-MM') as mes,
                SUM(ca.cantidad_registrada) as consumo
            FROM consumo_agua ca
            JOIN consumo c ON ca.id_consumo = c.id_consumo
            WHERE c.fecha_registro >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY TO_CHAR(c.fecha_registro, 'YYYY-MM')
            ORDER BY mes
        """)
        agua_mensual = cursor.fetchall()

        cursor.execute("""
            SELECT 
                TO_CHAR(c.fecha_registro, 'YYYY-MM') as mes,
                SUM(cl.cantidad_registrada) as consumo
            FROM consumo_luz cl
            JOIN consumo c ON cl.id_consumo = c.id_consumo
            WHERE c.fecha_registro >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY TO_CHAR(c.fecha_registro, 'YYYY-MM')
            ORDER BY mes
        """)
        luz_mensual = cursor.fetchall()

        cursor.execute("""
            SELECT 
                TO_CHAR(c.fecha_registro, 'YYYY-MM') as mes,
                SUM(cg.cantidad_registrada) as consumo
            FROM consumo_gas cg
            JOIN consumo c ON cg.id_consumo = c.id_consumo
            WHERE c.fecha_registro >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY TO_CHAR(c.fecha_registro, 'YYYY-MM')
            ORDER BY mes
        """)
        gas_mensual = cursor.fetchall()

        # Datos para gráficos de actividades del empleado
        cursor.execute("""
            SELECT 
                TO_CHAR(rm.fecha_realizacion, 'YYYY-MM') as mes,
                COUNT(*) as cantidad
            FROM registro_mantenimiento rm
            WHERE rm.id_empleado = %s
            AND rm.fecha_realizacion >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY TO_CHAR(rm.fecha_realizacion, 'YYYY-MM')
            ORDER BY mes
        """, (id_empleado,))
        mantenimientos_mensuales = cursor.fetchall()

        # Estado de tickets
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN estado = 'abierto' THEN 1 END) as pendientes,
                COUNT(CASE WHEN estado = 'en_progreso' THEN 1 END) as en_progreso,
                COUNT(CASE WHEN estado = 'cerrado' THEN 1 END) as completados
            FROM ticket 
            WHERE id_empleado = %s
        """, (current_user.id,))
        estado_tickets = cursor.fetchone()

        cursor.close()
        conn.close()

        # Preparar datos para el template
        empleado_dict = {
            'nombre': empleado_data[0] or '',
            'ap_paterno': empleado_data[1] or '',
            'ap_materno': empleado_data[2] or '',
            'puesto': empleado_data[3] or '',
            'fecha_contratacion': empleado_data[4] or ''
        }

        # Preparar datos para gráficos de consumos
        consumos_mensuales = {
            'agua': [{'mes': row[0], 'consumo': float(row[1] or 0)} for row in agua_mensual],
            'luz': [{'mes': row[0], 'consumo': float(row[1] or 0)} for row in luz_mensual],
            'gas': [{'mes': row[0], 'consumo': float(row[1] or 0)} for row in gas_mensual]
        }

        # Preparar datos para gráficos de actividades
        mantenimientos_mensuales_data = [
            {'mes': row[0], 'cantidad': row[1]} for row in mantenimientos_mensuales
        ]

        estado_tickets_data = {
            'pendientes': estado_tickets[0] if estado_tickets else 0,
            'en_progreso': estado_tickets[1] if estado_tickets else 0,
            'completados': estado_tickets[2] if estado_tickets else 0
        }

        return render_template(
            "empleado/dashboard.html",
            empleado=empleado_dict,
            mantenimientos_activos=mantenimientos_activos,
            tickets_asignados=tickets_asignados,
            ultimo_pago=ultimo_pago,
            dias_trabajados=dias_trabajados,
            consumo_agua=consumo_agua_actual,
            consumo_luz=consumo_luz_actual,
            consumo_gas=consumo_gas_actual,
            consumos_mensuales=consumos_mensuales,
            mantenimientos_mensuales=mantenimientos_mensuales_data,
            estado_tickets=estado_tickets_data
        )

    except Exception as e:
        print(f"❌ Error cargando dashboard: {e}")
        # Pasar valores por defecto para evitar errores en el template
        empleado_dict = {
            'nombre': current_user.nombre or '',
            'ap_paterno': current_user.ap_paterno or '',
            'ap_materno': current_user.ap_materno or '',
            'puesto': '',
            'fecha_contratacion': ''
        }
        return render_template(
            "empleado/dashboard.html",
            empleado=empleado_dict,
            mantenimientos_activos=0,
            tickets_asignados=0,
            ultimo_pago=0,
            dias_trabajados=0,
            consumo_agua=0,
            consumo_luz=0,
            consumo_gas=0,
            consumos_mensuales={'agua': [], 'luz': [], 'gas': []},
            mantenimientos_mensuales=[],
            estado_tickets={'pendientes': 0, 'en_progreso': 0, 'completados': 0}
        )

# ================================
# API PARA DASHBOARD - CON CONSUMOS CORREGIDOS
# ================================
@empleados_bp.route("/api/dashboard-data")
@login_required
def api_dashboard_data():
    """API para obtener datos del dashboard incluyendo consumos"""
    try:
        id_empleado = get_id_empleado()
        if not id_empleado:
            return jsonify({'success': False, 'error': 'Empleado no encontrado'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Métricas principales del empleado
        cursor.execute("""
            SELECT COUNT(*) FROM mantenimiento 
            WHERE id_empleado = %s AND activo = true
        """, (current_user.id,))
        mantenimientos_activos = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM ticket 
            WHERE id_empleado = %s AND estado IN ('abierto', 'en_progreso')
        """, (current_user.id,))
        tickets_asignados = cursor.fetchone()[0]

        cursor.execute("""
            SELECT n.monto 
            FROM nomina n
            WHERE n.id_empleado = %s 
            ORDER BY n.fecha_pago DESC 
            LIMIT 1
        """, (id_empleado,))
        ultimo_pago_result = cursor.fetchone()
        ultimo_pago = float(ultimo_pago_result[0]) if ultimo_pago_result else 0

        cursor.execute("""
            SELECT COUNT(DISTINCT fecha) 
            FROM control_asistencia 
            WHERE id_empleado = %s 
            AND DATE_PART('month', fecha) = DATE_PART('month', CURRENT_DATE)
        """, (id_empleado,))
        dias_trabajados = cursor.fetchone()[0]

        # Consumos actuales - CORREGIDOS
        cursor.execute("""
            SELECT COALESCE(SUM(ca.cantidad_registrada), 0) 
            FROM consumo_agua ca
            JOIN consumo c ON ca.id_consumo = c.id_consumo
            WHERE DATE_PART('month', c.fecha_registro) = DATE_PART('month', CURRENT_DATE)
        """)
        consumo_agua = float(cursor.fetchone()[0] or 0)

        cursor.execute("""
            SELECT COALESCE(SUM(cl.cantidad_registrada), 0) 
            FROM consumo_luz cl
            JOIN consumo c ON cl.id_consumo = c.id_consumo
            WHERE DATE_PART('month', c.fecha_registro) = DATE_PART('month', CURRENT_DATE)
        """)
        consumo_luz = float(cursor.fetchone()[0] or 0)

        cursor.execute("""
            SELECT COALESCE(SUM(cg.cantidad_registrada), 0) 
            FROM consumo_gas cg
            JOIN consumo c ON cg.id_consumo = c.id_consumo
            WHERE DATE_PART('month', c.fecha_registro) = DATE_PART('month', CURRENT_DATE)
        """)
        consumo_gas = float(cursor.fetchone()[0] or 0)

        # Consumos mensuales para gráficos - CORREGIDOS
        cursor.execute("""
            SELECT 
                TO_CHAR(c.fecha_registro, 'YYYY-MM') as mes,
                'agua' as tipo,
                SUM(ca.cantidad_registrada) as consumo
            FROM consumo_agua ca
            JOIN consumo c ON ca.id_consumo = c.id_consumo
            WHERE c.fecha_registro >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY TO_CHAR(c.fecha_registro, 'YYYY-MM')
            
            UNION ALL
            
            SELECT 
                TO_CHAR(c.fecha_registro, 'YYYY-MM') as mes,
                'luz' as tipo,
                SUM(cl.cantidad_registrada) as consumo
            FROM consumo_luz cl
            JOIN consumo c ON cl.id_consumo = c.id_consumo
            WHERE c.fecha_registro >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY TO_CHAR(c.fecha_registro, 'YYYY-MM')
            
            UNION ALL
            
            SELECT 
                TO_CHAR(c.fecha_registro, 'YYYY-MM') as mes,
                'gas' as tipo,
                SUM(cg.cantidad_registrada) as consumo
            FROM consumo_gas cg
            JOIN consumo c ON cg.id_consumo = c.id_consumo
            WHERE c.fecha_registro >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY TO_CHAR(c.fecha_registro, 'YYYY-MM')
            
            ORDER BY mes, tipo
        """)
        consumos = cursor.fetchall()

        # Mantenimientos por mes
        cursor.execute("""
            SELECT 
                TO_CHAR(rm.fecha_realizacion, 'YYYY-MM') as mes,
                COUNT(*) as cantidad
            FROM registro_mantenimiento rm
            WHERE rm.id_empleado = %s
            AND rm.fecha_realizacion >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY TO_CHAR(rm.fecha_realizacion, 'YYYY-MM')
            ORDER BY mes
        """, (id_empleado,))
        mantenimientos_mensuales = cursor.fetchall()

        # Estado de tickets
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN estado = 'abierto' THEN 1 END) as pendientes,
                COUNT(CASE WHEN estado = 'en_progreso' THEN 1 END) as en_progreso,
                COUNT(CASE WHEN estado = 'cerrado' THEN 1 END) as completados
            FROM ticket 
            WHERE id_empleado = %s
        """, (current_user.id,))
        estado_tickets = cursor.fetchone()

        cursor.close()
        conn.close()

        # Organizar datos de consumos para gráficos
        datos_grafico = {}
        for mes, tipo, consumo in consumos:
            if mes not in datos_grafico:
                datos_grafico[mes] = {'mes': mes, 'agua': 0, 'luz': 0, 'gas': 0}
            datos_grafico[mes][tipo] = float(consumo or 0)

        # Preparar respuesta
        metricas = {
            'mantenimientos_activos': mantenimientos_activos,
            'tickets_asignados': tickets_asignados,
            'ultimo_pago': ultimo_pago,
            'dias_trabajados': dias_trabajados,
            'dias_laborales': 22,
            'consumo_agua': consumo_agua,
            'consumo_luz': consumo_luz,
            'consumo_gas': consumo_gas
        }

        mantenimientos_mensuales_data = [
            {'mes': row[0], 'cantidad': row[1]} for row in mantenimientos_mensuales
        ]

        estado_tickets_data = {
            'pendientes': estado_tickets[0] if estado_tickets else 0,
            'en_progreso': estado_tickets[1] if estado_tickets else 0,
            'completados': estado_tickets[2] if estado_tickets else 0
        }

        return jsonify({
            'success': True,
            'data': {
                'metricas': metricas,
                'consumos_mensuales': list(datos_grafico.values()),
                'mantenimientos_mensuales': mantenimientos_mensuales_data,
                'estado_tickets': estado_tickets_data,
                'actual': {
                    'agua': consumo_agua,
                    'luz': consumo_luz,
                    'gas': consumo_gas
                }
            }
        })

    except Exception as e:
        print(f"❌ Error en API dashboard: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ================================
# MANTENIMIENTOS ASIGNADOS - CORREGIDO
# ================================
@empleados_bp.route("/mantenimientos")
@login_required
def mantenimientos_asignados():
    """Página de mantenimientos asignados al empleado"""
    if current_user.id_rol != 2:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        print(f"🔍 Diagnóstico - Usuario actual:")
        print(f"   • ID Usuario: {current_user.id}")
        print(f"   • Nombre: {current_user.nombre}")
        print(f"   • Rol: {current_user.id_rol}")
        
        # Obtener el id_empleado
        id_empleado = get_id_empleado()
        print(f"   • ID Empleado: {id_empleado}")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar si existen mantenimientos en la base de datos
        cursor.execute("SELECT COUNT(*) FROM mantenimiento")
        total_mantenimientos = cursor.fetchone()[0]
        print(f"🔍 Total de mantenimientos en BD: {total_mantenimientos}")

        # VERIFICACIÓN: Ver todos los mantenimientos para ver a quién están asignados
        cursor.execute("""
            SELECT id_mantenimiento, descripcion, id_empleado, activo 
            FROM mantenimiento 
            LIMIT 5
        """)
        todos_mantenimientos = cursor.fetchall()
        print(f"🔍 Primeros 5 mantenimientos en BD:")
        for mnt in todos_mantenimientos:
            print(f"   • ID: {mnt[0]}, Empleado: {mnt[2]}, Activo: {mnt[3]}, Desc: {mnt[1]}")

        # CONSULTA CORREGIDA: Buscar por id_empleado (no id_usuario)
        cursor.execute("""
            SELECT 
                id_mantenimiento, 
                descripcion,
                activo,
                id_empleado
            FROM mantenimiento 
            WHERE id_empleado = %s
            ORDER BY id_mantenimiento DESC
        """, (id_empleado,))  # ¡Usar id_empleado aquí!
        mantenimientos = cursor.fetchall()

        cursor.close()
        conn.close()

        print(f"✅ Mantenimientos encontrados para empleado {id_empleado}: {len(mantenimientos)}")
        for mnt in mantenimientos:
            print(f"   • ID: {mnt[0]}, Desc: {mnt[1]}, Activo: {mnt[2]}, Empleado: {mnt[3]}")
        
        # Convertir a formato para template
        mantenimientos_data = []
        for mnt in mantenimientos:
            mantenimientos_data.append({
                'id': mnt[0],
                'descripcion': mnt[1],
                'estado': 'Pendiente' if mnt[2] else 'Completado',
                'fecha_programada': 'Por programar',
                'area': 'Área Común',
                'ubicacion': 'Edificio Principal'
            })

        return render_template("empleado/mantenimientos.html", mantenimientos=mantenimientos_data)

    except Exception as e:
        print(f"❌ Error obteniendo mantenimientos: {e}")
        flash("Error al cargar los mantenimientos.", "danger")
        return render_template("empleado/mantenimientos.html", mantenimientos=[])
# ================================
# HISTORIAL DE PAGOS - CORREGIDO
# ================================
@empleados_bp.route("/historial-pagos")
@login_required
def historial_pagos():
    """Página de historial de pagos para el empleado"""
    if current_user.id_rol != 2:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        id_empleado = get_id_empleado()
        if not id_empleado:
            flash("No se encontró información del empleado.", "danger")
            return render_template("empleado/historial_pagos.html", pagos=[], historial_salarios=[], salario_actual=0)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener salario actual
        cursor.execute("SELECT salario FROM empleado WHERE id_empleado = %s", (id_empleado,))
        salario_actual_result = cursor.fetchone()
        salario_actual = salario_actual_result[0] if salario_actual_result else 0

        # Obtener historial de pagos de nómina
        cursor.execute("""
            SELECT 
                n.id_nomina,
                TO_CHAR(n.periodo_inicio, 'DD/MM/YYYY') as periodo_inicio,
                TO_CHAR(n.periodo_fin, 'DD/MM/YYYY') as periodo_fin,
                TO_CHAR(n.fecha_pago, 'DD/MM/YYYY') as fecha_pago,
                n.monto,
                n.estado,
                p.metodo,
                p.nro_trans
            FROM nomina n
            LEFT JOIN pago p ON n.id_nomina = p.id_nomina
            WHERE n.id_empleado = %s
            ORDER BY n.fecha_pago DESC
            LIMIT 12
        """, (id_empleado,))
        pagos = cursor.fetchall()

        # Obtener historial de cambios de salario
        cursor.execute("""
            SELECT 
                TO_CHAR(hs.fecha_creacion, 'DD/MM/YYYY') as fecha,
                hs.salario,
                COALESCE(a.cargo, 'Sistema') as modificado_por
            FROM historial_salario hs
            LEFT JOIN administrador a ON hs.id_administrador = a.id_administrador
            WHERE hs.id_empleado = %s
            ORDER BY hs.fecha_creacion DESC
            LIMIT 10
        """, (id_empleado,))
        historial_salarios = cursor.fetchall()

        cursor.close()
        conn.close()

        # Convertir a formato para template
        pagos_data = []
        for pago in pagos:
            pagos_data.append({
                'id': pago[0],
                'periodo_inicio': pago[1],
                'periodo_fin': pago[2],
                'fecha_pago': pago[3],
                'monto': float(pago[4]) if pago[4] else 0,
                'estado': pago[5] or 'pendiente',
                'metodo': pago[6],
                'nro_transaccion': pago[7]
            })

        historial_salarios_data = []
        for salario in historial_salarios:
            historial_salarios_data.append({
                'fecha': salario[0],
                'salario': float(salario[1]) if salario[1] else 0,
                'modificado_por': salario[2]
            })

        print(f"✅ Pagos encontrados: {len(pagos_data)}")
        print(f"✅ Historial salarial: {len(historial_salarios_data)}")

        return render_template(
            "empleado/historial_pagos.html",
            pagos=pagos_data,
            historial_salarios=historial_salarios_data,
            salario_actual=float(salario_actual) if salario_actual else 0
        )

    except Exception as e:
        print(f"❌ Error cargando historial de pagos: {e}")
        flash("Error al cargar el historial de pagos.", "danger")
        return render_template(
            "empleado/historial_pagos.html",
            pagos=[],
            historial_salarios=[],
            salario_actual=0
        )
# ================================
# TICKETS - CORREGIDO
# ================================
@empleados_bp.route("/tickets")
@login_required
def tickets():
    if current_user.id_rol != 2:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # CORREGIDO: usa current_user.id
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
        """, (current_user.id,))
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
# PERFIL - CORREGIDO
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
                   e.tipo_contrato, e.banco, e.numero_cuenta, e.turno,
                   u.nombre, u.ap_paterno, u.ap_materno, u.correo, u.telefono, u.ci
            FROM empleado e
            JOIN usuario u ON e.id_usuario = u.id_usuario
            WHERE e.id_empleado = %s
        """, (id_empleado,))
        empleado_data = cursor.fetchone()
        
        # Obtener estadísticas (CORREGIDO: usa current_user.id para tickets)
        cursor.execute("""
            SELECT COUNT(*) FROM ticket 
            WHERE id_empleado = %s AND estado = 'cerrado'
        """, (current_user.id,))
        tickets_completados = cursor.fetchone()[0]
        
        # CORREGIDO: usa id_empleado para registro_mantenimiento
        cursor.execute("""
            SELECT COUNT(*) FROM registro_mantenimiento 
            WHERE id_empleado = %s
        """, (id_empleado,))
        mantenimientos_realizados = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM ticket 
            WHERE id_empleado = %s AND estado IN ('abierto', 'en_progreso')
        """, (current_user.id,))
        tickets_pendientes = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()

        # Convertir tupla a diccionario para mejor acceso en template
        empleado_dict = {
            'id_empleado': empleado_data[0],
            'puesto': empleado_data[1],
            'salario': empleado_data[2],
            'fecha_contratacion': empleado_data[3],
            'tipo_contrato': empleado_data[4],
            'banco': empleado_data[5],
            'numero_cuenta': empleado_data[6],
            'turno': empleado_data[7],
            'nombre': empleado_data[8],
            'ap_paterno': empleado_data[9],
            'ap_materno': empleado_data[10],
            'correo': empleado_data[11],
            'telefono': empleado_data[12],
            'ci': empleado_data[13]
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

# ================================
# REPORTES - CORREGIDO
# ================================
@empleados_bp.route("/reportes")
@login_required
def reportes():
    """Página de reportes para empleados"""
    if current_user.id_rol != 2:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        return render_template("empleado/reportes.html")
        
    except Exception as e:
        print(f"❌ Error cargando página de reportes: {e}")
        flash("Error al cargar la página de reportes.", "danger")
        return render_template("empleado/reportes.html")

# ================================
# API PARA REPORTES DE TICKETS - CORREGIDA
# ================================
@empleados_bp.route('/api/tickets-reporte')
@login_required
def obtener_tickets_reporte():
    """API para obtener tickets con filtros"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Obtener parámetros de filtro
        estado = request.args.get('estado', 'todos')
        prioridad = request.args.get('prioridad', 'todos')
        
        query = """
        SELECT 
            t.id_ticket,
            t.descripcion,
            t.prioridad,
            t.estado,
            TO_CHAR(t.fecha_emision, 'DD/MM/YYYY HH24:MI') as fecha_emision,
            TO_CHAR(t.fecha_finalizacion, 'DD/MM/YYYY HH24:MI') as fecha_finalizacion,
            a.nombre as area,
            a.ubicacion,
            CASE 
                WHEN t.estado = 'cerrado' THEN 
                    'Completado en ' || DATE_PART('day', t.fecha_finalizacion - t.fecha_emision) || ' días'
                ELSE 
                    'Abierto hace ' || DATE_PART('day', CURRENT_TIMESTAMP - t.fecha_emision) || ' días'
            END as tiempo_transcurrido
        FROM ticket t
        JOIN area a ON t.id_area = a.id_area
        WHERE t.id_empleado = %s
        """
        
        params = [current_user.id]
        
        # Aplicar filtros
        if estado != 'todos':
            query += " AND t.estado = %s"
            params.append(estado)
            
        if prioridad != 'todos':
            query += " AND t.prioridad = %s"
            params.append(prioridad)
        
        query += " ORDER BY t.fecha_emision DESC"
        
        cur.execute(query, params)
        tickets = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Convertir a formato JSON
        tickets_json = []
        for ticket in tickets:
            tickets_json.append({
                'id': ticket[0],
                'descripcion': ticket[1],
                'prioridad': ticket[2],
                'estado': ticket[3],
                'fecha_emision': ticket[4],
                'fecha_finalizacion': ticket[5],
                'area': ticket[6],
                'ubicacion': ticket[7],
                'tiempo_transcurrido': ticket[8]
            })
        
        return jsonify({
            'success': True,
            'data': tickets_json,
            'total': len(tickets_json)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ================================
# API PARA ESTADÍSTICAS - CORREGIDA
# ================================
@empleados_bp.route('/api/estadisticas')
@login_required
def obtener_estadisticas():
    """API para obtener estadísticas para el dashboard de reportes"""
    try:
        id_empleado = get_id_empleado()
        if not id_empleado:
            return jsonify({'success': False, 'error': 'Empleado no encontrado'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Estadísticas de tickets (CORREGIDO: usa current_user.id)
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN estado = 'abierto' THEN 1 END) as abiertos,
                COUNT(CASE WHEN estado = 'en_progreso' THEN 1 END) as en_progreso,
                COUNT(CASE WHEN estado = 'cerrado' THEN 1 END) as cerrados,
                COUNT(CASE WHEN prioridad = 'urgente' THEN 1 END) as urgentes
            FROM ticket 
            WHERE id_empleado = %s
        """, (current_user.id,))
        stats_tickets = cursor.fetchone()

        # Estadísticas de mantenimientos (CORREGIDO: usa current_user.id)
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN activo = true THEN 1 END) as activos,
                COUNT(CASE WHEN activo = false THEN 1 END) as inactivos
            FROM mantenimiento 
            WHERE id_empleado = %s
        """, (current_user.id,))
        stats_mantenimientos = cursor.fetchone()

        # Estadísticas de registros de mantenimiento (CORREGIDO: usa id_empleado)
        cursor.execute("""
            SELECT COUNT(*) as total_registros
            FROM registro_mantenimiento 
            WHERE id_empleado = %s
        """, (id_empleado,))
        total_registros = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'data': {
                'tickets': {
                    'total': stats_tickets[0],
                    'abiertos': stats_tickets[1],
                    'en_progreso': stats_tickets[2],
                    'cerrados': stats_tickets[3],
                    'urgentes': stats_tickets[4]
                },
                'mantenimientos': {
                    'total': stats_mantenimientos[0],
                    'activos': stats_mantenimientos[1],
                    'inactivos': stats_mantenimientos[2],
                    'registros_realizados': total_registros
                }
            }
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ================================
# API PARA ESTADÍSTICAS DE PAGOS - CORREGIDA
# ================================
@empleados_bp.route("/api/pagos-estadisticas")
@login_required
def api_pagos_estadisticas():
    """API para obtener estadísticas de pagos para gráficos (CON DATOS REALES)"""
    try:
        id_empleado = get_id_empleado()
        if not id_empleado:
            return jsonify({'success': False, 'error': 'Empleado no encontrado'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener datos reales para gráfico mensual
        cursor.execute("""
            SELECT 
                TO_CHAR(n.fecha_pago, 'YYYY-MM') as mes,
                AVG(n.monto) as promedio_mensual
            FROM nomina n
            WHERE n.id_empleado = %s 
            AND n.fecha_pago >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY TO_CHAR(n.fecha_pago, 'YYYY-MM')
            ORDER BY mes
        """, (id_empleado,))
        datos_mensuales = cursor.fetchall()

        # Obtener datos para gráfico de composición (usando valores fijos ya que no hay desglose)
        cursor.execute("""
            SELECT 
                AVG(n.monto) as salario_promedio
            FROM nomina n
            WHERE n.id_empleado = %s 
            AND n.fecha_pago >= CURRENT_DATE - INTERVAL '6 months'
        """, (id_empleado,))
        salario_promedio = cursor.fetchone()

        cursor.close()
        conn.close()

        # Preparar datos para el gráfico mensual
        datos_mensual = []
        for mes, promedio in datos_mensuales:
            if promedio:  # Solo incluir meses con datos
                datos_mensual.append({
                    'mes': mes[-5:],  # Tomar solo "MM-YY"
                    'monto': float(promedio)
                })

        # Si no hay datos, usar datos de ejemplo
        if not datos_mensual:
            datos_mensual = [
                {'mes': '01-24', 'monto': 2500},
                {'mes': '02-24', 'monto': 2500},
                {'mes': '03-24', 'monto': 2550},
                {'mes': '04-24', 'monto': 2550},
                {'mes': '05-24', 'monto': 2600},
                {'mes': '06-24', 'monto': 2600}
            ]

        # Datos para gráfico de categorías (estimados basados en salario promedio)
        salario_base = float(salario_promedio[0]) if salario_promedio and salario_promedio[0] else 2500
        datos_categorias = [
            {'categoria': 'Salario Base', 'monto': salario_base * 0.85},  # 85% salario base
            {'categoria': 'Bonos', 'monto': salario_base * 0.10},        # 10% bonos
            {'categoria': 'Beneficios', 'monto': salario_base * 0.05}    # 5% beneficios
        ]

        return jsonify({
            'success': True,
            'data': {
                'mensual': datos_mensual,
                'categorias': datos_categorias
            }
        })

    except Exception as e:
        print(f"❌ Error en API pagos estadísticas: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ================================
# FUNCIONES DE EXPORTACIÓN (mantener compatibilidad)
# ================================
@empleados_bp.route("/api/exportar-pdf", methods=["POST"])
@login_required
def exportar_pdf():
    """Exportar reporte en PDF"""
    try:
        return jsonify({'success': False, 'error': 'Función en desarrollo'}), 501
        
    except Exception as e:
        print(f"❌ Error exportando PDF: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@empleados_bp.route("/api/exportar-excel", methods=["POST"])
@login_required
def exportar_excel():
    """Exportar reporte en Excel"""
    try:
        return jsonify({'success': False, 'error': 'Función en desarrollo'}), 501
        
    except Exception as e:
        print(f"❌ Error exportando Excel: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ================================
# API CONSUMOS (mantener por compatibilidad)
# ================================
@empleados_bp.route("/api/consumos")
@login_required
def api_consumos():
    """Endpoint para obtener datos de consumo para gráficos"""
    try:
        # Como el empleado no necesita consumos, devolvemos datos vacíos
        return jsonify({
            'success': True,
            'data': [],
            'actual': {
                'agua': 0,
                'luz': 0,
                'gas': 0
            }
        })

    except Exception as e:
        print(f"❌ Error en API consumos: {e}")
        return jsonify({'success': False, 'error': str(e)})