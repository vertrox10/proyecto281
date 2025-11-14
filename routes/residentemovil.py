# residentemovil.py - Blueprint especial para la app móvil con JWT CORREGIDO
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from db import get_db_connection
import json
import logging
import os
from werkzeug.utils import secure_filename
from flask_cors import CORS
import jwt as pyjwt

logger = logging.getLogger(__name__)

residentemovil_bp = Blueprint('residentemovil', __name__, url_prefix='/residentemovil')
CORS(residentemovil_bp, supports_credentials=True)

# Configuración para subida de archivos
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
UPLOAD_FOLDER = 'static/uploads/bouchers_movil'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_id_from_jwt():
    """Obtiene el user_id desde el token JWT - VERSIÓN CORREGIDA PARA TU TOKEN"""
    try:
        # Obtener el token del header
        auth_header = request.headers.get('Authorization', '')
        print(f"🔐 [RESIDENTEMOVIL] Auth Header recibido: {auth_header[:50]}...")
        
        if not auth_header.startswith('Bearer '):
            print("❌ [RESIDENTEMOVIL] ERROR: No se encontró Bearer token")
            return None
            
        token = auth_header[7:]  # Remover 'Bearer '
        print(f"🔐 [RESIDENTEMOVIL] Token limpio: {token[:50]}...")
        
        # ✅ USAR LA CLAVE CORRECTA
        SECRET_KEY = 'tu-clave-secreta-muy-segura-para-movil-2024'
        print(f"🔐 [RESIDENTEMOVIL] Secret Key usada: {SECRET_KEY[:10]}...")
        
        # Decodificar el token con PyJWT
        try:
            decoded = pyjwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            print(f"✅ [RESIDENTEMOVIL] Token decodificado COMPLETO: {decoded}")
            
            # 🔥 BUSCAR EL USER_ID EN EL FORMATO CORRECTO DE TU TOKEN
            user_id = decoded.get('user_id')  # ← ESTE ES EL CAMPO CORRECTO
            
            print(f"✅ [RESIDENTEMOVIL] User ID encontrado: {user_id}")
            
            if user_id:
                return int(user_id)
            else:
                print("❌ [RESIDENTEMOVIL] ERROR: No se encontró 'user_id' en el token")
                print(f"🔍 [RESIDENTEMOVIL] Todos los campos disponibles: {decoded}")
                return None
                
        except pyjwt.ExpiredSignatureError:
            print("❌ [RESIDENTEMOVIL] ERROR: Token expirado")
            return None
        except pyjwt.InvalidTokenError as e:
            print(f"❌ [RESIDENTEMOVIL] ERROR: Token inválido - {e}")
            return None
            
    except Exception as e:
        print(f"💥 [RESIDENTEMOVIL] ERROR general: {e}")
        return None
@residentemovil_bp.route('/api/debug_token_formato')
def debug_token_formato():
    """Debug específico para el formato de token personalizado"""
    try:
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'message': 'No Bearer token'
            }), 401
            
        token = auth_header[7:]
        SECRET_KEY = 'tu-clave-secreta-muy-segura-para-movil-2024'
        
        try:
            decoded = pyjwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            
            return jsonify({
                'success': True,
                'message': '✅ Token decodificado exitosamente',
                'token_format': 'PERSONALIZADO',
                'payload': decoded,
                'user_id_location': decoded.get('user_id'),
                'all_fields': list(decoded.keys()),
                'secret_key_match': True
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'❌ Error decodificando: {str(e)}',
                'secret_key_used': SECRET_KEY[:10] + '...'
            }), 422
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error en debug: {str(e)}'
        }), 500
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
            print(f"✅ [RESIDENTEMOVIL] Residente encontrado: ID={residente[0]}, Piso={residente[1]}, Depto={residente[2]}")
        else:
            print("❌ [RESIDENTEMOVIL] No se encontró residente")
            
        return residente
    except Exception as e:
        logger.error(f"Error obteniendo residente: {e}")
        return None

