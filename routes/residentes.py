from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from db import get_db_connection
import json
import logging

logger = logging.getLogger(__name__)

residentes_bp = Blueprint('residentes', __name__)

def debug_current_user():
    """Debug function to see what's in current_user"""
    print("🔍 DEBUG current_user:")
    print(f"  get_id(): {current_user.get_id()}")
    print(f"  Type: {type(current_user)}")
    
    # Try to access common attributes
    try:
        print(f"  id_usuario: {current_user.id_usuario}")
    except:
        print("  ❌ id_usuario not found")
    
    try:
        print(f"  nombre: {current_user.nombre}")
    except:
        print("  ❌ nombre not found")
    
    try:
        print(f"  correo: {current_user.correo}")
    except:
        print("  ❌ correo not found")
    
    try:
        print(f"  id_rol: {current_user.id_rol}")
    except:
        print("  ❌ id_rol not found")

def get_user_id():
    """Safe way to get user ID"""
    try:
        # Primero intentar con el atributo directo
        return current_user.id_usuario
    except AttributeError:
        # Si falla, usar get_id()
        return int(current_user.get_id())

# Helper functions CORREGIDAS
def get_rol_usuario():
    """Obtiene el rol del usuario actual - CORREGIDO"""
    try:
        user_id = get_user_id()
        
        conn = get_db_connection()
        if conn is None:
            return None
            
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.nombre 
            FROM usuario u
            JOIN rol r ON u.id_rol = r.id_rol
            WHERE u.id_usuario = %s
        """, (user_id,))
        rol = cursor.fetchone()
        cursor.close()
        conn.close()
        return rol[0] if rol else None
    except Exception as e:
        logger.error(f"Error obteniendo rol del usuario: {e}")
        return None

def get_residente_data():
    """Obtiene los datos del residente actual - CON MANEJO DE ERRORES"""
    try:
        user_id = get_user_id()
        print(f"🔍 Buscando residente con user_id: {user_id}")
        
        conn = get_db_connection()
        if conn is None:
            return None
            
        cursor = conn.cursor()
        
        # Usar LEFT JOIN para que no falle si no existe el departamento
        cursor.execute("""
            SELECT 
                r.id_residente,      
                r.id_usuario,        
                r.piso,              
                r.nro_departamento,  
                r.fecha_ingreso,     
                r.fecha_salida,      
                d.piso,              
                d.nro,               
                d.id_departamento    
            FROM residente r
            LEFT JOIN departamento d ON r.piso::varchar = d.piso AND r.nro_departamento = d.nro
            WHERE r.id_usuario = %s
        """, (user_id,))
        
        residente = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if residente:
            print(f"✅ Datos del residente obtenidos:")
            print(f"   - ID Residente: {residente[0]}")
            print(f"   - Piso: {residente[2]}")
            print(f"   - Departamento: {residente[3]}")
            print(f"   - ID Departamento: {residente[8]}")
            
            # Si no hay departamento (id_departamento es NULL), usar un valor por defecto
            if not residente[8]:
                print("⚠️  No se encontró departamento asociado, usando valor temporal")
                # Podemos usar el ID del residente como temporal o crear uno
                residente_list = list(residente)
                residente_list[8] = residente[0]  # Usar id_residente como id_departamento temporal
                residente = tuple(residente_list)
        
        return residente
        
    except Exception as e:
        logger.error(f"Error obteniendo datos del residente: {e}")
        return None
def get_departamento_usuario():
    """Obtiene el departamento del usuario actual - CORREGIDO"""
    try:
        user_id = get_user_id()
        
        conn = get_db_connection()
        if conn is None:
            return None
            
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.id_departamento, d.piso, d.nro
            FROM residente r
            JOIN departamento d ON r.piso = d.piso::integer AND r.nro_departamento = d.nro
            WHERE r.id_usuario = %s
        """, (user_id,))
        
        departamento = cursor.fetchone()
        cursor.close()
        conn.close()
        return departamento
        
    except Exception as e:
        logger.error(f"Error obteniendo departamento: {e}")
        return None

