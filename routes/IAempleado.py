import google.generativeai as genai
from flask import Blueprint, request, jsonify, current_app, render_template
from db import get_db_connection
from datetime import datetime, timedelta
from flask_login import login_required, current_user

# Crear blueprint
ia_empleado = Blueprint('ia_empleado', __name__, url_prefix='/empleado/ia')

# Configurar Gemini
GEMINI_API_KEY = "AIzaSyAXFoEwM8vwwhU8FQEyir_DAqr67a-fVJ0"
genai.configure(api_key=GEMINI_API_KEY)

def get_id_empleado():
    """Obtener el id_empleado del usuario actual - Misma función que en empleado.py"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print(f"🔍 [IA] Buscando empleado para usuario ID: {current_user.id}")
        
        cursor.execute("SELECT id_empleado FROM empleado WHERE id_usuario = %s", (current_user.id,))
        result = cursor.fetchone()
        
        if result:
            print(f"✅ [IA] Empleado encontrado: ID {result[0]}")
        else:
            print(f"❌ [IA] No se encontró empleado para usuario {current_user.id}")
        
        cursor.close()
        conn.close()
        
        return result[0] if result else None
    except Exception as e:
        print(f"❌ [IA] Error obteniendo id_empleado: {e}")
        return None

def is_employee_user():
    """Verifica si el usuario tiene permisos de empleado - Basado en empleado.py"""
    # Misma verificación que en empleado.py - rol 2 para empleados
    if hasattr(current_user, 'id_rol') and current_user.id_rol == 2:
        return True
    
    # Verificar adicionalmente si existe en la tabla empleado
    id_empleado = get_id_empleado()
    return id_empleado is not None

def get_ia_employee_context():
    """Obtener contexto específico del empleado para el IA"""
    conn = get_db_connection()
    if not conn:
        return {'error': 'No se pudo conectar a la base de datos'}
    
    context = {}
    
    try:
        id_empleado = get_id_empleado()
        if not id_empleado:
            return {'error': 'Empleado no encontrado'}
            
        cur = conn.cursor()
        
        # Información del empleado actual - Usando misma estructura que empleado.py
        cur.execute("""
            SELECT u.nombre, u.ap_paterno, u.ap_materno, e.puesto, e.salario, e.turno, e.fecha_contratacion
            FROM usuario u
            JOIN empleado e ON u.id_usuario = e.id_usuario
            WHERE e.id_empleado = %s
        """, (id_empleado,))
        empleado_data = cur.fetchone()
        
        if empleado_data:
            context['nombre_completo'] = f"{empleado_data[0] or ''} {empleado_data[1] or ''} {empleado_data[2] or ''}".strip()
            context['puesto'] = empleado_data[3] or 'No definido'
            context['salario'] = f"Bs {float(empleado_data[4]):,.2f}" if empleado_data[4] else 'No definido'
            context['turno'] = empleado_data[5] or 'No asignado'
            context['fecha_contratacion'] = empleado_data[6].strftime('%d/%m/%Y') if empleado_data[6] else 'N/A'
        else:
            context['nombre_completo'] = current_user.nombre or 'Usuario'
            context['puesto'] = 'Empleado'
            context['salario'] = 'No disponible'
            context['turno'] = 'No asignado'
            context['fecha_contratacion'] = 'N/A'
        
        # Tickets asignados - Misma consulta que empleado.py
        cur.execute("""
            SELECT COUNT(*) FROM ticket 
            WHERE id_empleado = %s 
            AND estado IN ('abierto', 'en_progreso')
        """, (current_user.id,))
        context['tickets_asignados'] = cur.fetchone()[0]
        
        # Asistencia del mes - Misma consulta que empleado.py
        cur.execute("""
            SELECT COUNT(DISTINCT fecha) 
            FROM control_asistencia 
            WHERE id_empleado = %s 
            AND DATE_PART('month', fecha) = DATE_PART('month', CURRENT_DATE)
            AND DATE_PART('year', fecha) = DATE_PART('year', CURRENT_DATE)
        """, (id_empleado,))
        context['dias_trabajados'] = cur.fetchone()[0]
        
        # Horas promedio trabajadas
        cur.execute("""
            SELECT AVG(horas_trabajadas) as horas_promedio
            FROM control_asistencia 
            WHERE id_empleado = %s 
            AND fecha >= DATE_TRUNC('month', CURRENT_DATE)
        """, (id_empleado,))
        horas_data = cur.fetchone()
        context['horas_promedio'] = f"{float(horas_data[0] or 0):.2f}" if horas_data else '0.00'
        
        # Mantenimientos activos - Misma consulta que empleado.py
        cur.execute("""
            SELECT COUNT(*) FROM mantenimiento 
            WHERE id_empleado = %s AND activo = true
        """, (current_user.id,))
        context['mantenimientos_activos'] = cur.fetchone()[0]
        
        # Último pago - Misma consulta que empleado.py
        cur.execute("""
            SELECT n.monto 
            FROM nomina n
            WHERE n.id_empleado = %s 
            ORDER BY n.fecha_pago DESC 
            LIMIT 1
        """, (id_empleado,))
        ultimo_pago_result = cur.fetchone()
        context['ultimo_pago'] = f"Bs {float(ultimo_pago_result[0]):,.2f}" if ultimo_pago_result and ultimo_pago_result[0] else 'No registrado'
        
        cur.close()
        
    except Exception as e:
        print(f"❌ [IA] Error obteniendo contexto IA empleado: {e}")
        context = {
            'nombre_completo': 'Error',
            'puesto': 'Error',
            'salario': 'Error',
            'turno': 'Error',
            'fecha_contratacion': 'Error',
            'tickets_asignados': 'Error',
            'dias_trabajados': 'Error',
            'horas_promedio': 'Error',
            'mantenimientos_activos': 'Error',
            'ultimo_pago': 'Error'
        }
    finally:
        if conn:
            conn.close()
    
    return context

def get_ia_employee_tasks():
    """Obtener tareas y actividades del empleado"""
    conn = get_db_connection()
    if not conn:
        return {}
    
    tasks_data = {}
    
    try:
        id_empleado = get_id_empleado()
        if not id_empleado:
            return {}
            
        cur = conn.cursor()
        
        # Tickets recientes - Misma estructura que empleado.py
        cur.execute("""
            SELECT 
                t.id_ticket,
                t.descripcion,
                t.prioridad,
                t.estado,
                TO_CHAR(t.fecha_emision, 'DD/MM/YYYY HH24:MI') as fecha_emision
            FROM ticket t
            WHERE t.id_empleado = %s
            ORDER BY t.fecha_emision DESC
            LIMIT 5
        """, (current_user.id,))
        tasks_data['recent_tickets'] = cur.fetchall()
        
        # Mantenimientos programados
        cur.execute("""
            SELECT 
                m.id_mantenimiento,
                m.descripcion,
                m.activo
            FROM mantenimiento m
            WHERE m.id_empleado = %s
            AND m.activo = true
            ORDER BY m.id_mantenimiento DESC
            LIMIT 5
        """, (current_user.id,))
        tasks_data['scheduled_maintenance'] = cur.fetchall()
        
        # Horario de esta semana
        cur.execute("""
            SELECT 
                fecha,
                hora_entrada,
                hora_salida,
                horas_trabajadas
            FROM control_asistencia 
            WHERE id_empleado = %s 
            AND fecha >= DATE_TRUNC('week', CURRENT_DATE)
            ORDER BY fecha
        """, (id_empleado,))
        tasks_data['weekly_schedule'] = cur.fetchall()
        
        # Historial de pagos recientes
        cur.execute("""
            SELECT 
                TO_CHAR(n.fecha_pago, 'DD/MM/YYYY'),
                n.monto,
                n.estado
            FROM nomina n
            WHERE n.id_empleado = %s
            ORDER BY n.fecha_pago DESC
            LIMIT 3
        """, (id_empleado,))
        tasks_data['recent_payments'] = cur.fetchall()
        
        cur.close()
        
    except Exception as e:
        print(f"❌ [IA] Error obteniendo tareas IA empleado: {e}")
    finally:
        if conn:
            conn.close()
    
    return tasks_data

def generate_ia_employee_response(user_message, context, tasks_data):
    """Generar respuesta usando Gemini AI para empleados"""
    try:
        # Generar prompt contextualizado para empleados
        prompt = f"""
