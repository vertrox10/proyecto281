// residente.js - Funciones JavaScript para residentes

document.addEventListener('DOMContentLoaded', function() {
    console.log('Sistema de residentes cargado');
    
    // Inicializar tooltips si se usan
    const tooltips = document.querySelectorAll('[data-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        // Aquí puedes inicializar tooltips si usas Bootstrap
    });
    
    // Manejar notificaciones
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// Función para mostrar notificaciones
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-flotante show`;
    notification.innerHTML = `
        <div class="alert-content">
            <i class="fas fa-${type === 'success' ? 'check' : 'exclamation'}-circle"></i>
            <span>${message}</span>
            <button onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Función para confirmaciones
function confirmAction(message) {
    return confirm(message);
}