import google.generativeai as genai
from flask import Blueprint, request, jsonify, current_app, render_template, flash, redirect, url_for
from db import get_db_connection
from datetime import datetime, timedelta
from flask_login import login_required, current_user

# Crear blueprint
ia_residente_bp = Blueprint('ia_residente', __name__, url_prefix='/residente/ia')

# Configurar Gemini
GEMINI_API_KEY = "AIzaSyAXFoEwM8vwwhU8FQEyir_DAqr67a-fVJ0"
genai.configure(api_key=GEMINI_API_KEY)

def get_user_id():
    """Safe way to get user ID"""
    try:
        return current_user.id_usuario
    except AttributeError:
        try:
            user_id = current_user.get_id()
            return int(user_id) if user_id else None
        except:
            return None

def get_user_role():
    """Obtiene el rol del usuario actual"""
    try:
        user_id = get_user_id()
        if not user_id:
            return None
            
        conn = get_db_connection()
        if conn is None:
            return None
            
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_rol 
            FROM usuario 
            WHERE id_usuario = %s
        """, (user_id,))
        rol = cursor.fetchone()
        cursor.close()
        conn.close()
        return rol[0] if rol else None
    except Exception as e:
        print(f"❌ [IA-Residente] Error obteniendo rol del usuario: {e}")
        return None

def get_residente_data():
    """Obtiene los datos del residente actual"""
    try:
        user_id = get_user_id()
        if not user_id:
            return None
            
        conn = get_db_connection()
        if conn is None:
            return None
            
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                r.id_residente,
                r.id_usuario,
                COALESCE(r.piso, 0) as piso,
                COALESCE(r.nro_departamento, 'N/A') as nro_departamento,
                r.fecha_ingreso,
                u.nombre,
                u.ap_paterno,
                u.ap_materno,
                u.correo,
                u.telefono
            FROM residente r
            JOIN usuario u ON r.id_usuario = u.id_usuario
            WHERE r.id_usuario = %s
        """, (user_id,))
        
        residente = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return residente
        
    except Exception as e:
        print(f"❌ [IA-Residente] Error obteniendo datos del residente: {e}")
        return None

