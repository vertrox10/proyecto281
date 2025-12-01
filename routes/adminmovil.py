from flask import Blueprint, jsonify, request
from datetime import datetime, date
import sys
import os
import traceback

# Agregar el directorio raíz al path de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar después de agregar al path
try:
    from db import get_db_connection
    from jwt_decorators import jwt_required
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")

# Crear Blueprint para API móvil del admin
# ✅ CAMBIAR EL NOMBRE Y PREFIJO DEL BLUEPRINT
admin_movil_bp = Blueprint('admin_movil', __name__, url_prefix='/admin')

def calcular_tiempo_relativo(fecha):
    """Calcular tiempo relativo para mostrar en actividades"""
    if not fecha:
        return "Recientemente"
    
    ahora = datetime.now()
    
    # Si la fecha es un string, convertirla a datetime
    if isinstance(fecha, str):
        try:
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S.%f'):
                try:
                    fecha = datetime.strptime(fecha, fmt)
                    break
                except ValueError:
                    continue
        except:
            return "Recientemente"
    
    # Si es date (no datetime), convertir a datetime
    if isinstance(fecha, date) and not isinstance(fecha, datetime):
        fecha = datetime.combine(fecha, datetime.min.time())
    
    diferencia = ahora - fecha
    
    if diferencia.days > 0:
        if diferencia.days == 1:
            return "Hace 1 día"
        elif diferencia.days < 7:
            return f"Hace {diferencia.days} días"
        elif diferencia.days < 30:
            semanas = diferencia.days // 7
            return f"Hace {semanas} semana{'s' if semanas > 1 else ''}"
        else:
            meses = diferencia.days // 30
            return f"Hace {meses} mes{'es' if meses > 1 else ''}"
    else:
        segundos = diferencia.seconds
        if segundos < 60:
            return "Hace unos segundos"
        elif segundos < 3600:
            minutos = segundos // 60
            return f"Hace {minutos} minuto{'s' if minutos > 1 else ''}"
        else:
            horas = segundos // 3600
            return f"Hace {horas} hora{'s' if horas > 1 else ''}"

# Health check endpoint
@admin_movil_bp.route("/api/health")
def api_health():
    """Endpoint para verificar que la API está funcionando"""
    return jsonify({"status": "ok", "message": "API funcionando"})

