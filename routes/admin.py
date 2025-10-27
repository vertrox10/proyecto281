from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user, logout_user
from invitaciones import crear_invitacion, obtener_invitaciones_activas
from db import get_db_connection  # <- Importar la conexión a la BD
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart as MimeMultipart
from email.mime.text import MIMEText as MimeText

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener estadísticas principales con valores por defecto
        total_usuarios = 0
        tickets_pendientes = 0
        tickets_urgentes = 0
        total_tickets = 0
        ingresos_mensuales = 0
        variacion_ingresos = 0
        nuevos_usuarios_mes = 0
        reservas_activas = 0
        reservas_hoy = 0
        
        # Consulta para total de usuarios
        try:
            cursor.execute("SELECT COUNT(*) FROM usuario")
            result = cursor.fetchone()
            total_usuarios = result[0] if result else 0
        except Exception as e:
            print(f"Error contando usuarios: {str(e)}")
            total_usuarios = 0
        
        # Consulta para tickets pendientes
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM ticket 
                WHERE estado IN ('Abierto', 'En Progreso', 'Pendiente')
            """)
            result = cursor.fetchone()
            tickets_pendientes = result[0] if result else 0
        except Exception as e:
            print(f"Error contando tickets pendientes: {str(e)}")
            tickets_pendientes = 0
        
        # Consulta para tickets urgentes
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM ticket 
                WHERE prioridad = 'Alta' AND estado IN ('Abierto', 'En Progreso', 'Pendiente')
            """)
            result = cursor.fetchone()
            tickets_urgentes = result[0] if result else 0
        except Exception as e:
            print(f"Error contando tickets urgentes: {str(e)}")
            tickets_urgentes = 0
        
        # Consulta para total de tickets
        try:
            cursor.execute("SELECT COUNT(*) FROM ticket")
            result = cursor.fetchone()
            total_tickets = result[0] if result else 0
        except Exception as e:
            print(f"Error contando total tickets: {str(e)}")
            total_tickets = 0
        
        # Consulta para ingresos mensuales
        try:
            cursor.execute("""
                SELECT COALESCE(SUM(monto_total), 0) 
                FROM factura 
                WHERE fecha_emision >= DATE_TRUNC('month', CURRENT_DATE)
                AND estado_factura = 'Pagada'
            """)
            result = cursor.fetchone()
            ingresos_mensuales = float(result[0]) if result and result[0] else 0
        except Exception as e:
            print(f"Error calculando ingresos: {str(e)}")
            ingresos_mensuales = 0
        
        # Consulta para variación de ingresos
        try:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN fecha_emision >= DATE_TRUNC('month', CURRENT_DATE) THEN monto_total END), 0) as actual,
                    COALESCE(SUM(CASE WHEN fecha_emision >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') 
                                 AND fecha_emision < DATE_TRUNC('month', CURRENT_DATE) THEN monto_total END), 0) as anterior
                FROM factura 
                WHERE estado_factura = 'Pagada'
            """)
            result = cursor.fetchone()
            if result and result[1] and float(result[1]) > 0:
                variacion = ((float(result[0]) - float(result[1])) / float(result[1])) * 100
                variacion_ingresos = round(variacion, 1)
            else:
                variacion_ingresos = 0
        except Exception as e:
            print(f"Error calculando variación: {str(e)}")
            variacion_ingresos = 0
        
        # Consulta para nuevos usuarios del mes
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM usuario 
                WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)
            """)
            result = cursor.fetchone()
            nuevos_usuarios_mes = result[0] if result else 0
        except Exception as e:
            print(f"Error contando nuevos usuarios: {str(e)}")
            nuevos_usuarios_mes = 0
        
        # Consulta para consumos mensuales
        consumos_mensuales = []
        try:
            cursor.execute("""
                SELECT 
                    'Luz' as tipo,
                    COALESCE(SUM(cl.cantidad_registrada), 0) as total,
                    'kWh' as unidad,
                    '#FF6B6B' as color
                FROM consumo_luz cl
                JOIN consumo c ON cl.id_consumo = c.id_consumo
                WHERE c.fecha_registro >= DATE_TRUNC('month', CURRENT_DATE)
                
                UNION ALL
                
                SELECT 
                    'Agua' as tipo,
                    COALESCE(SUM(ca.cantidad_registrada), 0) as total,
                    'm³' as unidad,
                    '#4ECDC4' as color
                FROM consumo_agua ca
                JOIN consumo c ON ca.id_consumo = c.id_consumo
                WHERE c.fecha_registro >= DATE_TRUNC('month', CURRENT_DATE)
                
                UNION ALL
                
                SELECT 
                    'Gas' as tipo,
                    COALESCE(SUM(cg.cantidad_registrada), 0) as total,
                    'm³' as unidad,
                    '#45B7D1' as color
                FROM consumo_gas cg
                JOIN consumo c ON cg.id_consumo = c.id_consumo
                WHERE c.fecha_registro >= DATE_TRUNC('month', CURRENT_DATE)
            """)
            
            for row in cursor.fetchall():
                consumos_mensuales.append({
                    'tipo': row[0],
                    'total': float(row[1]) if row[1] else 0,
                    'unidad': row[2],
                    'color': row[3]
                })
        except Exception as e:
            print(f"Error obteniendo consumos: {str(e)}")
            # Datos por defecto si hay error
            consumos_mensuales = [
                {'tipo': 'Luz', 'total': 0, 'unidad': 'kWh', 'color': '#FF6B6B'},
                {'tipo': 'Agua', 'total': 0, 'unidad': 'm³', 'color': '#4ECDC4'},
                {'tipo': 'Gas', 'total': 0, 'unidad': 'm³', 'color': '#45B7D1'}
            ]
        
        # Consulta para actividades recientes
        actividades_recientes = []
        try:
            cursor.execute("""
                (SELECT 
                    'Pago registrado' as titulo,
                    'Nuevo pago procesado en el sistema' as descripcion,
                    'success' as tipo,
                    'fas fa-check-circle' as icono,
                    fecha_pago as fecha
                FROM pago 
                ORDER BY fecha_pago DESC 
                LIMIT 3)
                
                UNION ALL
                
                (SELECT 
                    'Ticket creado' as titulo,
                    'Nuevo ticket de soporte creado' as descripcion,
                    'warning' as tipo,
                    'fas fa-ticket-alt' as icono,
                    fecha_emision as fecha
                FROM ticket 
                ORDER BY fecha_emision DESC 
                LIMIT 2)
                
                ORDER BY fecha DESC 
                LIMIT 5
            """)
            
            for row in cursor.fetchall():
                tiempo = calcular_tiempo_relativo(row[4]) if row[4] else "Recientemente"
                actividades_recientes.append({
                    'titulo': row[0],
                    'descripcion': row[1],
                    'tipo': row[2],
                    'icono': row[3],
                    'tiempo': tiempo
                })
        except Exception as e:
            print(f"Error obteniendo actividades: {str(e)}")
            actividades_recientes = []
        
        cursor.close()
        conn.close()
        
        return render_template("administrador/dashboard_admin.html",
                            total_usuarios=total_usuarios,
                            tickets_pendientes=tickets_pendientes,
                            tickets_urgentes=tickets_urgentes,
                            total_tickets=total_tickets,
                            ingresos_mensuales=ingresos_mensuales,
                            variacion_ingresos=variacion_ingresos,
                            nuevos_usuarios_mes=nuevos_usuarios_mes,
                            reservas_activas=reservas_activas,
                            reservas_hoy=reservas_hoy,
                            consumos_mensuales=consumos_mensuales,
                            actividades_recientes=actividades_recientes,
                            ahora=datetime.now())
        
    except Exception as e:
        print(f"Error cargando dashboard: {str(e)}")
        flash("Error al cargar el dashboard.", "danger")
        # Retornar valores por defecto en caso de error
        return render_template("administrador/dashboard_admin.html", 
                            total_usuarios=0,
                            tickets_pendientes=0,
                            tickets_urgentes=0,
                            total_tickets=0,
                            ingresos_mensuales=0,
                            variacion_ingresos=0,
                            nuevos_usuarios_mes=0,
                            reservas_activas=0,
                            reservas_hoy=0,
                            consumos_mensuales=[],
                            actividades_recientes=[],
                            ahora=datetime.now())

def calcular_tiempo_relativo(fecha):
    """Calcula el tiempo relativo para mostrar en el feed de actividad"""
    if not fecha:
        return "Recientemente"
        
    ahora = datetime.now()
    if isinstance(fecha, str):
        try:
            fecha = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
        except:
            return "Recientemente"
    
    diferencia = ahora - fecha
    
    if diferencia.days > 0:
        return f"Hace {diferencia.days} días"
    elif diferencia.seconds // 3600 > 0:
        return f"Hace {diferencia.seconds // 3600} horas"
    elif diferencia.seconds // 60 > 0:
        return f"Hace {diferencia.seconds // 60} minutos"
    else:
        return "Justo ahora"