def get_ia_residente_context():
    """Obtener contexto específico del residente para el IA - CONSULTAS CORREGIDAS"""
    conn = get_db_connection()
    if not conn:
        return {'error': 'No se pudo conectar a la base de datos'}
    
    context = {}
    
    try:
        user_id = get_user_id()
        residente_data = get_residente_data()
        
        if not residente_data:
            return {'error': 'Residente no encontrado'}
            
        cur = conn.cursor()
        
        # Información básica del residente
        context['nombre_completo'] = f"{residente_data[5] or ''} {residente_data[6] or ''} {residente_data[7] or ''}".strip()
        context['piso'] = residente_data[2] if residente_data[2] else 'N/A'
        context['departamento'] = residente_data[3] if residente_data[3] else 'N/A'
        context['fecha_ingreso'] = residente_data[4].strftime('%d/%m/%Y') if residente_data[4] else 'N/A'
        
        # Tickets activos (solicitudes de mantenimiento de áreas comunes) - CONSULTA SIMPLIFICADA
        cur.execute("""
            SELECT COUNT(*) 
            FROM ticket t
            JOIN departamento d ON t.id_departamento = d.id_departamento
            JOIN residente r ON (
                (d.piso = 'Piso ' || r.piso::varchar AND d.nro = r.nro_departamento) OR
                (d.piso = r.piso::varchar AND d.nro = r.nro_departamento)
            )
            WHERE r.id_usuario = %s 
            AND t.estado IN ('abierto', 'en_progreso')
        """, (user_id,))
        tickets_data = cur.fetchone()
        context['tickets_activos'] = tickets_data[0] if tickets_data else 0
        
        # Reservas activas de áreas comunes - CONSULTA SIMPLIFICADA
        cur.execute("""
            SELECT COUNT(*)
            FROM pagos_qr pq
            JOIN residente r ON pq.id_residente = r.id_residente
            WHERE r.id_usuario = %s 
            AND pq.estado = 'completado'
            AND pq.fecha_reserva >= CURRENT_DATE
        """, (user_id,))
        reservas_data = cur.fetchone()
        context['reservas_activas'] = reservas_data[0] if reservas_data else 0
        
        # Facturas pendientes - CONSULTA CORREGIDA (sin columna descripcion)
        try:
            cur.execute("""
                SELECT COUNT(*), COALESCE(SUM(monto_total), 0)
                FROM factura 
                WHERE id_usuario = %s 
                AND estado_factura = 'pendiente'
                AND fecha_vencimiento >= CURRENT_DATE
            """, (user_id,))
            facturas_data = cur.fetchone()
            context['facturas_pendientes'] = facturas_data[0] if facturas_data else 0
            context['monto_pendiente'] = f"Bs {float(facturas_data[1]):,.2f}" if facturas_data and facturas_data[1] else 'Bs 0.00'
        except Exception as e:
            print(f"⚠️ [IA-Residente] Error en consulta de facturas: {e}")
            context['facturas_pendientes'] = 0
            context['monto_pendiente'] = 'Bs 0.00'
        
        # Próximo vencimiento - CONSULTA CORREGIDA
        try:
            cur.execute("""
                SELECT MIN(fecha_vencimiento)
                FROM factura 
                WHERE id_usuario = %s 
                AND estado_factura = 'pendiente'
                AND fecha_vencimiento >= CURRENT_DATE
            """, (user_id,))
            vencimiento_data = cur.fetchone()
            context['proximo_vencimiento'] = vencimiento_data[0].strftime('%d/%m/%Y') if vencimiento_data and vencimiento_data[0] else 'No hay vencimientos'
        except Exception as e:
            print(f"⚠️ [IA-Residente] Error en consulta de vencimiento: {e}")
            context['proximo_vencimiento'] = 'No hay vencimientos'
        
        # Datos para el HTML
        context['estado'] = 'Activo'
        context['tickets_abiertos'] = context['tickets_activos']
        context['deudas_pendientes'] = context['facturas_pendientes']
        context['total_deuda'] = context['monto_pendiente']
        
        cur.close()
        
    except Exception as e:
        print(f"❌ [IA-Residente] Error obteniendo contexto IA residente: {e}")
        context = {
            'nombre_completo': 'Residente',
            'piso': 'N/A',
            'departamento': 'N/A',
            'fecha_ingreso': 'N/A',
            'facturas_pendientes': 0,
            'monto_pendiente': 'Bs 0.00',
            'tickets_activos': 0,
            'reservas_activas': 0,
            'proximo_vencimiento': 'No hay vencimientos',
            'estado': 'Activo',
            'tickets_abiertos': 0,
            'deudas_pendientes': 0,
            'total_deuda': 'Bs 0.00'
        }
    finally:
        if conn:
            conn.close()
    
    return context