# ✅ DASHBOARD - URL CORREGIDA: /admin/api/dashboard
@admin_movil_bp.route("/api/dashboard")
@jwt_required
def api_dashboard():
    """Endpoint API para el dashboard de Flutter"""
    print("🎯 Dashboard API accedido - Iniciando...")
    
    # ✅ VERIFICAR ROL USANDO JWT
    current_user_id = request.current_user_id
    current_user_role = getattr(request, 'current_user_role', None)
    
    print(f"🔐 Usuario: {current_user_id}, Rol: {current_user_role}")
    
    if current_user_role != 1:  # 1 = Administrador
        return jsonify({
            "success": False,
            "error": "Acceso no autorizado. Se requiere rol de administrador"
        }), 403
    
    conn = None
    cursor = None
    
    try:
        print("🔗 Intentando conectar a la base de datos...")
        
        conn = get_db_connection()
        
        if conn is None:
            print("❌ Error: No se pudo conectar a la BD")
            return jsonify({
                "success": False,
                "error": "Error de conexión a la base de datos"
            }), 500
        
        print("✅ Conexión a BD establecida")
        cursor = conn.cursor()
        
        # Obtener estadísticas principales
        total_usuarios = 0
        tickets_pendientes = 0
        tickets_urgentes = 0
        total_tickets = 0
        reservas_activas = 0
        reservas_hoy = 0
        
        # Consulta para total de usuarios
        try:
            cursor.execute("SELECT COUNT(*) FROM usuario")
            result = cursor.fetchone()
            total_usuarios = result[0] if result else 0
            print(f"✅ Total usuarios: {total_usuarios}")
        except Exception as e:
            print(f"❌ Error contando usuarios: {str(e)}")
            total_usuarios = 0
        
        # Consulta para tickets pendientes
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM ticket 
                WHERE estado IN ('Abierto', 'En Progreso', 'Pendiente')
            """)
            result = cursor.fetchone()
            tickets_pendientes = result[0] if result else 0
            print(f"✅ Tickets pendientes: {tickets_pendientes}")
        except Exception as e:
            print(f"❌ Error contando tickets pendientes: {str(e)}")
            tickets_pendientes = 0
        
        # Consulta para tickets urgentes
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM ticket 
                WHERE prioridad = 'Alta' AND estado IN ('Abierto', 'En Progreso', 'Pendiente')
            """)
            result = cursor.fetchone()
            tickets_urgentes = result[0] if result else 0
            print(f"✅ Tickets urgentes: {tickets_urgentes}")
        except Exception as e:
            print(f"❌ Error contando tickets urgentes: {str(e)}")
            tickets_urgentes = 0
        
        # Consulta para total de tickets
        try:
            cursor.execute("SELECT COUNT(*) FROM ticket")
            result = cursor.fetchone()
            total_tickets = result[0] if result else 0
            print(f"✅ Total tickets: {total_tickets}")
        except Exception as e:
            print(f"❌ Error contando total tickets: {str(e)}")
            total_tickets = 0
        
        # Consulta para reservas activas
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM reserva 
                WHERE estado = 'Activa' OR estado = 'Confirmada'
            """)
            result = cursor.fetchone()
            reservas_activas = result[0] if result else 0
            print(f"✅ Reservas activas: {reservas_activas}")
        except Exception as e:
            print(f"❌ Error contando reservas activas: {str(e)}")
            reservas_activas = 0
        
        # Consulta para reservas hoy
        try:
            today = date.today().isoformat()
            cursor.execute("""
                SELECT COUNT(*) FROM reserva 
                WHERE fecha_reserva = %s
            """, (today,))
            result = cursor.fetchone()
            reservas_hoy = result[0] if result else 0
            print(f"✅ Reservas hoy: {reservas_hoy}")
        except Exception as e:
            print(f"❌ Error contando reservas hoy: {str(e)}")
            reservas_hoy = 0
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "data": {
                "total_usuarios": total_usuarios,
                "tickets_pendientes": tickets_pendientes,
                "tickets_urgentes": tickets_urgentes,
                "total_tickets": total_tickets,
                "reservas_activas": reservas_activas,
                "reservas_hoy": reservas_hoy
            }
        })
        
    except Exception as e:
        print(f"💥 ERROR en api_dashboard: {str(e)}")
        traceback.print_exc()
        
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
        return jsonify({
            "success": False,
            "error": f"Error interno: {str(e)}"
        }), 500

# ✅ USUARIOS - URL CORREGIDA: /admin/api/usuarios
@admin_movil_bp.route("/api/usuarios")
@jwt_required
def api_usuarios():
    """Endpoint API para obtener usuarios"""
    current_user_role = getattr(request, 'current_user_role', None)
    
    if current_user_role != 1:
        return jsonify({
            "success": False,
            "error": "Acceso no autorizado"
        }), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id_usuario, nombre, correo, telefono, id_rol
            FROM usuario
            ORDER BY id_usuario DESC
        """)
        
        usuarios = []
        for row in cursor.fetchall():
            # Determinar nombre del rol
            rol_nombre = "Desconocido"
            if row[4] == 1:
                rol_nombre = "Administrador"
            elif row[4] == 2:
                rol_nombre = "Empleado"
            elif row[4] == 3:
                rol_nombre = "Residente"
                
            usuarios.append({
                'id_usuario': row[0],
                'nombre': row[1] or 'Sin nombre',
                'email': row[2] or 'Sin email',
                'telefono': row[3] or 'Sin teléfono',
                'rol': rol_nombre
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "data": usuarios
        })
        
    except Exception as e:
        print(f"Error obteniendo usuarios: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error al obtener usuarios: {str(e)}"
        }), 500

# ✅ COMUNICADOS - URL CORREGIDA: /admin/api/comunicados
@admin_movil_bp.route("/api/comunicados")
@jwt_required
def api_comunicados():
    """Endpoint API para obtener comunicados"""
    current_user_role = getattr(request, 'current_user_role', None)
    
    if current_user_role != 1:
        return jsonify({
            "success": False,
            "error": "Acceso no autorizado"
        }), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id_comunicado, titulo, contenido, fecha_publicacion
            FROM comunicado
            ORDER BY fecha_publicacion DESC
        """)
        
        comunicados = []
        for row in cursor.fetchall():
            comunicados.append({
                'id_comunicado': row[0],
                'titulo': row[1] or 'Sin título',
                'contenido': row[2] or 'Sin contenido',
                'fecha_publicacion': str(row[3]) if row[3] else 'No especificada',
                'tiempo_relativo': calcular_tiempo_relativo(row[3])
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "data": comunicados
        })
        
    except Exception as e:
        print(f"Error obteniendo comunicados: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error al obtener comunicados: {str(e)}"
        }), 500

# ✅ CREAR COMUNICADO - URL CORREGIDA: /admin/api/comunicados
@admin_movil_bp.route("/api/comunicados", methods=["POST"])
@jwt_required
def crear_comunicado():
    """Endpoint API para crear un nuevo comunicado"""
    current_user_role = getattr(request, 'current_user_role', None)
    
    if current_user_role != 1:
        return jsonify({
            "success": False,
            "error": "Acceso no autorizado"
        }), 403
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Datos JSON requeridos"
            }), 400
            
        if not data.get('titulo') or not data.get('contenido'):
            return jsonify({
                "success": False,
                "error": "Título y contenido son requeridos"
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO comunicado (titulo, contenido, fecha_publicacion)
            VALUES (%s, %s, NOW())
        """, (data['titulo'], data['contenido']))
        
        conn.commit()
        comunicado_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Comunicado creado exitosamente",
            "id_comunicado": comunicado_id
        })
        
    except Exception as e:
        print(f"Error creando comunicado: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error al crear comunicado: {str(e)}"
        }), 500