def get_consumos_mes(departamento_id, mes, año):
    """Obtiene consumos del mes actual - CORREGIDO"""
    try:
        conn = get_db_connection()
        if conn is None:
            return {'luz': 0, 'agua': 0, 'gas': 0}
            
        cursor = conn.cursor()
        
        # Consulta corregida según tu estructura de BD
        cursor.execute("""
            SELECT 
                COALESCE((SELECT SUM(cantidad_registrada) 
                         FROM consumo_luz 
                         WHERE id_departamento = %s
                         AND EXTRACT(MONTH FROM fecha_registro) = %s
                         AND EXTRACT(YEAR FROM fecha_registro) = %s), 0) as luz,
                COALESCE((SELECT SUM(cantidad_registrada) 
                         FROM consumo_agua 
                         WHERE id_departamento = %s
                         AND EXTRACT(MONTH FROM fecha_registro) = %s
                         AND EXTRACT(YEAR FROM fecha_registro) = %s), 0) as agua,
                COALESCE((SELECT SUM(cantidad_registrada) 
                         FROM consumo_gas 
                         WHERE id_departamento = %s
                         AND EXTRACT(MONTH FROM fecha_registro) = %s
                         AND EXTRACT(YEAR FROM fecha_registro) = %s), 0) as gas
        """, (departamento_id, mes, año, 
              departamento_id, mes, año, 
              departamento_id, mes, año))
        
        consumos = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return {
            'luz': float(consumos[0]) if consumos and consumos[0] else 0,
            'agua': float(consumos[1]) if consumos and consumos[1] else 0,
            'gas': float(consumos[2]) if consumos and consumos[2] else 0
        }
    except Exception as e:
        logger.error(f"Error obteniendo consumos: {e}")
        return {'luz': 0, 'agua': 0, 'gas': 0}

