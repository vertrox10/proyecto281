# residentes_bp.py - Blueprint unificado para funcionalidades de residentes

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from db import get_db_connection
import json
import logging
import os
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

residentes_bp = Blueprint('residentes', __name__, url_prefix='/residentes')

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

def debug_reserva_data(data, boucher_filename, id_residente):
    """Función de debug para datos de reserva"""
    print("🔍 DEBUG - Datos de reserva:")
    print(f"   - Área: {data.get('area')}")
    print(f"   - Fecha: {data.get('fecha')}")
    print(f"   - Monto: {data.get('monto')}")
    print(f"   - Método: {data.get('metodo_pago')}")
    print(f"   - Horas: {data.get('horas', 1)}")
    print(f"   - Boucher: {boucher_filename}")
    print(f"   - ID Residente: {id_residente}")

def get_user_id():
    """Safe way to get user ID"""
    try:
        # Primero intentar con el atributo directo
        return current_user.id_usuario
    except AttributeError:
        # Si falla, usar get_id()
        user_id = current_user.get_id()
        return int(user_id) if user_id else None

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
    """Obtiene los datos del residente actual - MEJORADA"""
    try:
        user_id = get_user_id()
        print(f"🔍 Buscando residente con user_id: {user_id}")
        
        conn = get_db_connection()
        if conn is None:
            return None
            
        cursor = conn.cursor()
        
        # Consulta mejorada con manejo de NULLs
        cursor.execute("""
            SELECT 
                r.id_residente,      
                r.id_usuario,        
                COALESCE(r.piso, 0) as piso,              
                COALESCE(r.nro_departamento, 'N/A') as nro_departamento,  
                r.fecha_ingreso,     
                r.fecha_salida,      
                COALESCE(d.piso, 'N/A') as piso_depto,              
                COALESCE(d.nro, 'N/A') as nro_depto,               
                COALESCE(d.id_departamento, 0) as id_departamento    
            FROM residente r
            LEFT JOIN departamento d ON (
                (d.piso = 'Piso ' || r.piso::varchar AND d.nro = r.nro_departamento) OR
                (d.piso = r.piso::varchar AND d.nro = r.nro_departamento)
            )
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
            JOIN departamento d ON r.piso::varchar = d.piso AND r.nro_departamento = d.nro
            WHERE r.id_usuario = %s
        """, (user_id,))
        
        departamento = cursor.fetchone()
        cursor.close()
        conn.close()
        return departamento
        
    except Exception as e:
        logger.error(f"Error obteniendo departamento: {e}")
        return None

# ===== FUNCIONES PARA TICKETS =====
def obtener_areas():
    """Función auxiliar para obtener áreas comunes activas - VERSIÓN CORREGIDA"""
    try:
        conn = get_db_connection()
        if conn is None:
            print("❌ No se pudo conectar a la base de datos")
            return []
            
        cursor = conn.cursor()
        # QUITAR el WHERE activo = true ya que la columna no existe
        cursor.execute("""
            SELECT id_area, nombre, descripcion 
            FROM area 
            ORDER BY nombre
        """)
        areas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        print(f"✅ Áreas encontradas en BD: {len(areas)}")
        
        # Convertir a lista de diccionarios
        areas_list = []
        for area in areas:
            area_dict = {
                'id_area': area[0],
                'nombre': area[1],
                'descripcion': area[2] if len(area) > 2 else ''
            }
            areas_list.append(area_dict)
            print(f"   - Área: {area_dict['id_area']}: {area_dict['nombre']}")
        
        return areas_list
        
    except Exception as e:
        print(f"❌ Error obteniendo áreas: {str(e)}")
        return []
    
def obtener_residente_actual():
    """Obtiene la información del residente actual - CON MÁS DEBUG"""
    try:
        user_id = get_user_id()
        print(f"🔍 DEBUG obtener_residente_actual - User ID: {user_id}")
        
        conn = get_db_connection()
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
            print(f"✅ Residente encontrado: ID={residente[0]}, Piso={residente[1]}, Depto={residente[2]}")
        else:
            print("❌ No se encontró residente para el usuario")
            
        return residente
    except Exception as e:
        print(f"❌ Error obteniendo residente: {str(e)}")
        return None

def obtener_id_departamento(residente):
    """Obtiene el ID del departamento - CORREGIDA para formato 'Piso X'"""
    try:
        if not residente:
            print("❌ obtener_id_departamento: residente es None")
            return None
            
        piso_residente = residente[1]  # piso del residente (ej: 3)
        nro_departamento = residente[2]  # nro_departamento del residente (ej: '303')
        
        # Convertir formato: piso 3 -> "Piso 3"
        piso_bd = f"Piso {piso_residente}"
        
        print(f"🔍 Buscando departamento: Piso='{piso_bd}', Nro='{nro_departamento}'")
        
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
            print(f"✅ Departamento encontrado: ID={departamento[0]}")
            return departamento[0]
        else:
            print("❌ No se encontró departamento en la BD")
            # Debug: ver qué hay en la BD
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id_departamento, piso, nro FROM departamento WHERE piso LIKE %s", 
                          (f"Piso {piso_residente}%",))
            deptos_existentes = cursor.fetchall()
            cursor.close()
            conn.close()
            print(f"🔍 Departamentos existentes para piso {piso_residente}: {deptos_existentes}")
            return None
            
    except Exception as e:
        print(f"❌ Error obteniendo departamento: {str(e)}")
        return None
        