@admin_bp.route("/consumos")
@login_required
def panel_admin():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener métricas de sensores
        cursor.execute("""
            SELECT 
                COUNT(*) as total_sensores,
                COUNT(CASE WHEN disponibilidad = true THEN 1 END) as sensores_activos,
                COUNT(DISTINCT id_departamento) as deptos_con_sensores
            FROM sensor
        """)
        metricas_sensores = cursor.fetchone()
        
        # Obtener todos los sensores
        cursor.execute("""
            SELECT s.id_sensor, s.id_departamento, s.num_serie, 
                   s.disponibilidad, s.descripcion,
                   d.piso, d.nro as numero_departamento
            FROM sensor s
            LEFT JOIN departamento d ON s.id_departamento = d.id_departamento
            ORDER BY s.id_sensor
        """)
        sensores_data = cursor.fetchall()
        
        sensores = []
        for sensor in sensores_data:
            sensores.append({
                'id_sensor': sensor[0],
                'id_departamento': sensor[1],
                'num_serie': sensor[2],
                'disponibilidad': sensor[3],
                'descripcion': sensor[4],
                'piso': sensor[5],
                'numero_departamento': sensor[6]
            })
        
        # Obtener consumos combinados - CORREGIDO según tu estructura de BD
        cursor.execute("""
            -- Consumo de Luz
            SELECT 
                'luz' as tipo,
                c.id_consumo,
                c.id_sensor,
                cl.cantidad_registrada,
                c.fecha_registro,
                s.id_departamento
            FROM consumo c
            JOIN consumo_luz cl ON c.id_consumo = cl.id_consumo
            JOIN sensor s ON c.id_sensor = s.id_sensor
            WHERE c.fecha_registro >= CURRENT_DATE - INTERVAL '30 days'
            
            UNION ALL
            
            -- Consumo de Agua
            SELECT 
                'agua' as tipo,
                c.id_consumo,
                c.id_sensor,
                ca.cantidad_registrada,
                c.fecha_registro,
                s.id_departamento
            FROM consumo c
            JOIN consumo_agua ca ON c.id_consumo = ca.id_consumo
            JOIN sensor s ON c.id_sensor = s.id_sensor
            WHERE c.fecha_registro >= CURRENT_DATE - INTERVAL '30 days'
            
            UNION ALL
            
            -- Consumo de Gas
            SELECT 
                'gas' as tipo,
                c.id_consumo,
                c.id_sensor,
                cg.cantidad_registrada,
                c.fecha_registro,
                s.id_departamento
            FROM consumo c
            JOIN consumo_gas cg ON c.id_consumo = cg.id_consumo
            JOIN sensor s ON c.id_sensor = s.id_sensor
            WHERE c.fecha_registro >= CURRENT_DATE - INTERVAL '30 days'
            
            ORDER BY fecha_registro DESC
            LIMIT 100
        """)
        
        consumos_data = cursor.fetchall()
        consumos = []
        for consumo in consumos_data:
            consumos.append({
                'tipo': consumo[0],
                'id_consumo': consumo[1],
                'id_sensor': consumo[2],
                'cantidad_registrada': float(consumo[3]) if consumo[3] else 0,
                'fecha_registro': consumo[4],
                'id_departamento': consumo[5]
            })
        
        # Calcular métricas de costos
        agua = calcular_metricas_servicio(consumos, 'agua')
        gas = calcular_metricas_servicio(consumos, 'gas')
        luz = calcular_metricas_servicio(consumos, 'luz')
        
        cursor.close()
        conn.close()
        
        return render_template("administrador/consumos.html",
                            metricas_sensores={
                                'total_sensores': metricas_sensores[0] if metricas_sensores else 0,
                                'sensores_activos': metricas_sensores[1] if metricas_sensores else 0,
                                'deptos_con_sensores': metricas_sensores[2] if metricas_sensores else 0
                            },
                            sensores=sensores,
                            consumos=consumos,
                            total_registros=len(consumos),
                            agua=agua,
                            gas=gas,
                            luz=luz,
                            current_month=datetime.now().strftime('%B %Y'))
        
    except Exception as e:
        print(f"Error cargando dashboard de consumos: {str(e)}")
        flash("Error al cargar el dashboard de consumos.", "danger")
        return render_template("administrador/consumos.html",
                            metricas_sensores={'total_sensores': 0, 'sensores_activos': 0, 'deptos_con_sensores': 0},
                            sensores=[],
                            consumos=[],
                            total_registros=0,
                            agua={'costo': 0, 'consumo_total': 0, 'variacion': 0, 'registros': 0},
                            gas={'costo': 0, 'consumo_total': 0, 'variacion': 0, 'registros': 0},
                            luz={'costo': 0, 'consumo_total': 0, 'variacion': 0, 'registros': 0},
                            current_month=datetime.now().strftime('%B %Y'))

def calcular_metricas_servicio(consumos, tipo_servicio):
    """Calcula métricas para un tipo de servicio específico"""
    consumos_filtrados = [c for c in consumos if c['tipo'] == tipo_servicio]
    
    if not consumos_filtrados:
        return {'costo': 0, 'consumo_total': 0, 'variacion': 0, 'registros': 0}
    
    # Calcular consumo total
    consumo_total = sum(c['cantidad_registrada'] for c in consumos_filtrados)
    
    # Tarifas simuladas (debes reemplazar con tus tarifas reales)
    tarifas = {
        'agua': 5.50,  # $ por m³
        'gas': 12.00,  # $ por m³
        'luz': 0.15    # $ por kWh
    }
    
    costo = consumo_total * tarifas.get(tipo_servicio, 1)
    
    # Variación simulada (en un sistema real, compararías con el mes anterior)
    import random
    variacion = random.uniform(-10, 20)
    
    return {
        'costo': round(costo, 2),
        'consumo_total': consumo_total,
        'variacion': round(variacion, 1),
        'registros': len(consumos_filtrados)
    }

@admin_bp.route("/dashboard-finanzas")
@login_required
def finanzas():
    """Página principal del dashboard de finanzas"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener empleados activos
        cursor.execute("""
            SELECT 
                u.id_usuario,
                u.nombre,
                u.ap_paterno,
                u.ap_materno,
                u.correo,
                e.puesto,
                e.salario,
                e.banco,
                e.numero_cuenta,
                e.estado
            FROM usuario u
            JOIN empleado e ON u.id_usuario = e.id_usuario
            WHERE e.estado = 'activo'
            ORDER BY u.nombre, u.ap_paterno
        """)
        empleados_rows = cursor.fetchall()
        
        empleados = []
        for row in empleados_rows:
            empleados.append({
                'id_usuario': row[0],
                'nombre': row[1],
                'ap_paterno': row[2],
                'ap_materno': row[3],
                'correo': row[4],
                'puesto': row[5],
                'salario': float(row[6]) if row[6] else 0.0,
                'banco': row[7],
                'numero_cuenta': row[8],
                'estado': row[9]
            })

        # Obtener residentes activos
        cursor.execute("""
            SELECT 
                u.id_usuario,
                u.nombre,
                u.ap_paterno,
                u.ap_materno,
                u.correo,
                r.piso,
                r.nro_departamento
            FROM usuario u
            JOIN residente r ON u.id_usuario = r.id_usuario
            WHERE r.fecha_salida IS NULL
            ORDER BY u.nombre, u.ap_paterno
        """)
        residentes_rows = cursor.fetchall()
        
        residentes = []
        for row in residentes_rows:
            residentes.append({
                'id_usuario': row[0],
                'nombre': row[1],
                'ap_paterno': row[2],
                'ap_materno': row[3],
                'correo': row[4],
                'piso': row[5],
                'nro_departamento': row[6]
            })

        # Obtener estadísticas financieras
        cursor.execute("""
            SELECT 
                COUNT(*) as total_pagos,
                COALESCE(SUM(monto), 0) as total_pagado,
                COALESCE(AVG(monto), 0) as promedio_pago
            FROM pago 
            WHERE fecha_pago >= DATE_TRUNC('month', CURRENT_DATE)
        """)
        stats_pagos = cursor.fetchone()

        cursor.execute("""
            SELECT 
                COUNT(*) as total_facturas,
                COALESCE(SUM(monto_total), 0) as total_facturado,
                COALESCE(AVG(monto_total), 0) as promedio_factura
            FROM factura 
            WHERE fecha_emision >= DATE_TRUNC('month', CURRENT_DATE)
        """)
        stats_facturas = cursor.fetchone()

        cursor.execute("""
            SELECT 
                COUNT(*) as deudas_pendientes,
                COALESCE(SUM(monto), 0) as total_deudado
            FROM deuda 
            WHERE estado = 'pendiente'
        """)
        stats_deudas = cursor.fetchone()

        # Obtener últimos pagos para el dashboard
        cursor.execute("""
            SELECT 
                p.id_pago,
                u.nombre || ' ' || u.ap_paterno as nombre_completo,
                p.monto,
                p.metodo,
                p.fecha_pago,
                p.estado
            FROM pago p
            JOIN usuario u ON p.id_usuario = u.id_usuario
            ORDER BY p.fecha_pago DESC
            LIMIT 10
        """)
        pagos_recientes_rows = cursor.fetchall()
        
        pagos_recientes = []
        for row in pagos_recientes_rows:
            pagos_recientes.append({
                'id_pago': row[0],
                'nombre_completo': row[1],
                'monto': float(row[2]),
                'metodo': row[3],
                'fecha_pago': row[4],
                'estado': row[5]
            })

        # Preparar métricas para el template
        metricas = {
            'total_pagos_mes': stats_pagos[0] if stats_pagos else 0,
            'total_pagado_mes': float(stats_pagos[1]) if stats_pagos else 0.0,
            'promedio_pago': float(stats_pagos[2]) if stats_pagos else 0.0,
            'total_facturas_mes': stats_facturas[0] if stats_facturas else 0,
            'total_facturado_mes': float(stats_facturas[1]) if stats_facturas else 0.0,
            'deudas_pendientes': stats_deudas[0] if stats_deudas else 0,
            'total_deudado': float(stats_deudas[1]) if stats_deudas else 0.0
        }

        print(f"📊 Finanzas - Empleados: {len(empleados)}, Residentes: {len(residentes)}")

    except Exception as e:
        print(f"❌ Error al cargar dashboard de finanzas: {e}")
        flash(f"Error al cargar dashboard de finanzas: {str(e)}", "danger")
        empleados = []
        residentes = []
        pagos_recientes = []
        metricas = {}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "administrador/finanzas.html",
        empleados=empleados,
        residentes=residentes,
        pagos_recientes=pagos_recientes,
        metricas=metricas,
        current_date=datetime.now().date(),
        current_month=datetime.now().strftime('%B %Y')
    )

@admin_bp.route("/pagar-empleado", methods=["POST"])
@login_required
def pagar_empleado():
    """Procesar pago a empleados - VERSIÓN SIMPLIFICADA"""
    conn = None
    cursor = None
    try:
        id_usuario = request.form.get('id_usuario')
        monto = request.form.get('monto')
        metodo = request.form.get('metodo')
        nro_trans = request.form.get('nro_trans', '')

        # Validaciones básicas
        if not id_usuario or not metodo:
            flash('El empleado y método de pago son obligatorios', 'error')
            return redirect(url_for('admin.finanzas'))

        # Si no se proporciona monto, obtener el salario del empleado
        if not monto:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT salario FROM empleado 
                WHERE id_usuario = %s
            """, (id_usuario,))
            
            resultado = cursor.fetchone()
            if resultado and resultado[0]:
                monto = float(resultado[0])
            else:
                flash('No se pudo determinar el monto del pago', 'error')
                return redirect(url_for('admin.finanzas'))
        else:
            monto = float(monto)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener información del empleado
        cursor.execute("""
            SELECT 
                u.nombre, u.ap_paterno, u.correo,
                e.salario, e.banco, e.numero_cuenta
            FROM usuario u
            JOIN empleado e ON u.id_usuario = e.id_usuario
            WHERE u.id_usuario = %s
        """, (id_usuario,))
        
        empleado = cursor.fetchone()
        if not empleado:
            flash('Empleado no encontrado', 'error')
            return redirect(url_for('admin.finanzas'))

        # Generar número de transacción si no se proporciona
        if not nro_trans and metodo == 'transferencia':
            nro_trans = f"TRF-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # SOLUCIÓN SIMPLE: Usar el ID del usuario actual o un valor por defecto
        # Buscar el ID del administrador actual en la base de datos
        cursor.execute("""
            SELECT a.id_usuario 
            FROM administrador a 
            JOIN usuario u ON a.id_usuario = u.id_usuario 
            WHERE u.correo = %s OR u.id_usuario = %s 
            LIMIT 1
        """, (current_user.email if hasattr(current_user, 'email') else '', 
              current_user.id if hasattr(current_user, 'id') else 1))
        
        admin_result = cursor.fetchone()
        pagado_por = admin_result[0] if admin_result else 1

        # Registrar el pago en la base de datos
        cursor.execute("""
            INSERT INTO pago (
                id_usuario, monto, metodo, estado, fecha_pago, 
                nro_trans, pagado_por
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            id_usuario, monto, metodo, 'completado', 
            datetime.now().date(), nro_trans if metodo == 'transferencia' else None,
            pagado_por  # Usar el ID encontrado
        ))

        # Registrar movimiento financiero
        cursor.execute("""
            INSERT INTO movimientos (
                tipo, monto, categoria, descripcion, fecha, id_factura
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            'egreso', monto, 'nomina', 
            f'Pago de nómina a {empleado[0]} {empleado[1]}',
            datetime.now().date(), None
        ))

        conn.commit()

        flash(f'✅ Pago de Bs {monto:.2f} registrado exitosamente para {empleado[0]} {empleado[1]}', 'success')
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error al procesar el pago: {str(e)}")
        flash(f'Error al procesar el pago: {str(e)}', 'error')

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for('admin.finanzas'))