Eres un asistente IA especializado en apoyo a empleados de condominios y gestión de propiedades. 
Tu rol es ayudar al empleado con sus tareas diarias, gestión de tiempo y optimización de trabajo.

INFORMACIÓN DEL EMPLEADO:
- Nombre: {context.get('nombre_completo', 'N/A')}
- Puesto: {context.get('puesto', 'N/A')}
- Salario: {context.get('salario', 'N/A')}
- Turno: {context.get('turno', 'N/A')}
- Fecha de contratación: {context.get('fecha_contratacion', 'N/A')}

ESTADO ACTUAL:
- Tickets asignados: {context.get('tickets_asignados', 'N/A')}
- Mantenimientos activos: {context.get('mantenimientos_activos', 'N/A')}
- Días trabajados este mes: {context.get('dias_trabajados', 'N/A')}
- Horas promedio por día: {context.get('horas_promedio', 'N/A')}
- Último pago: {context.get('ultimo_pago', 'N/A')}

TAREAS Y ACTIVIDADES:
Tickets recientes: {tasks_data.get('recent_tickets', [])}
Mantenimientos programados: {tasks_data.get('scheduled_maintenance', [])}
Horario semanal: {tasks_data.get('weekly_schedule', [])}
Pagos recientes: {tasks_data.get('recent_payments', [])}

