from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from db import get_db_connection

empleados_bp = Blueprint("empleados", __name__)

# ================================
# DASHBOARD DEL EMPLEADO
# ================================
@empleados_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.id_rol != 2:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Datos del empleado logueado - USAR current_user.id (que es id_usuario)
        cursor.execute("""
            SELECT u.nombre, u.ap_paterno, u.ap_materno, e.puesto, e.salario
            FROM usuario u
            JOIN empleado e ON u.id_usuario = e.id_usuario
            WHERE u.id_usuario = %s
        """, (current_user.id,))  # ← Cambiar a current_user.id
        empleado = cursor.fetchone()

        # Total de tickets asignados
        cursor.execute("SELECT COUNT(*) FROM ticket WHERE id_empleado = %s", (current_user.id,))  # ← Cambiar aquí
        total_tickets = cursor.fetchone()[0]

        # Total de mantenimientos asignados
        cursor.execute("SELECT COUNT(*) FROM mantenimiento WHERE id_empleado = %s", (current_user.id,))  # ← Cambiar aquí
        total_mantenimientos = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return render_template(
            "empleado/dashboard.html",
            empleado=empleado,
            total_tickets=total_tickets,
            total_mantenimientos=total_mantenimientos
        )

    except Exception as e:
        print(f"❌ Error cargando dashboard empleado: {e}")
        flash("Error al cargar el panel del empleado.", "danger")
        return render_template("empleado/dashboard.html")

# ================================
# TICKETS ASIGNADOS
# ================================
@empleados_bp.route("/tickets")
@login_required
def tickets():
    if current_user.id_rol != 2:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # MOSTRAR TODOS LOS TICKETS ASIGNADOS (todos los estados)
        cursor.execute("""
            SELECT t.id_ticket, t.descripcion, t.prioridad, t.estado,
                   TO_CHAR(t.fecha_emision, 'DD/MM/YYYY HH24:MI') as fecha_emision,
                   TO_CHAR(t.fecha_finalizacion, 'DD/MM/YYYY HH24:MI') as fecha_finalizacion,
                   d.piso, d.nro,
                   (SELECT u.nombre || ' ' || u.ap_paterno FROM usuario u WHERE u.id_usuario = t.id_usuario) AS residente
            FROM ticket t
            JOIN departamento d ON t.id_departamento = d.id_departamento
            WHERE t.id_empleado = %s
            ORDER BY 
                CASE 
                    WHEN t.estado = 'en_progreso' THEN 1
                    WHEN t.estado = 'abierto' THEN 2
                    WHEN t.estado = 'cerrado' THEN 3
                    WHEN t.estado = 'cancelado' THEN 4
                    ELSE 5
                END,
                CASE 
                    WHEN t.prioridad = 'urgente' THEN 1
                    WHEN t.prioridad = 'alta' THEN 2
                    WHEN t.prioridad = 'media' THEN 3
                    WHEN t.prioridad = 'baja' THEN 4
                    ELSE 5
                END,
                t.fecha_emision DESC
        """, (current_user.id,))
        tickets = cursor.fetchall()

        # DEBUG: Ver qué tickets se obtuvieron
        print(f"🔍 DEBUG: Total tickets obtenidos para usuario {current_user.id}: {len(tickets)}")
        for ticket in tickets:
            print(f"  - Ticket {ticket[0]}: {ticket[1]} | Estado: {ticket[3]} | Prioridad: {ticket[2]}")

        cursor.close()
        conn.close()

        return render_template("empleado/tickets.html", tickets=tickets)
    except Exception as e:
        print(f"❌ Error obteniendo tickets: {e}")
        flash("Error al cargar los tickets.", "danger")
        return render_template("empleado/tickets.html", tickets=[])
# ================================
# MANTENIMIENTOS
# ================================
@empleados_bp.route("/mantenimientos")
@login_required
def mantenimientos():
    if current_user.id_rol != 2:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT m.id_mantenimiento, m.descripcion, 
                   TO_CHAR(m.fecha_programada, 'DD/MM/YYYY'), 
                   m.estado, d.piso, d.nro
            FROM mantenimiento m
            JOIN departamento d ON m.id_departamento = d.id_departamento
            WHERE m.id_empleado = %s
            ORDER BY m.fecha_programada DESC
        """, (current_user.id,))  # ← Cambiar aquí
        mantenimientos = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template("empleado/mantenimientos.html", mantenimientos=mantenimientos)

    except Exception as e:
        print(f"❌ Error obteniendo mantenimientos: {e}")
        flash("Error al cargar los mantenimientos.", "danger")
        return render_template("empleado/mantenimientos.html", mantenimientos=[])

# ================================
# REPORTES (Tickets + Mantenimientos)
# ================================
@empleados_bp.route("/reportes")
@login_required
def reportes():
    if current_user.id_rol != 2:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Tickets agrupados por estado
        cursor.execute("""
            SELECT estado, COUNT(*) 
            FROM ticket 
            WHERE id_empleado = %s 
            GROUP BY estado
        """, (current_user.id,))  # ← Cambiar aquí
        reporte_tickets = cursor.fetchall()

        # Mantenimientos agrupados por estado
        cursor.execute("""
            SELECT estado, COUNT(*) 
            FROM mantenimiento 
            WHERE id_empleado = %s 
            GROUP BY estado
        """, (current_user.id,))  # ← Cambiar aquí
        reporte_mantenimientos = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "empleado/reportes.html",
            reporte_tickets=reporte_tickets,
            reporte_mantenimientos=reporte_mantenimientos
        )

    except Exception as e:
        print(f"❌ Error generando reportes: {e}")
        flash("Error al generar los reportes.", "danger")
        return render_template("empleado/reportes.html")

# ================================
# CONSUMOS (si tienes tabla consumo)
# ================================
@empleados_bp.route("/consumos")
@login_required
def consumos():
    if current_user.id_rol != 2:
        flash("Acceso no autorizado.", "danger")
        return redirect(url_for("auth.login"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT d.id_departamento, d.piso, d.nro,
                   COALESCE(c.tipo, 'Sin registro'), COALESCE(c.valor, 0), 
                   TO_CHAR(c.fecha, 'DD/MM/YYYY')
            FROM departamento d
            LEFT JOIN consumo c ON d.id_departamento = c.id_departamento
            ORDER BY d.piso
        """)
        consumos = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template("empleado/consumo.html", consumos=consumos)

    except Exception as e:
        print(f"❌ Error obteniendo consumos: {e}")
        flash("Error al cargar los consumos.", "danger")
        return render_template("empleado/consumo.html", consumos=[])