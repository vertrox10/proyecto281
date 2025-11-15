# routes/empleadomovil.py
from flask import Blueprint, jsonify, request
import jwt  # ✅ Usar JWT normal como en auth.py
from db import get_db_connection

empleado_movil_bp = Blueprint('empleado_movil', __name__)

# ✅ MISMA CLAVE SECRETA QUE EN auth.py
JWT_SECRET_KEY = 'tu-clave-secreta-muy-segura-para-movil-2024'

def verificar_token_movil(token):
    """Verificar token JWT (igual que en auth.py)"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# ================================
# DASHBOARD EMPLEADO MÓVIL - CORREGIDO
# ================================
@empleado_movil_bp.route("/empleado/dashboard-data", methods=["GET"])
def api_dashboard_data_movil():
    """API para obtener datos del dashboard del empleado para móvil"""
    try:
        # Obtener token del header Authorization
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False, 
                'message': 'Token de autorización requerido'
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Verificar token usando JWT normal (como en auth.py)
        payload = verificar_token_movil(token)
        if not payload:
            return jsonify({
                'success': False, 
                'message': 'Token inválido o expirado'
            }), 401

        user_id = payload['user_id']
        print(f"📱 [EMPLEADO MOVIL] Dashboard solicitado por usuario: {user_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener el id_empleado
        cursor.execute("SELECT id_empleado FROM empleado WHERE id_usuario = %s", (user_id,))
        empleado_result = cursor.fetchone()
        
        if not empleado_result:
            return jsonify({
                'success': False, 
                'error': 'Empleado no encontrado'
            }), 404
        
        id_empleado = empleado_result[0]

        # Métricas principales del empleado
        cursor.execute("""
            SELECT COUNT(*) FROM mantenimiento 
            WHERE id_empleado = %s AND activo = true
        """, (id_empleado,))
        mantenimientos_activos = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM ticket 
            WHERE id_empleado = %s AND estado IN ('abierto', 'en_progreso')
        """, (user_id,))
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

        # Consumos actuales
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

        # Estado de tickets
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN estado = 'abierto' THEN 1 END) as pendientes,
                COUNT(CASE WHEN estado = 'en_progreso' THEN 1 END) as en_progreso,
                COUNT(CASE WHEN estado = 'cerrado' THEN 1 END) as completados
            FROM ticket 
            WHERE id_empleado = %s
        """, (user_id,))
        estado_tickets = cursor.fetchone()

        cursor.close()
        conn.close()

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

        estado_tickets_data = {
            'pendientes': estado_tickets[0] if estado_tickets else 0,
            'en_progreso': estado_tickets[1] if estado_tickets else 0,
            'completados': estado_tickets[2] if estado_tickets else 0
        }

        return jsonify({
            'success': True,
            'data': {
                'metricas': metricas,
                'estado_tickets': estado_tickets_data,
                'actual': {
                    'agua': consumo_agua,
                    'luz': consumo_luz,
                    'gas': consumo_gas
                }
            }
        })

    except Exception as e:
        print(f"❌ Error en API dashboard móvil: {e}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@empleado_movil_bp.route("/empleado/mantenimientos", methods=["GET"])
def api_mantenimientos_movil():
    """API para obtener mantenimientos asignados al empleado - CORREGIDO"""
    try:
        # Obtener token del header Authorization
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False, 
                'message': 'Token de autorización requerido'
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Verificar token
        payload = verificar_token_movil(token)
        if not payload:
            return jsonify({
                'success': False, 
                'message': 'Token inválido o expirado'
            }), 401

        user_id = payload['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener el id_empleado
        cursor.execute("SELECT id_empleado FROM empleado WHERE id_usuario = %s", (user_id,))
        empleado_result = cursor.fetchone()
        
        if not empleado_result:
            return jsonify({
                'success': False, 
                'error': 'Empleado no encontrado'
            }), 404
        
        id_empleado = empleado_result[0]

        # CONSULTA CORREGIDA - usando las columnas reales
        cursor.execute("""
            SELECT 
                id_mantenimiento, 
                descripcion,
                activo,
                id_empleado
            FROM mantenimiento 
            WHERE id_empleado = %s
            ORDER BY id_mantenimiento DESC
        """, (id_empleado,))
        mantenimientos = cursor.fetchall()

        cursor.close()
        conn.close()

        # Convertir a formato JSON usando la estructura real
        mantenimientos_data = []
        for mnt in mantenimientos:
            # Determinar estado basado en la columna 'activo'
            estado = 'Pendiente' if mnt[2] else 'Completado'
            
            mantenimientos_data.append({
                'id': mnt[0],
                'descripcion': mnt[1],
                'estado': estado,
                'activo': mnt[2],
                'id_empleado': mnt[3],
                'fecha_programada': 'Por programar',  # Valor por defecto ya que no existe la columna
                'area': 'Área Común',  # Valor por defecto
                'ubicacion': 'Edificio Principal'  # Valor por defecto
            })

        return jsonify({
            'success': True,
            'data': mantenimientos_data
        })

    except Exception as e:
        print(f"❌ Error obteniendo mantenimientos móvil: {e}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

# ================================
# HISTORIAL DE PAGOS - CORREGIDO
# ================================
@empleado_movil_bp.route("/empleado/pagos", methods=["GET"])
def api_pagos_movil():
    """API para obtener historial de pagos del empleado"""
    try:
        # Obtener token del header Authorization
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False, 
                'message': 'Token de autorización requerido'
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Verificar token
        payload = verificar_token_movil(token)
        if not payload:
            return jsonify({
                'success': False, 
                'message': 'Token inválido o expirado'
            }), 401

        user_id = payload['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener el id_empleado
        cursor.execute("SELECT id_empleado FROM empleado WHERE id_usuario = %s", (user_id,))
        empleado_result = cursor.fetchone()
        
        if not empleado_result:
            return jsonify({
                'success': False, 
                'error': 'Empleado no encontrado'
            }), 404
        
        id_empleado = empleado_result[0]

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

        cursor.close()
        conn.close()

        # Convertir a formato JSON
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

        return jsonify({
            'success': True,
            'data': {
                'pagos': pagos_data,
                'salario_actual': float(salario_actual) if salario_actual else 0
            }
        })

    except Exception as e:
        print(f"❌ Error cargando pagos móvil: {e}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

# ================================
# PERFIL DEL EMPLEADO - CORREGIDO
# ================================
@empleado_movil_bp.route("/empleado/perfil", methods=["GET"])
def api_perfil_movil():
    """API para obtener perfil del empleado"""
    try:
        # Obtener token del header Authorization
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False, 
                'message': 'Token de autorización requerido'
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Verificar token
        payload = verificar_token_movil(token)
        if not payload:
            return jsonify({
                'success': False, 
                'message': 'Token inválido o expirado'
            }), 401

        user_id = payload['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener el id_empleado
        cursor.execute("SELECT id_empleado FROM empleado WHERE id_usuario = %s", (user_id,))
        empleado_result = cursor.fetchone()
        
        if not empleado_result:
            return jsonify({
                'success': False, 
                'error': 'Empleado no encontrado'
            }), 404
        
        id_empleado = empleado_result[0]

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
        
        # Obtener estadísticas
        cursor.execute("""
            SELECT COUNT(*) FROM ticket 
            WHERE id_empleado = %s AND estado = 'cerrado'
        """, (user_id,))
        tickets_completados = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM registro_mantenimiento 
            WHERE id_empleado = %s
        """, (id_empleado,))
        mantenimientos_realizados = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM ticket 
            WHERE id_empleado = %s AND estado IN ('abierto', 'en_progreso')
        """, (user_id,))
        tickets_pendientes = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()

        # Convertir a diccionario
        empleado_dict = {
            'id_empleado': empleado_data[0],
            'puesto': empleado_data[1],
            'salario': float(empleado_data[2]) if empleado_data[2] else 0,
            'fecha_contratacion': empleado_data[3].strftime('%d/%m/%Y') if empleado_data[3] else '',
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
        
        return jsonify({
            'success': True,
            'data': {
                'empleado': empleado_dict,
                'estadisticas': {
                    'tickets_completados': tickets_completados,
                    'mantenimientos_realizados': mantenimientos_realizados,
                    'tickets_pendientes': tickets_pendientes
                }
            }
        })
    
    except Exception as e:
        print(f"❌ Error cargando perfil móvil: {e}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500