# ✅ TICKETS - URL CORREGIDA: /admin/api/tickets
@admin_movil_bp.route("/api/tickets")
@jwt_required
def api_tickets():
    """Endpoint API para obtener tickets"""
    current_user_role = getattr(request, 'current_user_role', None)
    
    if current_user_role != 1:
        return jsonify({
            "success": False,
            "error": "Acceso no autorizado"
        }), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.id_ticket, t.titulo, t.descripcion, t.estado, t.prioridad, 
                   t.fecha_creacion, u.nombre as usuario_nombre
            FROM ticket t
            LEFT JOIN usuario u ON t.id_usuario = u.id_usuario
            ORDER BY t.fecha_creacion DESC
        """)
        
        tickets = []
        for row in cursor.fetchall():
            tickets.append({
                'id_ticket': row[0],
                'titulo': row[1] or 'Sin título',
                'descripcion': row[2] or 'Sin descripción',
                'estado': row[3] or 'Desconocido',
                'prioridad': row[4] or 'Media',
                'fecha_creacion': str(row[5]) if row[5] else 'No especificada',
                'usuario_nombre': row[6] or 'Usuario anónimo',
                'tiempo_relativo': calcular_tiempo_relativo(row[5])
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "data": tickets
        })
        
    except Exception as e:
        print(f"Error obteniendo tickets: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error al obtener tickets: {str(e)}"
        }), 500

# ✅ RESERVAS - URL CORREGIDA: /admin/api/reservas
@admin_movil_bp.route("/api/reservas")
@jwt_required
def api_reservas():
    """Endpoint API para obtener reservas"""
    current_user_role = getattr(request, 'current_user_role', None)
    
    if current_user_role != 1:
        return jsonify({
            "success": False,
            "error": "Acceso no autorizado"
        }), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT r.id_reserva, a.nombre as area, u.nombre as usuario_nombre,
                   r.fecha_reserva, r.hora_inicio, r.hora_fin, r.estado
            FROM reserva r
            LEFT JOIN area a ON r.id_area = a.id_area
            LEFT JOIN usuario u ON r.id_usuario = u.id_usuario
            ORDER BY r.fecha_reserva DESC
        """)
        
        reservas = []
        for row in cursor.fetchall():
            reservas.append({
                'id_reserva': row[0],
                'area': row[1] or 'Área no especificada',
                'usuario_nombre': row[2] or 'Usuario anónimo',
                'fecha_reserva': str(row[3]) if row[3] else 'No especificada',
                'hora_inicio': str(row[4]) if row[4] else '',
                'hora_fin': str(row[5]) if row[5] else '',
                'estado': row[6] or 'Pendiente'
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "data": reservas
        })
        
    except Exception as e:
        print(f"Error obteniendo reservas: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error al obtener reservas: {str(e)}"
        }), 500

# ✅ ELIMINAR USUARIO - URL CORREGIDA: /admin/api/usuarios/<id>
@admin_movil_bp.route("/api/usuarios/<int:usuario_id>", methods=["DELETE"])
@jwt_required
def eliminar_usuario(usuario_id):
    """Endpoint API para eliminar un usuario"""
    current_user_role = getattr(request, 'current_user_role', None)
    
    if current_user_role != 1:
        return jsonify({
            "success": False,
            "error": "Acceso no autorizado"
        }), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el usuario existe
        cursor.execute("SELECT id_usuario FROM usuario WHERE id_usuario = %s", (usuario_id,))
        if not cursor.fetchone():
            return jsonify({
                "success": False,
                "error": "Usuario no encontrado"
            }), 404
        
        # Eliminar usuario
        cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (usuario_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Usuario eliminado exitosamente"
        })
        
    except Exception as e:
        print(f"Error eliminando usuario: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error al eliminar usuario: {str(e)}"
        }), 500

# ✅ ACTUALIZAR TICKET - URL CORREGIDA: /admin/api/tickets/<id>/estado
@admin_movil_bp.route("/api/tickets/<int:ticket_id>/estado", methods=["PUT"])
@jwt_required
def actualizar_estado_ticket(ticket_id):
    """Endpoint API para actualizar el estado de un ticket"""
    current_user_role = getattr(request, 'current_user_role', None)
    
    if current_user_role != 1:
        return jsonify({
            "success": False,
            "error": "Acceso no autorizado"
        }), 403
    
    try:
        data = request.get_json()
        
        if not data or not data.get('estado'):
            return jsonify({
                "success": False,
                "error": "Estado es requerido"
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el ticket existe
        cursor.execute("SELECT id_ticket FROM ticket WHERE id_ticket = %s", (ticket_id,))
        if not cursor.fetchone():
            return jsonify({
                "success": False,
                "error": "Ticket no encontrado"
            }), 404
        
        # Actualizar estado
        cursor.execute("""
            UPDATE ticket 
            SET estado = %s, fecha_actualizacion = NOW()
            WHERE id_ticket = %s
        """, (data['estado'], ticket_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Estado del ticket actualizado exitosamente"
        })
        
    except Exception as e:
        print(f"Error actualizando ticket: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error al actualizar ticket: {str(e)}"
        }), 500