# ===== MIDDLEWARE DE DEBUG =====

@residentemovil_bp.before_request
def debug_before_request():
    """Middleware para debuggear requests"""
    if request.endpoint and 'residentemovil' in request.endpoint:
        auth_header = request.headers.get('Authorization', '')
        print(f"\n🔐 [RESIDENTEMOVIL] === NUEVO REQUEST ===")
        print(f"🔐 [RESIDENTEMOVIL] Endpoint: {request.endpoint}")
        print(f"🔐 [RESIDENTEMOVIL] Method: {request.method}")
        print(f"🔐 [RESIDENTEMOVIL] Auth Header: {auth_header[:80]}...")
        print(f"🔐 [RESIDENTEMOVIL] JWT Secret: {current_app.config.get('JWT_SECRET_KEY', 'NO_CONFIG')[:10]}...")

# ===== ENDPOINTS CON VALIDACIÓN MANUAL =====

@residentemovil_bp.route('/api/areas_disponibles')
def areas_disponibles_movil():
    """Obtener áreas disponibles - VERSIÓN CON VALIDACIÓN MANUAL"""
    try:
        print("🎯 [RESIDENTEMOVIL] Entrando a áreas_disponibles_movil")
        
        # Validación manual del token
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        print(f"📱 [RESIDENTEMOVIL] Obteniendo áreas para usuario: {user_id}")
        
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
        
        print(f"✅ [RESIDENTEMOVIL] Enviando {len(areas)} áreas al usuario {user_id}")
        
        return jsonify({
            'success': True,
            'areas': areas,
            'total': len(areas),
            'user_id': user_id,
            'message': 'Áreas obtenidas exitosamente'
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo áreas móvil: {e}")
        return jsonify({
            'success': False,
            'message': 'Error obteniendo áreas disponibles'
        }), 500

@residentemovil_bp.route('/api/mis_reservas')
def mis_reservas_movil():
    """Obtener reservas del residente - VERSIÓN CON VALIDACIÓN MANUAL"""
    try:
        print("🎯 [RESIDENTEMOVIL] Entrando a mis_reservas_movil")
        
        # Validación manual del token
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        print(f"📱 [RESIDENTEMOVIL] Obteniendo reservas para usuario: {user_id}")
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': True,
                'reservas': _get_reservas_ejemplo(),
                'modo': 'simulacion_sin_bd',
                'user_id': user_id
            })
            
        cursor = conn.cursor()
        
        # Consulta optimizada para móvil
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
            JOIN residente r ON pq.id_residente = r.id_residente
            LEFT JOIN conceptos_pago c ON pq.id_concepto = c.id_concepto
            WHERE r.id_usuario = %s
            ORDER BY pq.fecha_generacion DESC
            LIMIT 20
        """, (user_id,))
        
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
        
        print(f"✅ [RESIDENTEMOVIL] Enviando {len(reservas_list)} reservas al usuario {user_id}")
        
        return jsonify({
            'success': True,
            'reservas': reservas_list,
            'total': len(reservas_list),
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo reservas móvil: {e}")
        return jsonify({
            'success': True,
            'reservas': _get_reservas_ejemplo(),
            'modo': 'simulacion_error',
            'user_id': user_id if 'user_id' in locals() else None
        })

@residentemovil_bp.route('/api/test_conexion')
def test_conexion():
    """Endpoint para probar conexión con el móvil - VERSIÓN CON VALIDACIÓN MANUAL"""
    try:
        print("🎯 [RESIDENTEMOVIL] Entrando a test_conexion")
        
        # Validación manual del token
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        print(f"🔐 [RESIDENTEMOVIL] Test conexión para usuario: {user_id}")
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        cursor.execute("SELECT nombre, correo FROM usuario WHERE id_usuario = %s", (user_id,))
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if usuario:
            return jsonify({
                'success': True,
                'message': '✅ Conexión exitosa con Flask + JWT',
                'usuario': usuario[0],
                'correo': usuario[1],
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Error en test_conexion: {e}")
        return jsonify({
            'success': False,
            'message': f'Error en el servidor: {str(e)}'
        }), 500

@residentemovil_bp.route('/api/procesar_reserva', methods=['POST'])
def procesar_reserva_movil():
    """Procesar reserva - VERSIÓN CON VALIDACIÓN MANUAL"""
    try:
        print("🎯 [RESIDENTEMOVIL] Entrando a procesar_reserva_movil")
        
        # Validación manual del token
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        print(f"📱 [RESIDENTEMOVIL] Procesando reserva para usuario: {user_id}")
        
        # Obtener datos del residente
        residente = get_residente_from_user_id(user_id)
        if not residente:
            return jsonify({
                'success': False, 
                'message': 'No se encontraron datos del residente'
            }), 400
        
        id_residente, piso, nro_departamento = residente
        print(f"📱 [RESIDENTEMOVIL] Residente: ID={id_residente}, Piso={piso}, Depto={nro_departamento}")
        
        # Manejar tanto JSON como FormData
        if request.content_type and request.content_type.startswith('application/json'):
            data = request.get_json()
            boucher_filename = None
            print("📱 [RESIDENTEMOVIL] Datos recibidos como JSON")
        else:
            data = request.form.to_dict()
            boucher_file = request.files.get('boucher')
            boucher_filename = None
            
            if boucher_file and allowed_file(boucher_file.filename):
                filename = secure_filename(boucher_file.filename)
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                timestamp = int(datetime.now().timestamp())
                boucher_filename = f"movil_boucher_{user_id}_{timestamp}_{filename}"
                boucher_path = os.path.join(UPLOAD_FOLDER, boucher_filename)
                boucher_file.save(boucher_path)
                print(f"📱 [RESIDENTEMOVIL] Boucher guardado: {boucher_filename}")

            print("📱 [RESIDENTEMOVIL] Datos recibidos como FormData")

        # Debug
        print(f"📱 [RESIDENTEMOVIL] Datos recibidos: {list(data.keys())}")
        for key, value in data.items():
            print(f"   {key}: {value}")
        
        # Validaciones básicas
        required_fields = ['area', 'nombre_area', 'fecha', 'monto']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False, 
                    'message': f'Campo requerido faltante: {field}'
                }), 400
        
        # CONEXIÓN REAL A LA BASE DE DATOS
        try:
            conn = get_db_connection()
            if conn is None:
                raise Exception("No se pudo conectar a la base de datos")
                
            cursor = conn.cursor()
            
            # Determinar concepto_id basado en el área
            conceptos = {
                'salon': 1,
                'piscina': 2, 
                'gimnasio': 3,
                'parqueo': 4
            }
            concepto_id = conceptos.get(data['area'])
            print(f"🔍 [RESIDENTEMOVIL] Concepto ID: {concepto_id} para área: {data['area']}")
            
            # Si no existe concepto, usar uno por defecto
            if not concepto_id:
                cursor.execute("SELECT id_concepto FROM conceptos_pago WHERE activo = true LIMIT 1")
                concepto_default = cursor.fetchone()
                concepto_id = concepto_default[0] if concepto_default else 1
                print(f"⚠️ [RESIDENTEMOVIL] Usando concepto por defecto: {concepto_id}")
            
            # Calcular horas y monto
            horas = int(data.get('horas', 1))
            monto = float(data['monto'])
            
            # Generar código único
            codigo_qr = f"RESERVA_{user_id}_{int(datetime.now().timestamp())}"
            
            # Procesar fecha
            fecha_reserva_obj = None
            fecha_reserva_str = data.get('fecha', '')
            
            if fecha_reserva_str:
                try:
                    fecha_reserva_obj = datetime.strptime(fecha_reserva_str, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        fecha_reserva_obj = datetime.strptime(fecha_reserva_str, '%d/%m/%Y').date()
                    except ValueError:
                        fecha_reserva_obj = datetime.now().date()
            else:
                fecha_reserva_obj = datetime.now().date()
            
            # Método de pago
            metodo_pago = data.get('metodo_pago', 'qr')
            
            # Insertar en pagos_qr
            query = """
                INSERT INTO pagos_qr (
                    id_residente, id_concepto, monto, descripcion, codigo_qr,
                    fecha_generacion, fecha_expiracion, metodo_pago, comprobante,
                    img_boucher, horas, fecha_reserva, observaciones
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id_pago
            """
            
            valores = (
                id_residente,
                concepto_id,
                monto,
                f"Reserva de {data['nombre_area']} para {data['fecha']} - {horas} hora(s)",
                codigo_qr,
                datetime.now(),
                datetime.now() + timedelta(hours=24),
                metodo_pago,
                data.get('comprobante', f"{metodo_pago.upper()}_{int(datetime.now().timestamp())}"),
                boucher_filename,
                horas,
                fecha_reserva_obj,
                f"Reserva móvil - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            
            print(f"🚀 [RESIDENTEMOVIL] Ejecutando inserción...")
            cursor.execute(query, valores)
            pago_id = cursor.fetchone()[0]
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ [RESIDENTEMOVIL] Reserva REAL insertada en BD. ID: {pago_id}")
            
            return jsonify({
                'success': True, 
                'pago_id': pago_id,
                'message': 'Reserva procesada exitosamente',
                'residente': {
                    'id': id_residente,
                    'piso': piso,
                    'departamento': nro_departamento
                },
                'user_id': user_id,
                'modo': 'bd_real'
            })
            
        except Exception as db_error:
            print(f"❌ [RESIDENTEMOVIL] Error en BD: {db_error}")
            # Si hay error en BD, retornar simulación
            pago_id = int(datetime.now().timestamp())
            
            return jsonify({
                'success': True, 
                'pago_id': pago_id,
                'message': 'Reserva procesada en modo simulación (error BD)',
                'user_id': user_id,
                'modo': 'simulacion_error_bd'
            })
        
    except Exception as e:
        logger.error(f"Error procesando reserva móvil: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False, 
            'message': f'Error al procesar reserva: {str(e)}'
        }), 500

@residentemovil_bp.route('/api/generar_factura/<int:pago_id>')
def generar_factura_movil(pago_id):
    """Generar factura - VERSIÓN CON VALIDACIÓN MANUAL"""
    try:
        # Validación manual del token
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        print(f"🧾 [RESIDENTEMOVIL] Generando factura para pago {pago_id}, usuario {user_id}")
        
        # Obtener datos del usuario para la factura
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.nombre, u.ap_paterno, u.ap_materno, u.ci, r.piso, r.nro_departamento
            FROM usuario u
            JOIN residente r ON u.id_usuario = r.id_usuario
            WHERE u.id_usuario = %s
        """, (user_id,))
        
        usuario_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if usuario_data:
            nombre, ap_paterno, ap_materno, ci, piso, depto = usuario_data
            nombre_completo = f"{nombre} {ap_paterno or ''} {ap_materno or ''}".strip()
            departamento = f"Piso {piso} - Dpto {depto}"
        else:
            nombre_completo = "Residente Móvil"
            ci = "1234567"
            departamento = "Piso X - Dpto Y"

        # Factura de ejemplo
        factura_data = {
            'numero_factura': f"FAC-MOVIL-{pago_id:06d}",
            'fecha_emision': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'cliente': {
                'nombre': nombre_completo,
                'ci': ci,
                'departamento': departamento
            },
            'concepto': 'Reserva de Área Común',
            'monto': 350.00,
            'metodo_pago': 'qr',
            'estado': 'CONFIRMADO',
            'qr_data': f'RESERVA_{pago_id}',
            'user_id': user_id
        }
        
        return jsonify({
            'success': True,
            'factura': factura_data
        })
        
    except Exception as e:
        logger.error(f"Error generando factura móvil: {e}")
        return jsonify({
            'success': False,
            'message': 'Error generando factura'
        }), 500