@admin_bp.route("/registrar-cobros", methods=["POST"])
@login_required
def registrar_cobros():
    """Registrar cobros a residentes - VERSIÓN CORREGIDA"""
    conn = None
    cursor = None
    try:
        id_usuario = request.form.get('id_usuario')
        conceptos = request.form.getlist('concepto[]')
        montos = request.form.getlist('monto[]')

        # Validaciones
        if not id_usuario:
            flash('Debe seleccionar un residente', 'error')
            return redirect(url_for('admin.finanzas'))

        if not conceptos or not montos:
            flash('Debe agregar al menos un concepto de cobro', 'error')
            return redirect(url_for('admin.finanzas'))

        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener información del residente
        cursor.execute("""
            SELECT u.nombre, u.ap_paterno, u.correo, r.piso, r.nro_departamento
            FROM usuario u
            JOIN residente r ON u.id_usuario = r.id_usuario
            WHERE u.id_usuario = %s
        """, (id_usuario,))
        
        residente = cursor.fetchone()
        if not residente:
            flash('Residente no encontrado', 'error')
            return redirect(url_for('admin.finanzas'))

        # INICIALIZAR total_monto aquí
        total_monto = 0.0
        descripcion_factura = "Cobros varios:\n"

        # Procesar cada concepto
        for i, (concepto, monto_str) in enumerate(zip(conceptos, montos)):
            if concepto.strip() and monto_str:
                try:
                    monto_float = float(monto_str)
                    total_monto += monto_float
                    descripcion_factura += f"- {concepto}: Bs {monto_float:.2f}\n"
                except ValueError:
                    flash(f'Error: El monto "{monto_str}" no es válido', 'error')
                    return redirect(url_for('admin.finanzas'))

        # Validar que haya al menos un concepto válido
        if total_monto <= 0:
            flash('Debe agregar al menos un concepto de cobro con monto válido', 'error')
            return redirect(url_for('admin.finanzas'))

        # Crear factura
        cursor.execute("""
            INSERT INTO factura (
                monto_total, fecha_emision, fecha_vencimiento, 
                estado_factura, pdf_url, id_usuario
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_factura
        """, (
            total_monto, 
            datetime.now().date(), 
            (datetime.now() + timedelta(days=7)).date(),
            'pendiente', 
            None, 
            id_usuario
        ))
        
        id_factura = cursor.fetchone()[0]

        # Registrar movimiento financiero
        cursor.execute("""
            INSERT INTO movimientos (
                tipo, monto, categoria, descripcion, fecha, id_factura
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            'ingreso', 
            total_monto, 
            'cobros',
            f'Cobros a {residente[0]} {residente[1]} - Depto. {residente[3]}-{residente[4]}',
            datetime.now().date(), 
            id_factura
        ))

        # Registrar deuda
        cursor.execute("""
            INSERT INTO deuda (
                id_usuario, identificador, monto, estado, 
                fecha_pago, invoice_id, invoice_url
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            id_usuario, 
            f"FAC-{id_factura}", 
            total_monto, 
            'pendiente',
            None, 
            f"INV-{id_factura}", 
            None
        ))

        conn.commit()

        flash(f'✅ Cobros registrados exitosamente por Bs {total_monto:.2f} para {residente[0]} {residente[1]}', 'success')
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error al registrar cobros: {str(e)}")
        flash(f'Error al registrar cobros: {str(e)}', 'error')

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for('admin.finanzas'))