INSTRUCCIONES ESPECÍFICAS PARA EMPLEADOS:
1. Enfócate en tareas prácticas y gestión del trabajo diario
2. Proporciona consejos para optimizar el tiempo y eficiencia
3. Ayuda con procedimientos y protocolos de trabajo
4. Sugiere formas de mejorar la comunicación con residentes
5. Asiste con reportes y documentación requerida
6. Mantén un tono motivacional y de apoyo
7. Usa emojis para hacer la respuesta más amigable
8. Sé específico con recomendaciones accionables
9. Si preguntan sobre pagos, salarios o nóminas, refiere a la sección correspondiente
10. Para temas técnicos específicos, sugiere consultar con supervisores

PREGUNTA DEL EMPLEADO: {user_message}

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
        print(f"❌ [IA] Error generando respuesta IA empleado: {e}")
        # Respuesta de respaldo si falla la IA
        return f"""🤖 **Asistente para Empleados - Respuesta Básica**

Basándome en tu información actual:

👤 **Tu Estado:**
• Puesto: {context.get('puesto', 'N/A')}
• Turno: {context.get('turno', 'N/A')}
• Tickets asignados: {context.get('tickets_asignados', 'N/A')}
• Mantenimientos activos: {context.get('mantenimientos_activos', 'N/A')}

💡 **Consejos generales:**
1. Prioriza tus tareas por urgencia e importancia
2. Mantén comunicación clara con residentes
3. Documenta bien tu trabajo
4. Reporta cualquier incidencia inmediatamente

¿En qué tarea específica necesitas ayuda?"""

def generate_daily_plan_ia(context, tasks_data):
    """Generar plan diario con IA"""
    try:
        prompt = f"""
Genera un plan de trabajo diario optimizado para un empleado de condominio con esta información:

INFORMACIÓN DEL EMPLEADO:
Puesto: {context.get('puesto', 'N/A')}
Tickets asignados: {context.get('tickets_asignados', 'N/A')}
Mantenimientos activos: {context.get('mantenimientos_activos', 'N/A')}

TAREAS PENDIENTES:
Tickets: {tasks_data.get('recent_tickets', [])}
Mantenimientos: {tasks_data.get('scheduled_maintenance', [])}

Por favor, genera:
1. Plan de trabajo organizado por prioridad
2. Estimación de tiempos para cada tarea
3. Recomendaciones para eficiencia
4. Recordatorios importantes
5. Consejos para manejo de múltiples tareas

Formato claro y fácil de seguir.
"""
        
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Error generando plan diario: {str(e)}"