@residentes_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        # DEBUG: Ver qué tiene current_user
        debug_current_user()
        
        # Primero verificar que el usuario sea residente - CORREGIDO
        user_id = get_user_id()
        
        # Obtener el rol del usuario de forma segura
        conn = get_db_connection()
        if conn is None:
            flash('Error de conexión a la base de datos', 'error')
            return redirect(url_for('auth.login'))
            
        cursor = conn.cursor()
        cursor.execute("SELECT id_rol FROM usuario WHERE id_usuario = %s", (user_id,))
        user_rol = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user_rol or user_rol[0] != 3:
            flash('Acceso no autorizado para este rol', 'error')
            return redirect(url_for('auth.login'))
        
        print(f"🔍 DEBUG - Usuario ID {user_id} accediendo al dashboard de residentes")
        
        # Para residentes
        residente = get_residente_data()
        if not residente:
            print("❌ No se encontraron datos del residente")
            flash('No se encontraron datos del residente. Contacte al administrador.', 'error')
            return redirect(url_for('auth.logout'))
        
        print(f"✅ Datos del residente obtenidos: {len(residente)} campos")
        
        # DEBUG: Mostrar estructura de datos del residente
        print("🔍 Estructura de datos del residente:")
        for i, valor in enumerate(residente):
            print(f"  residente[{i}] = {valor}")
        
        # Obtener el id_departamento CORRECTAMENTE
        id_departamento = residente[8]  # Último campo según tu JOIN
        
        # Datos básicos para el dashboard
        ahora = datetime.now()
        
        # Obtener consumos del mes actual
        consumos_actual = get_consumos_mes(id_departamento, ahora.month, ahora.year)
        print(f"✅ Consumos obtenidos: {consumos_actual}")
        
        # Estado de pagos
        conn = get_db_connection()
        if conn is None:
            flash('Error de conexión a la base de datos', 'error')
            return render_template('residente/dashboard.html')
            
        cursor = conn.cursor()
        
        # Estado de pagos
        estado_pagos = None
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as pendientes,
                    COALESCE(SUM(f.monto_total), 0) as total_pendiente,
                    MIN(f.fecha_vencimiento) as proximo_vencimiento
                FROM factura f
                WHERE f.id_usuario = %s 
                AND f.estado_factura = 'pendiente'
                AND f.fecha_vencimiento >= CURRENT_DATE
            """, (user_id,))
            estado_pagos = cursor.fetchone()
            print(f"✅ Estado de pagos: {estado_pagos}")
        except Exception as e:
            print(f"❌ Error en consulta de pagos: {e}")
            estado_pagos = (0, 0, None)
        
        # Solicitudes activas
        solicitudes_activas = None
        try:
            cursor.execute("""
                SELECT COUNT(*) as activas,
                       SUM(CASE WHEN prioridad = 'alta' OR prioridad = 'urgente' THEN 1 ELSE 0 END) as urgentes
                FROM ticket 
                WHERE id_usuario = %s 
                AND estado IN ('pendiente', 'en_proceso')
            """, (user_id,))
            solicitudes_activas = cursor.fetchone()
            print(f"✅ Solicitudes activas: {solicitudes_activas}")
        except Exception as e:
            print(f"❌ Error en consulta de solicitudes: {e}")
            solicitudes_activas = (0, 0)
        
        # Actividades recientes
        actividades_recientes = []
        try:
            cursor.execute("""
                (SELECT 'pago' as tipo, fecha_pago as fecha, 
                        'Pago realizado' as descripcion, 'fa-money-bill-wave' as icono
                 FROM pago 
                 WHERE id_usuario = %s 
                 AND fecha_pago >= CURRENT_DATE - INTERVAL '7 days'
                 LIMIT 3)
                UNION
                (SELECT 'ticket' as tipo, fecha_emision as fecha,
                        'Solicitud creada' as descripcion, 'fa-ticket-alt' as icono
                 FROM ticket 
                 WHERE id_usuario = %s 
                 AND fecha_emision >= CURRENT_DATE - INTERVAL '7 days'
                 LIMIT 3)
                ORDER BY fecha DESC
                LIMIT 5
            """, (user_id, user_id))
            
            actividades = cursor.fetchall()
            print(f"✅ Actividades encontradas: {len(actividades)}")
            
            for act in actividades:
                actividades_recientes.append({
                    'icono': act[3] if len(act) > 3 else 'fa-circle',
                    'descripcion': act[2] if len(act) > 2 else 'Actividad',
                    'fecha': act[1].strftime('%d/%m/%Y') if act[1] else 'N/A'
                })
        except Exception as e:
            print(f"❌ Error en consulta de actividades: {e}")
            # Actividades por defecto si hay error
            actividades_recientes = [{
                'icono': 'fa-info-circle',
                'descripcion': 'Bienvenido al sistema de residentes',
                'fecha': ahora.strftime('%d/%m/%Y')
            }]
        
        cursor.close()
        conn.close()
        
        # Obtener nombre del usuario de forma segura
        nombre_usuario = "Residente"
        correo_usuario = "usuario@ejemplo.com"
        try:
            nombre_usuario = current_user.nombre
            correo_usuario = current_user.correo
        except:
            # Si falla, obtener de la base de datos
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT nombre, correo FROM usuario WHERE id_usuario = %s", (user_id,))
                usuario_data = cursor.fetchone()
                cursor.close()
                conn.close()
                if usuario_data:
                    nombre_usuario = usuario_data[0]
                    correo_usuario = usuario_data[1]
        
        # Preparar datos para el template CON ÍNDICES CORRECTOS
        datos_dashboard = {
            'rol_usuario': 'residente',
            'usuario_nombre': nombre_usuario,
            'usuario_correo': correo_usuario,
            'estado_pagos': {
                'estado': 'Al día' if not estado_pagos or estado_pagos[0] == 0 else 'Pendiente',
                'monto_pendiente': float(estado_pagos[1]) if estado_pagos and estado_pagos[1] else 0.0,
                'fecha_vencimiento': estado_pagos[2].strftime('%d/%m/%Y') if estado_pagos and estado_pagos[2] else 'N/A'
            },
            'consumos': consumos_actual,
            'solicitudes_activas': solicitudes_activas[0] if solicitudes_activas else 0,
            'solicitudes_prioridad_alta': solicitudes_activas[1] if solicitudes_activas else 0,
            'actividades_recientes': actividades_recientes,
            'residente_data': {
                'piso': residente[2],  # piso de residente (integer)
                'departamento': residente[3],  # nro_departamento de residente
                'fecha_ingreso': residente[4].strftime('%d/%m/%Y') if residente[4] else 'N/A',
                'id_departamento': id_departamento
            }
        }
        
        print(f"✅ Dashboard cargado exitosamente para {nombre_usuario}")
        print(f"   - Piso: {residente[2]}, Departamento: {residente[3]}")
        print(f"   - ID Departamento: {id_departamento}")
        
        return render_template('residente/dashboard.html', **datos_dashboard)
    
    except Exception as e:
        logger.error(f"Error en dashboard: {e}")
        import traceback
        print(f"📋 Traceback completo: {traceback.format_exc()}")
        flash('Error al cargar el dashboard', 'error')
        
        # Datos mínimos para que el template no falle
        datos_minimos = {
            'rol_usuario': 'residente',
            'usuario_nombre': 'Residente',
            'usuario_correo': 'usuario@ejemplo.com',
            'estado_pagos': {'estado': 'Error', 'monto_pendiente': 0, 'fecha_vencimiento': 'N/A'},
            'consumos': {'luz': 0, 'agua': 0, 'gas': 0},
            'solicitudes_activas': 0,
            'solicitudes_prioridad_alta': 0,
            'actividades_recientes': [{
                'icono': 'fa-exclamation-triangle',
                'descripcion': 'Error al cargar actividades',
                'fecha': datetime.now().strftime('%d/%m/%Y')
            }],
            'residente_data': {
                'piso': 'N/A',
                'departamento': 'N/A', 
                'fecha_ingreso': 'N/A',
                'id_departamento': 0
            }
        }
        return render_template('residente/dashboard.html', **datos_minimos)

@residentes_bp.route('/facturacion')
@login_required
def facturacion():
    try:
        user_id = get_user_id()
        
        conn = get_db_connection()
        if conn is None:
            flash('Error de conexión a la base de datos', 'error')
            return render_template('residente/facturacion.html')
            
        cursor = conn.cursor()
        
        # Resumen de facturación
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN estado_factura = 'pagada' THEN monto_total ELSE 0 END), 0) as pagado,
                COALESCE(SUM(CASE WHEN estado_factura = 'pendiente' THEN monto_total ELSE 0 END), 0) as pendiente,
                COALESCE(SUM(monto_total), 0) as total_facturado
            FROM factura
            WHERE id_usuario = %s
            AND EXTRACT(YEAR FROM fecha_emision) = EXTRACT(YEAR FROM CURRENT_DATE)
        """, (user_id,))
        
        resumen = cursor.fetchone()
        
        # Facturas
        cursor.execute("""
            SELECT f.*, a.periodo_inicio, a.periodo_fin,
                   TO_CHAR(f.fecha_emision, 'Month YYYY') as periodo
            FROM factura f
            LEFT JOIN alquiler a ON f.id_alquiler = a.id_alquiler
            WHERE f.id_usuario = %s
            ORDER BY f.fecha_emision DESC
        """, (user_id,))
        
        facturas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convertir a diccionarios
        facturas_con_consumo = []
        for factura in facturas:
            factura_dict = {
                'id_factura': factura[0],
                'monto_total': float(factura[1]) if factura[1] else 0.0,
                'fecha_emision': factura[2],
                'fecha_vencimiento': factura[3],
                'estado_factura': factura[4],
                'periodo_inicio': factura[5],
                'periodo_fin': factura[6],
                'periodo': factura[7]
            }
            facturas_con_consumo.append(factura_dict)
        
        resumen_dict = {
            'pagado': float(resumen[0]) if resumen and resumen[0] else 0.0,
            'pendiente': float(resumen[1]) if resumen and resumen[1] else 0.0,
            'total_facturado': float(resumen[2]) if resumen and resumen[2] else 0.0
        }
        
        return render_template('residente/facturacion.html',
                            resumen=resumen_dict,
                            facturas=facturas_con_consumo,
                            anos=[2024, 2023],
                            ano_actual=2024,
                            meses=[
                                {'numero': 1, 'nombre': 'Enero'},
                                {'numero': 2, 'nombre': 'Febrero'}
                            ])
    
    except Exception as e:
        logger.error(f"Error en facturacion: {e}")
        flash('Error al cargar la facturación', 'error')
        return render_template('residente/facturacion.html')