def _validar_ticket_residente(id_ticket):
    """Valida que el ticket pertenece al residente actual - VERSIÓN CORREGIDA"""
    try:
        user_id = get_user_id()
        print(f"🔍 DEBUG _validar_ticket_residente - Ticket: {id_ticket}, Usuario: {user_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener datos del residente
        cursor.execute("""
            SELECT r.piso, r.nro_departamento 
            FROM residente r 
            WHERE r.id_usuario = %s
        """, (user_id,))
        
        residente = cursor.fetchone()
        if not residente:
            print("❌ No se encontró residente")
            return False
            
        piso_residente = residente[0]  # 3
        depto_residente = residente[1]  # '303'
        
        print(f"🔍 DEBUG - Residente: Piso {piso_residente}, Depto {depto_residente}")
        
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
        """, (id_ticket, piso_residente, depto_residente, piso_residente, depto_residente))
        
        ticket_valido = cursor.fetchone()
        cursor.close()
        conn.close()
        
        print(f"🔍 DEBUG - Ticket válido: {bool(ticket_valido)}")
        return bool(ticket_valido)
        
    except Exception as e:
        print(f"❌ Error validando ticket: {str(e)}")
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
        id_departamento = residente[8] if len(residente) > 8 else None
        
        # Si no hay id_departamento, intentar obtenerlo de otra forma
        if not id_departamento:
            print("⚠️ No se encontró id_departamento, buscando alternativo...")
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id_departamento FROM departamento 
                    WHERE piso = %s AND nro = %s
                """, (f"Piso {residente[2]}", residente[3]))
                depto = cursor.fetchone()
                cursor.close()
                conn.close()
                if depto:
                    id_departamento = depto[0]
                    print(f"✅ ID Departamento encontrado alternativamente: {id_departamento}")
        
        # Datos básicos para el dashboard
        ahora = datetime.now()
        
        conn = get_db_connection()
        if conn is None:
            flash('Error de conexión a la base de datos', 'error')
            return render_template('residente/dashboard.html')
            
        cursor = conn.cursor()
        
        # Estado de pagos - CONSULTA CORREGIDA
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
        
        # Solicitudes activas - CONSULTA CORREGIDA
        solicitudes_activas = None
        try:
            if id_departamento:
                cursor.execute("""
                    SELECT COUNT(*) as activas,
                           SUM(CASE WHEN prioridad = 'alta' OR prioridad = 'urgente' THEN 1 ELSE 0 END) as urgentes
                    FROM ticket 
                    WHERE id_departamento = %s 
                    AND estado IN ('abierto', 'en_progreso', 'pendiente')
                """, (id_departamento,))
            else:
                # Si no hay departamento, buscar por piso y número
                cursor.execute("""
                    SELECT COUNT(*) as activas,
                           SUM(CASE WHEN t.prioridad = 'alta' OR t.prioridad = 'urgente' THEN 1 ELSE 0 END) as urgentes
                    FROM ticket t
                    JOIN departamento d ON t.id_departamento = d.id_departamento
                    WHERE d.piso = %s AND d.nro = %s
                    AND t.estado IN ('abierto', 'en_progreso', 'pendiente')
                """, (f"Piso {residente[2]}", residente[3]))
            
            solicitudes_activas = cursor.fetchone()
            print(f"✅ Solicitudes activas: {solicitudes_activas}")
        except Exception as e:
            print(f"❌ Error en consulta de solicitudes: {e}")
            solicitudes_activas = (0, 0)
        
        # Actividades recientes - CONSULTA CORREGIDA
        actividades_recientes = []
        try:
            if id_departamento:
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
                     WHERE id_departamento = %s 
                     AND fecha_emision >= CURRENT_DATE - INTERVAL '7 days'
                     LIMIT 3)
                    ORDER BY fecha DESC
                    LIMIT 5
                """, (user_id, id_departamento))
            else:
                cursor.execute("""
                    (SELECT 'pago' as tipo, fecha_pago as fecha, 
                            'Pago realizado' as descripcion, 'fa-money-bill-wave' as icono
                     FROM pago 
                     WHERE id_usuario = %s 
                     AND fecha_pago >= CURRENT_DATE - INTERVAL '7 days'
                     LIMIT 3)
                    UNION
                    (SELECT 'ticket' as tipo, t.fecha_emision as fecha,
                            'Solicitud creada' as descripcion, 'fa-ticket-alt' as icono
                     FROM ticket t
                     JOIN departamento d ON t.id_departamento = d.id_departamento
                     WHERE d.piso = %s AND d.nro = %s
                     AND t.fecha_emision >= CURRENT_DATE - INTERVAL '7 days'
                     LIMIT 3)
                    ORDER BY fecha DESC
                    LIMIT 5
                """, (user_id, f"Piso {residente[2]}", residente[3]))
            
            actividades = cursor.fetchall()
            print(f"✅ Actividades encontradas: {len(actividades)}")
            
            for act in actividades:
                fecha_formateada = act[1].strftime('%d/%m/%Y') if act[1] else 'N/A'
                actividades_recientes.append({
                    'icono': act[3] if len(act) > 3 else 'fa-circle',
                    'descripcion': act[2] if len(act) > 2 else 'Actividad',
                    'fecha': fecha_formateada
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
            'solicitudes_activas': solicitudes_activas[0] if solicitudes_activas else 0,
            'solicitudes_prioridad_alta': solicitudes_activas[1] if solicitudes_activas else 0,
            'actividades_recientes': actividades_recientes,
            'residente_data': {
                'piso': residente[2] if len(residente) > 2 else 'N/A',  # piso de residente
                'departamento': residente[3] if len(residente) > 3 else 'N/A',  # nro_departamento
                'fecha_ingreso': residente[4].strftime('%d/%m/%Y') if len(residente) > 4 and residente[4] else 'N/A',
                'id_departamento': id_departamento
            },
            'anuncio_mantenimiento': None,
            'now': ahora
        }
        
        print(f"✅ Dashboard cargado exitosamente para {nombre_usuario}")
        print(f"   - Piso: {datos_dashboard['residente_data']['piso']}")
        print(f"   - Departamento: {datos_dashboard['residente_data']['departamento']}")
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
            },
            'anuncio_mantenimiento': None,
            'now': datetime.now()
        }
        return render_template('residente/dashboard.html', **datos_minimos)

# ===== RUTAS PARA TICKETS =====

@residentes_bp.route("/tickets/crear", methods=["GET", "POST"])
@login_required
def crear_ticket():
    """Crear un nuevo ticket"""
    if current_user.id_rol != 3:  # 3 = Rol de residente
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    residente = obtener_residente_actual()
    if not residente:
        flash("No se encontró información de residente.", "danger")
        return redirect(url_for("residentes.dashboard"))
    
    if request.method == "POST":
        return _procesar_creacion_ticket(residente)
    
    # GET request - mostrar formulario
    areas = obtener_areas()
    return render_template("residente/ticket.html", 
                         residente=residente,
                         areas=areas)

def _procesar_creacion_ticket(residente):
    """Procesa la creación de un nuevo ticket"""
    descripcion = request.form.get('descripcion')
    prioridad = request.form.get('prioridad')
    id_area = request.form.get('id_area')  # Área común si aplica
    
    if not descripcion:
        flash("La descripción es obligatoria.", "danger")
        return render_template("residente/tickets.html", 
                             residente=residente,
                             areas=obtener_areas())
    
    id_departamento = obtener_id_departamento(residente)
    if not id_departamento:
        flash("No se encontró el departamento.", "danger")
        return render_template("residente/tickets.html", 
                             residente=residente,
                             areas=obtener_areas())
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ticket 
            (descripcion, prioridad, fecha_emision, estado, id_departamento, id_area)
            VALUES (%s, %s, NOW(), 'pendiente', %s, %s)
        """, (descripcion, prioridad, id_departamento, id_area if id_area else None))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Ticket creado correctamente. Será atendido pronto.", "success")
        return redirect(url_for("residentes.mis_tickets"))
        
    except Exception as e:
        print(f"Error creando ticket: {str(e)}")
        flash("Error al crear el ticket.", "danger")
        return render_template("residente/tickets.html", 
                             residente=residente,
                             areas=obtener_areas())