def get_ia_residente_activities():
    """Obtener actividades relacionadas con servicios del edificio - CONSULTAS CORREGIDAS"""
    conn = get_db_connection()
    if not conn:
        return {}
    
    activities_data = {}
    
    try:
        user_id = get_user_id()
        
        if not user_id:
            return {}
            
        cur = conn.cursor()
        
        # Últimos tickets (solicitudes de mantenimiento) - CONSULTA SIMPLIFICADA
        cur.execute("""
            SELECT 
                t.id_ticket,
                t.descripcion,
                t.prioridad,
                t.estado,
                TO_CHAR(t.fecha_emision, 'DD/MM/YYYY HH24:MI') as fecha_emision
            FROM ticket t
            JOIN departamento d ON t.id_departamento = d.id_departamento
            JOIN residente r ON (
                (d.piso = 'Piso ' || r.piso::varchar AND d.nro = r.nro_departamento) OR
                (d.piso = r.piso::varchar AND d.nro = r.nro_departamento)
            )
            WHERE r.id_usuario = %s
            ORDER BY t.fecha_emision DESC
            LIMIT 5
        """, (user_id,))
        activities_data['recent_tickets'] = cur.fetchall()
        
        # Próximas reservas de áreas comunes - CONSULTA SIMPLIFICADA
        cur.execute("""
            SELECT 
                pq.id_pago,
                pq.descripcion,
                pq.fecha_reserva,
                pq.monto
            FROM pagos_qr pq
            JOIN residente r ON pq.id_residente = r.id_residente
            WHERE r.id_usuario = %s 
            AND pq.estado = 'completado'
            AND pq.fecha_reserva >= CURRENT_DATE
            ORDER BY pq.fecha_reserva ASC
            LIMIT 5
        """, (user_id,))
        activities_data['upcoming_reservations'] = cur.fetchall()
        
        # Áreas comunes disponibles - CONSULTA SIMPLIFICADA
        cur.execute("""
            SELECT 
                id_area,
                nombre,
                descripcion
            FROM area
            ORDER BY nombre
            LIMIT 10
        """)
        activities_data['available_areas'] = cur.fetchall()
        
        # Comunicados recientes del edificio - CONSULTA CON MANEJO DE ERRORES
        try:
            cur.execute("""
                SELECT 
                    titulo,
                    mensaje,
                    fecha_publicacion
                FROM comunicado
                WHERE fecha_publicacion >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY fecha_publicacion DESC
                LIMIT 5
            """)
            activities_data['recent_announcements'] = cur.fetchall()
        except Exception as e:
            print(f"⚠️ [IA-Residente] Error obteniendo comunicados: {e}")
            activities_data['recent_announcements'] = []
        
        cur.close()
        
    except Exception as e:
        print(f"❌ [IA-Residente] Error obteniendo actividades IA residente: {e}")
        # Valores por defecto en caso de error
        activities_data = {
            'recent_tickets': [],
            'upcoming_reservations': [],
            'available_areas': [],
            'recent_announcements': []
        }
    finally:
        if conn:
            conn.close()
    
    return activities_data