@admin_bp.route('/marcar-pagado/<int:id_deuda>', methods=['POST'])
@login_required
def marcar_pagado(id_deuda):
    """Marcar una deuda como pagada"""
    if current_user.id_rol != 1:
        return jsonify({'success': False, 'message': 'Acceso no autorizado'})

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener información de la deuda
        cursor.execute("""
            SELECT d.monto, d.id_usuario, u.nombre, u.ap_paterno, d.identificador
            FROM deuda d
            JOIN usuario u ON d.id_usuario = u.id_usuario
            WHERE d.id_deuda = %s
        """, (id_deuda,))
        
        deuda_info = cursor.fetchone()
        if not deuda_info:
            return jsonify({'success': False, 'message': 'Deuda no encontrada'})

        monto = deuda_info[0]
        id_usuario = deuda_info[1]
        nombre = f"{deuda_info[2]} {deuda_info[3]}"
        identificador = deuda_info[4]

        # Marcar deuda como pagada
        cursor.execute("""
            UPDATE deuda 
            SET estado = 'pagado', fecha_pago = %s 
            WHERE id_deuda = %s
        """, (datetime.now().date(), id_deuda))

        # Registrar pago
        cursor.execute("""
            INSERT INTO pago (
                id_usuario, monto, metodo, estado, fecha_pago, 
                nro_trans, pagado_por, id_factura
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_usuario, monto, 'efectivo', 'completado', 
            datetime.now().date(), f"PAGO-{id_deuda}", 
            current_user.id_usuario, None
        ))

        # Actualizar estado de la factura si existe
        if identificador.startswith('FAC-'):
            try:
                id_factura = identificador.split('-')[1]
                cursor.execute("""
                    UPDATE factura 
                    SET estado_factura = 'pagada' 
                    WHERE id_factura = %s
                """, (id_factura,))
            except:
                print("⚠️ No se pudo actualizar la factura asociada")

        conn.commit()

        return jsonify({
            'success': True, 
            'message': f'Deuda marcada como pagada para {nombre}'
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error al marcar deuda como pagada: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@admin_bp.route('/eliminar-deuda/<int:id_deuda>', methods=['POST'])
@login_required
def eliminar_deuda(id_deuda):
    """Eliminar una deuda"""
    if current_user.id_rol != 1:
        return jsonify({'success': False, 'message': 'Acceso no autorizado'})

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar que la deuda existe
        cursor.execute("SELECT id_deuda FROM deuda WHERE id_deuda = %s", (id_deuda,))
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': 'Deuda no encontrada'})

        # Eliminar deuda
        cursor.execute("DELETE FROM deuda WHERE id_deuda = %s", (id_deuda,))
        conn.commit()

        return jsonify({'success': True, 'message': 'Deuda eliminada correctamente'})

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error al eliminar deuda: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@admin_bp.route('/obtener-detalle-deuda/<int:id_deuda>')
@login_required
def obtener_detalle_deuda(id_deuda):
    """Obtener detalles de una deuda específica"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                d.id_deuda,
                u.nombre || ' ' || u.ap_paterno as nombre_completo,
                u.correo,
                r.piso,
                r.nro_departamento,
                d.identificador,
                d.monto,
                d.estado,
                d.fecha_pago,
                d.invoice_id,
                d.invoice_url
            FROM deuda d
            JOIN usuario u ON d.id_usuario = u.id_usuario
            LEFT JOIN residente r ON u.id_usuario = r.id_usuario
            WHERE d.id_deuda = %s
        """, (id_deuda,))
        
        deuda = cursor.fetchone()

        if not deuda:
            return jsonify({'success': False, 'message': 'Deuda no encontrada'})

        deuda_info = {
            'id_deuda': deuda[0],
            'nombre_completo': deuda[1],
            'correo': deuda[2],
            'departamento': f"Piso {deuda[3]} - Depto {deuda[4]}" if deuda[3] and deuda[4] else "No asignado",
            'concepto': deuda[5],
            'monto': float(deuda[6]),
            'estado': deuda[7],
            'fecha_pago': deuda[8].strftime('%d/%m/%Y') if deuda[8] else 'No pagado',
            'invoice_id': deuda[9],
            'invoice_url': deuda[10]
        }

        return jsonify({'success': True, 'deuda': deuda_info})

    except Exception as e:
        print(f"❌ Error al obtener detalle de deuda: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@admin_bp.route("/comprobantes")
@login_required
def ver_comprobantes():
    """Lista de comprobantes/pagos incluyendo los de reservas"""
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener todos los pagos
        cursor.execute("""
            SELECT 
                p.id_pago, 
                u.nombre, 
                u.ap_paterno,  
                p.monto, 
                p.metodo, 
                p.nro_trans, 
                p.fecha_pago, 
                p.estado
            FROM pago p
            JOIN usuario u ON p.id_usuario = u.id_usuario
            ORDER BY p.fecha_pago DESC
        """)
        comprobantes = cursor.fetchall()

        return render_template('administrador/comprobante.html', comprobantes=comprobantes)
    except Exception as e:
        print(f"❌ Error al listar comprobantes: {e}")
        flash("Error al cargar comprobantes.", "danger")
        return render_template('administrador/comprobante.html', comprobantes=[])
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@admin_bp.route('/comprobante/<int:id_pago>')
@login_required
def ver_comprobante(id_pago):
    """Ver detalle de un comprobante de pago"""
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener información del pago - ajustado para tu template
        cursor.execute("""
            SELECT 
                p.id_pago, 
                u.nombre, 
                u.ap_paterno, 
                p.monto, 
                p.metodo, 
                p.nro_trans, 
                p.fecha_pago, 
                p.estado,
                up.nombre as admin_nombre,
                up.ap_paterno as admin_ap_paterno
            FROM pago p
            JOIN usuario u ON p.id_usuario = u.id_usuario
            JOIN usuario up ON p.pagado_por = up.id_usuario
            WHERE p.id_pago = %s
        """, (id_pago,))
        pago = cursor.fetchone()

        if not pago:
            flash('Comprobante no encontrado.', 'warning')
            return redirect(url_for('admin.ver_comprobantes'))

        # Para identificar si es de reserva, verificamos el formato del nro_trans
        info_extra = None
        if pago[5] and pago[5].startswith('RES'):  # CORREGIDO: pago[5] es nro_trans
            # Extraer ID de reserva del número de transacción
            reserva_id = pago[5][3:9]  # RES{6 dígitos}...
            try:
                reserva_id_int = int(reserva_id)
                cursor.execute("""
                    SELECT pq.fecha_reserva, pq.horas, a.nombre as area_nombre,
                           CASE 
                               WHEN u.id_usuario IS NOT NULL THEN 
                                   CONCAT(u.nombre, ' ', u.ap_paterno, ' - Piso ', r.piso, ' Depto ', r.nro_departamento)
                               ELSE 'Persona Externa'
                           END as solicitante_info
                    FROM pagos_qr pq
                    LEFT JOIN usuario u ON pq.id_residente = u.id_usuario
                    LEFT JOIN residente r ON u.id_usuario = r.id_usuario
                    JOIN area a ON pq.id_concepto = a.id_area
                    WHERE pq.id_pago = %s
                """, (reserva_id_int,))
                
                reserva_info = cursor.fetchone()
                if reserva_info:
                    info_extra = {
                        'tipo': 'reserva',
                        'fecha_reserva': reserva_info[0],
                        'horas': reserva_info[1],
                        'area_nombre': reserva_info[2],
                        'solicitante_info': reserva_info[3]
                    }
            except ValueError:
                pass  # No es un ID de reserva válido

        # Fecha actual para el pie del comprobante
        fecha_actual = datetime.now().strftime('%d/%m/%Y a las %H:%M')

        return render_template('administrador/comprobante_detalle.html', 
                             pago=pago, 
                             info_extra=info_extra,
                             fecha_actual=fecha_actual)
        
    except Exception as e:
        print(f"❌ Error al cargar comprobante: {e}")
        flash(f'Error al cargar comprobante: {str(e)}', 'danger')
        return redirect(url_for('admin.ver_comprobantes'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
@admin_bp.route("/enviar-mensaje-residente", methods=["POST"])
@login_required
def enviar_mensaje_residente():
    """Enviar mensaje de cobro al residente"""
    try:
        id_usuario = request.form.get('id_usuario')
        mensaje = request.form.get('mensaje')

        if not id_usuario or not mensaje:
            return jsonify({'success': False, 'message': 'Datos incompletos'})

        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener información del residente
        cursor.execute("""
            SELECT nombre, ap_paterno, correo 
            FROM usuario 
            WHERE id_usuario = %s
        """, (id_usuario,))
        
        residente = cursor.fetchone()
        
        if not residente:
            return jsonify({'success': False, 'message': 'Residente no encontrado'})

        # Enviar correo electrónico
        enviar_correo_cobro(residente[2], mensaje)

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Mensaje enviado correctamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al enviar mensaje: {str(e)}'})

@admin_bp.route("/generar-reporte-finanzas")
@login_required
def generar_reporte_finanzas():
    """Generar reporte de finanzas"""
    try:
        # Obtener parámetros de filtro
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        tipo_reporte = request.args.get('tipo', 'general')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta base para movimientos
        query = """
            SELECT 
                m.id, m.tipo, m.monto, m.categoria, m.descripcion, m.fecha,
                u.nombre || ' ' || u.ap_paterno as usuario
            FROM movimientos m
            LEFT JOIN factura f ON m.id_factura = f.id_factura
            LEFT JOIN usuario u ON f.id_usuario = u.id_usuario
            WHERE 1=1
        """
        params = []

        # Aplicar filtros de fecha
        if fecha_inicio:
            query += " AND m.fecha >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            query += " AND m.fecha <= %s"
            params.append(fecha_fin)

        query += " ORDER BY m.fecha DESC"

        cursor.execute(query, params)
        movimientos_rows = cursor.fetchall()

        movimientos = []
        for row in movimientos_rows:
            movimientos.append({
                'id': row[0],
                'tipo': row[1],
                'monto': float(row[2]),
                'categoria': row[3],
                'descripcion': row[4],
                'fecha': row[5],
                'usuario': row[6]
            })

        # Calcular totales
        total_ingresos = sum(m['monto'] for m in movimientos if m['tipo'] == 'ingreso')
        total_egresos = sum(m['monto'] for m in movimientos if m['tipo'] == 'egreso')
        balance = total_ingresos - total_egresos

        # Preparar datos para el reporte
        datos_reporte = {
            'movimientos': movimientos,
            'total_ingresos': total_ingresos,
            'total_egresos': total_egresos,
            'balance': balance,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'tipo_reporte': tipo_reporte
        }

        cursor.close()
        conn.close()

        return render_template("administrador/reportes_finanzas.html", **datos_reporte)
        
    except Exception as e:
        flash(f'Error al generar reporte: {str(e)}', 'error')
        return redirect(url_for('admin.finanzas'))


@admin_bp.route('/reporte-deudas')
@login_required
def reporte_deudas():
    """Lista de deudas pendientes - VERSIÓN SIMPLIFICADA"""
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # CONSULTA SIMPLIFICADA - sin fecha_creacion
        cursor.execute("""
            SELECT
                d.id_deuda,
                u.nombre || ' ' || u.ap_paterno || 
                CASE 
                    WHEN u.ap_materno IS NOT NULL THEN ' ' || u.ap_materno 
                    ELSE '' 
                END as nombre_completo,
                u.correo,
                CASE 
                    WHEN r.piso IS NOT NULL AND r.nro_departamento IS NOT NULL 
                    THEN 'Piso ' || r.piso || ' - Depto ' || r.nro_departamento
                    WHEN r.piso IS NOT NULL THEN 'Piso ' || r.piso
                    WHEN r.nro_departamento IS NOT NULL THEN 'Depto ' || r.nro_departamento
                    ELSE 'No asignado'
                END as departamento,
                d.identificador,
                d.monto,
                d.estado,
                d.fecha_pago
            FROM deuda d
            JOIN usuario u ON d.id_usuario = u.id_usuario
            LEFT JOIN residente r ON u.id_usuario = r.id_usuario
            WHERE d.estado = 'pendiente'
            ORDER BY d.id_deuda DESC
        """)
        rows = cursor.fetchall()

        deudas = []
        for r in rows:
            deudas.append({
                'id_deuda': r[0],
                'nombre_completo': r[1],
                'correo': r[2],
                'departamento': r[3],
                'identificador': r[4],
                'monto': float(r[5]) if r[5] is not None else 0.0,
                'estado': r[6],
                'fecha_registro': r[7],  # Usamos fecha_pago como fecha_registro
                'fecha_pago': r[7]
            })

        # El resto del código de estadísticas permanece igual...
        cursor.execute("SELECT COALESCE(SUM(monto),0) FROM deuda WHERE estado = 'pendiente'")
        total_pendiente = float(cursor.fetchone()[0] or 0.0)

        cursor.execute("SELECT COALESCE(SUM(monto),0) FROM deuda WHERE estado = 'pagado'")
        total_pagado = float(cursor.fetchone()[0] or 0.0)

        cursor.execute("SELECT COUNT(*) FROM deuda WHERE estado = 'pendiente'")
        total_deudas_pendientes = int(cursor.fetchone()[0] or 0)

        print(f"📊 Reporte deudas cargado: {len(deudas)} deudas pendientes")
        
        return render_template('administrador/reporte.html',
                               deudas=deudas,
                               deudas_empleados=deudas,
                               pagos_empleados=[],
                               movimientos=[],
                               total_ingresos=0.0,
                               total_egresos=0.0,
                               balance=0.0,
                               total_pendiente=total_pendiente,
                               total_pagado=total_pagado,
                               total_deudas_pendientes=total_deudas_pendientes,
                               fecha_inicio=None,
                               fecha_fin=None,
                               tipo_reporte='deudas')
                               
    except Exception as e:
        print(f"❌ Error cargando reporte de deudas: {e}")
        flash('Error al cargar reporte de deudas.', 'danger')
        return render_template('administrador/reporte.html',
                               deudas=[],
                               total_pendiente=0.0,
                               total_pagado=0.0,
                               total_deudas_pendientes=0,
                               total_ingresos=0.0,
                               total_egresos=0.0,
                               balance=0.0,
                               movimientos=[],
                               pagos_empleados=[],
                               deudas_empleados=[],
                               fecha_inicio=None,
                               fecha_fin=None,
                               tipo_reporte='deudas')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@admin_bp.route("/obtener-datos-empleado/<int:id_usuario>")
@login_required
def obtener_datos_empleado(id_usuario):
    """Obtener datos específicos de un empleado para AJAX"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                u.nombre, u.ap_paterno, u.correo,
                e.salario, e.banco, e.numero_cuenta, e.puesto
            FROM usuario u
            JOIN empleado e ON u.id_usuario = e.id_usuario
            WHERE u.id_usuario = %s
        """, (id_usuario,))
        
        empleado = cursor.fetchone()

        cursor.close()
        conn.close()

        if empleado:
            return jsonify({
                'success': True,
                'data': {
                    'nombre': f"{empleado[0]} {empleado[1]}",
                    'salario': float(empleado[3]),
                    'banco': empleado[4] or 'No registrado',
                    'cuenta': empleado[5] or 'No registrada',
                    'puesto': empleado[6],
                    'correo': empleado[2]
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Empleado no encontrado'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Funciones auxiliares para envío de correos (igual que antes)
def enviar_comprobante_pago(empleado, monto, metodo, nro_trans):
    """Enviar comprobante de pago por correo al empleado"""
    try:
        # Configuración SMTP
        smtp_server = "smtp.gmail.com"
        port = 587
        sender_email = "tu_correo@gmail.com"
        password = "tu_password"

        # Crear mensaje
        message = MimeMultipart("alternative")
        message["Subject"] = "Comprobante de Pago - Sistema de Gestión"
        message["From"] = sender_email
        message["To"] = empleado[2]  # correo

        # Contenido del mensaje
        text = f"""
        Hola {empleado[0]},

        Se ha procesado tu pago de nómina:

        Monto: Bs {monto}
        Método: {metodo}
        {'Número de transacción: ' + nro_trans if nro_trans else ''}
        Fecha: {datetime.now().strftime('%d/%m/%Y')}

        Saludos,
        Administración
        """

        html = f"""
        <html>
          <body>
            <h2>Comprobante de Pago</h2>
            <p>Hola <strong>{empleado[0]}</strong>,</p>
            <p>Se ha procesado tu pago de nómina:</p>
            <ul>
              <li><strong>Monto:</strong> Bs {monto}</li>
              <li><strong>Método:</strong> {metodo}</li>
              {f'<li><strong>Número de transacción:</strong> {nro_trans}</li>' if nro_trans else ''}
              <li><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y')}</li>
            </ul>
            <p>Saludos,<br>Administración</p>
          </body>
        </html>
        """

        part1 = MimeText(text, "plain")
        part2 = MimeText(html, "html")
        message.attach(part1)
        message.attach(part2)

        # Enviar correo
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, empleado[2], message.as_string())
            
    except Exception as e:
        print(f"Error al enviar correo: {str(e)}")

def enviar_correo_cobro(correo_residente, mensaje):
    """Enviar correo de cobro al residente"""
    try:
        smtp_server = "smtp.gmail.com"
        port = 587
        sender_email = "tu_correo@gmail.com"
        password = "tu_password"

        message = MimeMultipart("alternative")
        message["Subject"] = "Notificación de Cobro - Sistema de Gestión"
        message["From"] = sender_email
        message["To"] = correo_residente

        mensaje_html = mensaje.replace('\n', '<br>')

        html = f"""
        <html>
          <body>
            <h2>Notificación de Cobro</h2>
            <div>{mensaje_html}</div>
            <br>
            <p>Atentamente,<br>Administración del Edificio</p>
          </body>
        </html>
        """

        part = MimeText(html, "html")
        message.attach(part)

        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, correo_residente, message.as_string())
            
    except Exception as e:
        print(f"Error al enviar correo de cobro: {str(e)}")

@admin_bp.route("/reportes-finanzas")
@login_required
def reportes_finanzas():
    """Página de reportes financieros - VERSIÓN CORREGIDA"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener parámetros de filtro con valores por defecto
        fecha_inicio = request.args.get('fecha_inicio', '')
        fecha_fin = request.args.get('fecha_fin', '')
        tipo_reporte = request.args.get('tipo_reporte', 'general')

        # Inicializar todas las variables necesarias
        pagos_empleados = []
        deudas_empleados = []
        deudas_residentes = []
        movimientos = []
        total_ingresos = 0.0
        total_egresos = 0.0
        balance = 0.0

        # 1. OBTENER EMPLEADOS PAGADOS
        query_pagos = """
            SELECT 
                p.id_pago,
                u.nombre || ' ' || u.ap_paterno as nombre_completo,
                u.correo,
                e.puesto,
                p.monto,
                p.metodo,
                p.fecha_pago,
                p.nro_trans,
                p.estado
            FROM pago p
            JOIN usuario u ON p.id_usuario = u.id_usuario
            JOIN empleado e ON u.id_usuario = e.id_usuario
            WHERE p.estado = 'completado'
        """
        params_pagos = []

        if fecha_inicio:
            query_pagos += " AND p.fecha_pago >= %s"
            params_pagos.append(fecha_inicio)
        if fecha_fin:
            query_pagos += " AND p.fecha_pago <= %s"
            params_pagos.append(fecha_fin)

        query_pagos += " ORDER BY p.fecha_pago DESC"

        cursor.execute(query_pagos, params_pagos)
        pagos_rows = cursor.fetchall()
        
        for row in pagos_rows:
            pagos_empleados.append({
                'id_pago': row[0],
                'nombre_completo': row[1],
                'correo': row[2],
                'puesto': row[3],
                'monto': float(row[4]),
                'metodo': row[5],
                'fecha_pago': row[6],
                'nro_trans': row[7],
                'estado': row[8]
            })

        # 2. OBTENER DEUDAS PENDIENTES (RESIDENTES)
        query_deudas = """
            SELECT 
                d.id_deuda,
                u.nombre || ' ' || u.ap_paterno as nombre_completo,
                r.piso,
                r.nro_departamento,
                d.identificador as concepto,
                d.monto,
                d.fecha_pago,
                d.estado,
                EXTRACT(DAYS FROM (CURRENT_DATE - d.fecha_pago)) as dias_atraso
            FROM deuda d
            JOIN usuario u ON d.id_usuario = u.id_usuario
            LEFT JOIN residente r ON u.id_usuario = r.id_usuario
            WHERE d.estado = 'pendiente'
        """
        params_deudas = []

        if fecha_inicio:
            query_deudas += " AND d.fecha_pago >= %s"
            params_deudas.append(fecha_inicio)
        if fecha_fin:
            query_deudas += " AND d.fecha_pago <= %s"
            params_deudas.append(fecha_fin)

        query_deudas += " ORDER BY d.fecha_pago DESC"

        cursor.execute(query_deudas, params_deudas)
        deudas_rows = cursor.fetchall()
        
        for row in deudas_rows:
            departamento = f"Piso {row[2]} - {row[3]}" if row[2] and row[3] else "No asignado"
            deudas_residentes.append({
                'id_deuda': row[0],
                'nombre_completo': row[1],
                'departamento': departamento,
                'concepto': row[4],
                'monto': float(row[5]),
                'fecha_vencimiento': row[6],
                'estado': row[7],
                'dias_atraso': int(row[8]) if row[8] else 0
            })

        # 3. OBTENER MOVIMIENTOS FINANCIEROS
        query_movimientos = """
            SELECT 
                m.id, 
                m.tipo, 
                m.monto, 
                m.categoria, 
                m.descripcion, 
                m.fecha,
                COALESCE(u.nombre || ' ' || u.ap_paterno, 'Sistema') as usuario
            FROM movimientos m
            LEFT JOIN factura f ON m.id_factura = f.id_factura
            LEFT JOIN usuario u ON f.id_usuario = u.id_usuario
            WHERE 1=1
        """
        params_movimientos = []

        if fecha_inicio:
            query_movimientos += " AND m.fecha >= %s"
            params_movimientos.append(fecha_inicio)
        if fecha_fin:
            query_movimientos += " AND m.fecha <= %s"
            params_movimientos.append(fecha_fin)

        # Filtrar por tipo de reporte
        if tipo_reporte == 'pagos':
            query_movimientos += " AND m.tipo = 'egreso'"
        elif tipo_reporte == 'deudas':
            query_movimientos += " AND m.tipo = 'ingreso'"

        query_movimientos += " ORDER BY m.fecha DESC"

        cursor.execute(query_movimientos, params_movimientos)
        movimientos_rows = cursor.fetchall()

        for row in movimientos_rows:
            movimiento = {
                'id': row[0],
                'tipo': row[1],
                'monto': float(row[2]),
                'categoria': row[3],
                'descripcion': row[4],
                'fecha': row[5],
                'usuario': row[6]
            }
            movimientos.append(movimiento)
            
            # Calcular totales
            if movimiento['tipo'] == 'ingreso':
                total_ingresos += movimiento['monto']
            else:
                total_egresos += movimiento['monto']

        balance = total_ingresos - total_egresos

        print(f"📊 Reportes - Pagos: {len(pagos_empleados)}, Deudas: {len(deudas_residentes)}, Movimientos: {len(movimientos)}")
        print(f"💰 Totales - Ingresos: {total_ingresos}, Egresos: {total_egresos}, Balance: {balance}")

    except Exception as e:
        print(f"❌ Error al cargar reportes financieros: {e}")
        flash(f"Error al cargar reportes financieros: {str(e)}", "danger")
        # Asegurar que las variables tengan valores por defecto incluso en caso de error
        pagos_empleados = []
        deudas_residentes = []
        movimientos = []
        total_ingresos = 0.0
        total_egresos = 0.0
        balance = 0.0

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "administrador/reporte.html",
        # Variables principales
        pagos_empleados=pagos_empleados,
        deudas_residentes=deudas_residentes,  # Cambiado de deudas_empleados
        movimientos=movimientos,
        
        # Variables de totales
        total_ingresos=total_ingresos,
        total_egresos=total_egresos,
        balance=balance,
        
        # Variables de filtros
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        tipo_reporte=tipo_reporte,
        
        # Variables de contexto
        current_date=datetime.now().date(),
        current_month=datetime.now().strftime('%B %Y')
    )

