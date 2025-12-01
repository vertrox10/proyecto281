# residenteticketmovil.py - Blueprint para tickets de la app móvil con JWT CORREGIDO
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from db import get_db_connection
import json
import logging
import jwt as pyjwt
from flask_cors import CORS

logger = logging.getLogger(__name__)

residente_ticket_movil = Blueprint('residente_ticket_movil', __name__, url_prefix='/api/movil')
CORS(residente_ticket_movil, supports_credentials=True)

def get_user_id_from_jwt():
    """Obtiene el user_id desde el token JWT - CORREGIDO"""
    try:
        # Obtener el token del header
        auth_header = request.headers.get('Authorization', '')
        print(f"🔐 [TICKETS MOVIL] Auth Header recibido: {auth_header[:50]}...")
        
        if not auth_header.startswith('Bearer '):
            print("❌ [TICKETS MOVIL] ERROR: No se encontró Bearer token")
            return None
            
        token = auth_header[7:]  # Remover 'Bearer '
        print(f"🔐 [TICKETS MOVIL] Token limpio: {token[:50]}...")
        
        # ✅ USAR LA MISMA CLAVE QUE EL SISTEMA PRINCIPAL
        SECRET_KEY = 'tu-clave-super-segura-inf281-2025-movil-app-12345' 
        print(f"🔐 [TICKETS MOVIL] Secret Key usada: {SECRET_KEY[:10]}...")
        
        # Decodificar el token con PyJWT
        try:
            decoded = pyjwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            print(f"✅ [TICKETS MOVIL] Token decodificado COMPLETO: {decoded}")
            
            # 🔥 CORREGIDO: Buscar en 'sub' (como hace el sistema principal)
            user_id = decoded.get('sub')  # ← CAMBIO IMPORTANTE
            
            print(f"✅ [TICKETS MOVIL] User ID encontrado en 'sub': {user_id}")
            
            if user_id:
                return int(user_id)
            else:
                print("❌ [TICKETS MOVIL] ERROR: No se encontró 'sub' en el token")
                print(f"🔍 [TICKETS MOVIL] Todos los campos disponibles: {decoded}")
                return None
                
        except pyjwt.ExpiredSignatureError:
            print("❌ [TICKETS MOVIL] ERROR: Token expirado")
            return None
        except pyjwt.InvalidTokenError as e:
            print(f"❌ [TICKETS MOVIL] ERROR: Token inválido - {e}")
            return None
            
    except Exception as e:
        print(f"💥 [TICKETS MOVIL] ERROR general: {e}")
        return None

def validate_jwt_token():
    """Valida el token JWT y retorna user_id o error"""
    user_id = get_user_id_from_jwt()
    if not user_id:
        return None, jsonify({
            'success': False,
            'message': 'Token inválido o faltante'
        }), 422
    return user_id, None, None

