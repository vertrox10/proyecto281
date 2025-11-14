# routes/residenteperfilmovil.py - VERSIÓN COMPATIBLE CON TU JWT
from flask import Blueprint, request, jsonify
from datetime import datetime
from db import get_db_connection
import logging
import jwt

logger = logging.getLogger(__name__)

# ✅ SIN url_prefix aquí - se define en app.py
residente_perfil_movil_bp = Blueprint('residente_perfil_movil', __name__)

# Clave secreta JWT (debe coincidir con auth.py)
JWT_SECRET_KEY = 'tu-clave-secreta-muy-segura-para-movil-2024'

def get_user_id_from_token():
    """Obtener user_id desde el token JWT (como lo haces en auth.py)"""
    try:
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        
        # Decodificar token JWT
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        
        print(f"🔐 [JWT AUTH] User ID obtenido: {user_id}")
        return user_id
        
    except jwt.ExpiredSignatureError:
        print("❌ [JWT AUTH] Token expirado")
        return None
    except jwt.InvalidTokenError as e:
        print(f"❌ [JWT AUTH] Token inválido: {e}")
        return None
    except Exception as e:
        print(f"❌ [JWT AUTH] Error general: {e}")
        return None

def jwt_required(f):
    """Decorator personalizado para JWT (reemplaza @login_required)"""
    def decorated_function(*args, **kwargs):
        user_id = get_user_id_from_token()
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Token de autorización requerido o inválido'
            }), 401
        return f(user_id, *args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# ===== APIS CORREGIDAS CON JWT =====

@residente_perfil_movil_bp.route('/residente/perfil', methods=['GET'])
@jwt_required
def obtener_perfil_movil(user_id):
    """Obtener perfil completo para la app móvil"""
    try:
        print(f"📱 [PERFIL-MÓVIL] Obteniendo perfil para usuario: {user_id}")
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        # Obtener datos básicos del usuario
        cursor.execute("""
            SELECT 
                u.id_usuario, u.nombre, u.ap_paterno, u.ap_materno, 
                u.correo, u.telefono, u.ci, r.nombre as rol_nombre
            FROM usuario u
            JOIN rol r ON u.id_rol = r.id_rol
            WHERE u.id_usuario = %s
        """, (user_id,))
        
        usuario = cursor.fetchone()
        
        if not usuario:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404
        
        # Obtener información del residente
        cursor.execute("""
            SELECT 
                r.id_residente, r.piso, r.nro_departamento, r.fecha_ingreso
            FROM residente r 
            WHERE r.id_usuario = %s
        """, (user_id,))
        
        residente_data = cursor.fetchone()
        
        # Obtener información del departamento
        departamento_data = None
        if residente_data:
            cursor.execute("""
                SELECT id_departamento, piso, nro
                FROM departamento 
                WHERE piso = %s AND nro = %s
            """, (f"Piso {residente_data[1]}", residente_data[2]))
            departamento_data = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        # Construir respuesta
        respuesta = {
            'success': True,
            'usuario': {
                'id_usuario': usuario[0],
                'nombre': usuario[1] or '',
                'ap_paterno': usuario[2] or '',
                'ap_materno': usuario[3] or '',
                'correo': usuario[4] or '',
                'telefono': usuario[5] or '',
                'ci': usuario[6] or '',
                'rol_nombre': usuario[7] or 'Residente'
            },
            'departamento': None,
            'residente': None,
            'fecha_actual': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        
        # Agregar datos del residente si existen
        if residente_data:
            respuesta['residente'] = {
                'id_residente': residente_data[0],
                'piso': residente_data[1],
                'nro_departamento': residente_data[2],
                'fecha_ingreso': residente_data[3].strftime('%d/%m/%Y') if residente_data[3] else 'N/A'
            }
        
        # Agregar datos del departamento si existen
        if departamento_data:
            respuesta['departamento'] = {
                'id_departamento': departamento_data[0],
                'piso': departamento_data[1],
                'nro': departamento_data[2]
            }
        
        print(f"✅ [PERFIL-MÓVIL] Perfil obtenido exitosamente para usuario {user_id}")
        return jsonify(respuesta)
        
    except Exception as e:
        logger.error(f"Error en obtener_perfil_movil: {e}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500

@residente_perfil_movil_bp.route('/residente/perfil/actualizar', methods=['POST'])
@jwt_required
def actualizar_perfil_movil(user_id):
    """Actualizar perfil desde la app móvil"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos'
            }), 400
        
        print(f"📱 [PERFIL-MÓVIL] Actualizando perfil para usuario: {user_id}")
        
        # Validaciones básicas
        if not data.get('nombre'):
            return jsonify({
                'success': False,
                'message': 'El nombre es obligatorio'
            }), 400
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        # Verificar que el usuario existe
        cursor.execute("SELECT id_usuario FROM usuario WHERE id_usuario = %s", (user_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404
        
        # Actualizar información del usuario
        cursor.execute("""
            UPDATE usuario 
            SET nombre = %s, 
                ap_paterno = %s, 
                ap_materno = %s, 
                telefono = %s, 
                ci = %s
            WHERE id_usuario = %s
        """, (
            data.get('nombre', ''),
            data.get('ap_paterno', ''),
            data.get('ap_materno', ''),
            data.get('telefono', ''),
            data.get('ci', ''),
            user_id
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ [PERFIL-MÓVIL] Perfil actualizado exitosamente")
        
        return jsonify({
            'success': True,
            'message': 'Perfil actualizado correctamente'
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error en actualizar_perfil_movil: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al actualizar el perfil'
        }), 500

@residente_perfil_movil_bp.route('/residente/dashboard/resumen', methods=['GET'])
@jwt_required
def obtener_resumen_dashboard_movil(user_id):
    """Obtener resumen para el dashboard móvil"""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        # Obtener datos del residente
        cursor.execute("""
            SELECT r.id_residente, r.piso, r.nro_departamento
            FROM residente r 
            WHERE r.id_usuario = %s
        """, (user_id,))
        
        residente_data = cursor.fetchone()
        
        if not residente_data:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'No se encontraron datos del residente'
            }), 404
        
        id_residente = residente_data[0]
        piso = residente_data[1]
        nro_departamento = residente_data[2]
        
        # Buscar departamento para obtener id_departamento
        cursor.execute("""
            SELECT id_departamento 
            FROM departamento 
            WHERE piso = %s AND nro = %s
        """, (f"Piso {piso}", nro_departamento))
        
        depto_result = cursor.fetchone()
        id_departamento = depto_result[0] if depto_result else None
        
        # Tickets abiertos
        tickets_abiertos = 0
        tickets_urgentes = 0
        
        if id_departamento:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN prioridad IN ('alta', 'urgente') THEN 1 END) as urgentes
                FROM ticket 
                WHERE id_departamento = %s 
                AND estado IN ('abierto', 'en_progreso', 'pendiente')
            """, (id_departamento,))
        else:
            # Fallback: buscar por piso y número
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN t.prioridad IN ('alta', 'urgente') THEN 1 END) as urgentes
                FROM ticket t
                JOIN departamento d ON t.id_departamento = d.id_departamento
                WHERE d.piso = %s AND d.nro = %s
                AND t.estado IN ('abierto', 'en_progreso', 'pendiente')
            """, (f"Piso {piso}", nro_departamento))
        
        tickets_result = cursor.fetchone()
        if tickets_result:
            tickets_abiertos = tickets_result[0] or 0
            tickets_urgentes = tickets_result[1] or 0
        
        # Pagos pendientes
        cursor.execute("""
            SELECT 
                COUNT(*) as pendientes,
                COALESCE(SUM(monto_total), 0) as total_pendiente
            FROM factura 
            WHERE id_usuario = %s 
            AND estado_factura = 'pendiente'
        """, (user_id,))
        
        pagos_result = cursor.fetchone()
        pagos_pendientes = pagos_result[0] or 0 if pagos_result else 0
        monto_pendiente = float(pagos_result[1] or 0) if pagos_result else 0.0
        
        # Reservas activas (hoy o futuras)
        cursor.execute("""
            SELECT COUNT(*) as activas
            FROM pagos_qr 
            WHERE id_residente = %s 
            AND estado = 'completado'
            AND fecha_reserva >= CURRENT_DATE
        """, (id_residente,))
        
        reservas_result = cursor.fetchone()
        reservas_activas = reservas_result[0] or 0 if reservas_result else 0
        
        cursor.close()
        conn.close()
        
        resumen = {
            'tickets': {
                'abiertos': tickets_abiertos,
                'urgentes': tickets_urgentes
            },
            'pagos': {
                'pendientes': pagos_pendientes,
                'monto_pendiente': monto_pendiente
            },
            'reservas': {
                'activas': reservas_activas
            },
            'departamento': {
                'piso': piso,
                'numero': nro_departamento
            }
        }
        
        return jsonify({
            'success': True,
            'resumen': resumen
        })
        
    except Exception as e:
        logger.error(f"Error en obtener_resumen_dashboard_movil: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al obtener resumen del dashboard'
        }), 500

@residente_perfil_movil_bp.route('/residente/test', methods=['GET'])
def test_movil():
    """Endpoint de prueba sin autenticación"""
    return jsonify({
        'success': True,
        'message': 'API de perfil móvil funcionando',
        'timestamp': datetime.now().isoformat(),
        'endpoints': [
            'GET /api/movil/residente/perfil (JWT required)',
            'POST /api/movil/residente/perfil/actualizar (JWT required)', 
            'GET /api/movil/residente/dashboard/resumen (JWT required)'
        ]
    })

@residente_perfil_movil_bp.route('/residente/debug', methods=['GET'])
@jwt_required
def debug_movil(user_id):
    """Endpoint de debug con JWT"""
    auth_header = request.headers.get('Authorization', '')
    
    return jsonify({
        'success': True,
        'message': 'JWT funcionando correctamente',
        'user_id': user_id,
        'auth_header': auth_header[:50] + '...' if len(auth_header) > 50 else auth_header,
        'timestamp': datetime.now().isoformat()
    })