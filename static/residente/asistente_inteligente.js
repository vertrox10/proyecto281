class AsistenteResidente {
    constructor() {
        this.usuarioId = usuarioId;
        this.usuarioNombre = usuarioNombre;
        this.departamento = departamento;
        this.inicializarEventos();
    }

    inicializarEventos() {
        this.mostrarTyping = this.mostrarTyping.bind(this);
        this.ocultarTyping = this.ocultarTyping.bind(this);
    }

    // Enviar mensaje al servidor
    async enviarMensaje(mensaje) {
        try {
            this.mostrarTyping();
            
            const response = await fetch('/asistente-inteligente/procesar-mensaje', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    usuario_id: this.usuarioId,
                    mensaje: mensaje,
                    departamento: this.departamento
                })
            });

            const data = await response.json();
            this.ocultarTyping();
            
            if (data.success) {
                this.mostrarRespuestaAgente(data.respuesta, data.tipo_respuesta);
            } else {
                this.mostrarError('Error al procesar la solicitud');
            }
        } catch (error) {
            this.ocultarTyping();
            this.mostrarError('Error de conexión con el servidor');
        }
    }

    // Mostrar indicador de typing
    mostrarTyping() {
        const chatMessages = document.getElementById('chatMessages');
        const typingIndicator = `
            <div class="message agent" id="typingIndicator">
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', typingIndicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Ocultar indicador de typing
    ocultarTyping() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    // Mostrar respuesta del agente
    mostrarRespuestaAgente(respuesta, tipo = 'texto') {
        const chatMessages = document.getElementById('chatMessages');
        const timestamp = new Date().toLocaleTimeString('es-ES', { 
            hour: '2-digit', minute: '2-digit' 
        });

        let contenido = '';
        
        if (tipo === 'consumo') {
            contenido = this.formatearRespuestaConsumo(respuesta);
        } else if (tipo === 'reserva') {
            contenido = this.formatearRespuestaReserva(respuesta);
        } else if (tipo === 'ticket') {
            contenido = this.formatearRespuestaTicket(respuesta);
        } else if (tipo === 'pago') {
            contenido = this.formatearRespuestaPago(respuesta);
        } else {
            contenido = `<p>${respuesta}</p>`;
        }

        const mensajeHTML = `
            <div class="message agent">
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    ${contenido}
                    <span class="message-time">${timestamp}</span>
                </div>
            </div>
        `;

        chatMessages.insertAdjacentHTML('beforeend', mensajeHTML);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Formatear respuesta de consumo
    formatearRespuestaConsumo(datos) {
        return `
            <h4>📊 Consumo Actual</h4>
            <div class="consumo-details">
                <p><strong>Agua:</strong> ${datos.agua || '--'} m³</p>
                <p><strong>Luz:</strong> ${datos.luz || '--'} kWh</p>
                <p><strong>Gas:</strong> ${datos.gas || '--'} m³</p>
                <p><strong>Período:</strong> ${datos.periodo || '--'}</p>
            </div>
            <p><em>${datos.mensaje || ''}</em></p>
        `;
    }

    // Formatear respuesta de reserva
    formatearRespuestaReserva(datos) {
        return `
            <h4>📅 Reserva de Área Común</h4>
            <div class="reserva-details">
                <p><strong>Área:</strong> ${datos.area || '--'}</p>
                <p><strong>Fecha:</strong> ${datos.fecha || '--'}</p>
                <p><strong>Hora:</strong> ${datos.hora || '--'}</p>
                <p><strong>Estado:</strong> ${datos.estado || '--'}</p>
            </div>
            <p><em>${datos.mensaje || ''}</em></p>
        `;
    }

    // Formatear respuesta de ticket
    formatearRespuestaTicket(datos) {
        return `
            <h4>🎫 Ticket de Soporte</h4>
            <div class="ticket-details">
                <p><strong>ID:</strong> ${datos.id || '--'}</p>
                <p><strong>Tipo:</strong> ${datos.tipo || '--'}</p>
                <p><strong>Prioridad:</strong> ${datos.prioridad || '--'}</p>
                <p><strong>Estado:</strong> ${datos.estado || '--'}</p>
            </div>
            <p><em>${datos.mensaje || ''}</em></p>
        `;
    }

    // Formatear respuesta de pago
    formatearRespuestaPago(datos) {
        return `
            <h4>💳 Información de Pago</h4>
            <div class="pago-details">
                <p><strong>Monto:</strong> $${datos.monto || '--'}</p>
                <p><strong>Vencimiento:</strong> ${datos.vencimiento || '--'}</p>
                <p><strong>Estado:</strong> ${datos.estado || '--'}</p>
                <p><strong>Método:</strong> ${datos.metodo || '--'}</p>
            </div>
            <p><em>${datos.mensaje || ''}</em></p>
        `;
    }

    // Mostrar mensaje de error
    mostrarError(mensaje) {
        const chatMessages = document.getElementById('chatMessages');
        const timestamp = new Date().toLocaleTimeString('es-ES', { 
            hour: '2-digit', minute: '2-digit' 
        });

        const mensajeHTML = `
            <div class="message agent">
                <div class="message-avatar">🤖</div>
                <div class="message-content" style="background: #f8d7da; color: #721c24;">
                    <p>❌ ${mensaje}</p>
                    <span class="message-time">${timestamp}</span>
                </div>
            </div>
        `;

        chatMessages.insertAdjacentHTML('beforeend', mensajeHTML);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Mostrar mensaje del usuario
    mostrarMensajeUsuario(mensaje) {
        const chatMessages = document.getElementById('chatMessages');
        const timestamp = new Date().toLocaleTimeString('es-ES', { 
            hour: '2-digit', minute: '2-digit' 
        });

        const mensajeHTML = `
            <div class="message user">
                <div class="message-avatar">👤</div>
                <div class="message-content">
                    <p>${mensaje}</p>
                    <span class="message-time">${timestamp}</span>
                </div>
            </div>
        `;

        chatMessages.insertAdjacentHTML('beforeend', mensajeHTML);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Instanciar el asistente
const asistente = new AsistenteResidente();

// Funciones globales para el HTML
function sugerirAccion(accion) {
    document.getElementById('userInput').value = accion;
    sendMessage();
}

function sendMessage() {
    const userInput = document.getElementById('userInput');
    const mensaje = userInput.value.trim();
    
    if (mensaje) {
        asistente.mostrarMensajeUsuario(mensaje);
        asistente.enviarMensaje(mensaje);
        userInput.value = '';
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function logout() {
    if (confirm('¿Estás seguro de que quieres salir?')) {
        window.location.href = '/logout';
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Focus en el input al cargar
    document.getElementById('userInput').focus();
});