@residentes_bp.route('/solicitudes')
@login_required
def solicitudes():
    try:
        user_id = get_user_id()
        
        conn = get_db_connection()
        if conn is None:
            flash('Error de conexión a la base de datos', 'error')
            return render_template('residente/solicitudes.html')
            
        cursor = conn.cursor()
        
        # Estadísticas
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN estado = 'pendiente' THEN 1 ELSE 0 END) as pendientes,
                SUM(CASE WHEN estado = 'en_proceso' THEN 1 ELSE 0 END) as en_proceso,
                SUM(CASE WHEN estado = 'completado' THEN 1 ELSE 0 END) as completados,
                SUM(CASE WHEN prioridad = 'alta' OR prioridad = 'urgente' THEN 1 ELSE 0 END) as urgentes
            FROM ticket
            WHERE id_usuario = %s
        """, (user_id,))
        
        stats = cursor.fetchone()
        
        # Áreas disponibles para tickets
        cursor.execute("""
            SELECT id_area, nombre, descripcion
            FROM area
            WHERE nombre IN ('Departamento', 'Áreas Comunes', 'Electricidad', 'Fontanería', 'Gas')
        """)
        
        areas = cursor.fetchall()
        
        # Solicitudes del usuario
        cursor.execute("""
            SELECT t.*, a.nombre as area,
                   e.nombre || ' ' || e.ap_paterno as empleado_asignado
            FROM ticket t
            LEFT JOIN area a ON t.id_area = a.id_area
            LEFT JOIN empleado emp ON t.id_empleado = emp.id_empleado
            LEFT JOIN usuario e ON emp.id_usuario = e.id_usuario
            WHERE t.id_usuario = %s
            ORDER BY t.fecha_emision DESC
        """, (user_id,))
        
        solicitudes = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convertir a diccionarios
        areas_dict = [{'id_area': a[0], 'nombre': a[1], 'descripcion': a[2]} for a in areas]
        solicitudes_dict = []
        for s in solicitudes:
            solicitudes_dict.append({
                'id_ticket': s[0],
                'descripcion': s[1],
                'prioridad': s[2],
                'fecha_emision': s[3],
                'estado': s[4],
                'area': s[5],
                'empleado_asignado': s[6]
            })
        
        estadisticas = {
            'total': stats[0] if stats else 0,
            'pendientes': stats[1] if stats else 0,
            'en_proceso': stats[2] if stats else 0,
            'completados': stats[3] if stats else 0,
            'urgentes': stats[4] if stats else 0
        }
        
        return render_template('residente/solicitudes.html',
                            rol_usuario='residente',
                            estadisticas=estadisticas,
                            areas=areas_dict,
                            solicitudes=solicitudes_dict)
    
    except Exception as e:
        logger.error(f"Error en solicitudes: {e}")
        flash('Error al cargar las solicitudes', 'error')
        return render_template('residente/solicitudes.html')

@residentes_bp.route('/consumos')
@login_required
def consumos():
    try:
        user_id = get_user_id()
        departamento = get_departamento_usuario()
        
        if not departamento:
            flash('No se encontró departamento asociado', 'error')
            return redirect(url_for('residentes.dashboard'))
        
        # Consumos actuales
        ahora = datetime.now()
        consumos_actual = get_consumos_mes(departamento[0], ahora.month, ahora.year)  # departamento[0] = id_departamento
        
        # Añadir variaciones (datos de ejemplo)
        consumos_actual.update({
            'variacion_luz': -5.2,
            'variacion_agua': 2.1,
            'variacion_gas': -1.8,
            'total_estimado': 285.50
        })
        
        # Recomendaciones de ahorro
        recomendaciones = [
            {
                'tipo': 'luz',
                'icono': 'fa-lightbulb',
                'titulo': 'Usa LED de bajo consumo',
                'descripcion': 'Cambia las bombillas tradicionales por LED para ahorrar hasta 80% de energía.',
                'ahorro': '15-20% mensual'
            },
            {
                'tipo': 'agua',
                'icono': 'fa-shower',
                'titulo': 'Duchas más cortas',
                'descripcion': 'Reduce el tiempo de ducha para ahorrar agua y energía para calentarla.',
                'ahorro': '10-15% mensual'
            },
            {
                'tipo': 'gas',
                'icono': 'fa-thermometer-half',
                'titulo': 'Optimiza la calefacción',
                'descripcion': 'Mantén la temperatura entre 19-21°C y cierra puertas para mejor aislamiento.',
                'ahorro': '20-25% mensual'
            }
        ]
        
        return render_template('residente/consumos.html',
                            rol_usuario='residente',
                            consumos_actual=consumos_actual,
                            recomendaciones=recomendaciones,
                            periodos=[
                                {'value': '2024-02', 'nombre': 'Febrero 2024', 'selected': True},
                                {'value': '2024-01', 'nombre': 'Enero 2024'},
                                {'value': '2023-12', 'nombre': 'Diciembre 2023'}
                            ])
    
    except Exception as e:
        logger.error(f"Error en consumos: {e}")
        flash('Error al cargar los consumos', 'error')
        return render_template('residente/consumos.html')

@residentes_bp.route('/perfil')
@login_required
def perfil():
    try:
        user_id = get_user_id()
        
        conn = get_db_connection()
        if conn is None:
            flash('Error de conexión a la base de datos', 'error')
            return render_template('residente/perfil.html')
            
        cursor = conn.cursor()
        
        # Datos del usuario
        cursor.execute("""
            SELECT u.*, r.nombre as rol_nombre
            FROM usuario u
            JOIN rol r ON u.id_rol = r.id_rol
            WHERE u.id_usuario = %s
        """, (user_id,))
        
        usuario = cursor.fetchone()
        
        # Información específica del residente
        datos_extra = {}
        residente = get_residente_data()
        if residente:
            cursor.execute("""
                SELECT d.*, a.periodo_fin, a.monto as monto_mensual
                FROM departamento d
                LEFT JOIN alquiler a ON d.id_departamento = a.id_departamento
                WHERE d.piso = %s AND d.nro = %s
                ORDER BY a.periodo_inicio DESC
                LIMIT 1
            """, (residente[2], residente[3]))  # residente[2] = piso, residente[3] = nro_departamento
            
            departamento = cursor.fetchone()
            
            datos_extra = {
                'departamento': {
                    'id_departamento': departamento[0] if departamento else 'N/A',
                    'piso': departamento[1] if departamento else 'N/A',
                    'nro': departamento[2] if departamento else 'N/A'
                },
                'contrato': {
                    'fecha_fin': departamento[3] if departamento else 'N/A',
                    'monto_mensual': float(departamento[4]) if departamento and departamento[4] else 0
                }
            }
        
        cursor.close()
        conn.close()
        
        # Configuración (datos de ejemplo)
        config = {
            'notif_pagos': True,
            'notif_solicitudes': True,
            'notif_consumos': False,
            'notif_mantenimientos': True,
            'dos_pasos': False
        }
        
        usuario_dict = {
            'id_usuario': usuario[0],
            'nombre': usuario[1],
            'ap_paterno': usuario[2],
            'ap_materno': usuario[3],
            'correo': usuario[4],
            'telefono': usuario[5],
            'rol_nombre': usuario[8] if len(usuario) > 8 else 'Residente'
        }
        
        return render_template('residente/perfil.html',
                            rol_usuario='residente',
                            usuario=usuario_dict,
                            config=config,
                            sesion={
                                'fecha_inicio': datetime.now().strftime('%d/%m/%Y %H:%M'),
                                'dispositivo': 'Chrome en Windows'
                            },
                            **datos_extra)
    
    except Exception as e:
        logger.error(f"Error en perfil: {e}")
        flash('Error al cargar el perfil', 'error')
        return render_template('residente/perfil.html')

# API Endpoints
@residentes_bp.route('/api/crear_solicitud', methods=['POST'])
@login_required
def crear_solicitud():
    try:
        user_id = get_user_id()
        data = request.get_json()
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor()
        
        # Insertar nueva solicitud
        cursor.execute("""
            INSERT INTO ticket (descripcion, prioridad, fecha_emision, estado, id_usuario, id_area)
            VALUES (%s, %s, NOW(), 'pendiente', %s, %s)
            RETURNING id_ticket
        """, (
            data.get('descripcion'),
            data.get('prioridad', 'media'),
            user_id,
            data.get('id_area')
        ))
        
        ticket_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'ticket_id': ticket_id, 'message': 'Solicitud creada exitosamente'})
    
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error creando solicitud: {e}")
        return jsonify({'success': False, 'message': 'Error al crear la solicitud'}), 500

@residentes_bp.route('/api/realizar_pago', methods=['POST'])
@login_required
def realizar_pago():
    try:
        user_id = get_user_id()
        data = request.get_json()
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor()
        
        # Registrar el pago
        cursor.execute("""
            INSERT INTO pago (monto, metodo, estado, fecha_pago, id_usuario, id_factura, nro_trans)
            VALUES (%s, %s, 'completado', NOW(), %s, %s, %s)
            RETURNING id_pago
        """, (
            data.get('monto'),
            data.get('metodo'),
            user_id,
            data.get('id_factura'),
            f"TRX{datetime.now().strftime('%Y%m%d%H%M%S')}"
        ))
        
        # Actualizar estado de la factura
        cursor.execute("""
            UPDATE factura 
            SET estado_factura = 'pagada' 
            WHERE id_factura = %s
        """, (data.get('id_factura'),))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Pago realizado exitosamente'})
    
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error procesando pago: {e}")
        return jsonify({'success': False, 'message': 'Error al procesar el pago'}), 500

# Error handlers
@residentes_bp.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@residentes_bp.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500