@residentemovil_bp.route('/api/horarios_areas')
def horarios_areas_movil():
    """Obtener horarios de áreas - VERSIÓN CON VALIDACIÓN MANUAL"""
    try:
        # Validación manual del token
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        print(f"📱 [RESIDENTEMOVIL] Obteniendo horarios para usuario: {user_id}")
        
        horarios = {
            'salon': 'Lunes a Domingo: 8:00 - 22:00',
            'piscina': 'Martes a Domingo: 9:00 - 19:00', 
            'gimnasio': 'Lunes a Sábado: 6:00 - 22:00',
            'parqueo': 'Todos los días: 24 horas'
        }
        
        return jsonify({
            'success': True,
            'horarios': horarios,
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo horarios: {e}")
        return jsonify({
            'success': False,
            'message': 'Error obteniendo horarios'
        }), 500

# ===== ENDPOINT DE DEBUG JWT =====

@residentemovil_bp.route('/api/debug_jwt')
def debug_jwt():
    """Endpoint para debuggear JWT"""
    try:
        auth_header = request.headers.get('Authorization', '')
        print(f"🔐 [DEBUG JWT] Auth Header: {auth_header}")
        
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'message': 'No Bearer token found',
                'auth_header': auth_header
            }), 401
            
        token = auth_header[7:]
        
        # Probar con PyJWT
        try:
            secret_key = current_app.config.get('JWT_SECRET_KEY', 'NO_CONFIGURADO')
            decoded = pyjwt.decode(token, secret_key, algorithms=['HS256'])
            
            return jsonify({
                'success': True,
                'message': '✅ JWT válido en residentemovil',
                'decoded': decoded,
                'secret_key_used': secret_key[:10] + '...',
                'user_id': decoded.get('sub'),
                'token_length': len(token)
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'❌ JWT inválido: {str(e)}',
                'secret_key_used': secret_key[:10] + '...' if secret_key != 'NO_CONFIGURADO' else 'NO_CONFIGURADO',
                'token_length': len(token)
            }), 422
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error en debug: {str(e)}'
        }), 500

