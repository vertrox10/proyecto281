// perfil.js - Gestión del perfil del residente
document.addEventListener('DOMContentLoaded', function() {
    inicializarEventos();
    cargarPreferencias();
});

function inicializarEventos() {
    // Event listener para fuerza de contraseña
    const passwordInput = document.querySelector('input[name="password_nueva"]');
    if (passwordInput) {
        passwordInput.addEventListener('input', verificarFuerzaPassword);
    }
    
    // Event listener para confirmación de contraseña
    const confirmInput = document.querySelector('input[name="password_confirm"]');
    if (confirmInput) {
        confirmInput.addEventListener('input', verificarCoincidenciaPassword);
    }
}

// Funciones para la gestión del perfil
function editarPerfil() {
    const infoGrid = document.querySelector('.info-grid');
    const campos = infoGrid.querySelectorAll('.info-item p');
    const boton = document.querySelector('.perfil-section .btn-outline');
    
    // Habilitar edición de campos
    campos.forEach(campo => {
        const valor = campo.textContent.trim();
        const label = campo.previousElementSibling.textContent.toLowerCase();
        let tipoInput = 'text';
        
        // Determinar tipo de input según el campo
        if (label.includes('correo')) {
            tipoInput = 'email';
        } else if (label.includes('teléfono')) {
            tipoInput = 'tel';
        }
        
        campo.innerHTML = `
            <input type="${tipoInput}" class="form-control edit-input" value="${valor}" 
                   data-field="${getFieldName(label)}"
                   ${label.includes('correo') ? 'readonly' : ''}>
        `;
    });
    
    // Cambiar botón de editar a guardar/cancelar
    boton.innerHTML = `
        <button class="btn btn-primary" onclick="guardarPerfil()">
            <i class="fas fa-save"></i> Guardar
        </button>
        <button class="btn btn-secondary" onclick="cancelarEdicion()">
            <i class="fas fa-times"></i> Cancelar
        </button>
    `;
}

function getFieldName(label) {
    const mapping = {
        'nombre completo': 'nombre_completo',
        'correo electrónico': 'correo',
        'teléfono': 'telefono',
        'fecha de registro': 'fecha_registro'
    };
    return mapping[label] || label.replace(' ', '_');
}

function cancelarEdicion() {
    location.reload();
}