def generate_communication_tips_ia(context):
    """Generar consejos de comunicación con IA"""
    try:
        prompt = f"""
Genera consejos prácticos de comunicación para un empleado de condominio con puesto: {context.get('puesto', 'N/A')}

Enfócate en:
1. Comunicación efectiva con residentes
2. Reportes claros a supervisores
3. Trabajo en equipo con otros empleados
4. Manejo de quejas y sugerencias
5. Comunicación en situaciones de emergencia

Proporciona ejemplos prácticos y frases útiles.
"""
        
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Error generando consejos de comunicación: {str(e)}"

# =============================================================================
# RUTAS DEL ASISTENTE IA PARA EMPLEADOS
# =============================================================================

@ia_empleado.route("/")
@login_required
def dashboard():
    """Dashboard del asistente IA para empleados"""
    # Misma verificación que en empleado.py - rol 2 para empleados
    if current_user.id_rol != 2:
        print(f"❌ [IA] Acceso denegado - Rol incorrecto: {current_user.id_rol}")
        return "Acceso no autorizado", 403
    
    if not is_employee_user():
        print(f"❌ [IA] Acceso denegado - No es empleado válido")
        return "Acceso no autorizado", 403
    
    print(f"✅ [IA] Acceso permitido para empleado: {current_user.id}")
    return render_template("empleado/IAempleado.html", now=datetime.now())

@ia_empleado.route("/context")
@login_required
def context():
    """Obtener contexto del empleado para el IA"""
    if current_user.id_rol != 2 or not is_employee_user():
        return jsonify({'success': False, 'error': 'Acceso no autorizado'}), 403
    
    try:
        context = get_ia_employee_context()
        return jsonify({
            'success': True,
            'context': context
        })
    except Exception as e:
        print(f"❌ [IA] Error obteniendo contexto IA empleado: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ia_empleado.route("/chat", methods=["POST"])
@login_required
def chat():
    """Endpoint para chat con IA para empleados"""
    if current_user.id_rol != 2 or not is_employee_user():
        return jsonify({'success': False, 'error': 'Acceso no autorizado'}), 403
    
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Mensaje vacío'
            }), 400
        
        # Obtener datos contextuales
        context = get_ia_employee_context()
        tasks_data = get_ia_employee_tasks()
        
        # Generar respuesta con Gemini
        response = generate_ia_employee_response(user_message, context, tasks_data)
        
        return jsonify({
            'success': True,
            'response': response
        })
        
    except Exception as e:
        print(f"❌ [IA] Error en chat IA empleado: {e}")
        # Respuesta de respaldo en caso de error
        backup_response = f"""🤖 **Asistente para Empleados**

Actualmente estoy experimentando dificultades técnicas. Mientras tanto:

📋 **Tu Información:**
• Puesto: {context.get('puesto', 'N/A') if 'context' in locals() else 'N/A'}
• Tickets asignados: {context.get('tickets_asignados', 'N/A') if 'context' in locals() else 'N/A'}
• Mantenimientos activos: {context.get('mantenimientos_activos', 'N/A') if 'context' in locals() else 'N/A'}

💡 **Recordatorios:**
1. Revisa tu lista de tareas diarias
2. Prioriza las actividades más urgentes
3. Reporta tu progreso regularmente

El equipo técnico está trabajando para restaurar el servicio completo."""
        
        return jsonify({
            'success': True,
            'response': backup_response
        })

@ia_empleado.route("/daily-plan")
@login_required
def daily_plan():
    """Generar plan diario con IA"""
    if current_user.id_rol != 2 or not is_employee_user():
        return jsonify({'success': False, 'error': 'Acceso no autorizado'}), 403
    
    try:
        context = get_ia_employee_context()
        tasks_data = get_ia_employee_tasks()
        plan = generate_daily_plan_ia(context, tasks_data)
        
        return jsonify({
            'success': True,
            'plan': plan
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ia_empleado.route("/communication-tips")
@login_required
def communication_tips():
    """Generar consejos de comunicación con IA"""
    if current_user.id_rol != 2 or not is_employee_user():
        return jsonify({'success': False, 'error': 'Acceso no autorizado'}), 403
    
    try:
        context = get_ia_employee_context()
        tips = generate_communication_tips_ia(context)
        
        return jsonify({
            'success': True,
            'tips': tips
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500