def get_residente_from_user_id(user_id):
    """Obtiene datos del residente desde user_id"""
    try:
        conn = get_db_connection()
        if conn is None:
            return None
            
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_residente, piso, nro_departamento 
            FROM residente 
            WHERE id_usuario = %s
        """, (user_id,))
        
        residente = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if residente:
            print(f"✅ [TICKETS MOVIL] Residente encontrado: ID={residente[0]}, Piso={residente[1]}, Depto={residente[2]}")
        else:
            print("❌ [TICKETS MOVIL] No se encontró residente")
            
        return residente
    except Exception as e:
        logger.error(f"Error obteniendo residente: {e}")
        return None

def obtener_id_departamento(residente):
    """Obtiene el ID del departamento del residente"""
    try:
        if not residente:
            return None
            
        piso_residente = residente[1]  # piso del residente
        nro_departamento = residente[2]  # nro_departamento del residente
        
        # Convertir formato: piso 3 -> "Piso 3"
        piso_bd = f"Piso {piso_residente}"
        
        print(f"🔍 [TICKETS MOVIL] Buscando departamento: Piso='{piso_bd}', Nro='{nro_departamento}'")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar con el formato correcto de la BD
        cursor.execute("""
            SELECT id_departamento 
            FROM departamento 
            WHERE piso = %s AND nro = %s
        """, (piso_bd, nro_departamento))
        
        departamento = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if departamento:
            print(f"✅ [TICKETS MOVIL] Departamento encontrado: ID={departamento[0]}")
            return departamento[0]
        else:
            print("❌ [TICKETS MOVIL] No se encontró departamento en la BD")
            return None
            
    except Exception as e:
        print(f"❌ [TICKETS MOVIL] Error obteniendo departamento: {str(e)}")
        return None

# ===== MIDDLEWARE DE DEBUG =====

@residente_ticket_movil.before_request
def debug_before_request():
    """Middleware para debuggear requests"""
    if request.endpoint and 'residente_ticket_movil' in request.endpoint:
        auth_header = request.headers.get('Authorization', '')
        print(f"\n🔐 [TICKETS MOVIL] === NUEVO REQUEST ===")
        print(f"🔐 [TICKETS MOVIL] Endpoint: {request.endpoint}")
        print(f"🔐 [TICKETS MOVIL] Method: {request.method}")
        print(f"🔐 [TICKETS MOVIL] Auth Header: {auth_header[:80]}...")

# ===== ENDPOINTS PRINCIPALES =====

@residente_ticket_movil.route('/tickets', methods=['GET'])
def obtener_tickets_movil():
    """Obtener todos los tickets del residente"""
    try:
        print("🎯 [TICKETS MOVIL] Entrando a obtener_tickets_movil")
        
        # Validación manual del token
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        print(f"📱 [TICKETS MOVIL] Obteniendo tickets para usuario: {user_id}")
        
        # Obtener datos del residente
        residente = get_residente_from_user_id(user_id)
        if not residente:
            return jsonify({
                'success': False,
                'message': 'No se encontró información del residente'
            }), 404
        
        # Obtener ID del departamento
        id_departamento = obtener_id_departamento(residente)
        if not id_departamento:
            return jsonify({
                'success': False,
                'message': 'No se encontró departamento asociado'
            }), 404
        
        # Parámetros de paginación y filtros
        pagina = request.args.get('pagina', 1, type=int)
        por_pagina = request.args.get('por_pagina', 10, type=int)
        estado = request.args.get('estado', '')
        prioridad = request.args.get('prioridad', '')
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        # Construir consulta con filtros
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
                a.nombre as area_nombre
            FROM ticket t
            JOIN departamento d ON t.id_departamento = d.id_departamento
            LEFT JOIN empleado e ON t.id_empleado = e.id_empleado
            LEFT JOIN usuario u ON e.id_usuario = u.id_usuario
            LEFT JOIN area a ON t.id_area = a.id_area
            WHERE t.id_departamento = %s
        """
        
        params = [id_departamento]
        
        # Aplicar filtros
        if estado:
            query += " AND t.estado = %s"
            params.append(estado)
        
        if prioridad:
            query += " AND t.prioridad = %s"
            params.append(prioridad)
        
        # Ordenar y paginar
        query += " ORDER BY t.fecha_emision DESC LIMIT %s OFFSET %s"
        params.extend([por_pagina, (pagina - 1) * por_pagina])
        
        cursor.execute(query, params)
        tickets = cursor.fetchall()
        
        # Obtener estadísticas
        stats_query = """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN t.estado = 'abierto' THEN 1 END) as abiertos,
                COUNT(CASE WHEN t.estado = 'en_progreso' THEN 1 END) as en_progreso,
                COUNT(CASE WHEN t.estado IN ('cerrado', 'completado') THEN 1 END) as cerrados,
                COUNT(CASE WHEN t.prioridad = 'alta' OR t.prioridad = 'urgente' THEN 1 END) as urgentes
            FROM ticket t
            WHERE t.id_departamento = %s
        """
        
        cursor.execute(stats_query, (id_departamento,))
        stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        # Formatear tickets
        tickets_list = []
        for ticket in tickets:
            tickets_list.append({
                'id_ticket': ticket[0],
                'descripcion': ticket[1],
                'prioridad': ticket[2],
                'estado': ticket[3],
                'fecha_emision': ticket[4].strftime('%Y-%m-%d %H:%M:%S') if ticket[4] else None,
                'fecha_finalizacion': ticket[5].strftime('%Y-%m-%d %H:%M:%S') if ticket[5] else None,
                'piso': ticket[6],
                'nro_departamento': ticket[7],
                'empleado_nombre': f"{ticket[9]} {ticket[10] or ''}".strip() if ticket[9] else "No asignado",
                'area_nombre': ticket[11] or 'General'
            })
        
        # Preparar estadísticas
        estadisticas = {
            'total': stats[0] if stats else 0,
            'abiertos': stats[1] if stats else 0,
            'en_progreso': stats[2] if stats else 0,
            'cerrados': stats[3] if stats else 0,
            'urgentes': stats[4] if stats else 0
        }
        
        print(f"✅ [TICKETS MOVIL] Enviando {len(tickets_list)} tickets al usuario {user_id}")
        
        return jsonify({
            'success': True,
            'tickets': tickets_list,
            'estadisticas': estadisticas,
            'paginacion': {
                'pagina_actual': pagina,
                'por_pagina': por_pagina,
                'total': stats[0] if stats else 0
            },
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo tickets móvil: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al obtener los tickets'
        }), 500