@admin_bp.route("/reservas")
@login_required
def reservas():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener todas las reservas con información completa
        cursor.execute("""
            SELECT 
                pq.id_pago,
                pq.monto,
                pq.descripcion,
                pq.estado,
                pq.fecha_generacion,
                pq.fecha_expiracion,
                pq.fecha_pago,
                pq.fecha_reserva,
                pq.horas,
                pq.observaciones,
                -- Información del residente (si existe)
                u.id_usuario,
                u.nombre as residente_nombre,
                u.ap_paterno as residente_ap_paterno,
                u.ap_materno as residente_ap_materno,
                u.correo as residente_correo,
                u.telefono as residente_telefono,
                r.piso,
                r.nro_departamento,
                -- Información del área
                a.id_area,
                a.nombre as area_nombre,
                a.descripcion as area_descripcion,
                a.ubicacion as area_ubicacion,
                cp.nombre as concepto_nombre,
                -- Determinar tipo de solicitante
                CASE 
                    WHEN u.id_usuario IS NOT NULL THEN 'residente'
                    ELSE 'externo'
                END as tipo_solicitante
            FROM pagos_qr pq
            LEFT JOIN usuario u ON pq.id_residente = u.id_usuario
            LEFT JOIN residente r ON u.id_usuario = r.id_usuario
            JOIN area a ON pq.id_concepto = a.id_area
            JOIN conceptos_pago cp ON pq.id_concepto = cp.id_concepto
            ORDER BY 
                CASE 
                    WHEN pq.estado = 'pendiente' THEN 1
                    WHEN pq.estado = 'pagado' THEN 2
                    WHEN pq.estado = 'expirado' THEN 3
                    ELSE 4
                END,
                pq.fecha_reserva DESC,
                pq.fecha_generacion DESC
        """)
        reservas = cursor.fetchall()
        
        # Convertir a lista de diccionarios
        reservas_list = []
        for reserva in reservas:
            # Determinar información del solicitante
            if reserva[22] == 'residente':  # tipo_solicitante
                solicitante_nombre = f"{reserva[11]} {reserva[12]} {reserva[13] or ''}"
                solicitante_contacto = f"{reserva[14]} | {reserva[15]}"
                solicitante_ubicacion = f"Piso {reserva[16]} - Depto {reserva[17]}" if reserva[16] else "Residente"
                tipo_solicitante = "residente"
            else:
                # Para externos, usamos campos adicionales que almacenaremos en observaciones o descripción
                solicitante_nombre = "Externo - Ver observaciones"
                solicitante_contacto = "Información en observaciones"
                solicitante_ubicacion = "Externo"
                tipo_solicitante = "externo"
            
            reservas_list.append({
                'id_pago': reserva[0],
                'monto': float(reserva[1]) if reserva[1] else 0.0,
                'descripcion': reserva[2],
                'estado': reserva[3],
                'fecha_generacion': reserva[4],
                'fecha_expiracion': reserva[5],
                'fecha_pago': reserva[6],
                'fecha_reserva': reserva[7],
                'horas': reserva[8],
                'observaciones': reserva[9],
                'id_usuario': reserva[10],
                'solicitante_nombre': solicitante_nombre,
                'solicitante_contacto': solicitante_contacto,
                'solicitante_ubicacion': solicitante_ubicacion,
                'tipo_solicitante': tipo_solicitante,
                'id_area': reserva[18],
                'area_nombre': reserva[19],
                'area_descripcion': reserva[20],
                'area_ubicacion': reserva[21],
                'concepto_nombre': reserva[22]
            })
        
        # Obtener estadísticas
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN estado = 'pendiente' THEN 1 END) as pendientes,
                COUNT(CASE WHEN estado = 'pagado' THEN 1 END) as pagados,
                COUNT(CASE WHEN estado = 'expirado' THEN 1 END) as expirados,
                COUNT(CASE WHEN fecha_reserva = CURRENT_DATE THEN 1 END) as hoy,
                -- Contar residentes vs externos
                COUNT(CASE WHEN id_residente IS NOT NULL THEN 1 END) as residentes,
                COUNT(CASE WHEN id_residente IS NULL THEN 1 END) as externos
            FROM pagos_qr
        """)
        stats = cursor.fetchone()
        
        # Obtener áreas disponibles para el formulario
        cursor.execute("""
            SELECT 
                id_area,
                nombre,
                descripcion,
                ubicacion
            FROM area
            ORDER BY nombre
        """)
        areas = cursor.fetchall()
        
        areas_list = []
        for area in areas:
            areas_list.append({
                'id_area': area[0],
                'nombre': area[1],
                'descripcion': area[2],
                'ubicacion': area[3]
            })
        
        # Obtener residentes para el formulario
        cursor.execute("""
            SELECT 
                u.id_usuario,
                u.nombre,
                u.ap_paterno,
                u.ap_materno,
                u.correo,
                u.telefono,
                r.piso,
                r.nro_departamento
            FROM usuario u
            JOIN residente r ON u.id_usuario = r.id_usuario
            WHERE u.id_rol = 3
            ORDER BY u.nombre, u.ap_paterno
        """)
        residentes = cursor.fetchall()
        
        residentes_list = []
        for res in residentes:
            residentes_list.append({
                'id_usuario': res[0],
                'nombre_completo': f"{res[1]} {res[2]} {res[3] or ''}",
                'correo': res[4],
                'telefono': res[5],
                'departamento': f"Piso {res[6]} - Depto {res[7]}"
            })
        
        cursor.close()
        conn.close()
        
        return render_template("administrador/reservas.html", 
                             reservas=reservas_list,
                             total_reservas=stats[0],
                             pendientes=stats[1],
                             pagados=stats[2],
                             expirados=stats[3],
                             hoy=stats[4],
                             residentes_count=stats[5],
                             externos_count=stats[6],
                             areas=areas_list,
                             residentes=residentes_list)
        
    except Exception as e:
        print(f"Error obteniendo reservas: {str(e)}")
        flash("Error al cargar las reservas.", "danger")
        return render_template("administrador/reservas.html", 
                             reservas=[], 
                             total_reservas=0,
                             pendientes=0,
                             pagados=0,
                             expirados=0,
                             hoy=0,
                             residentes_count=0,
                             externos_count=0,
                             areas=[],
                             residentes=[])


@admin_bp.route("/api/reservas/crear", methods=["POST"])
@login_required
def crear_reserva():
    if current_user.id_rol != 1:
        return jsonify({"error": "No autorizado"}), 403
    
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        required_fields = ['id_area', 'fecha_reserva', 'horas', 'monto', 'tipo_solicitante']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Campo requerido: {field}"}), 400
        
        # Validaciones específicas por tipo de solicitante
        if data['tipo_solicitante'] == 'residente' and not data.get('id_residente'):
            return jsonify({"error": "ID de residente requerido para residentes"}), 400
        
        if data['tipo_solicitante'] == 'externo' and not data.get('info_externo'):
            return jsonify({"error": "Información del externo requerida"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar disponibilidad del área
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pagos_qr 
            WHERE id_concepto = %s 
            AND fecha_reserva = %s 
            AND estado IN ('pendiente', 'pagado')
        """, (data['id_area'], data['fecha_reserva']))
        
        reservas_existentes = cursor.fetchone()[0]
        
        if reservas_existentes > 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "El área ya está reservada para esta fecha"}), 400
        
        # Preparar datos para la inserción
        id_residente = data.get('id_residente') if data['tipo_solicitante'] == 'residente' else None
        
        # Para externos, almacenar información en observaciones
        observaciones = data.get('observaciones', '')
        if data['tipo_solicitante'] == 'externo' and data.get('info_externo'):
            info_externo = data['info_externo']
            observaciones += f"\n[EXTERNO] Nombre: {info_externo.get('nombre', '')}, " \
                           f"CI: {info_externo.get('ci', '')}, " \
                           f"Teléfono: {info_externo.get('telefono', '')}, " \
                           f"Correo: {info_externo.get('correo', '')}"
        
        # Crear nueva reserva
        cursor.execute("""
            INSERT INTO pagos_qr (
                id_residente, 
                id_concepto, 
                monto, 
                descripcion, 
                estado, 
                fecha_generacion, 
                fecha_expiracion,
                fecha_reserva,
                horas,
                observaciones
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_pago
        """, (
            id_residente,
            data['id_area'],
            data['monto'],
            data.get('descripcion', 'Reserva de área común'),
            'pendiente',
            datetime.now(),
            datetime.now() + timedelta(hours=24),
            data['fecha_reserva'],
            data['horas'],
            observaciones.strip()
        ))
        
        nuevo_id = cursor.fetchone()[0]
        
        # Registrar movimiento
        cursor.execute("""
            INSERT INTO movimientos (
                tipo, monto, categoria, descripcion, fecha
            ) VALUES (%s, %s, %s, %s, %s)
        """, (
            'ingreso',
            data['monto'],
            'reservas',
            f"Reserva #{nuevo_id} - {data.get('descripcion', 'Área común')}",
            datetime.now().date()
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "mensaje": "Reserva creada exitosamente",
            "id_reserva": nuevo_id
        })
        
    except Exception as e:
        print(f"Error creando reserva: {str(e)}")
        return jsonify({"error": "Error al crear la reserva"}), 500


