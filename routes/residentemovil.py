# residentemovil.py - Blueprint especial para la app móvil con JWT CORREGIDO
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from db import get_db_connection
import json
import logging
import os
from werkzeug.utils import secure_filename
from flask_cors import CORS
from jwt_decorators import jwt_required  # ✅ DECORADOR CORRECTO

logger = logging.getLogger(__name__)

# ✅ CORRECTO: Crear el blueprint aquí
residentemovil_bp = Blueprint('residentemovil', __name__)
CORS(residentemovil_bp, supports_credentials=True)

# Configuración para subida de archivos
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
UPLOAD_FOLDER = 'static/uploads/bouchers_movil'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            print(f"✅ [RESIDENTEMOVIL] Residente encontrado: ID={residente[0]}, Piso={residente[1]}, Depto={residente[2]}")
            return {
                'id_residente': residente[0],
                'piso': residente[1],
                'nro_departamento': residente[2]
            }
        else:
            print("❌ [RESIDENTEMOVIL] No se encontró residente")
            return None
    except Exception as e:
        logger.error(f"Error obteniendo residente: {e}")
        return None

# ===== ENDPOINTS CON DECORADOR JWT =====

@residentemovil_bp.route('/residente/dashboard-data')
@jwt_required  # ✅ USAR EL DECORADOR CORRECTO
def dashboard_data_movil():
    """Endpoint de dashboard para residentes móviles - VERSIÓN CORREGIDA"""
    try:
        current_user_id = request.current_user_id  # ✅ AHORA FUNCIONARÁ
        
        print(f"📱 [RESIDENTEMOVIL] Obteniendo dashboard para usuario: {current_user_id}")
        
        # Obtener datos del residente
        residente = get_residente_from_user_id(current_user_id)
        if not residente:
            return jsonify({
                'success': False,
                'message': 'No se encontraron datos del residente'
            }), 404
        
        id_residente = residente['id_residente']
        piso = residente['piso']
        nro_departamento = residente['nro_departamento']
        
        # CONEXIÓN A BD PARA DATOS REALES
        conn = get_db_connection()
        if conn is None:
            # Datos de ejemplo si no hay conexión
            return jsonify({
                'success': True,
                'dashboard': {
                    'residente': {
                        'id': id_residente,
                        'nombre': 'Ana Rojas',
                        'piso': piso,
                        'departamento': nro_departamento,
                        'correo': 'grr012096@gmail.com'
                    },
                    'estadisticas': {
                        'reservas_activas': 2,
                        'reservas_totales': 15,
                        'pagos_pendientes': 0,
                        'monto_gastado': 1250.00
                    },
                    'reservas_recientes': [
                        {
                            'id': 1,
                            'area': 'Salón de Eventos',
                            'fecha': '15/01/2024',
                            'estado': 'confirmado',
                            'monto': 350.00
                        },
                        {
                            'id': 2, 
                            'area': 'Gimnasio',
                            'fecha': '16/01/2024',
                            'estado': 'pendiente',
                            'monto': 50.00
                        }
                    ],
                    'alertas': [
                        {
                            'tipo': 'info',
                            'mensaje': 'Bienvenido al sistema móvil',
                            'fecha': datetime.now().strftime('%d/%m/%Y')
                        }
                    ]
                },
                'modo': 'simulacion_sin_bd'
            })
        
        cursor = conn.cursor()
        
        # Obtener datos reales del residente
        cursor.execute("""
            SELECT u.nombre, u.ap_paterno, u.ap_materno, u.correo, u.telefono
            FROM usuario u
            WHERE u.id_usuario = %s
        """, (current_user_id,))
        
        usuario_data = cursor.fetchone()
        
        # Contar reservas activas
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pagos_qr 
            WHERE id_residente = %s AND estado IN ('confirmado', 'pendiente')
        """, (id_residente,))
        reservas_activas = cursor.fetchone()[0]
        
        # Contar reservas totales
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pagos_qr 
            WHERE id_residente = %s
        """, (id_residente,))
        reservas_totales = cursor.fetchone()[0]
        
        # Sumar montos pagados
        cursor.execute("""
            SELECT COALESCE(SUM(monto), 0) 
            FROM pagos_qr 
            WHERE id_residente = %s AND estado = 'confirmado'
        """, (id_residente,))
        monto_gastado = float(cursor.fetchone()[0])
        
        # Reservas recientes
        cursor.execute("""
            SELECT 
                pq.id_pago,
                c.nombre as area,
                pq.fecha_reserva,
                pq.estado,
                pq.monto
            FROM pagos_qr pq
            LEFT JOIN conceptos_pago c ON pq.id_concepto = c.id_concepto
            WHERE pq.id_residente = %s
            ORDER BY pq.fecha_generacion DESC
            LIMIT 5
        """, (id_residente,))
        
        reservas_recientes = []
        for reserva in cursor.fetchall():
            reservas_recientes.append({
                'id': reserva[0],
                'area': reserva[1] or 'Área común',
                'fecha': reserva[2].strftime('%d/%m/%Y') if reserva[2] else 'Pendiente',
                'estado': reserva[3],
                'monto': float(reserva[4])
            })
        
        cursor.close()
        conn.close()
        
        # Construir respuesta
        nombre_completo = f"{usuario_data[0]} {usuario_data[1] or ''}".strip() if usuario_data else "Residente"
        
        dashboard_data = {
            'residente': {
                'id': id_residente,
                'nombre': nombre_completo,
                'piso': piso,
                'departamento': nro_departamento,
                'correo': usuario_data[3] if usuario_data else 'No disponible',
                'telefono': usuario_data[4] if usuario_data else 'No disponible'
            },
            'estadisticas': {
                'reservas_activas': reservas_activas,
                'reservas_totales': reservas_totales,
                'pagos_pendientes': 0,
                'monto_gastado': monto_gastado
            },
            'reservas_recientes': reservas_recientes,
            'alertas': [
                {
                    'tipo': 'success',
                    'mensaje': f'Bienvenido/a {nombre_completo}',
                    'fecha': datetime.now().strftime('%d/%m/%Y')
                }
            ]
        }
        
        print(f"✅ [RESIDENTEMOVIL] Dashboard enviado para usuario {current_user_id}")
        
        return jsonify({
            'success': True,
            'dashboard': dashboard_data,
            'user_id': current_user_id,
            'modo': 'bd_real'
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo dashboard: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        
        # Respuesta de emergencia
        return jsonify({
            'success': True,
            'dashboard': {
                'residente': {
                    'id': 0,
                    'nombre': 'Ana Rojas',
                    'piso': 'X',
                    'departamento': 'Y',
                    'correo': 'grr012096@gmail.com'
                },
                'estadisticas': {
                    'reservas_activas': 0,
                    'reservas_totales': 0,
                    'pagos_pendientes': 0,
                    'monto_gastado': 0
                },
                'reservas_recientes': [],
                'alertas': [
                    {
                        'tipo': 'warning',
                        'mensaje': 'Datos en modo simulación',
                        'fecha': datetime.now().strftime('%d/%m/%Y')
                    }
                ]
            },
            'modo': 'simulacion_error'
        })

@residentemovil_bp.route('/residente/areas_disponibles')
@jwt_required  # ✅ AGREGAR DECORADOR
def areas_disponibles_movil():
    """Obtener áreas disponibles"""
    try:
        current_user_id = request.current_user_id
        
        print(f"📱 [RESIDENTEMOVIL] Obteniendo áreas para usuario: {current_user_id}")
        
        # Datos estáticos para el móvil
        areas = [
            {
                'id': 'salon',
                'nombre': 'Salón de Eventos',
                'descripcion': 'Capacidad: 50 personas. Ideal para celebraciones y reuniones.',
                'precio': 350.00,
                'precio_texto': '350 Bs',
                'horario': 'Lun-Dom: 8:00-22:00',
                'capacidad': 'Máx. 50 personas',
                'disponible': True,
                'icono': 'celebration'
            },
            {
                'id': 'piscina', 
                'nombre': 'Piscina',
                'descripcion': 'Área recreativa con capacidad para 30 personas simultáneamente.',
                'precio': 200.00,
                'precio_texto': '200 Bs',
                'horario': 'Mar-Dom: 9:00-19:00',
                'capacidad': 'Máx. 30 personas',
                'disponible': True,
                'icono': 'pool'
            },
            {
                'id': 'gimnasio',
                'nombre': 'Gimnasio SincroHome', 
                'descripcion': 'Equipo completo de ejercicio. Uso por horas.',
                'precio': 25.00,
                'precio_texto': '25 Bs/hora',
                'horario': 'Lun-Sáb: 6:00-22:00',
                'capacidad': 'Máx. 15 personas',
                'disponible': True,
                'icono': 'fitness_center'
            },
            {
                'id': 'parqueo',
                'nombre': 'Parqueo de Visitantes',
                'descripcion': 'Espacios adicionales para visitantes del residente.',
                'precio': 10.00,
                'precio_texto': '10 Bs/día', 
                'horario': 'Todos los días: 24h',
                'capacidad': '1 vehículo por reserva',
                'disponible': True,
                'icono': 'local_parking'
            }
        ]
        
        print(f"✅ [RESIDENTEMOVIL] Enviando {len(areas)} áreas al usuario {current_user_id}")
        
        return jsonify({
            'success': True,
            'areas': areas,
            'total': len(areas),
            'user_id': current_user_id,
            'message': 'Áreas obtenidas exitosamente'
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo áreas móvil: {e}")
        return jsonify({
            'success': False,
            'message': 'Error obteniendo áreas disponibles'
        }), 500

@residentemovil_bp.route('/residente/mis_reservas')
@jwt_required  # ✅ AGREGAR DECORADOR
def mis_reservas_movil():
    """Obtener reservas del residente"""
    try:
        current_user_id = request.current_user_id
        
        print(f"📱 [RESIDENTEMOVIL] Obteniendo reservas para usuario: {current_user_id}")
        
        # Obtener el id_residente
        residente = get_residente_from_user_id(current_user_id)
        if not residente:
            return jsonify({
                'success': False,
                'message': 'No se encontraron datos del residente'
            }), 404
        
        id_residente = residente['id_residente']
        print(f"✅ ID Residente encontrado: {id_residente}")

        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': True,
                'reservas': _get_reservas_ejemplo(),
                'modo': 'simulacion_sin_bd',
                'user_id': current_user_id
            })
            
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                pq.id_pago,
                pq.descripcion,
                pq.monto,
                pq.fecha_generacion,
                pq.estado,
                pq.metodo_pago,
                pq.comprobante,
                pq.horas,
                pq.fecha_reserva,
                c.nombre as concepto_nombre
            FROM pagos_qr pq
            LEFT JOIN conceptos_pago c ON pq.id_concepto = c.id_concepto
            WHERE pq.id_residente = %s
            ORDER BY pq.fecha_generacion DESC
            LIMIT 20
        """, (id_residente,))
        
        reservas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        reservas_list = []
        for reserva in reservas:
            reservas_list.append({
                'id': reserva[0],
                'descripcion': reserva[1],
                'monto': float(reserva[2]),
                'fecha_generacion': reserva[3].strftime('%d/%m/%Y %H:%M'),
                'estado': reserva[4],
                'metodo_pago': reserva[5],
                'comprobante': reserva[6],
                'horas': reserva[7] or 1,
                'fecha_reserva': reserva[8].strftime('%d/%m/%Y') if reserva[8] else '',
                'concepto': reserva[9] or 'Área común'
            })
        
        print(f"✅ [RESIDENTEMOVIL] Enviando {len(reservas_list)} reservas al usuario {current_user_id}")
        
        return jsonify({
            'success': True,
            'reservas': reservas_list,
            'total': len(reservas_list),
            'user_id': current_user_id,
            'id_residente': id_residente
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo reservas móvil: {e}")
        return jsonify({
            'success': True,
            'reservas': _get_reservas_ejemplo(),
            'modo': 'simulacion_error',
            'user_id': current_user_id
        })

@residentemovil_bp.route('/residente/test-jwt')
@jwt_required  # ✅ AGREGAR DECORADOR
def test_jwt_residente():
    """Endpoint de prueba para verificar que JWT funciona en residente"""
    try:
        current_user_id = request.current_user_id
        
        return jsonify({
            'success': True,
            'message': '✅ JWT funcionando correctamente en residente móvil',
            'user_id': current_user_id,
            'auth_header': request.headers.get('Authorization', 'No header')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== FUNCIONES AUXILIARES =====

def _get_reservas_ejemplo():
    """Datos de ejemplo para desarrollo"""
    return [
        {
            'id': 1,
            'descripcion': 'Salón de Eventos - Reserva familiar',
            'monto': 350.00,
            'fecha_generacion': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'estado': 'confirmado',
            'metodo_pago': 'qr',
            'comprobante': 'TRX_MOVIL_001',
            'horas': 4,
            'fecha_reserva': '15/01/2024',
            'concepto': 'Salón de Eventos'
        },
        {
            'id': 2,
            'descripcion': 'Gimnasio SincroHome - Entrenamiento',
            'monto': 50.00,
            'fecha_generacion': (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y %H:%M'),
            'estado': 'pendiente',
            'metodo_pago': 'transferencia',
            'comprobante': 'TRX_MOVIL_002',
            'horas': 2,
            'fecha_reserva': '16/01/2024',
            'concepto': 'Gimnasio'
        }
    ]