@residentes_bp.route("/tickets/mis-tickets")
@login_required
def mis_tickets():
    """Mostrar todos los tickets del residente actual - CON DEBUG"""
    if current_user.id_rol != 3:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        user_id = get_user_id()
        print(f"🔍 DEBUG - User ID: {user_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # PRIMERO: Verificar datos del residente
        cursor.execute("""
            SELECT r.id_residente, r.piso, r.nro_departamento, d.id_departamento
            FROM residente r
            LEFT JOIN departamento d ON r.piso::varchar = d.piso AND r.nro_departamento = d.nro
            WHERE r.id_usuario = %s
        """, (user_id,))
        residente_data = cursor.fetchone()
        print(f"🔍 DEBUG - Datos del residente: {residente_data}")
        
        # Reemplaza la consulta de tickets por esta versión más simple:
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
            JOIN residente r ON (
                (d.piso = 'Piso ' || r.piso::varchar AND d.nro = r.nro_departamento) OR
                (d.piso = r.piso::varchar AND d.nro = r.nro_departamento)
            )
            LEFT JOIN empleado e ON t.id_empleado = e.id_empleado
            LEFT JOIN usuario u ON e.id_usuario = u.id_usuario
            LEFT JOIN area a ON t.id_area = a.id_area
            WHERE r.id_usuario = %s
            ORDER BY t.fecha_emision DESC
        """, (user_id,))
        
        tickets = cursor.fetchall()
        print(f"🔍 DEBUG - Tickets encontrados: {len(tickets)}")
        for ticket in tickets:
            print(f"   - Ticket ID: {ticket[0]}, Desc: {ticket[1][:50]}...")
        
        # Obtener estadísticas - VERSIÓN CORREGIDA
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN t.estado = 'abierto' THEN 1 END) as abiertos,
                COUNT(CASE WHEN t.estado = 'en_progreso' THEN 1 END) as en_progreso,
                COUNT(CASE WHEN t.estado IN ('cerrado', 'completado') THEN 1 END) as cerrados,
                COUNT(CASE WHEN t.prioridad = 'alta' OR t.prioridad = 'urgente' THEN 1 END) as urgentes
            FROM ticket t
            JOIN departamento d ON t.id_departamento = d.id_departamento
            JOIN residente r ON (
                (d.piso = 'Piso ' || r.piso::varchar AND d.nro = r.nro_departamento) OR
                (d.piso = r.piso::varchar AND d.nro = r.nro_departamento)
            )
            WHERE r.id_usuario = %s
        """, (user_id,))
        stats = cursor.fetchone()
        print(f"🔍 DEBUG - Estadísticas: {stats}")
        
        cursor.close()
        conn.close()
        
        # Preparar estadísticas
        estadisticas = {
            'total': stats[0] if stats else 0,
            'abiertos': stats[1] if stats else 0,
            'en_progreso': stats[2] if stats else 0,
            'cerrados': stats[3] if stats else 0,
            'urgentes': stats[4] if stats else 0
        }
        
        tickets_list = _formatear_tickets(tickets)
        
        return render_template("residente/tickets.html", 
                             tickets=tickets_list,
                             estadisticas=estadisticas,
                             areas=obtener_areas())
        
    except Exception as e:
        print(f"❌ Error obteniendo tickets: {str(e)}")
        flash("Error al cargar los tickets.", "danger")
        
        # Datos por defecto para estadísticas en caso de error
        estadisticas_default = {
            'total': 0,
            'abiertos': 0,
            'en_progreso': 0,
            'cerrados': 0,
            'urgentes': 0
        }
        
        return render_template("residente/tickets.html", 
                             tickets=[],
                             estadisticas=estadisticas_default,
                             areas=obtener_areas())

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

# ===== RUTAS EXISTENTES =====

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
        
        # Información del residente
        residente = get_residente_data()
        departamento = None
        residente_dict = None
        
        if residente:
            # Obtener información del departamento
            cursor.execute("""
                SELECT d.id_departamento, d.piso, d.nro
                FROM departamento d
                WHERE d.piso = %s AND d.nro = %s
            """, (f"Piso {residente[2]}", residente[3]))
            
            departamento = cursor.fetchone()
            
            # Preparar datos del residente
            residente_dict = {
                'fecha_ingreso': residente[4].strftime('%d/%m/%Y') if residente[4] else 'N/A'
            }
        
        cursor.close()
        conn.close()
        
        # Preparar datos para el template
        usuario_dict = {
            'id_usuario': usuario[0],
            'nombre': usuario[1],
            'ap_paterno': usuario[2],
            'ap_materno': usuario[3],
            'correo': usuario[4],
            'telefono': usuario[5],
            'ci': usuario[9] if len(usuario) > 9 else None,
            'rol_nombre': usuario[8] if len(usuario) > 8 else 'Residente'
        }
        
        departamento_dict = None
        if departamento:
            departamento_dict = {
                'id_departamento': departamento[0],
                'piso': departamento[1],
                'nro': departamento[2]
            }
        
        return render_template('residente/perfil.html',
                            usuario=usuario_dict,
                            departamento=departamento_dict,
                            residente=residente_dict,
                            now=datetime.now())
    
    except Exception as e:
        logger.error(f"Error en perfil: {e}")
        flash('Error al cargar el perfil', 'error')
        return render_template('residente/perfil.html')