@admin_bp.route("/api/reservas/estadisticas")
@login_required
def estadisticas_reservas():
    if current_user.id_rol != 1:
        return jsonify({"error": "No autorizado"}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Estadísticas generales
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN estado = 'pendiente' THEN 1 END) as pendientes,
                COUNT(CASE WHEN estado = 'pagado' THEN 1 END) as pagados,
                COUNT(CASE WHEN estado = 'expirado' THEN 1 END) as expirados,
                COUNT(CASE WHEN fecha_reserva = CURRENT_DATE THEN 1 END) as hoy,
                COALESCE(SUM(CASE WHEN estado = 'pagado' THEN monto ELSE 0 END), 0) as ingresos_totales,
                -- Estadísticas por tipo de solicitante
                COUNT(CASE WHEN id_residente IS NOT NULL THEN 1 END) as residentes,
                COUNT(CASE WHEN id_residente IS NULL THEN 1 END) as externos,
                -- Ingresos del mes en reservas
                COALESCE(SUM(CASE WHEN estado = 'pagado' AND EXTRACT(MONTH FROM fecha_pago) = EXTRACT(MONTH FROM CURRENT_DATE) THEN monto ELSE 0 END), 0) as ingresos_mes_reservas
            FROM pagos_qr
        """)
        stats = cursor.fetchone()
        
        # Total de comprobantes generados por reservas
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pago 
            WHERE descripcion LIKE 'Pago reserva%'
        """)
        comprobantes_reservas = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "total": stats[0],
            "pendientes": stats[1],
            "pagados": stats[2],
            "expirados": stats[3],
            "hoy": stats[4],
            "ingresos_totales": float(stats[5]),
            "residentes": stats[6],
            "externos": stats[7],
            "ingresos_mes": float(stats[8]),
            "comprobantes_generados": comprobantes_reservas
        })
        
    except Exception as e:
        print(f"Error obteniendo estadísticas: {str(e)}")
        return jsonify({"error": "Error al obtener estadísticas"}), 500
    
