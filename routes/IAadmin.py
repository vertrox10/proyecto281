import google.generativeai as genai
from flask import Blueprint, request, jsonify, current_app, render_template
from db import get_db_connection
from datetime import datetime, timedelta
from flask_login import login_required, current_user

# Crear blueprint
ia_admin = Blueprint('ia_admin', __name__, url_prefix='/admin/ia')

# Configurar Gemini
GEMINI_API_KEY = "AIzaSyAXFoEwM8vwwhU8FQEyir_DAqr67a-fVJ0"
genai.configure(api_key=GEMINI_API_KEY)

def get_ia_system_context():
    """Obtener contexto actual del sistema para el IA"""
    conn = get_db_connection()
    if not conn:
        return {'error': 'No se pudo conectar a la base de datos'}
    
    context = {}
    
    try:
        cur = conn.cursor()
        
        # Empleados activos
        cur.execute("SELECT COUNT(*) FROM empleado WHERE estado = 'activo'")
        context['active_employees'] = cur.fetchone()[0]
        
        # Total residentes
        cur.execute("SELECT COUNT(*) FROM residente WHERE fecha_salida IS NULL")
        context['total_residents'] = cur.fetchone()[0]
        
        # Ingresos del mes actual
        cur.execute("""
            SELECT COALESCE(SUM(monto_total), 0) FROM factura 
            WHERE fecha_emision >= DATE_TRUNC('month', CURRENT_DATE)
            AND estado_factura = 'pagada'
        """)
        context['monthly_income'] = f"Bs {float(cur.fetchone()[0]):,.2f}"
        
        # Tickets abiertos
        cur.execute("""
            SELECT COUNT(*) FROM ticket 
            WHERE estado IN ('abierto', 'en_progreso', 'pendiente')
        """)
        context['open_tickets'] = cur.fetchone()[0]
        
        cur.close()
        
    except Exception as e:
        print(f"Error obteniendo contexto IA: {e}")
        context = {
            'active_employees': 'Error',
            'total_residents': 'Error', 
            'monthly_income': 'Error',
            'open_tickets': 'Error'
        }
    finally:
        if conn:
            conn.close()
    
    return context

def get_ia_financial_data():
    """Obtener datos financieros para el IA"""
    conn = get_db_connection()
    if not conn:
        return {}
    
    financial_data = {}
    
    try:
        cur = conn.cursor()
        
        # Ingresos últimos 6 meses
        cur.execute("""
            SELECT 
                TO_CHAR(DATE_TRUNC('month', fecha), 'YYYY-MM') as mes,
                SUM(monto) as total
            FROM movimientos 
            WHERE tipo = 'ingreso'
            AND fecha >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY DATE_TRUNC('month', fecha)
            ORDER BY mes
        """)
        financial_data['monthly_income'] = cur.fetchall()
        
        # Gastos últimos 6 meses
        cur.execute("""
            SELECT 
                TO_CHAR(DATE_TRUNC('month', fecha), 'YYYY-MM') as mes,
                SUM(monto) as total
            FROM movimientos 
            WHERE tipo = 'egreso'
            AND fecha >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY DATE_TRUNC('month', fecha)
            ORDER BY mes
        """)
        financial_data['monthly_expenses'] = cur.fetchall()
        
        # Nóminas del mes actual
        cur.execute("""
            SELECT COALESCE(SUM(monto), 0) FROM nomina 
            WHERE periodo_inicio >= DATE_TRUNC('month', CURRENT_DATE)
        """)
        financial_data['current_payroll'] = float(cur.fetchone()[0] or 0)
        
        cur.close()
        
    except Exception as e:
        print(f"Error obteniendo datos financieros IA: {e}")
    finally:
        if conn:
            conn.close()
    
    return financial_data

