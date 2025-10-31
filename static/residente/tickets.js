// tickets.js - Funcionalidades para la gestión de tickets

document.addEventListener('DOMContentLoaded', function() {
    console.log('Página de tickets cargada');
    inicializarEventos();
});

function inicializarEventos() {
    // Inicializar tooltips si es necesario
    inicializarTooltips();
    
    // Configurar eventos de los botones de acción
    configurarEventosBotones();
}

function inicializarTooltips() {
    // Inicializar tooltips de Bootstrap si están disponibles
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

function configurarEventosBotones() {
    // Los eventos ya están configurados en los onclick de los botones en el HTML
    console.log('Eventos de botones configurados');
}

// Ver detalles de un ticket
async function verDetallesTicket(ticketId) {
    try {
        console.log(`Solicitando detalles del ticket: ${ticketId}`);
        
        const response = await fetch(`/residentes/api/tickets/${ticketId}`);
        const result = await response.json();
        
        if (result.success) {
            mostrarDetallesTicket(result);
        } else {
            alert('Error: ' + result.message);
        }
    } catch (error) {
        console.error('Error obteniendo detalles del ticket:', error);
        alert('Error al cargar los detalles del ticket');
    }
}

// Mostrar detalles del ticket en modal
function mostrarDetallesTicket(data) {
    const modal = document.getElementById('modalDetallesTicket');
    const content = document.getElementById('detallesTicketContent');
    
    const ticket = data.ticket;
    const comentarios = data.comentarios || [];
    const archivos = data.archivos || [];
    
    content.innerHTML = `
        <div class="detalles-ticket">
            <!-- Información Principal -->
            <div class="seccion-detalles">
                <h4>Información del Ticket</h4>
                <div class="info-grid">
                    <div class="info-item">
                        <label>ID del Ticket:</label>
                        <span>#${ticket.id_ticket}</span>
                    </div>
                    <div class="info-item">
                        <label>Estado:</label>
                        <span class="ticket-estado ${ticket.estado}">${ticket.estado}</span>
                    </div>
                    <div class="info-item">
                        <label>Prioridad:</label>
                        <span class="ticket-prioridad ${ticket.prioridad}">${ticket.prioridad}</span>
                    </div>
                    <div class="info-item">
                        <label>Fecha de Creación:</label>
                        <span>${ticket.fecha_emision}</span>
                    </div>
                    ${ticket.fecha_finalizacion ? `
                    <div class="info-item">
                        <label>Fecha de Finalización:</label>
                        <span>${ticket.fecha_finalizacion}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
            
            <!-- Descripción -->
            <div class="seccion-detalles">
                <h4>Descripción</h4>
                <div class="descripcion-content">
                    <p>${ticket.descripcion}</p>
                </div>
            </div>
            
            <!-- Ubicación -->
            <div class="seccion-detalles">
                <h4>Ubicación</h4>
                <div class="info-grid">
                    <div class="info-item">
                        <label>Piso:</label>
                        <span>${ticket.piso}</span>
                    </div>
                    <div class="info-item">
                        <label>Departamento:</label>
                        <span>${ticket.nro_departamento}</span>
                    </div>
                    ${ticket.area_nombre ? `
                    <div class="info-item">
                        <label>Área:</label>
                        <span>${ticket.area_nombre}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
            
            <!-- Asignación -->
            ${ticket.empleado_asignado ? `
            <div class="seccion-detalles">
                <h4>Personal Asignado</h4>
                <div class="asignacion-info">
                    <p><strong>Empleado:</strong> ${ticket.empleado_asignado}</p>
                </div>
            </div>
            ` : ''}
            
            <!-- Comentarios -->
            <div class="seccion-detalles">
                <h4>Comentarios (${comentarios.length})</h4>
                ${comentarios.length > 0 ? `
                <div class="comentarios-list">
                    ${comentarios.map(comentario => `
                    <div class="comentario-item">
                        <div class="comentario-header">
                            <strong>${comentario.autor}</strong>
                            <span class="comentario-fecha">${comentario.fecha}</span>
                        </div>
                        <div class="comentario-mensaje">
                            <p>${comentario.mensaje}</p>
                        </div>
                    </div>
                    `).join('')}
                </div>
                ` : `
                <div class="no-comentarios">
                    <p>No hay comentarios aún.</p>
                </div>
                `}
                
                <!-- Formulario para nuevo comentario -->
                <div class="nuevo-comentario">
                    <h5>Agregar Comentario</h5>
                    <form id="formNuevoComentario" onsubmit="agregarComentario(event, ${ticket.id_ticket})">
                        <div class="form-group">
                            <textarea id="mensajeComentario" rows="3" placeholder="Escribe tu comentario..." required></textarea>
                        </div>
                        <button type="submit" class="btn-enviar-comentario">
                            <i class="fas fa-paper-plane"></i> Enviar Comentario
                        </button>
                    </form>
                </div>
            </div>
            
            <!-- Archivos Adjuntos -->
            ${archivos.length > 0 ? `
            <div class="seccion-detalles">
                <h4>Archivos Adjuntos (${archivos.length})</h4>
                <div class="archivos-list">
                    ${archivos.map(archivo => `
                    <div class="archivo-item">
                        <i class="fas fa-file-${archivo.tipo === 'pdf' ? 'pdf' : 'image'}"></i>
                        <div class="archivo-info">
                            <span class="archivo-nombre">${archivo.nombre}</span>
                            <span class="archivo-fecha">${archivo.fecha_subida}</span>
                        </div>
                        <a href="${archivo.url}" target="_blank" class="btn-descargar">
                            <i class="fas fa-download"></i>
                        </a>
                    </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}
        </div>
    `;
    
    modal.style.display = 'block';
}

// Cerrar modal de detalles
function cerrarModalDetalles() {
    document.getElementById('modalDetallesTicket').style.display = 'none';
}

// Agregar comentario a un ticket
async function agregarComentario(event, ticketId) {
    event.preventDefault();
    
    const mensaje = document.getElementById('mensajeComentario').value;
    
    if (!mensaje.trim()) {
        alert('Por favor escribe un mensaje');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('mensaje', mensaje);
        
        const response = await fetch(`/residentes/ticket/${ticketId}/comentario`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            // Recargar los detalles del ticket para mostrar el nuevo comentario
            verDetallesTicket(ticketId);
            document.getElementById('mensajeComentario').value = '';
        } else {
            alert('Error al agregar el comentario');
        }
    } catch (error) {
        console.error('Error agregando comentario:', error);
        alert('Error al agregar el comentario');
    }
}

// Cancelar un ticket
async function cancelarTicket(ticketId) {
    if (!confirm('¿Estás seguro de que quieres cancelar este ticket? Esta acción no se puede deshacer.')) {
        return;
    }
    
    try {
        const response = await fetch(`/residentes/api/tickets/${ticketId}/cancelar`, {
            method: 'PUT'
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Ticket cancelado correctamente');
            location.reload(); // Recargar la página para actualizar la lista
        } else {
            alert('Error: ' + result.message);
        }
    } catch (error) {
        console.error('Error cancelando ticket:', error);
        alert('Error al cancelar el ticket');
    }
}

// Cerrar modales al hacer click fuera
window.onclick = function(event) {
    const modal = document.getElementById('modalDetallesTicket');
    if (event.target === modal) {
        cerrarModalDetalles();
    }
}

// Manejar tecla Escape para cerrar modales
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        cerrarModalDetalles();
    }
});

// Función para formatear fechas
function formatearFecha(fecha) {
    if (!fecha) return 'N/A';
    
    const date = new Date(fecha);
    return date.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}