@residente_ticket_movil.route('/tickets', methods=['POST'])
def crear_ticket_movil():
    """Crear nuevo ticket desde la app móvil"""
    try:
        print("🎯 [TICKETS MOVIL] Entrando a crear_ticket_movil")
        
        # Validación manual del token
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        data = request.get_json()
        
        print(f"📱 [TICKETS MOVIL] Creando ticket para usuario: {user_id}")
        print(f"📝 [TICKETS MOVIL] Datos recibidos: {data}")
        
        # Validar datos requeridos
        if not data.get('descripcion'):
            return jsonify({
                'success': False,
                'message': 'La descripción es obligatoria'
            }), 400
        
        # Obtener datos del residente
        residente = get_residente_from_user_id(user_id)
        if not residente:
            return jsonify({
                'success': False,
                'message': 'No se encontró información del residente'
            }), 404
        
        # Obtener ID del departamento
        id_departamento = obtener_id_departamento(residente)
        if not id_departamento:
            return jsonify({
                'success': False,
                'message': 'No se encontró departamento asociado'
            }), 400
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        # Validar que el área existe si se proporciona
        id_area = data.get('id_area')
        if id_area:
            cursor.execute("SELECT id_area FROM area WHERE id_area = %s", (id_area,))
            if not cursor.fetchone():
                id_area = None
        
        # Insertar nuevo ticket
        cursor.execute("""
            INSERT INTO ticket (
                descripcion, 
                prioridad, 
                fecha_emision, 
                estado, 
                id_departamento, 
                id_area
            ) VALUES (%s, %s, NOW(), 'abierto', %s, %s)
            RETURNING id_ticket
        """, (
            data.get('descripcion'),
            data.get('prioridad', 'media'),
            id_departamento,
            id_area if id_area else None
        ))
        
        ticket_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ [TICKETS MOVIL] Ticket creado exitosamente. ID: {ticket_id}")
        
        return jsonify({
            'success': True,
            'message': 'Ticket creado exitosamente',
            'ticket_id': ticket_id,
            'user_id': user_id
        })
            
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error creando ticket móvil: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al crear el ticket'
        }), 500

