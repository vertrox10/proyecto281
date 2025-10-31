// residente.js - Funcionalidades generales para residentes

document.addEventListener('DOMContentLoaded', function() {
    console.log('Sistema de residentes cargado');
    inicializarComponentes();
});

function inicializarComponentes() {
    // Inicializar tooltips de Bootstrap si están disponibles
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Manejar alerts automáticos
    manejarAlerts();
}

function manejarAlerts() {
    // Auto-ocultar alerts después de 5 segundos
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.style.opacity = '0';
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.parentNode.removeChild(alert);
                    }
                }, 300);
            }
        }, 5000);
    });
}

// Función para mostrar loading en botones
function mostrarLoading(boton, texto = 'Procesando...') {
    const originalText = boton.innerHTML;
    boton.innerHTML = `
        <i class="fas fa-spinner fa-spin"></i>
        ${texto}
    `;
    boton.disabled = true;
    
    return () => {
        boton.innerHTML = originalText;
        boton.disabled = false;
    };
}

// Función para formatear fechas
function formatearFecha(fecha) {
    if (!fecha) return 'N/A';
    
    const date = new Date(fecha);
    return date.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

// Función para formatear montos
function formatearMonto(monto) {
    if (!monto) return '0.00';
    
    return parseFloat(monto).toFixed(2);
}

// Manejar errores de fetch
function manejarErrorFetch(error) {
    console.error('Error en la solicitud:', error);
    alert('Error de conexión. Por favor, intenta nuevamente.');
}

// Validar email
function validarEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

// Validar teléfono
function validarTelefono(telefono) {
    const regex = /^[0-9+\-\s()]{7,15}$/;
    return regex.test(telefono);
}