@admin_bp.route("/api/reservas/<int:id_reserva>/estado", methods=["PUT"])
@login_required
def actualizar_estado_reserva(id_reserva):
    if current_user.id_rol != 1:
        return jsonify({"error": "No autorizado"}), 403
    
    conn = None
    cursor = None
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        print(f"DEBUG: Actualizando reserva {id_reserva} a estado {nuevo_estado}")
        
        if nuevo_estado not in ['pagado', 'expirado', 'cancelado']:
            return jsonify({"error": "Estado no válido"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Primero obtener información de la reserva
        cursor.execute("""
            SELECT pq.id_pago, pq.monto, pq.id_residente, pq.descripcion, 
                   u.nombre, u.ap_paterno, u.ap_materno, u.id_usuario,
                   a.nombre as area_nombre
            FROM pagos_qr pq
            LEFT JOIN usuario u ON pq.id_residente = u.id_usuario
            JOIN area a ON pq.id_concepto = a.id_area
            WHERE pq.id_pago = %s
        """, (id_reserva,))
        
        reserva_info = cursor.fetchone()
        
        if not reserva_info:
            cursor.close()
            conn.close()
            return jsonify({"error": "Reserva no encontrada"}), 404
        
        # Actualizar estado de la reserva en pagos_qr
        cursor.execute("""
            UPDATE pagos_qr 
            SET estado = %s,
                fecha_pago = CASE WHEN %s = 'pagado' THEN CURRENT_TIMESTAMP ELSE fecha_pago END
            WHERE id_pago = %s
            RETURNING id_pago
        """, (nuevo_estado, nuevo_estado, id_reserva))
        
        if cursor.fetchone() is None:
            cursor.close()
            conn.close()
            return jsonify({"error": "Error al actualizar la reserva"}), 500
        
        # Si el estado es "pagado", crear registro en la tabla pago
        if nuevo_estado == 'pagado':
            # Generar número de transacción
            nro_trans = f"RES{id_reserva:06d}{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Obtener el ID del usuario administrador actual
            id_admin = current_user.id  # Usamos id (no id_usuario)
            
            # Para externos, el id_usuario puede ser NULL, usamos el usuario admin actual
            id_usuario_pago = reserva_info[7] if reserva_info[7] else id_admin
            pagado_por = id_admin
            
            print(f"DEBUG: id_usuario_pago: {id_usuario_pago}, pagado_por: {pagado_por}")
            
            # INSERT CORREGIDO - usando solo columnas que existen en la tabla pago
            cursor.execute("""
                INSERT INTO pago (
                    monto, metodo, estado, fecha_pago, nro_trans,
                    id_usuario, pagado_por
                    -- NOTA: No incluimos 'descripcion' porque no existe en la tabla
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id_pago
            """, (
                float(reserva_info[1]),  # monto
                'transferencia',  # método por defecto para reservas
                'completado',
                datetime.now().date(),
                nro_trans,
                id_usuario_pago,
                pagado_por
                # descripcion se eliminó porque no existe en la tabla
            ))
            
            nuevo_pago_id = cursor.fetchone()[0]
            
            # Actualizar pagos_qr con la referencia al pago
            cursor.execute("""
                UPDATE pagos_qr 
                SET comprobante_url = %s
                WHERE id_pago = %s
            """, (f"/admin/comprobante/{nuevo_pago_id}", id_reserva))
            
            print(f"DEBUG: Comprobante generado con ID: {nuevo_pago_id}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        mensaje = f"Reserva {nuevo_estado} exitosamente"
        if nuevo_estado == 'pagado':
            mensaje += " y comprobante generado"
        
        return jsonify({
            "success": True,
            "mensaje": mensaje,
            "id_pago_generado": nuevo_pago_id if nuevo_estado == 'pagado' else None
        })
        
    except Exception as e:
        print(f"Error actualizando reserva: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
        return jsonify({"error": "Error al actualizar la reserva"}), 500



@admin_bp.route("/tickets")
@login_required
def tickets():
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener parámetros de filtro
        estado_filter = request.args.get('estado', 'all')
        prioridad_filter = request.args.get('prioridad', 'all')
        
        # Construir consulta base
        query = """
            SELECT 
                t.id_ticket,
                t.descripcion,
                t.prioridad,
                t.estado,
                t.fecha_emision,
                t.fecha_finalizacion,
                d.piso,
                d.nro as nro_departamento,
                e.id_empleado,
                u.nombre as empleado_nombre,
                u.ap_paterno as empleado_ap_paterno,
                a.nombre as area_nombre,
                res_u.nombre as residente_nombre,
                res_u.ap_paterno as residente_ap_paterno
            FROM ticket t
            LEFT JOIN departamento d ON t.id_departamento = d.id_departamento
            LEFT JOIN empleado e ON t.id_empleado = e.id_empleado
            LEFT JOIN usuario u ON e.id_usuario = u.id_usuario
            LEFT JOIN area a ON t.id_area = a.id_area
            LEFT JOIN residente r ON t.id_departamento = d.id_departamento
            LEFT JOIN usuario res_u ON r.id_usuario = res_u.id_usuario
        """
        
        params = []
        where_clauses = []
        
        # Aplicar filtros
        if estado_filter != 'all':
            where_clauses.append("t.estado = %s")
            params.append(estado_filter)
        
        if prioridad_filter != 'all':
            where_clauses.append("t.prioridad = %s")
            params.append(prioridad_filter)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += """
            ORDER BY 
                CASE 
                    WHEN t.estado = 'pendiente' THEN 1
                    WHEN t.estado = 'en_proceso' THEN 2
                    WHEN t.estado = 'resuelto' THEN 3
                    ELSE 4
                END,
                CASE 
                    WHEN t.prioridad = 'alta' THEN 1
                    WHEN t.prioridad = 'media' THEN 2
                    WHEN t.prioridad = 'baja' THEN 3
                END,
                t.fecha_emision DESC
        """
        
        cursor.execute(query, params)
        tickets = cursor.fetchall()
        
        # Convertir a lista de diccionarios
        tickets_list = []
        for ticket in tickets:
            tickets_list.append({
                'id_ticket': ticket[0],
                'descripcion': ticket[1],
                'prioridad': ticket[2],
                'estado': ticket[3],
                'fecha_emision': ticket[4],
                'fecha_finalizacion': ticket[5],
                'piso': ticket[6],
                'nro_departamento': ticket[7],
                'id_empleado': ticket[8],
                'empleado_nombre': f"{ticket[9]} {ticket[10]}" if ticket[9] else "No asignado",
                'area_nombre': ticket[11],
                'residente_nombre': f"{ticket[12]} {ticket[13]}" if ticket[12] else "N/A"
            })
        
        # Obtener estadísticas
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN estado = 'pendiente' THEN 1 END) as pendientes,
                COUNT(CASE WHEN estado = 'en_proceso' THEN 1 END) as en_proceso,
                COUNT(CASE WHEN estado = 'resuelto' THEN 1 END) as resueltos
            FROM ticket
        """)
        stats = cursor.fetchone()
        
        # Obtener empleados para asignación
        cursor.execute("""
            SELECT 
                e.id_empleado,
                u.nombre,
                u.ap_paterno,
                u.ap_materno,
                e.puesto,
                e.turno
            FROM empleado e
            JOIN usuario u ON e.id_usuario = u.id_usuario
            WHERE e.estado = 'activo'
            ORDER BY e.puesto, u.nombre
        """)
        empleados = cursor.fetchall()
        
        empleados_list = []
        for emp in empleados:
            empleados_list.append({
                'id_empleado': emp[0],
                'nombre_completo': f"{emp[1]} {emp[2]} {emp[3]}",
                'puesto': emp[4],
                'turno': emp[5]
            })
        
        cursor.close()
        conn.close()
        
        return render_template("administrador/tickets.html", 
                             tickets=tickets_list,
                             total_tickets=stats[0],
                             pendientes=stats[1],
                             en_proceso=stats[2],
                             resueltos=stats[3],
                             empleados=empleados_list,
                             hoy=datetime.now().strftime('%Y-%m-%d'))
        
    except Exception as e:
        print(f"Error obteniendo tickets: {str(e)}")
        flash("Error al cargar los tickets.", "danger")
        return render_template("administrador/tickets.html", 
                             tickets=[], 
                             total_tickets=0,
                             pendientes=0,
                             en_proceso=0,
                             resueltos=0,
                             empleados=[],
                             hoy=datetime.now().strftime('%Y-%m-%d'))

@admin_bp.route("/ticket/<int:id_ticket>")
@login_required
def obtener_ticket(id_ticket):
    if current_user.id_rol != 1:
        return jsonify({'error': 'Acceso no autorizado'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener información completa del ticket
        cursor.execute("""
            SELECT 
                t.id_ticket,
                t.descripcion,
                t.prioridad,
                t.estado,
                t.fecha_emision,
                t.fecha_finalizacion,
                d.piso,
                d.nro as nro_departamento,
                e.id_empleado,
                u.nombre as empleado_nombre,
                u.ap_paterno as empleado_ap_paterno,
                u.ap_materno as empleado_ap_materno,
                a.nombre as area_nombre,
                res_u.nombre as residente_nombre,
                res_u.ap_paterno as residente_ap_paterno,
                res_u.correo as residente_correo,
                res_u.telefono as residente_telefono
            FROM ticket t
            LEFT JOIN departamento d ON t.id_departamento = d.id_departamento
            LEFT JOIN empleado e ON t.id_empleado = e.id_empleado
            LEFT JOIN usuario u ON e.id_usuario = u.id_usuario
            LEFT JOIN area a ON t.id_area = a.id_area
            LEFT JOIN residente r ON t.id_departamento = d.id_departamento
            LEFT JOIN usuario res_u ON r.id_usuario = res_u.id_usuario
            WHERE t.id_ticket = %s
        """, (id_ticket,))
        
        ticket = cursor.fetchone()
        
        if not ticket:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        # Obtener comentarios del ticket
        cursor.execute("""
            SELECT 
                ct.id_comentario,
                ct.mensaje,
                ct.fecha_creacion,
                ct.es_interno,
                u.nombre,
                u.ap_paterno,
                u.ap_materno,
                r.nombre as rol_nombre
            FROM comentario_ticket ct
            JOIN usuario u ON ct.id_usuario = u.id_usuario
            JOIN rol r ON u.id_rol = r.id_rol
            WHERE ct.id_ticket = %s
            ORDER BY ct.fecha_creacion ASC
        """, (id_ticket,))
        
        comentarios = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Formatear respuesta
        ticket_data = {
            'id_ticket': ticket[0],
            'descripcion': ticket[1],
            'prioridad': ticket[2],
            'estado': ticket[3],
            'fecha_emision': ticket[4].strftime('%d/%m/%Y %H:%M') if ticket[4] else None,
            'fecha_finalizacion': ticket[5].strftime('%d/%m/%Y %H:%M') if ticket[5] else None,
            'piso': ticket[6],
            'nro_departamento': ticket[7],
            'id_empleado': ticket[8],
            'empleado_asignado': f"{ticket[9]} {ticket[10]} {ticket[11]}" if ticket[9] else "No asignado",
            'area_nombre': ticket[12],
            'residente_nombre': f"{ticket[13]} {ticket[14]}" if ticket[13] else "N/A",
            'residente_contacto': f"{ticket[15]} | {ticket[16]}" if ticket[15] else "N/A",
            'comentarios': []
        }
        
        for comentario in comentarios:
            ticket_data['comentarios'].append({
                'id_comentario': comentario[0],
                'mensaje': comentario[1],
                'fecha_creacion': comentario[2].strftime('%d/%m/%Y %H:%M'),
                'es_interno': comentario[3],
                'usuario_nombre': f"{comentario[4]} {comentario[5]} {comentario[6]}",
                'rol_nombre': comentario[7]
            })
        
        return jsonify(ticket_data)
        
    except Exception as e:
        print(f"Error obteniendo ticket: {str(e)}")
        return jsonify({'error': 'Error al obtener el ticket'}), 500

@admin_bp.route("/tickets/asignar", methods=["POST"])
@login_required
def asignar_ticket():
    if current_user.id_rol != 1:
        return jsonify({'error': 'Acceso no autorizado'}), 403
    
    try:
        data = request.get_json()
        id_ticket = data.get('id_ticket')
        id_empleado = data.get('id_empleado')
        fecha_estimada = data.get('fecha_estimada')
        instrucciones = data.get('instrucciones')
        
        if not id_ticket or not id_empleado:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el ticket existe y está pendiente
        cursor.execute("""
            SELECT estado FROM ticket WHERE id_ticket = %s
        """, (id_ticket,))
        
        ticket = cursor.fetchone()
        if not ticket:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        if ticket[0] != 'pendiente':
            return jsonify({'error': 'Solo se pueden asignar tickets pendientes'}), 400
        
        # Verificar que el empleado existe y está activo
        cursor.execute("""
            SELECT estado FROM empleado WHERE id_empleado = %s
        """, (id_empleado,))
        
        empleado = cursor.fetchone()
        if not empleado or empleado[0] != 'activo':
            return jsonify({'error': 'Empleado no disponible'}), 400
        
        # Actualizar ticket con empleado asignado y cambiar estado
        cursor.execute("""
            UPDATE ticket 
            SET id_empleado = %s, estado = 'en_proceso'
            WHERE id_ticket = %s
        """, (id_empleado, id_ticket))
        
        # Agregar comentario interno con las instrucciones si existen
        if instrucciones:
            cursor.execute("""
                INSERT INTO comentario_ticket 
                (id_ticket, id_usuario, mensaje, fecha_creacion, es_interno)
                VALUES (%s, %s, %s, NOW(), true)
            """, (id_ticket, current_user.id_usuario, f"Instrucciones del administrador: {instrucciones}"))
        
        # Registrar en mantenimiento
        cursor.execute("""
            INSERT INTO mantenimiento 
            (descripcion, fecha_programada, estado, id_departamento, id_empleado, id_ticket)
            SELECT 
                t.descripcion,
                %s as fecha_programada,
                'programado' as estado,
                t.id_departamento,
                %s as id_empleado,
                t.id_ticket
            FROM ticket t
            WHERE t.id_ticket = %s
        """, (fecha_estimada, id_empleado, id_ticket))
        
        conn.commit()
        
        # Obtener información para la respuesta
        cursor.execute("""
            SELECT 
                u.nombre, u.ap_paterno, u.ap_materno, e.puesto
            FROM empleado e
            JOIN usuario u ON e.id_usuario = u.id_usuario
            WHERE e.id_empleado = %s
        """, (id_empleado,))
        
        empleado_info = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        empleado_nombre = f"{empleado_info[0]} {empleado_info[1]} {empleado_info[2]}"
        
        return jsonify({
            'success': True, 
            'message': f'Ticket asignado a {empleado_nombre} ({empleado_info[3]})',
            'empleado_nombre': empleado_nombre,
            'puesto': empleado_info[3]
        })
        
    except Exception as e:
        print(f"Error asignando ticket: {str(e)}")
        return jsonify({'error': 'Error al asignar el ticket'}), 500

@admin_bp.route("/empleados/disponibles")
@login_required
def empleados_disponibles():
    if current_user.id_rol != 1:
        return jsonify({'error': 'Acceso no autorizado'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener empleados activos con su información y carga de trabajo
        cursor.execute("""
            SELECT 
                e.id_empleado,
                u.nombre,
                u.ap_paterno,
                u.ap_materno,
                e.puesto,
                e.turno,
                COUNT(t.id_ticket) as tickets_activos
            FROM empleado e
            JOIN usuario u ON e.id_usuario = u.id_usuario
            LEFT JOIN ticket t ON e.id_empleado = t.id_empleado AND t.estado = 'en_proceso'
            WHERE e.estado = 'activo'
            GROUP BY e.id_empleado, u.nombre, u.ap_paterno, u.ap_materno, e.puesto, e.turno
            ORDER BY e.puesto, u.nombre
        """)
        
        empleados = cursor.fetchall()
        
        empleados_list = []
        for emp in empleados:
            # Calcular disponibilidad
            if emp[6] < 3:
                disponibilidad = 'Alta'
            elif emp[6] < 5:
                disponibilidad = 'Media'
            else:
                disponibilidad = 'Baja'
                
            empleados_list.append({
                'id_empleado': emp[0],
                'nombre_completo': f"{emp[1]} {emp[2]} {emp[3]}",
                'puesto': emp[4],
                'turno': emp[5],
                'tickets_activos': emp[6],
                'disponibilidad': disponibilidad
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(empleados_list)
        
    except Exception as e:
        print(f"Error obteniendo empleados: {str(e)}")
        return jsonify({'error': 'Error al obtener empleados'}), 500

@admin_bp.route("/ticket/<int:id_ticket>/comentario", methods=["POST"])
@login_required
def agregar_comentario_ticket(id_ticket):
    if current_user.id_rol != 1:
        return jsonify({'error': 'Acceso no autorizado'}), 403
    
    try:
        data = request.get_json()
        mensaje = data.get('mensaje')
        es_interno = data.get('es_interno', False)
        
        if not mensaje:
            return jsonify({'error': 'El mensaje no puede estar vacío'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insertar comentario
        cursor.execute("""
            INSERT INTO comentario_ticket 
            (id_ticket, id_usuario, mensaje, fecha_creacion, es_interno)
            VALUES (%s, %s, %s, NOW(), %s)
        """, (id_ticket, current_user.id_usuario, mensaje, es_interno))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Comentario agregado correctamente'})
        
    except Exception as e:
        print(f"Error agregando comentario: {str(e)}")
        return jsonify({'error': 'Error al agregar comentario'}), 500

@admin_bp.route("/ticket/<int:id_ticket>/cambiar-estado", methods=["POST"])
@login_required
def cambiar_estado_ticket(id_ticket):
    if current_user.id_rol != 1:
        return jsonify({'error': 'Acceso no autorizado'}), 403
    
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'error': 'Estado no especificado'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Actualizar estado del ticket
        if nuevo_estado == 'resuelto':
            cursor.execute("""
                UPDATE ticket 
                SET estado = %s, fecha_finalizacion = NOW()
                WHERE id_ticket = %s
            """, (nuevo_estado, id_ticket))
        else:
            cursor.execute("""
                UPDATE ticket 
                SET estado = %s
                WHERE id_ticket = %s
            """, (nuevo_estado, id_ticket))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Estado actualizado a {nuevo_estado}'})
        
    except Exception as e:
        print(f"Error cambiando estado del ticket: {str(e)}")
        return jsonify({'error': 'Error al cambiar estado del ticket'}), 500


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
    
@admin_bp.route("/eliminar_usuario/<int:id_usuario>", methods=["POST"])
@login_required
def eliminar_usuario(id_usuario):
    if current_user.id_rol != 1:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que no sea el mismo usuario
        if id_usuario == current_user.id_usuario:
            flash("No puedes eliminar tu propio usuario.", "danger")
            return redirect(url_for("admin.usuarios"))
        
        # Eliminar registros relacionados primero (dependiendo de tu estructura de BD)
        # Eliminar de tablas hijas
        cursor.execute("DELETE FROM residente WHERE id_usuario = %s", (id_usuario,))
        cursor.execute("DELETE FROM empleado WHERE id_usuario = %s", (id_usuario,))
        cursor.execute("DELETE FROM administrador WHERE id_usuario = %s", (id_usuario,))
        
        # Finalmente eliminar el usuario
        cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (id_usuario,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Usuario eliminado correctamente.", "success")
        
    except Exception as e:
        conn.rollback()
        print(f"Error eliminando usuario: {str(e)}")
        flash("Error al eliminar el usuario.", "danger")
    
    return redirect(url_for("admin.usuarios"))

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