async function guardarPerfil() {
    const inputs = document.querySelectorAll('.edit-input');
    const datos = {};
    
    // Recoger datos del formulario
    inputs.forEach(input => {
        const field = input.getAttribute('data-field');
        datos[field] = input.value;
    });
    
    // Validaciones básicas
    if (datos.telefono && !validarTelefono(datos.telefono)) {
        mostrarAlerta('Por favor ingrese un número de teléfono válido', 'error');
        return;
    }
    
    try {
        const response = await fetch('/residentes/api/actualizar_perfil', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(datos)
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarAlerta('Perfil actualizado exitosamente', 'success');
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            throw new Error(data.message || 'Error al actualizar el perfil');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta(error.message, 'error');
    }
}

function cambiarAvatar() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = async function(e) {
        const file = e.target.files[0];
        if (file) {
            // Validar tipo y tamaño de archivo
            if (!file.type.startsWith('image/')) {
                mostrarAlerta('Por favor seleccione una imagen válida', 'error');
                return;
            }
            
            if (file.size > 5 * 1024 * 1024) { // 5MB
                mostrarAlerta('La imagen no debe superar los 5MB', 'error');
                return;
            }
            
            // Mostrar preview
            const reader = new FileReader();
            reader.onload = function(e) {
                const avatar = document.querySelector('.avatar-placeholder');
                avatar.innerHTML = `<img src="${e.target.result}" alt="Avatar" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
            };
            reader.readAsDataURL(file);
            
            // Aquí podrías subir la imagen al servidor
            // await subirAvatar(file);
            mostrarAlerta('Avatar actualizado exitosamente', 'success');
        }
    };
    input.click();
}

async function subirAvatar(file) {
    const formData = new FormData();
    formData.append('avatar', file);
    
    try {
        const response = await fetch('/residentes/api/subir_avatar', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Error al subir el avatar');
        }
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}

// Gestión de métodos de pago
function agregarMetodoPago() {
    // Redirigir a la sección de pagos o mostrar modal
    window.location.href = '/residentes/mis_pagos#agregar-metodo';
}

function editarMetodo(id) {
    // Implementar edición de método de pago
    console.log('Editando método de pago:', id);
    // Podrías mostrar un modal similar al de agregar pero con datos precargados
}

async function eliminarMetodo(id) {
    if (!confirm('¿Está seguro de que desea eliminar este método de pago?')) {
        return;
    }
    
    try {
        const response = await fetch(`/residentes/api/eliminar_metodo_pago/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarAlerta('Método de pago eliminado exitosamente', 'success');
            // Remover el elemento del DOM
            document.querySelector(`[data-metodo-id="${id}"]`)?.remove();
        } else {
            throw new Error(data.message || 'Error al eliminar el método de pago');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta(error.message, 'error');
    }
}

// Gestión de contraseña
function mostrarModalPassword() {
    document.getElementById('modalPassword').style.display = 'flex';
    // Resetear indicadores de fuerza
    actualizarFuerzaPassword(0, 'Seguridad de la contraseña');
}

function cerrarModalPassword() {
    document.getElementById('modalPassword').style.display = 'none';
    document.getElementById('formPassword').reset();
    actualizarFuerzaPassword(0, 'Seguridad de la contraseña');
}

function verificarFuerzaPassword() {
    const password = document.querySelector('input[name="password_nueva"]').value;
    const fuerza = calcularFuerzaPassword(password);
    actualizarFuerzaPassword(fuerza.puntaje, fuerza.mensaje);
}

function calcularFuerzaPassword(password) {
    let puntaje = 0;
    let mensaje = '';
    
    if (password.length >= 8) puntaje += 25;
    if (password.length >= 12) puntaje += 15;
    
    // Verificar caracteres diversos
    if (/[a-z]/.test(password)) puntaje += 10;
    if (/[A-Z]/.test(password)) puntaje += 15;
    if (/[0-9]/.test(password)) puntaje += 15;
    if (/[^a-zA-Z0-9]/.test(password)) puntaje += 20;
    
    // Verificar patrones comunes (restar puntos)
    if (/(.)\1{2,}/.test(password)) puntaje -= 10; // Caracteres repetidos
    if (/123|abc|password/i.test(password)) puntaje -= 20; // Patrones simples
    
    // Determinar mensaje según puntaje
    if (puntaje >= 80) {
        mensaje = 'Muy segura';
    } else if (puntaje >= 60) {
        mensaje = 'Segura';
    } else if (puntaje >= 40) {
        mensaje = 'Moderada';
    } else if (puntaje >= 20) {
        mensaje = 'Débil';
    } else {
        mensaje = 'Muy débil';
    }
    
    return { puntaje, mensaje };
}

function actualizarFuerzaPassword(puntaje, mensaje) {
    const fill = document.getElementById('strengthFill');
    const text = document.getElementById('strengthText');
    
    fill.style.width = `${puntaje}%`;
    text.textContent = mensaje;
    
    // Cambiar color según fuerza
    if (puntaje >= 80) {
        fill.style.background = '#7A8C6E'; // Verde oliva
    } else if (puntaje >= 60) {
        fill.style.background = '#A3C8D6'; // Celeste
    } else if (puntaje >= 40) {
        fill.style.background = '#E3A78C'; // Durazno
    } else {
        fill.style.background = '#dc3545'; // Rojo
    }
}

function verificarCoincidenciaPassword() {
    const password = document.querySelector('input[name="password_nueva"]').value;
    const confirm = document.querySelector('input[name="password_confirm"]').value;
    const confirmInput = document.querySelector('input[name="password_confirm"]');
    
    if (confirm && password !== confirm) {
        confirmInput.style.borderColor = '#dc3545';
        confirmInput.title = 'Las contraseñas no coinciden';
    } else if (confirm) {
        confirmInput.style.borderColor = '#7A8C6E';
        confirmInput.title = 'Las contraseñas coinciden';
    } else {
        confirmInput.style.borderColor = '';
        confirmInput.title = '';
    }
}

async function cambiarPassword() {
    const formData = new FormData(document.getElementById('formPassword'));
    const datos = Object.fromEntries(formData);
    
    // Validaciones
    if (!datos.password_actual) {
        mostrarAlerta('Por favor ingrese su contraseña actual', 'error');
        return;
    }
    
    if (!datos.password_nueva) {
        mostrarAlerta('Por favor ingrese la nueva contraseña', 'error');
        return;
    }
    
    if (datos.password_nueva.length < 8) {
        mostrarAlerta('La nueva contraseña debe tener al menos 8 caracteres', 'error');
        return;
    }
    
    if (datos.password_nueva !== datos.password_confirm) {
        mostrarAlerta('Las contraseñas no coinciden', 'error');
        return;
    }
    
    try {
        const response = await fetch('/residentes/api/cambiar_password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(datos)
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarAlerta('Contraseña cambiada exitosamente', 'success');
            cerrarModalPassword();
        } else {
            throw new Error(data.message || 'Error al cambiar la contraseña');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta(error.message, 'error');
    }
}

// Gestión de preferencias de notificación
async function actualizarConfig(clave, valor) {
    try {
        const response = await fetch('/residentes/api/actualizar_config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                clave: clave,
                valor: valor
            })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            // Revertir el cambio en la UI si falla
            const checkbox = document.querySelector(`input[onchange*="${clave}"]`);
            if (checkbox) {
                checkbox.checked = !valor;
            }
            throw new Error(data.message || 'Error al actualizar la configuración');
        }
        
        mostrarAlerta('Configuración actualizada', 'success', 2000);
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta(error.message, 'error');
    }
}

async function cargarPreferencias() {
    try {
        const response = await fetch('/residentes/api/obtener_config');
        const data = await response.json();
        
        if (data.success) {
            // Actualizar switches según las preferencias
            Object.keys(data.config).forEach(clave => {
                const checkbox = document.querySelector(`input[onchange*="${clave}"]`);
                if (checkbox) {
                    checkbox.checked = data.config[clave];
                }
            });
        }
    } catch (error) {
        console.error('Error cargando preferencias:', error);
    }
}

// Gestión de sesiones
function verSesiones() {
    // Implementar vista de sesiones activas
    console.log('Mostrando sesiones activas');
    // Podrías mostrar un modal con las sesiones activas
}

// Utilidades
function validarTelefono(telefono) {
    const regex = /^[\+]?[591]{0,3}?[0-9\s\-\(\)]{7,15}$/;
    return regex.test(telefono);
}

function mostrarAlerta(mensaje, tipo = 'info', duracion = 3000) {
    // Remover alertas existentes
    const alertasExistentes = document.querySelectorAll('.alert-flotante');
    alertasExistentes.forEach(alerta => alerta.remove());
    
    const alerta = document.createElement('div');
    alerta.className = `alert-flotante alert-${tipo}`;
    alerta.innerHTML = `
        <div class="alert-content">
            <i class="fas ${getIconoAlerta(tipo)}"></i>
            <span>${mensaje}</span>
            <button onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    document.body.appendChild(alerta);
    
    // Mostrar con animación
    setTimeout(() => {
        alerta.classList.add('show');
    }, 10);
    
    // Auto-remover después de la duración
    if (duracion > 0) {
        setTimeout(() => {
            if (alerta.parentElement) {
                alerta.classList.remove('show');
                setTimeout(() => {
                    if (alerta.parentElement) {
                        alerta.remove();
                    }
                }, 300);
            }
        }, duracion);
    }
    
    return alerta;
}

function getIconoAlerta(tipo) {
    const iconos = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    };
    return iconos[tipo] || 'fa-info-circle';
}

// Cerrar modales al hacer clic fuera
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
};

// Cerrar con ESC
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (modal.style.display === 'flex') {
                modal.style.display = 'none';
            }
        });
    }
});