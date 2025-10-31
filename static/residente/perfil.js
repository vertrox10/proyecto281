// perfil.js - Funcionalidades para la página de perfil

document.addEventListener('DOMContentLoaded', function() {
    console.log('Página de perfil cargada');
    inicializarPreferencias();
    inicializarFormularios();
});

function inicializarPreferencias() {
    const preferencias = JSON.parse(localStorage.getItem('preferencias_usuario')) || {
        notifPagos: true,
        notifTickets: true,
        notifReservas: true
    };

    Object.keys(preferencias).forEach(key => {
        const checkbox = document.getElementById(key);
        if (checkbox) {
            checkbox.checked = preferencias[key];
        }
    });

    document.querySelectorAll('.switch input').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            guardarPreferencias();
        });
    });
}

function guardarPreferencias() {
    const preferencias = {
        notifPagos: document.getElementById('notifPagos').checked,
        notifTickets: document.getElementById('notifTickets').checked,
        notifReservas: document.getElementById('notifReservas').checked
    };

    localStorage.setItem('preferencias_usuario', JSON.stringify(preferencias));
    mostrarMensaje('Preferencias guardadas correctamente', 'success');
}

function inicializarFormularios() {
    const formEditar = document.getElementById('formEditar');
    const formPassword = document.getElementById('formPassword');

    if (formEditar) {
        formEditar.addEventListener('submit', function(e) {
            e.preventDefault();
            guardarInformacionPersonal();
        });
    }

    if (formPassword) {
        formPassword.addEventListener('submit', function(e) {
            e.preventDefault();
            cambiarContraseña();
        });
    }
}

function abrirModalEditar() {
    document.getElementById('modalEditar').style.display = 'block';
}

function cerrarModalEditar() {
    document.getElementById('modalEditar').style.display = 'none';
}

function abrirModalCambiarPassword() {
    document.getElementById('modalPassword').style.display = 'block';
}

function cerrarModalPassword() {
    document.getElementById('modalPassword').style.display = 'none';
    document.getElementById('formPassword').reset();
}

async function guardarInformacionPersonal() {
    const formData = {
        nombre: document.getElementById('editNombre').value,
        ap_paterno: document.getElementById('editApPaterno').value,
        ap_materno: document.getElementById('editApMaterno').value,
        telefono: document.getElementById('editTelefono').value,
        ci: document.getElementById('editCI').value
    };

    try {
        const response = await fetch('/residentes/api/actualizar_perfil', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        
        if (result.success) {
            cerrarModalEditar();
            mostrarMensaje('Información actualizada correctamente', 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            mostrarMensaje(result.message || 'Error al actualizar', 'error');
        }

    } catch (error) {
        console.error('Error:', error);
        mostrarMensaje('Error al actualizar la información', 'error');
    }
}

async function cambiarContraseña() {
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    if (newPassword !== confirmPassword) {
        mostrarMensaje('Las contraseñas no coinciden', 'error');
        return;
    }

    if (newPassword.length < 6) {
        mostrarMensaje('La contraseña debe tener al menos 6 caracteres', 'error');
        return;
    }

    try {
        const response = await fetch('/residentes/api/cambiar_password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });

        const result = await response.json();
        
        if (result.success) {
            cerrarModalPassword();
            mostrarMensaje('Contraseña cambiada correctamente', 'success');
        } else {
            mostrarMensaje(result.message || 'Error al cambiar contraseña', 'error');
        }

    } catch (error) {
        console.error('Error:', error);
        mostrarMensaje('Error al cambiar la contraseña', 'error');
    }
}

async function cerrarSesionesOtrosDispositivos() {
    if (!confirm('¿Estás seguro de que quieres cerrar todas las demás sesiones activas?')) {
        return;
    }

    try {
        const response = await fetch('/residentes/api/cerrar_otras_sesiones', { 
            method: 'POST' 
        });
        
        const result = await response.json();
        
        if (result.success) {
            mostrarMensaje('Otras sesiones cerradas correctamente', 'success');
        } else {
            mostrarMensaje(result.message || 'Error al cerrar sesiones', 'error');
        }
        
    } catch (error) {
        console.error('Error:', error);
        mostrarMensaje('Error al cerrar otras sesiones', 'error');
    }
}

function mostrarMensaje(mensaje, tipo) {
    const mensajeDiv = document.createElement('div');
    mensajeDiv.className = `alert alert-${tipo} mensaje-temporal`;
    mensajeDiv.innerHTML = `
        <i class="fas fa-${tipo === 'success' ? 'check-circle' : 'exclamation-triangle'}"></i>
        ${mensaje}
    `;

    const mainContent = document.querySelector('.main-content');
    mainContent.insertBefore(mensajeDiv, mainContent.firstChild);

    setTimeout(() => {
        if (mensajeDiv.parentNode) {
            mensajeDiv.parentNode.removeChild(mensajeDiv);
        }
    }, 5000);
}

window.onclick = function(event) {
    const modals = ['modalEditar', 'modalPassword'];
    modals.forEach(modalId => {
        const modal = document.getElementById(modalId);
        if (event.target === modal) {
            if (modalId === 'modalEditar') {
                cerrarModalEditar();
            } else if (modalId === 'modalPassword') {
                cerrarModalPassword();
            }
        }
    });
}

document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        cerrarModalEditar();
        cerrarModalPassword();
    }
});