# routes/residentes.py - Blueprint corregido para residentes
# routes/residentes.py - Blueprint corregido para residentes
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from db import get_db_connection

# 🚫 COMENTAR O ELIMINAR ESTA LÍNCA
# from models import Departamento

import json
import logging
import os
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)

# CORREGIDO: Solo un blueprint
residentes_bp = Blueprint('residentes', __name__, url_prefix='/residente')

# Configuración para subida de archivos
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
UPLOAD_FOLDER = 'static/uploads/bouchers'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

# Helper functions
def get_rol_usuario():
    """Obtiene el rol del usuario actual"""
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
    """Obtiene los datos del residente actual"""
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
    """Obtiene el departamento del usuario actual"""
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
    """Obtiene consumos del mes actual"""
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

# ===== FUNCIONES PARA TICKETS =====

def obtener_areas():
    """Función auxiliar para obtener áreas comunes activas"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_area, nombre 
            FROM area 
            WHERE activo = true 
            ORDER BY nombre
        """)
        areas = cursor.fetchall()
        cursor.close()
        conn.close()
        return areas
    except Exception as e:
        print(f"Error obteniendo áreas: {str(e)}")
        return []

def obtener_residente_actual():
    """Obtiene la información del residente actual"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_residente, piso, nro_departamento 
            FROM residente 
            WHERE id_usuario = %s
        """, (get_user_id(),))
        residente = cursor.fetchone()
        cursor.close()
        conn.close()
        return residente
    except Exception as e:
        print(f"Error obteniendo residente: {str(e)}")
        return None

def obtener_id_departamento(residente):
    """Obtiene el ID del departamento basado en piso y número"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_departamento 
            FROM departamento 
            WHERE piso = %s AND nro = %s
        """, (residente[1], residente[2]))
        departamento = cursor.fetchone()
        cursor.close()
        conn.close()
        return departamento[0] if departamento else None
    except Exception as e:
        print(f"Error obteniendo departamento: {str(e)}")
        return None

def _validar_ticket_residente(id_ticket):
    """Valida que el ticket pertenece al residente actual"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id_ticket 
            FROM ticket t
            JOIN departamento d ON t.id_departamento = d.id_departamento
            JOIN residente r ON d.piso = r.piso AND d.nro = r.nro_departamento
            WHERE t.id_ticket = %s AND r.id_usuario = %s
        """, (id_ticket, get_user_id()))
        
        ticket_valido = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return bool(ticket_valido)
    except Exception as e:
        print(f"Error validando ticket: {str(e)}")
        return False

def _formatear_tickets(tickets):
    """Convierte los resultados de la consulta en una lista de diccionarios"""
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
            'area_nombre': ticket[11]
        })
    return tickets_list

# ===== RUTAS PRINCIPALES =====

@residentes_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        # DEBUG: Ver qué tiene current_user
        debug_current_user()
        
        # Primero verificar que el usuario sea residente
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

# ===== RUTAS PARA TICKETS =====