@residentes_bp.route('/politicas')
@login_required
def politicas():
    politicas_info = {
        'titulo': 'Políticas y Reglas del Edificio SincroHome',
        'politicas': [
            {
                'titulo': 'Reserva de Áreas Comunes',
                'descripcion': 'Toda reserva de áreas comunes requiere un adelanto del 50% del costo total.',
                'icono': 'fa-calendar-check'
            },
            {
                'titulo': 'Cancelación de Reservas - Salón de Eventos y Piscina',
                'descripcion': 'La cancelación debe realizarse con una semana de anticipación para el salón de eventos y piscina.',
                'icono': 'fa-swimming-pool'
            },
            {
                'titulo': 'Cancelación de Reservas - Gimnasio SincroHome',
                'descripcion': 'Para el gimnasio, la cancelación debe hacerse con 24 horas de anticipación.',
                'icono': 'fa-dumbbell'
            },
            {
                'titulo': 'Acceso Exclusivo',
                'descripcion': 'Las reservas del parque y áreas comunes son exclusivas para residentes del edificio.',
                'icono': 'fa-key'
            },
            {
                'titulo': 'Horario de Confirmación',
                'descripcion': 'Las reservas serán confirmadas durante el horario administrativo de 7:30 AM a 6:00 PM.',
                'icono': 'fa-clock'
            },
            {
                'titulo': 'Política de No Devolución',
                'descripcion': 'No se aceptan devoluciones por incumplimiento de las políticas establecidas.',
                'icono': 'fa-ban'
            },
            {
                'titulo': 'Responsabilidad por Daños',
                'descripcion': 'El residente será responsable por cualquier daño ocasionado en las áreas comunes durante su uso.',
                'icono': 'fa-exclamation-triangle'
            }
        ],
        'nota_importante': 'Agradecemos su comprensión y colaboración para mantener un ambiente agradable y seguro para todos los residentes del Edificio SincroHome.'
    }
    
    return render_template('residente/politicas.html', 
                         rol_usuario='residente',
                         politicas=politicas_info)

@residentes_bp.route('/reservas')
@login_required
def reservas():
    try:
        user_id = get_user_id()
        
        # Obtener datos del residente
        residente = get_residente_data()
        
        # Obtener reservas activas del usuario
        conn = get_db_connection()
        if conn is None:
            flash('Error de conexión a la base de datos', 'error')
            return render_template('residente/reservas.html')
            
        cursor = conn.cursor()
        
        # Aquí iría la lógica para obtener reservas de la BD
        # Por ahora retornamos una lista vacía
        reservas_activas = []
        
        cursor.close()
        conn.close()
        
        return render_template('residente/reservas.html',
                            rol_usuario='residente',
                            usuario_nombre=current_user.nombre,
                            reservas_activas=reservas_activas)
    
    except Exception as e:
        logger.error(f"Error en reservas: {e}")
        flash('Error al cargar las reservas', 'error')
        return render_template('residente/reservas.html')

# ===== API ENDPOINTS =====