def generate_ia_residente_response(user_message, context, activities_data):
    """Generar respuesta usando Gemini AI para residentes - ENFOCADO EN SERVICIOS DEL EDIFICIO"""
    try:
        # Generar prompt contextualizado para servicios del edificio
        prompt = f"""
Eres SincroHome AI, un asistente IA especializado en servicios de condominios y edificios.
Tu rol es asistir al residente EXCLUSIVAMENTE con servicios comunitarios del edificio.

⚠️ **IMPORTANTE:** No debes ayudar con:
- Gastos personales del departamento 
- Mantenimientos internos del departamento
- Problemas de servicios básicos personales (agua, luz, gas personal)
- Compras o gastos particulares

INFORMACIÓN DEL RESIDENTE:
- Nombre: {context.get('nombre_completo', 'N/A')}
- Departamento: Piso {context.get('piso', 'N/A')} - Dpto {context.get('departamento', 'N/A')}
- Miembro desde: {context.get('fecha_ingreso', 'N/A')}

ESTADO ACTUAL EN EL EDIFICIO:
- Solicitudes activas: {context.get('tickets_activos', 'N/A')}
- Reservas activas: {context.get('reservas_activas', 'N/A')}
- Cuotas pendientes: {context.get('facturas_pendientes', 'N/A')} (solo mantenimiento del edificio)

SERVICIOS DISPONIBLES:
Áreas comunes: {[area[1] for area in activities_data.get('available_areas', [])]}
Reservas próximas: {len(activities_data.get('upcoming_reservations', []))}
Comunicados recientes: {len(activities_data.get('recent_announcements', []))}

INSTRUCCIONES ESPECÍFICAS:
1. 🏢 Enfócate SOLO en servicios comunitarios del edificio
2. 📋 Ayuda con reservas de áreas comunes (salón, piscina, gimnasio)
3. 🔧 Asiste con reporte de problemas en áreas comunes
4. 📢 Proporciona información sobre comunicados del edificio
5. 💡 Explica políticas y reglas del condominio
6. 🚨 Para emergencias del edificio, proporciona contactos de administración
7. ❌ NO ayudes con gastos personales o mantenimientos internos
8. ❌ NO des consejos sobre servicios básicos personales
9. ❌ NO te involucres en problemas entre vecinos
10. ✅ Mantén un tono amigable pero profesional

PREGUNTA DEL RESIDENTE: {user_message}

Si la pregunta es sobre gastos personales o mantenimientos internos del departamento, responde educadamente que eso no forma parte de los servicios del edificio.

RESPUESTA:
"""
        
        # Configurar el modelo
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 1024,
        }
        
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=generation_config
        )
        
        # Generar respuesta
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"❌ [IA-Residente] Error generando respuesta IA residente: {e}")
        # Respuesta de respaldo enfocada en servicios del edificio
        return f"""🏠 **SincroHome AI - Asistente para Servicios del Edificio**

Basándome en tu información como residente:

📊 **Tu Estado en el Edificio:**
• Departamento: Piso {context.get('piso', 'N/A')} - Dpto {context.get('departamento', 'N/A')}
• Solicitudes activas: {context.get('tickets_activos', 'N/A')}
• Reservas activas: {context.get('reservas_activas', 'N/A')}

💡 **Servicios Comunitarios Disponibles:**
• Reservas de áreas comunes (salón, piscina, gimnasio)
• Reporte de problemas en áreas comunes
• Información sobre políticas del edificio
• Consultas sobre comunicados y anuncios

⚠️ **Nota:** Solo puedo ayudarte con servicios comunitarios del edificio, no con gastos personales o mantenimientos internos de tu departamento.

¿En qué servicio del edificio necesitas ayuda?"""

def generate_building_guide_ia(context):
    """Generar guía del edificio con IA"""
    try:
        prompt = f"""
Genera una guía útil sobre los servicios comunitarios del edificio para un residente del departamento {context.get('piso', 'N/A')}-{context.get('departamento', 'N/A')}.

Incluye:
1. Horarios de áreas comunes
2. Proceso para reservas
3. Políticas de uso de espacios comunes
4. Contactos de emergencia del edificio
5. Normas de convivencia
6. Procedimiento para reportar problemas en áreas comunes

Sé claro y conciso, enfocado en la información práctica que necesita un residente.
"""
        
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Error generando guía del edificio: {str(e)}"

def generate_reservation_tips_ia(activities_data):
    """Generar consejos para reservas con IA"""
    try:
        prompt = f"""
Genera consejos prácticos para hacer reservas de áreas comunes basado en estas áreas disponibles:

ÁREAS DISPONIBLES: {[area[1] for area in activities_data.get('available_areas', [])]}

Enfócate en:
1. Cómo planificar reservas exitosas
2. Horarios recomendados para cada área
3. Políticas de cancelación
4. Consejos para eventos en áreas comunes
5. Normas de uso y cuidado

Proporciona información útil y práctica para residentes.
"""
        
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Error generando consejos de reservas: {str(e)}"

# =============================================================================
# RUTAS DEL ASISTENTE IA PARA RESIDENTES
# =============================================================================

@ia_residente_bp.route("/")
@login_required
def dashboard():
    """Dashboard del asistente IA para residentes"""
    user_role = get_user_role()
    
    # ✅ PERMITIR ACCESO A RESIDENTES (rol 3) Y ADMINS (rol 1)
    if user_role not in [1, 3]:
        print(f"❌ [IA-Residente] Acceso denegado - Rol incorrecto: {user_role}")
        flash('Acceso no autorizado para este rol', 'error')
        return redirect(url_for('residentes.dashboard'))
    
    print(f"✅ [IA-Residente] Acceso permitido para usuario: {get_user_id()}, Rol: {user_role}")
    return render_template("residente/ia_dashboard.html", now=datetime.now())