# ===== ENDPOINTS PÚBLICOS (sin autenticación) =====

@residentemovil_bp.route('/api/public/test')
def test_publico():
    """Endpoint público para pruebas de conexión"""
    return jsonify({
        'success': True,
        'message': '✅ Endpoint móvil funcionando',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0-jwt-manual'
    })

@residentemovil_bp.route('/api/public/areas')
def areas_publicas():
    """Áreas disponibles sin autenticación (para desarrollo)"""
    return jsonify({
        'success': True,
        'areas': [
            {
                'id': 'salon',
                'nombre': 'Salón de Eventos',
                'precio': 350.00,
                'disponible': True
            },
            {
                'id': 'piscina',
                'nombre': 'Piscina', 
                'precio': 200.00,
                'disponible': True
            }
        ]
    })

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

# ===== ENDPOINT PARA RENOVAR TOKEN =====

@residentemovil_bp.route('/api/renovar_token', methods=['POST'])
def renovar_token():
    """Renovar token JWT"""
    try:
        # Validación manual del token actual
        user_id, error_response, status_code = validate_jwt_token()
        if error_response:
            return error_response, status_code
        
        # Crear nuevo token
        from flask_jwt_extended import create_access_token
        nuevo_token = create_access_token(
            identity=user_id,
            expires_delta=timedelta(days=7)
        )
        
        return jsonify({
            'success': True,
            'token': nuevo_token,
            'message': 'Token renovado exitosamente',
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Error renovando token: {e}")
        return jsonify({
            'success': False,
            'message': 'Error renovando token'
        }), 500