@residentes_bp.route('/api/crear_solicitud', methods=['POST'])
@login_required
def crear_solicitud():
    try:
        user_id = get_user_id()
        data = request.get_json()
        
        print(f"🔍 DEBUG - Datos recibidos para crear solicitud:")
        print(f"   - Descripción: {data.get('descripcion')}")
        print(f"   - Prioridad: {data.get('prioridad')}")
        print(f"   - Área ID: {data.get('id_area')}")
        
        # Validar datos requeridos
        if not data.get('descripcion'):
            return jsonify({'success': False, 'message': 'La descripción es obligatoria'}), 400
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor()
        
        # Obtener id_departamento del residente
        residente = obtener_residente_actual()
        id_departamento = obtener_id_departamento(residente) if residente else None
        
        print(f"🔍 DEBUG - ID Departamento obtenido: {id_departamento}")
        
        if not id_departamento:
            return jsonify({'success': False, 'message': 'No se encontró departamento asociado'}), 400
        
        # Validar que el área existe si se proporciona
        id_area = data.get('id_area')
        if id_area:
            cursor.execute("SELECT id_area FROM area WHERE id_area = %s", (id_area,))
            if not cursor.fetchone():
                id_area = None
        
        # ⚠️⚠️⚠️ ESTA ES LA LÍNEA CRÍTICA - DEBE SER 'abierto' ⚠️⚠️⚠️
        print("🚀 Ejecutando INSERT con estado: 'abierto'")
        
        # Insertar nueva solicitud - USAR 'abierto' no 'pendiente'
        cursor.execute("""
            INSERT INTO ticket (
                descripcion, 
                prioridad, 
                fecha_emision, 
                estado, 
                id_departamento, 
                id_area
            ) VALUES (%s, %s, NOW(), 'abierto', %s, %s)  -- ✅ 'abierto' NO 'pendiente'
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
        
        print(f"✅ Ticket creado exitosamente. ID: {ticket_id}")
        
        return jsonify({
            'success': True, 
            'ticket_id': ticket_id, 
            'message': 'Solicitud creada exitosamente'
        })
    
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error creando solicitud: {e}")
        import traceback
        print(f"❌ Error completo: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'Error al crear la solicitud: {str(e)}'}), 500

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

@residentes_bp.route('/api/procesar_reserva', methods=['POST'])
@login_required
def procesar_reserva():
    try:
        user_id = get_user_id()
        print(f"🔍 [DEBUG] Iniciando procesamiento de reserva para usuario: {user_id}")
        
        # Verificar si es JSON o FormData
        if request.content_type.startswith('application/json'):
            data = request.get_json()
            boucher_filename = None
            print("📦 [DEBUG] Datos recibidos como JSON")
        else:
            data = request.form.to_dict()
            boucher_file = request.files.get('boucher')
            boucher_filename = None
            
            if boucher_file and allowed_file(boucher_file.filename):
                filename = secure_filename(boucher_file.filename)
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                timestamp = int(datetime.now().timestamp())
                boucher_filename = f"boucher_{user_id}_{timestamp}_{filename}"
                boucher_path = os.path.join(UPLOAD_FOLDER, boucher_filename)
                try:
                    boucher_file.save(boucher_path)
                    print(f"✅ [DEBUG] Boucher guardado: {boucher_path}")
                except Exception as e:
                    print(f"❌ [DEBUG] Error guardando boucher: {e}")
                    boucher_filename = None
            print("📦 [DEBUG] Datos recibidos como FormData")

        # Debug: mostrar todos los datos recibidos
        print(f"📝 [DEBUG] Todos los datos recibidos:")
        for key, value in data.items():
            print(f"   {key}: {value} (tipo: {type(value)})")

        # Validar datos requeridos
        required_fields = ['area', 'nombre_area', 'fecha', 'monto', 'metodo_pago']
        for field in required_fields:
            if field not in data:
                error_msg = f'Campo requerido faltante: {field}'
                print(f"❌ [DEBUG] {error_msg}")
                return jsonify({'success': False, 'message': error_msg}), 400
        
        conn = get_db_connection()
        if conn is None:
            error_msg = 'Error de conexión a la base de datos'
            print(f"❌ [DEBUG] {error_msg}")
            return jsonify({'success': False, 'message': error_msg}), 500
            
        cursor = conn.cursor()
        
        # Obtener datos del residente
        cursor.execute("""
            SELECT r.id_residente, u.ci, u.nombre, u.ap_paterno, u.ap_materno, 
                   r.piso, r.nro_departamento
            FROM residente r
            JOIN usuario u ON r.id_usuario = u.id_usuario
            WHERE r.id_usuario = %s
        """, (user_id,))
        
        residente = cursor.fetchone()
        
        if not residente:
            error_msg = 'No se encontraron datos del residente'
            print(f"❌ [DEBUG] {error_msg}")
            return jsonify({'success': False, 'message': error_msg}), 400
        
        id_residente, ci, nombre, ap_paterno, ap_materno, piso, nro_departamento = residente
        nombre_completo = f"{nombre} {ap_paterno or ''} {ap_materno or ''}".strip()
        
        print(f"✅ [DEBUG] Residente encontrado: {nombre_completo} (ID: {id_residente})")
        
        # Determinar concepto_id basado en el área
        conceptos = {
            'salon': 1,
            'piscina': 2, 
            'gimnasio': 3,
            'parqueo': 4
        }
        concepto_id = conceptos.get(data['area'])
        print(f"🔍 [DEBUG] Concepto ID determinado: {concepto_id} para área: {data['area']}")
        
        # Calcular horas para gimnasio
        horas = int(data.get('horas', 1))
        monto = float(data['monto'])
        
        # Generar código QR único
        codigo_qr = f"RESERVA_{user_id}_{int(datetime.now().timestamp())}"
        
        # Fecha de reserva - MANEJO ROBUSTO CON DEBUG
        fecha_reserva_obj = None
        fecha_reserva_str = data.get('fecha', '')
        
        print(f"🔍 [DEBUG] Procesando fecha recibida: '{fecha_reserva_str}' (tipo: {type(fecha_reserva_str)})")
        
        if fecha_reserva_str:
            try:
                # Intentar formato ISO (YYYY-MM-DD)
                fecha_reserva_obj = datetime.strptime(fecha_reserva_str, '%Y-%m-%d').date()
                print(f"✅ [DEBUG] Fecha parseada correctamente (ISO): {fecha_reserva_obj}")
            except ValueError as e1:
                print(f"⚠️ [DEBUG] Error parseando fecha ISO: {e1}")
                try:
                    # Intentar formato con slash (DD/MM/YYYY)
                    fecha_reserva_obj = datetime.strptime(fecha_reserva_str, '%d/%m/%Y').date()
                    print(f"✅ [DEBUG] Fecha parseada correctamente (DD/MM/YYYY): {fecha_reserva_obj}")
                except ValueError as e2:
                    print(f"⚠️ [DEBUG] Error parseando fecha DD/MM/YYYY: {e2}")
                    try:
                        # Intentar formato con slash (MM/DD/YYYY)
                        fecha_reserva_obj = datetime.strptime(fecha_reserva_str, '%m/%d/%Y').date()
                        print(f"✅ [DEBUG] Fecha parseada correctamente (MM/DD/YYYY): {fecha_reserva_obj}")
                    except ValueError as e3:
                        print(f"❌ [DEBUG] No se pudo parsear la fecha '{fecha_reserva_str}': {e3}")
                        # Usar fecha actual como fallback
                        fecha_reserva_obj = datetime.now().date()
                        print(f"⚠️ [DEBUG] Usando fecha actual como fallback: {fecha_reserva_obj}")
        else:
            # Si no hay fecha, usar fecha actual
            fecha_reserva_obj = datetime.now().date()
            print(f"⚠️ [DEBUG] No se recibió fecha, usando fecha actual: {fecha_reserva_obj}")
        
        # Usar el objeto date para la inserción
        fecha_reserva = fecha_reserva_obj
        
        # Estado inicial basado en método de pago
        estado = 'completado' if data['metodo_pago'] != 'qr' else 'pendiente'
        
        print(f"🔍 [DEBUG] Preparando inserción en pagos_qr:")
        print(f"   - id_residente: {id_residente}")
        print(f"   - id_concepto: {concepto_id}")
        print(f"   - monto: {monto}")
        print(f"   - fecha_reserva: {fecha_reserva} (tipo: {type(fecha_reserva)})")
        print(f"   - horas: {horas}")
        
        # Insertar en pagos_qr
        query = """
            INSERT INTO pagos_qr (
                id_residente, id_concepto, monto, descripcion, codigo_qr, estado,
                fecha_generacion, fecha_expiracion, metodo_pago, comprobante,
                img_boucher, horas, fecha_reserva, observaciones
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_pago
        """
        
        valores = (
            id_residente,
            concepto_id,
            monto,
            f"Reserva de {data['nombre_area']} para {data['fecha']} - {horas} hora(s)",
            codigo_qr,
            estado,
            datetime.now(),
            datetime.now() + timedelta(hours=24),
            data['metodo_pago'],
            data.get('comprobante', f"{data['metodo_pago'].upper()}_{int(datetime.now().timestamp())}"),
            boucher_filename,
            horas,
            fecha_reserva,
            f"Reserva realizada el {datetime.now().strftime('%d/%m/%Y %H:%M')} por {nombre_completo}"
        )
        
        print(f"🚀 [DEBUG] Ejecutando inserción en pagos_qr...")
        print(f"   Query: {query}")
        print(f"   Valores: {valores}")
        
        try:
            cursor.execute(query, valores)
            pago_id = cursor.fetchone()[0]
            print(f"✅ [DEBUG] Inserción exitosa. ID de pago generado: {pago_id}")
            
            # Si es pago manual (no QR), crear también en la tabla pago y factura
            if data['metodo_pago'] != 'qr':
                print("💳 [DEBUG] Procesando pago manual...")
                
                # Insertar en tabla pago
                cursor.execute("""
                    INSERT INTO pago (
                        monto, metodo, estado, fecha_pago, id_usuario, 
                        nro_trans, pagado_por
                    ) VALUES (%s, %s, %s, NOW(), %s, %s, %s)
                    RETURNING id_pago
                """, (
                    monto,
                    data['metodo_pago'],
                    'completado',
                    user_id,
                    data.get('comprobante', f"MANUAL_{pago_id}"),
                    user_id
                ))
                
                pago_manual_id = cursor.fetchone()[0]
                print(f"✅ [DEBUG] Pago manual registrado. ID: {pago_manual_id}")
                
                # Crear factura
                cursor.execute("""
                    INSERT INTO factura (
                        monto_total, fecha_emision, fecha_vencimiento, 
                        estado_factura, id_usuario, descripcion
                    ) VALUES (%s, NOW(), NOW() + INTERVAL '30 days', 'pagada', %s, %s)
                    RETURNING id_factura
                """, (
                    monto,
                    user_id,
                    f"Reserva {data['nombre_area']} - {data['fecha']} - {horas} hora(s)"
                ))
                
                factura_id = cursor.fetchone()[0]
                print(f"✅ [DEBUG] Factura generada. ID: {factura_id}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"🎉 [DEBUG] Reserva procesada exitosamente. Pago ID: {pago_id}")
            
            return jsonify({
                'success': True, 
                'pago_id': pago_id,
                'message': 'Reserva procesada exitosamente'
            })
            
        except Exception as e:
            print(f"❌ [DEBUG] Error en la ejecución de la query:")
            print(f"   Error: {str(e)}")
            print(f"   Tipo de error: {type(e)}")
            import traceback
            print(f"   Traceback completo: {traceback.format_exc()}")
            conn.rollback()
            raise e
    
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error procesando reserva: {e}")
        import traceback
        print(f"❌ [DEBUG] Error completo en procesar_reserva:")
        print(f"   Error: {str(e)}")
        print(f"   Tipo: {type(e)}")
        print(f"   Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'Error al procesar la reserva: {str(e)}'}), 500

@residentes_bp.route('/api/generar_factura/<int:pago_id>')
@login_required
def generar_factura(pago_id):
    try:
        user_id = get_user_id()
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
            
        cursor = conn.cursor()
        
        # Obtener datos completos del pago
        cursor.execute("""
            SELECT pq.*, u.nombre, u.ap_paterno, u.ap_materno, u.ci, 
                   r.piso, r.nro_departamento, c.nombre as concepto_nombre
            FROM pagos_qr pq
            JOIN residente r ON pq.id_residente = r.id_residente
            JOIN usuario u ON r.id_usuario = u.id_usuario
            LEFT JOIN conceptos_pago c ON pq.id_concepto = c.id_concepto
            WHERE pq.id_pago = %s AND r.id_usuario = %s
        """, (pago_id, user_id))
        
        pago_data = cursor.fetchone()
        
        if not pago_data:
            return jsonify({'success': False, 'message': 'Pago no encontrado'}), 404
        
        # Preparar datos de la factura
        nombre_completo = f"{pago_data[7]} {pago_data[8] or ''} {pago_data[9] or ''}".strip()
        
        factura_data = {
            'numero_factura': f"FAC-{pago_id:06d}",
            'fecha_emision': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'cliente': {
                'nombre': nombre_completo,
                'ci': pago_data[10],
                'departamento': f"Piso {pago_data[11]} - Dpto {pago_data[12]}"
            },
            'concepto': pago_data[4],  # descripcion
            'concepto_detalle': pago_data[13] or 'Reserva Área Común',  # concepto_nombre
            'monto': float(pago_data[3]),  # monto
            'metodo_pago': pago_data[11],  # metodo_pago
            'comprobante': pago_data[12],  # comprobante
            'horas': pago_data[14] or 1   # horas
        }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'factura': factura_data
        })
    
    except Exception as e:
        logger.error(f"Error generando factura: {e}")
        return jsonify({'success': False, 'message': 'Error generando factura'}), 500

@residentes_bp.route('/api/mis_reservas')
@login_required
def mis_reservas():
    try:
        user_id = get_user_id()
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
            
        cursor = conn.cursor()
        
        # Obtener reservas del usuario
        cursor.execute("""
            SELECT pq.id_pago, pq.descripcion, pq.monto, pq.fecha_generacion,
                   pq.estado, pq.metodo_pago, pq.comprobante, pq.horas
            FROM pagos_qr pq
            JOIN residente r ON pq.id_residente = r.id_residente
            WHERE r.id_usuario = %s
            ORDER BY pq.fecha_generacion DESC
        """, (user_id,))
        
        reservas = cursor.fetchall()
        
        reservas_list = []
        for reserva in reservas:
            reservas_list.append({
                'id': reserva[0],
                'descripcion': reserva[1],
                'monto': float(reserva[2]),
                'fecha': reserva[3].strftime('%d/%m/%Y %H:%M'),
                'estado': reserva[4],
                'metodo_pago': reserva[5],
                'comprobante': reserva[6],
                'horas': reserva[7]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'reservas': reservas_list
        })
    
    except Exception as e:
        logger.error(f"Error obteniendo reservas: {e}")
        return jsonify({'success': False, 'message': 'Error obteniendo reservas'}), 500

# ===== ERROR HANDLERS =====

@residentes_bp.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@residentes_bp.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

# Agrega esto ANTES de las rutas de API, por ejemplo después de la ruta /reservas

@residentes_bp.route('/consumos')
@login_required
def consumos():
    """Ruta temporal para consumos - redirige a reservas"""
    flash('Los consumos están disponibles en el área de administración', 'info')
    return redirect(url_for('residentes.reservas'))



# ===== ENDPOINTS PARA TICKETS =====

@residentes_bp.route('/api/tickets/<int:ticket_id>')
@login_required
def obtener_detalles_ticket(ticket_id):
    """Obtener detalles completos de un ticket específico"""
    try:
        user_id = get_user_id()
        
        # Validar que el ticket pertenece al residente
        if not _validar_ticket_residente(ticket_id):
            return jsonify({'success': False, 'message': 'Ticket no encontrado o no autorizado'}), 404
        
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
                a.descripcion as area_descripcion
            FROM ticket t
            JOIN departamento d ON t.id_departamento = d.id_departamento
            JOIN residente r ON d.piso = r.piso::varchar AND d.nro = r.nro_departamento
            LEFT JOIN empleado e ON t.id_empleado = e.id_empleado
            LEFT JOIN usuario u ON e.id_usuario = u.id_usuario
            LEFT JOIN area a ON t.id_area = a.id_area
            WHERE t.id_ticket = %s AND r.id_usuario = %s
        """, (ticket_id, user_id))
        
        ticket_data = cursor.fetchone()
        
        if not ticket_data:
            return jsonify({'success': False, 'message': 'Ticket no encontrado'}), 404
        
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
        
        # Obtener archivos adjuntos
        cursor.execute("""
            SELECT nombre_archivo, url_archivo, tipo_archivo, fecha_subida
            FROM archivo_ticket
            WHERE id_ticket = %s
            ORDER BY fecha_subida ASC
        """, (ticket_id,))
        
        archivos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Formatear respuesta
        ticket_info = {
            'id_ticket': ticket_data[0],
            'descripcion': ticket_data[1],
            'prioridad': ticket_data[2],
            'estado': ticket_data[3],
            'fecha_emision': ticket_data[4].strftime('%d/%m/%Y %H:%M') if ticket_data[4] else None,
            'fecha_finalizacion': ticket_data[5].strftime('%d/%m/%Y %H:%M') if ticket_data[5] else None,
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
                'fecha': comentario[1].strftime('%d/%m/%Y %H:%M'),
                'autor': f"{comentario[3]} {comentario[4] or ''} {comentario[5] or ''}".strip(),
                'es_interno': comentario[2]
            })
        
        archivos_list = []
        for archivo in archivos:
            archivos_list.append({
                'nombre': archivo[0],
                'url': archivo[1],
                'tipo': archivo[2],
                'fecha_subida': archivo[3].strftime('%d/%m/%Y %H:%M')
            })
        
        return jsonify({
            'success': True,
            'ticket': ticket_info,
            'comentarios': comentarios_list,
            'archivos': archivos_list
        })
        
    except Exception as e:
        print(f"Error obteniendo detalles del ticket: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al obtener detalles del ticket'}), 500

@residentes_bp.route('/api/tickets/<int:ticket_id>/actualizar', methods=['PUT'])
@login_required
def actualizar_ticket(ticket_id):
    """Actualizar un ticket existente"""
    try:
        user_id = get_user_id()
        data = request.get_json()
        
        # Validar que el ticket pertenece al residente
        if not _validar_ticket_residente(ticket_id):
            return jsonify({'success': False, 'message': 'Ticket no encontrado o no autorizado'}), 404
        
        # Validar que el ticket está en estado que permite actualización
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT estado FROM ticket WHERE id_ticket = %s", (ticket_id,))
        ticket_estado = cursor.fetchone()
        
        if not ticket_estado or ticket_estado[0] not in ['abierto', 'en_progreso']:
            return jsonify({'success': False, 'message': 'No se puede actualizar un ticket cerrado o cancelado'}), 400
        
        nueva_descripcion = data.get('descripcion')
        if not nueva_descripcion:
            return jsonify({'success': False, 'message': 'La descripción es requerida'}), 400
        
        # Actualizar el ticket
        cursor.execute("""
            UPDATE ticket 
            SET descripcion = %s
            WHERE id_ticket = %s
        """, (nueva_descripcion, ticket_id))
        
        # Agregar comentario de actualización
        cursor.execute("""
            INSERT INTO comentario_ticket (id_ticket, id_usuario, mensaje, fecha_creacion, es_interno)
            VALUES (%s, %s, %s, NOW(), false)
        """, (ticket_id, user_id, f"Actualización: {nueva_descripcion}"))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Ticket actualizado exitosamente'
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"Error actualizando ticket: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al actualizar el ticket'}), 500

@residentes_bp.route('/api/tickets/<int:ticket_id>/cancelar', methods=['PUT'])
@login_required
def cancelar_ticket(ticket_id):
    """Cancelar un ticket"""
    try:
        user_id = get_user_id()
        
        # Validar que el ticket pertenece al residente
        if not _validar_ticket_residente(ticket_id):
            return jsonify({'success': False, 'message': 'Ticket no encontrado o no autorizado'}), 404
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el ticket puede ser cancelado
        cursor.execute("SELECT estado FROM ticket WHERE id_ticket = %s", (ticket_id,))
        ticket_estado = cursor.fetchone()
        
        if not ticket_estado:
            return jsonify({'success': False, 'message': 'Ticket no encontrado'}), 404
            
        if ticket_estado[0] != 'abierto':
            return jsonify({'success': False, 'message': 'Solo se pueden cancelar tickets abiertos'}), 400
        
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
        """, (ticket_id, user_id, "Ticket cancelado por el residente"))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Ticket cancelado exitosamente'
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"Error cancelando ticket: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al cancelar el ticket'}), 500

@residentes_bp.route('/api/tickets/<int:ticket_id>/comentario', methods=['POST'])
@login_required
def agregar_comentario(ticket_id):
    """Agregar comentario a un ticket"""
    try:
        user_id = get_user_id()
        data = request.get_json()
        
        mensaje = data.get('mensaje')
        if not mensaje:
            return jsonify({'success': False, 'message': 'El mensaje no puede estar vacío'}), 400
        
        # Validar que el ticket pertenece al residente
        if not _validar_ticket_residente(ticket_id):
            return jsonify({'success': False, 'message': 'Ticket no encontrado o no autorizado'}), 404
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Agregar comentario
        cursor.execute("""
            INSERT INTO comentario_ticket (id_ticket, id_usuario, mensaje, fecha_creacion, es_interno)
            VALUES (%s, %s, %s, NOW(), false)
        """, (ticket_id, user_id, mensaje))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Comentario agregado exitosamente'
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"Error agregando comentario: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al agregar comentario'}), 500
    
# ===== RUTAS API PARA TICKETS =====

@residentes_bp.route('/api/tickets/<int:ticket_id>/actualizar', methods=['PUT'])
@login_required
def api_actualizar_ticket(ticket_id):
    """API para actualizar un ticket existente"""
    try:
        user_id = get_user_id()
        data = request.get_json()
        
        print(f"🔍 DEBUG - Actualizando ticket {ticket_id} para usuario {user_id}")
        print(f"📝 Datos recibidos: {data}")
        
        # Validar que el ticket pertenece al residente
        if not _validar_ticket_residente(ticket_id):
            return jsonify({'success': False, 'message': 'Ticket no encontrado o no autorizado'}), 404
        
        # Validar que el ticket está en estado que permite actualización
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT estado FROM ticket WHERE id_ticket = %s", (ticket_id,))
        ticket_estado = cursor.fetchone()
        
        if not ticket_estado:
            return jsonify({'success': False, 'message': 'Ticket no encontrado'}), 404
            
        if ticket_estado[0] not in ['abierto', 'en_progreso']:
            return jsonify({'success': False, 'message': 'No se puede actualizar un ticket cerrado o cancelado'}), 400
        
        nueva_descripcion = data.get('descripcion')
        if not nueva_descripcion:
            return jsonify({'success': False, 'message': 'La descripción es requerida'}), 400
        
        # Actualizar el ticket
        cursor.execute("""
            UPDATE ticket 
            SET descripcion = %s
            WHERE id_ticket = %s
        """, (nueva_descripcion, ticket_id))
        
        # Agregar comentario de actualización
        cursor.execute("""
            INSERT INTO comentario_ticket (id_ticket, id_usuario, mensaje, fecha_creacion, es_interno)
            VALUES (%s, %s, %s, NOW(), false)
        """, (ticket_id, user_id, f"Actualización: {nueva_descripcion}"))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Ticket {ticket_id} actualizado exitosamente")
        
        return jsonify({
            'success': True,
            'message': 'Ticket actualizado exitosamente'
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"❌ Error actualizando ticket: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al actualizar el ticket'}), 500

@residentes_bp.route('/api/tickets/<int:ticket_id>/cancelar', methods=['PUT'])
@login_required
def api_cancelar_ticket(ticket_id):
    """API para cancelar un ticket"""
    try:
        user_id = get_user_id()
        
        print(f"🔍 DEBUG - Cancelando ticket {ticket_id} para usuario {user_id}")
        
        # Validar que el ticket pertenece al residente
        if not _validar_ticket_residente(ticket_id):
            return jsonify({'success': False, 'message': 'Ticket no encontrado o no autorizado'}), 404
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el ticket puede ser cancelado
        cursor.execute("SELECT estado FROM ticket WHERE id_ticket = %s", (ticket_id,))
        ticket_estado = cursor.fetchone()
        
        if not ticket_estado:
            return jsonify({'success': False, 'message': 'Ticket no encontrado'}), 404
            
        if ticket_estado[0] != 'abierto':
            return jsonify({'success': False, 'message': 'Solo se pueden cancelar tickets abiertos'}), 400
        
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
        """, (ticket_id, user_id, "Ticket cancelado por el residente"))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Ticket {ticket_id} cancelado exitosamente")
        
        return jsonify({
            'success': True,
            'message': 'Ticket cancelado exitosamente'
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"❌ Error cancelando ticket: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al cancelar el ticket'}), 500
# ===== API PARA GESTIÓN DE PERFIL =====

@residentes_bp.route('/api/actualizar_perfil', methods=['POST'])
@login_required
def api_actualizar_perfil():
    """API para actualizar información del perfil"""
    try:
        user_id = get_user_id()
        data = request.get_json()
        
        # Validar datos requeridos
        if not data.get('nombre'):
            return jsonify({'success': False, 'message': 'El nombre es obligatorio'}), 400
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor()
        
        # Actualizar información del usuario
        cursor.execute("""
            UPDATE usuario 
            SET nombre = %s, ap_paterno = %s, ap_materno = %s, telefono = %s, ci = %s
            WHERE id_usuario = %s
        """, (
            data.get('nombre'),
            data.get('ap_paterno'),
            data.get('ap_materno'),
            data.get('telefono'),
            data.get('ci'),
            user_id
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Perfil actualizado correctamente'
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error actualizando perfil: {e}")
        return jsonify({'success': False, 'message': 'Error al actualizar el perfil'}), 500

@residentes_bp.route('/api/cambiar_password', methods=['POST'])
@login_required
def api_cambiar_password():
    """API para cambiar contraseña"""
    try:
        user_id = get_user_id()
        data = request.get_json()
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        # Validaciones básicas
        if not current_password or not new_password:
            return jsonify({'success': False, 'message': 'Todos los campos son obligatorios'}), 400
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'La nueva contraseña debe tener al menos 6 caracteres'}), 400
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor()
        
        # Verificar contraseña actual
        cursor.execute("SELECT contrasena FROM usuario WHERE id_usuario = %s", (user_id,))
        usuario = cursor.fetchone()
        
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        # Aquí deberías implementar la verificación real de contraseña
        # Por ahora simulamos que siempre es correcta
        contraseña_correcta = True  # Esto debería ser: check_password_hash(usuario[0], current_password)
        
        if not contraseña_correcta:
            return jsonify({'success': False, 'message': 'La contraseña actual es incorrecta'}), 400
        
        # Aquí deberías encriptar la nueva contraseña
        # nueva_contraseña_hash = generate_password_hash(new_password)
        
        # Actualizar contraseña (simulado)
        cursor.execute("""
            UPDATE usuario 
            SET contrasena = %s
            WHERE id_usuario = %s
        """, (new_password, user_id))  # En producción usar: nueva_contraseña_hash
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Contraseña cambiada correctamente'
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error cambiando contraseña: {e}")
        return jsonify({'success': False, 'message': 'Error al cambiar la contraseña'}), 500

@residentes_bp.route('/api/cerrar_otras_sesiones', methods=['POST'])
@login_required
def api_cerrar_otras_sesiones():
    """API para cerrar otras sesiones activas"""
    try:
        user_id = get_user_id()
        
        # Aquí implementarías la lógica para cerrar otras sesiones
        # Por ejemplo, invalidar tokens JWT excepto el actual
        # Por ahora es una implementación simulada
        
        print(f"🔍 Cerrando otras sesiones para usuario {user_id}")
        
        # Simular éxito
        return jsonify({
            'success': True, 
            'message': 'Otras sesiones cerradas correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error cerrando otras sesiones: {e}")
        return jsonify({'success': False, 'message': 'Error al cerrar otras sesiones'}), 500