@ia_residente_bp.route("/context")
@login_required
def context():
    """Obtener contexto del residente para el IA"""
    user_role = get_user_role()
    
    if user_role not in [1, 3]:
        return jsonify({'success': False, 'error': 'Acceso no autorizado'}), 403
    
    try:
        context = get_ia_residente_context()
        return jsonify({
            'success': True,
            'context': context
        })
    except Exception as e:
        print(f"❌ [IA-Residente] Error obteniendo contexto IA residente: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ia_residente_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    """Endpoint para chat con IA para residentes - SOLO SERVICIOS DEL EDIFICIO"""
    user_role = get_user_role()
    
    if user_role not in [1, 3]:
        return jsonify({'success': False, 'error': 'Acceso no autorizado'}), 403
    
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Mensaje vacío'
            }), 400
        
        # Verificar si la pregunta es sobre servicios del edificio
        building_keywords = ['reserva', 'área común', 'piscina', 'gimnasio', 'salón', 'edificio', 'condominio', 
                           'mantenimiento común', 'comunidad', 'vecino', 'política', 'regla', 'comunicado']
        
        personal_keywords = ['mi departamento', 'mi casa', 'gasto personal', 'luz', 'agua', 'gas', 
                           'internet', 'comprar', 'reparar', 'mueble', 'electrodoméstico']
        
        message_lower = user_message.lower()
        is_building_related = any(keyword in message_lower for keyword in building_keywords)
        is_personal_related = any(keyword in message_lower for keyword in personal_keywords)
        
        # Obtener datos contextuales
        context = get_ia_residente_context()
        activities_data = get_ia_residente_activities()
        
        # Si es claramente personal, responder directamente
        if is_personal_related and not is_building_related:
            response = "⚠️ **SincroHome AI - Servicios del Edificio**\n\nSolo puedo ayudarte con servicios comunitarios del edificio como reservas de áreas comunes, reporte de problemas en espacios compartidos, políticas del condominio y comunicados.\n\nPara temas personales de tu departamento, consulta con los servicios correspondientes."
        else:
            # Generar respuesta con Gemini
            response = generate_ia_residente_response(user_message, context, activities_data)
        
        return jsonify({
            'success': True,
            'response': response
        })
        
    except Exception as e:
        print(f"❌ [IA-Residente] Error en chat IA residente: {e}")
        # Respuesta de respaldo enfocada en servicios del edificio
        backup_response = """🏠 **SincroHome AI - Asistente para Servicios del Edificio**

Actualmente estoy experimentando dificultades técnicas. Mientras tanto:

💡 **Servicios Comunitarios Disponibles:**
• Reservas de áreas comunes
• Reporte de problemas en espacios compartidos  
• Información sobre políticas del edificio
• Consultas sobre comunicados

⚠️ **Nota:** Solo puedo ayudarte con servicios comunitarios del edificio.

El equipo técnico está trabajando para restaurar el servicio completo."""
        
        return jsonify({
            'success': True,
            'response': backup_response
        })

@ia_residente_bp.route("/building-guide")
@login_required
def building_guide():
    """Generar guía del edificio con IA"""
    user_role = get_user_role()
    
    if user_role not in [1, 3]:
        return jsonify({'success': False, 'error': 'Acceso no autorizado'}), 403
    
    try:
        context = get_ia_residente_context()
        guide = generate_building_guide_ia(context)
        
        return jsonify({
            'success': True,
            'guide': guide
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ia_residente_bp.route("/reservation-tips")
@login_required
def reservation_tips():
    """Generar consejos para reservas con IA"""
    user_role = get_user_role()
    
    if user_role not in [1, 3]:
        return jsonify({'success': False, 'error': 'Acceso no autorizado'}), 403
    
    try:
        activities_data = get_ia_residente_activities()
        tips = generate_reservation_tips_ia(activities_data)
        
        return jsonify({
            'success': True,
            'tips': tips
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500