def get_ia_employee_performance():
    """Obtener datos de rendimiento de empleados para IA"""
    conn = get_db_connection()
    if not conn:
        return {}
    
    performance_data = {}
    
    try:
        cur = conn.cursor()
        
        # Asistencia del mes actual
        cur.execute("""
            SELECT 
                u.nombre,
                COUNT(ca.id_asistencia) as dias_trabajados,
                AVG(ca.horas_trabajadas) as horas_promedio
            FROM usuario u
            JOIN empleado e ON u.id_usuario = e.id_usuario
            LEFT JOIN control_asistencia ca ON u.id_usuario = ca.id_empleado
            WHERE ca.fecha >= DATE_TRUNC('month', CURRENT_DATE)
            AND e.estado = 'activo'
            GROUP BY u.id_usuario, u.nombre
            ORDER BY dias_trabajados DESC
            LIMIT 10
        """)
        performance_data['attendance'] = cur.fetchall()
        
        # Tickets asignados y completados
        cur.execute("""
            SELECT 
                u.nombre,
                COUNT(t.id_ticket) as total_tickets,
                SUM(CASE WHEN t.estado = 'cerrado' THEN 1 ELSE 0 END) as tickets_completados
            FROM usuario u
            JOIN empleado e ON u.id_usuario = e.id_usuario
            LEFT JOIN ticket t ON u.id_usuario = t.id_empleado
            WHERE t.fecha_emision >= DATE_TRUNC('month', CURRENT_DATE)
            GROUP BY u.id_usuario, u.nombre
        """)
        performance_data['ticket_performance'] = cur.fetchall()
        
        cur.close()
        
    except Exception as e:
        print(f"Error obteniendo rendimiento IA: {e}")
    finally:
        if conn:
            conn.close()
    
    return performance_data

def generate_ia_response(user_message, context, financial_data, performance_data):
    """Generar respuesta usando Gemini AI"""
    try:
        # Generar prompt contextualizado
        prompt = f"""
Eres un asistente IA especializado en administración de condominios y gestión de propiedades. 
Tu rol es ayudar al administrador con análisis de datos, toma de decisiones y optimización de procesos.

CONTEXTO ACTUAL DEL SISTEMA:
- Empleados activos: {context.get('active_employees', 'N/A')}
- Residentes totales: {context.get('total_residents', 'N/A')}
- Ingresos del mes: {context.get('monthly_income', 'N/A')}
- Tickets abiertos: {context.get('open_tickets', 'N/A')}

DATOS FINANCIEROS RECIENTES:
Ingresos últimos meses: {financial_data.get('monthly_income', [])}
Gastos últimos meses: {financial_data.get('monthly_expenses', [])}
Nómina actual: Bs {financial_data.get('current_payroll', 0):,.2f}

RENDIMIENTO DE EMPLEADOS:
Asistencia: {performance_data.get('attendance', [])}
Desempeño en tickets: {performance_data.get('ticket_performance', [])}

INSTRUCCIONES ESPECÍFICAS:
1. Proporciona análisis basados en datos cuando sea posible
2. Sugiere acciones concretas y medibles
3. Mantén un tono profesional pero accesible
4. Si piden reportes, estructura la información claramente
5. Para preguntas financieras, incluye recomendaciones prácticas
6. Sé conciso pero informativo
7. Usa emojis para hacer la respuesta más amigable

PREGUNTA DEL ADMINISTRADOR: {user_message}

RESPUESTA:
"""
        
        # Configurar el modelo - USAR MODELO CORRECTO
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 1024,
        }
        
        # Usar el modelo correcto - gemini-2.0-flash (disponible según tu diagnóstico)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=generation_config
        )
        
        # Generar respuesta
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"Error generando respuesta IA: {e}")
        # Respuesta de respaldo si falla la IA
        return f"""🤖 **Asistente Administrativo - Respuesta Básica**

Basándome en los datos del sistema:

📊 **Resumen del Sistema:**
• Empleados activos: {context.get('active_employees', 'N/A')}
• Residentes: {context.get('total_residents', 'N/A')}
• Ingresos del mes: {context.get('monthly_income', 'N/A')}
• Tickets pendientes: {context.get('open_tickets', 'N/A')}

💡 **Recomendaciones generales:**
1. Revise los reportes financieros en el dashboard
2. Monitoree el rendimiento de empleados regularmente  
3. Optimice los procesos de mantenimiento
4. Mantenga comunicación constante con residentes

¿En qué aspecto específico le gustaría profundizar?"""