@residente_ticket_movil.route('/tickets/<int:ticket_id>', methods=['GET'])
def obtener_detalle_ticket_movil(ticket_id):
    """Obtener detalle completo de un ticket"""
    try:
        print(f"🎯 [TICKETS MOVIL] Entrando a obtener_detalle_ticket_movil para ticket {ticket_id}")
        
        # Validación manual del token
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        print(f"📱 [TICKETS MOVIL] Obteniendo detalle del ticket {ticket_id} para usuario: {user_id}")
        
        # Validar que el ticket pertenece al residente
        if not _validar_ticket_residente(ticket_id, user_id):
            return jsonify({
                'success': False,
                'message': 'Ticket no encontrado o no autorizado'
            }), 404
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
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
                a.descripcion as area_descripcion
            FROM ticket t
            JOIN departamento d ON t.id_departamento = d.id_departamento
            LEFT JOIN empleado e ON t.id_empleado = e.id_empleado
            LEFT JOIN usuario u ON e.id_usuario = u.id_usuario
            LEFT JOIN area a ON t.id_area = a.id_area
            WHERE t.id_ticket = %s
        """, (ticket_id,))
        
        ticket_data = cursor.fetchone()
        
        if not ticket_data:
            return jsonify({
                'success': False,
                'message': 'Ticket no encontrado'
            }), 404
        
        # Obtener comentarios del ticket
        cursor.execute("""
            SELECT 
                c.mensaje,
                c.fecha_creacion,
                c.es_interno,
                u.nombre,
                u.ap_paterno,
                u.ap_materno
            FROM comentario_ticket c
            JOIN usuario u ON c.id_usuario = u.id_usuario
            WHERE c.id_ticket = %s AND c.es_interno = false
            ORDER BY c.fecha_creacion ASC
        """, (ticket_id,))
        
        comentarios = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Formatear respuesta
        ticket_info = {
            'id_ticket': ticket_data[0],
            'descripcion': ticket_data[1],
            'prioridad': ticket_data[2],
            'estado': ticket_data[3],
            'fecha_emision': ticket_data[4].strftime('%Y-%m-%d %H:%M:%S') if ticket_data[4] else None,
            'fecha_finalizacion': ticket_data[5].strftime('%Y-%m-%d %H:%M:%S') if ticket_data[5] else None,
            'piso': ticket_data[6],
            'nro_departamento': ticket_data[7],
            'empleado_asignado': f"{ticket_data[9]} {ticket_data[10] or ''} {ticket_data[11] or ''}".strip() if ticket_data[9] else None,
            'area_nombre': ticket_data[12],
            'area_descripcion': ticket_data[13]
        }
        
        comentarios_list = []
        for comentario in comentarios:
            comentarios_list.append({
                'mensaje': comentario[0],
                'fecha': comentario[1].strftime('%Y-%m-%d %H:%M:%S'),
                'autor': f"{comentario[3]} {comentario[4] or ''} {comentario[5] or ''}".strip(),
                'es_interno': comentario[2]
            })
        
        print(f"✅ [TICKETS MOVIL] Detalles del ticket {ticket_id} enviados")
        
        return jsonify({
            'success': True,
            'ticket': ticket_info,
            'comentarios': comentarios_list,
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo detalles del ticket: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al obtener detalles del ticket'
        }), 500

@residente_ticket_movil.route('/tickets/<int:ticket_id>/comentarios', methods=['POST'])
def agregar_comentario_movil(ticket_id):
    """Agregar comentario a un ticket"""
    try:
        print(f"🎯 [TICKETS MOVIL] Entrando a agregar_comentario_movil para ticket {ticket_id}")
        
        # Validación manual del token
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        data = request.get_json()
        
        print(f"📱 [TICKETS MOVIL] Agregando comentario al ticket {ticket_id}")
        
        if not data.get('comentario'):
            return jsonify({
                'success': False,
                'message': 'El comentario es requerido'
            }), 400
        
        # Validar que el ticket pertenece al residente
        if not _validar_ticket_residente(ticket_id, user_id):
            return jsonify({
                'success': False,
                'message': 'Ticket no encontrado o no autorizado'
            }), 404
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        # Agregar comentario
        cursor.execute("""
            INSERT INTO comentario_ticket 
            (id_ticket, id_usuario, mensaje, fecha_creacion, es_interno)
            VALUES (%s, %s, %s, NOW(), false)
        """, (ticket_id, user_id, data['comentario']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ [TICKETS MOVIL] Comentario agregado al ticket {ticket_id}")
        
        return jsonify({
            'success': True,
            'message': 'Comentario agregado exitosamente',
            'user_id': user_id
        })
            
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error agregando comentario: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al agregar comentario'
        }), 500

@residente_ticket_movil.route('/tickets/<int:ticket_id>/cancelar', methods=['PUT'])
def cancelar_ticket_movil(ticket_id):
    """Cancelar un ticket"""
    try:
        print(f"🎯 [TICKETS MOVIL] Entrando a cancelar_ticket_movil para ticket {ticket_id}")
        
        # Validación manual del token
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        print(f"📱 [TICKETS MOVIL] Cancelando ticket {ticket_id}")
        
        # Validar que el ticket pertenece al residente
        if not _validar_ticket_residente(ticket_id, user_id):
            return jsonify({
                'success': False,
                'message': 'Ticket no encontrado o no autorizado'
            }), 404
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        # Verificar que el ticket puede ser cancelado
        cursor.execute("SELECT estado FROM ticket WHERE id_ticket = %s", (ticket_id,))
        ticket_estado = cursor.fetchone()
        
        if not ticket_estado:
            return jsonify({
                'success': False,
                'message': 'Ticket no encontrado'
            }), 404
            
        if ticket_estado[0] != 'abierto':
            return jsonify({
                'success': False,
                'message': 'Solo se pueden cancelar tickets abiertos'
            }), 400
        
        # Cancelar el ticket
        cursor.execute("""
            UPDATE ticket 
            SET estado = 'cancelado', fecha_finalizacion = NOW()
            WHERE id_ticket = %s
        """, (ticket_id,))
        
        # Agregar comentario de cancelación
        cursor.execute("""
            INSERT INTO comentario_ticket (id_ticket, id_usuario, mensaje, fecha_creacion, es_interno)
            VALUES (%s, %s, %s, NOW(), false)
        """, (ticket_id, user_id, "Ticket cancelado por el residente desde la app móvil"))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ [TICKETS MOVIL] Ticket {ticket_id} cancelado exitosamente")
        
        return jsonify({
            'success': True,
            'message': 'Ticket cancelado exitosamente',
            'user_id': user_id
        })
            
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error cancelando ticket: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al cancelar el ticket'
        }), 500

@residente_ticket_movil.route('/areas', methods=['GET'])
def obtener_areas_movil():
    """Obtener áreas comunes para crear tickets"""
    try:
        print("🎯 [TICKETS MOVIL] Entrando a obtener_areas_movil")
        
        # Validación manual del token
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        print(f"📱 [TICKETS MOVIL] Obteniendo áreas para usuario: {user_id}")
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id_area, nombre, descripcion 
            FROM area 
            ORDER BY nombre
        """)
        
        areas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        areas_list = []
        for area in areas:
            areas_list.append({
                'id_area': area[0],
                'nombre': area[1],
                'descripcion': area[2] if len(area) > 2 else ''
            })
        
        print(f"✅ [TICKETS MOVIL] Enviando {len(areas_list)} áreas al usuario {user_id}")
        
        return jsonify({
            'success': True,
            'areas': areas_list,
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo áreas: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al obtener las áreas'
        }), 500