@residentes_bp.route('/crear_ticket', methods=['GET', 'POST'])
@login_required
def crear_ticket():
    """Ruta para crear nuevo ticket - CORREGIDA"""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            descripcion = request.form.get('descripcion')
            prioridad = request.form.get('prioridad')
            id_area = request.form.get('id_area')
            id_departamento = request.form.get('id_departamento')
            
            # Validar campos obligatorios
            if not all([descripcion, prioridad, id_area, id_departamento]):
                flash('Todos los campos son obligatorios', 'danger')
                return redirect(url_for('residentes.crear_ticket'))
            
            # Obtener datos del residente para el departamento
            residente = get_residente_data()
            if not residente:
                flash('No se encontraron datos del residente', 'danger')
                return redirect(url_for('residentes.crear_ticket'))
            
            # Crear nuevo ticket usando conexión directa
            conn = get_db_connection()
            if not conn:
                flash('Error de conexión a la base de datos', 'danger')
                return redirect(url_for('residentes.crear_ticket'))
                
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ticket (descripcion, prioridad, estado, id_area, id_departamento, fecha_emision)
                VALUES (%s, %s, 'abierto', %s, %s, NOW())
                RETURNING id_ticket
            """, (descripcion, prioridad, id_area, id_departamento))
            
            ticket_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Ticket creado exitosamente', 'success')
            return redirect(url_for('residentes.mis_tickets'))
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            logger.error(f"Error al crear el ticket: {str(e)}")
            flash(f'Error al crear el ticket: {str(e)}', 'danger')
            return redirect(url_for('residentes.crear_ticket'))
    
    # Método GET - mostrar formulario
    try:
        # Obtener áreas y departamentos para los dropdowns
        areas = obtener_areas()
        departamentos = Departamento.query.all() if hasattr(Departamento, 'query') else []
        
        # Si no funciona SQLAlchemy, obtener departamentos manualmente
        if not departamentos:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id_departamento, piso, nro FROM departamento")
                departamentos = cursor.fetchall()
                cursor.close()
                conn.close()
        
        return render_template("residente/crear_ticket.html",
                             areas=areas,
                             departamentos=departamentos)
    except Exception as e:
        logger.error(f"Error al cargar el formulario: {str(e)}")
        flash(f'Error al cargar el formulario: {str(e)}', 'danger')
        return redirect(url_for('residentes.dashboard'))

@residentes_bp.route("/mis_tickets")
@login_required
def mis_tickets():
    """Mostrar todos los tickets del residente actual - CORREGIDA"""
    if current_user.id_rol != 3:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
                a.nombre as area_nombre
            FROM ticket t
            JOIN departamento d ON t.id_departamento = d.id_departamento
            JOIN residente r ON d.piso = r.piso AND d.nro = r.nro_departamento
            LEFT JOIN empleado e ON t.id_empleado = e.id_empleado
            LEFT JOIN usuario u ON e.id_usuario = u.id_usuario
            LEFT JOIN area a ON t.id_area = a.id_area
            WHERE r.id_usuario = %s
            ORDER BY t.fecha_emision DESC
        """, (get_user_id(),))
        
        tickets = cursor.fetchall()
        cursor.close()
        conn.close()
        
        tickets_list = _formatear_tickets(tickets)
        return render_template("residente/tickets.html", tickets=tickets_list)
        
    except Exception as e:
        print(f"Error obteniendo tickets: {str(e)}")
        flash("Error al cargar los tickets.", "danger")
        return render_template("residente/tickets.html", tickets=[])

@residentes_bp.route("/ticket/<int:id_ticket>/comentario", methods=["POST"])
@login_required
def agregar_comentario_residente(id_ticket):
    """Agregar comentario a un ticket (solo público para residentes)"""
    if current_user.id_rol != 3:
        return jsonify({'error': 'Acceso no autorizado'}), 403
    
    mensaje = request.form.get('mensaje')
    if not mensaje:
        flash("El mensaje no puede estar vacío.", "danger")
        return redirect(url_for("residentes.mis_tickets"))
    
    if not _validar_ticket_residente(id_ticket):
        flash("Ticket no válido.", "danger")
        return redirect(url_for("residentes.mis_tickets"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO comentario_ticket 
            (id_ticket, id_usuario, mensaje, fecha_creacion, es_interno)
            VALUES (%s, %s, %s, NOW(), false)
        """, (id_ticket, get_user_id(), mensaje))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Comentario agregado correctamente.", "success")
        return redirect(url_for("residentes.mis_tickets"))
        
    except Exception as e:
        print(f"Error agregando comentario: {str(e)}")
        flash("Error al agregar comentario.", "danger")
        return redirect(url_for("residentes.mis_tickets"))

# ===== OTRAS RUTAS EXISTENTES (mantener igual) =====

@residentes_bp.route('/facturacion')
@login_required
def facturacion():
    # ... (mantener el código existente)
    pass

@residentes_bp.route('/consumos')
@login_required
def consumos():
    # ... (mantener el código existente)
    pass

@residentes_bp.route('/perfil')
@login_required
def perfil():
    # ... (mantener el código existente)
    pass

@residentes_bp.route('/politicas')
@login_required
def politicas():
    # ... (mantener el código existente)
    pass

@residentes_bp.route('/reservas')
@login_required
def reservas():
    # ... (mantener el código existente)
    pass

# ===== API ENDPOINTS (mantener igual) =====

@residentes_bp.route('/api/crear_solicitud', methods=['POST'])
@login_required
def crear_solicitud():
    # ... (mantener el código existente)
    pass

# ... (mantener el resto de las rutas API)

# ===== ERROR HANDLERS =====

@residentes_bp.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@residentes_bp.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500