def generate_financial_report_ia(financial_data):
    """Generar reporte financiero con IA"""
    try:
        prompt = f"""
Genera un reporte financiero ejecutivo basado en los siguientes datos:

INGRESOS ÚLTIMOS 6 MESES:
{financial_data.get('monthly_income', [])}

GASTOS ÚLTIMOS 6 MESES:
{financial_data.get('monthly_expenses', [])}

NÓMINA ACTUAL: Bs {financial_data.get('current_payroll', 0):,.2f}

Por favor, proporciona:
1. Análisis de tendencias de ingresos y gastos
2. Identificación de patrones estacionales
3. Recomendaciones para optimizar finanzas
4. Proyecciones para el próximo trimestre

Formato el reporte de manera clara y profesional.
"""
        
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Error generando reporte financiero: {str(e)}"

def generate_employee_analysis_ia(performance_data):
    """Generar análisis de empleados con IA"""
    try:
        prompt = f"""
Analiza el rendimiento del personal basado en estos datos:

ASISTENCIA Y HORAS TRABAJADOS:
{performance_data.get('attendance', [])}

DESEMPEÑO EN TICKETS:
{performance_data.get('ticket_performance', [])}

Proporciona:
1. Identificación de empleados destacados
2. Áreas de oportunidad para mejora
3. Recomendaciones para capacitación
4. Sugerencias para incentivos y reconocimientos

Enfócate en insights accionables para el administrador.
"""
        
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Error generando análisis de empleados: {str(e)}"

# =============================================================================
# RUTAS DEL ASISTENTE IA
# =============================================================================

@ia_admin.route("/")
@login_required
def dashboard():
    """Dashboard del asistente IA para administradores"""
    if current_user.id_rol != 1:
        return "Acceso no autorizado", 403
    
    return render_template("administrador/IAadmin.html", now=datetime.now())

@ia_admin.route("/context")
@login_required
def context():
    """Obtener contexto del sistema para el IA"""
    if current_user.id_rol != 1:
        return jsonify({'success': False, 'error': 'Acceso no autorizado'}), 403
    
    try:
        context = get_ia_system_context()
        return jsonify({
            'success': True,
            'context': context
        })
    except Exception as e:
        print(f"Error obteniendo contexto IA: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ia_admin.route("/chat", methods=["POST"])
@login_required
def chat():
    """Endpoint para chat con IA"""
    if current_user.id_rol != 1:
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
        context = get_ia_system_context()
        financial_data = get_ia_financial_data()
        performance_data = get_ia_employee_performance()
        
        # Generar respuesta con Gemini
        response = generate_ia_response(user_message, context, financial_data, performance_data)
        
        return jsonify({
            'success': True,
            'response': response
        })
        
    except Exception as e:
        print(f"Error en chat IA: {e}")
        # Respuesta de respaldo en caso de error
        backup_response = f"""🤖 **Asistente Administrativo**

Actualmente estoy experimentando dificultades técnicas con el servicio de IA. Mientras tanto, puedo proporcionarle información básica del sistema:

📊 **Estado Actual:**
• Empleados activos: {context.get('active_employees', 'N/A') if 'context' in locals() else 'N/A'}
• Residentes: {context.get('total_residents', 'N/A') if 'context' in locals() else 'N/A'}
• Tickets pendientes: {context.get('open_tickets', 'N/A') if 'context' in locals() else 'N/A'}

💡 **Sugerencias Inmediatas:**
1. Revise el dashboard financiero para análisis detallado
2. Consulte los reportes de nómina en la sección correspondiente
3. Verifique el estado de tickets en el módulo de soporte

El equipo técnico está trabajando para restaurar el servicio completo."""
        
        return jsonify({
            'success': True,
            'response': backup_response
        })

@ia_admin.route("/financial-report")
@login_required
def financial_report():
    """Generar reporte financiero con IA"""
    if current_user.id_rol != 1:
        return jsonify({'success': False, 'error': 'Acceso no autorizado'}), 403
    
    try:
        financial_data = get_ia_financial_data()
        report = generate_financial_report_ia(financial_data)
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ia_admin.route("/employee-analysis")
@login_required
def employee_analysis():
    """Generar análisis de empleados con IA"""
    if current_user.id_rol != 1:
        return jsonify({'success': False, 'error': 'Acceso no autorizado'}), 403
    
    try:
        performance_data = get_ia_employee_performance()
        analysis = generate_employee_analysis_ia(performance_data)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500