@residente_ticket_movil.route('/estadisticas', methods=['GET'])
def obtener_estadisticas_movil():
    """Obtener estadísticas para el dashboard móvil"""
    try:
        print("🎯 [TICKETS MOVIL] Entrando a obtener_estadisticas_movil")
        
        # Validación manual del token
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        print(f"📱 [TICKETS MOVIL] Obteniendo estadísticas para usuario: {user_id}")
        
        # Obtener datos del residente
        residente = get_residente_from_user_id(user_id)
        if not residente:
            return jsonify({
                'success': False,
                'message': 'No se encontró información del residente'
            }), 404
        
        # Obtener ID del departamento
        id_departamento = obtener_id_departamento(residente)
        if not id_departamento:
            return jsonify({
                'success': False,
                'message': 'No se encontró departamento asociado'
            }), 404
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        # Obtener estadísticas
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN estado = 'abierto' THEN 1 END) as abiertos,
                COUNT(CASE WHEN estado = 'en_progreso' THEN 1 END) as en_progreso,
                COUNT(CASE WHEN estado IN ('cerrado', 'completado') THEN 1 END) as cerrados,
                COUNT(CASE WHEN prioridad = 'alta' OR prioridad = 'urgente' THEN 1 END) as urgentes
            FROM ticket 
            WHERE id_departamento = %s
        """, (id_departamento,))
        
        stats = cursor.fetchone()
        cursor.close()
        conn.close()
        
        estadisticas = {
            'total': stats[0] if stats else 0,
            'abiertos': stats[1] if stats else 0,
            'en_progreso': stats[2] if stats else 0,
            'cerrados': stats[3] if stats else 0,
            'urgentes': stats[4] if stats else 0
        }
        
        return jsonify({
            'success': True,
            'estadisticas': estadisticas,
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al obtener estadísticas'
        }), 500

# ===== FUNCIONES AUXILIARES =====

def _validar_ticket_residente(ticket_id, user_id):
    """Valida que el ticket pertenece al residente actual"""
    try:
        print(f"🔍 [TICKETS MOVIL] Validando ticket {ticket_id} para usuario {user_id}")
        
        conn = get_db_connection()
        if conn is None:
            return False
            
        cursor = conn.cursor()
        
        # Obtener datos del residente
        cursor.execute("""
            SELECT r.piso, r.nro_departamento 
            FROM residente r 
            WHERE r.id_usuario = %s
        """, (user_id,))
        
        residente = cursor.fetchone()
        if not residente:
            return False
            
        piso_residente = residente[0]  # 3
        depto_residente = residente[1]  # '303'
        
        # Buscar el ticket comparando directamente piso y departamento
        cursor.execute("""
            SELECT t.id_ticket 
            FROM ticket t
            JOIN departamento d ON t.id_departamento = d.id_departamento
            WHERE t.id_ticket = %s 
            AND (
                (d.piso = 'Piso ' || %s::varchar AND d.nro = %s) OR
                (d.piso = %s::varchar AND d.nro = %s)
            )
        """, (ticket_id, piso_residente, depto_residente, piso_residente, depto_residente))
        
        ticket_valido = cursor.fetchone()
        cursor.close()
        conn.close()
        
        print(f"🔍 [TICKETS MOVIL] Ticket válido: {bool(ticket_valido)}")
        return bool(ticket_valido)
        
    except Exception as e:
        print(f"❌ [TICKETS MOVIL] Error validando ticket: {str(e)}")
        return False

# ===== ENDPOINTS DE DIAGNÓSTICO =====

@residente_ticket_movil.route('/debug', methods=['GET'])
def debug_tickets():
    """Endpoint de diagnóstico para tickets"""
    return jsonify({
        'success': True,
        'message': '✅ residente_ticket_movil está funcionando',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'tickets': '/api/movil/tickets (GET)',
            'create_ticket': '/api/movil/tickets (POST)', 
            'ticket_detail': '/api/movil/tickets/<id> (GET)',
            'areas': '/api/movil/areas (GET)',
            'estadisticas': '/api/movil/estadisticas (GET)'
        },
        'version': '1.0.0-jwt-manual-corregido'
    })

@residente_ticket_movil.route('/test_conexion', methods=['GET'])
def test_conexion_tickets():
    """Test de conexión para tickets"""
    try:
        # Validación manual del token
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        return jsonify({
            'success': True,
            'message': '✅ Conexión exitosa con tickets móvil',
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error en test: {str(e)}'
        }), 500