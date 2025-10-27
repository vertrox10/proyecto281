// finanzas.js - Sistema de Gestión de Pagos y Cobros

// =============================================
// VARIABLES GLOBALES
// =============================================

let conceptosState = [];
let empleadosMap = {};

// =============================================
// SISTEMA DE EMPLEADOS - PAGOS
// =============================================

function inicializarSistemaEmpleados() {
    const selectEmpleado = document.getElementById('select-empleado');
    const metodoPago = document.getElementById('metodo-pago');
    const campoTransferencia = document.getElementById('campo-transferencia');
    
    if (!selectEmpleado) return;
    
    // Obtener datos de empleados del atributo data
    try {
        const empleadosData = JSON.parse(selectEmpleado.dataset.empleados || '[]');
        empleadosMap = {};
        
        empleadosData.forEach(emp => {
            empleadosMap[emp.id_usuario] = {
                salario: emp.salario,
                banco: emp.banco,
                cuenta: emp.numero_cuenta,
                puesto: emp.puesto
            };
        });
        
        console.log('Datos de empleados cargados:', empleadosMap);
    } catch (error) {
        console.error('Error al cargar datos de empleados:', error);
    }
    
    // Event listeners
    selectEmpleado.addEventListener('change', actualizarInfoEmpleado);
    if (metodoPago) {
        metodoPago.addEventListener('change', mostrarCampoTransferencia);
    }
    
    // Ejecutar al cargar
    actualizarInfoEmpleado();
    mostrarCampoTransferencia();
}

function actualizarInfoEmpleado() {
    const selectEmpleado = document.getElementById('select-empleado');
    const empleadoId = selectEmpleado.value;
    const infoEmpleado = document.getElementById('info-empleado');
    
    if (empleadosMap[empleadoId] && infoEmpleado) {
        const empleado = empleadosMap[empleadoId];
        
        // Actualizar información en la UI
        document.getElementById('salario-base').textContent = `Bs ${empleado.salario.toFixed(2)}`;
        document.getElementById('banco-empleado').textContent = empleado.banco;
        document.getElementById('cuenta-empleado').textContent = empleado.cuenta;
        
        // Actualizar monto automáticamente
        const inputMonto = document.getElementById('input-monto');
        if (inputMonto) {
            inputMonto.value = empleado.salario.toFixed(2);
        }
        
        infoEmpleado.style.display = 'block';
    }
}

function mostrarCampoTransferencia() {
    const metodoPago = document.getElementById('metodo-pago');
    const campoTransferencia = document.getElementById('campo-transferencia');
    
    if (metodoPago && campoTransferencia) {
        if (metodoPago.value === 'transferencia') {
            campoTransferencia.style.display = 'block';
            
            // Mostrar advertencia si no hay datos bancarios
            const empleadoId = document.getElementById('select-empleado').value;
            if (empleadosMap[empleadoId] && empleadosMap[empleadoId].cuenta === 'No registrada') {
                mostrarNotificacion('⚠️ Este empleado no tiene número de cuenta registrado', 'warning');
            }
        } else {
            campoTransferencia.style.display = 'none';
        }
    }
}

// =============================================
// SISTEMA DE COBROS - RESIDENTES
// =============================================

function inicializarSistemaCobros() {
    // Inicializar mensaje
    actualizarMensaje();
    
    // Event listeners para residentes
    const selectResidente = document.getElementById("select-residente");
    if (selectResidente) {
        selectResidente.addEventListener('change', actualizarMensaje);
    }
    
    // Event listeners para botones
    const btnAgregarConcepto = document.getElementById('btn-agregar-concepto');
    const btnEliminarConcepto = document.getElementById('btn-eliminar-concepto');
    const btnRegistrarEnviar = document.getElementById('btn-registrar-enviar');
    
    if (btnAgregarConcepto) {
        btnAgregarConcepto.addEventListener('click', agregarConcepto);
    }
    if (btnEliminarConcepto) {
        btnEliminarConcepto.addEventListener('click', eliminarUltimoConcepto);
    }
    if (btnRegistrarEnviar) {
        btnRegistrarEnviar.addEventListener('click', registrarYEnviar);
    }
    
    // Validación del formulario de cobros
    const formCobros = document.getElementById('form-cobros');
    if (formCobros) {
        formCobros.addEventListener('submit', validarFormularioCobros);
    }
    
    console.log('Sistema de cobros inicializado');
}

function agregarConcepto() {
    const container = document.getElementById("conceptos-container");
    const nuevo = document.createElement("div");
    nuevo.className = "concepto-item";
    nuevo.innerHTML = `
        <input type="text" name="concepto[]" placeholder="Ej. Servicio adicional" 
               class="form-input concepto-input" required>
        <input type="number" step="0.01" name="monto[]" placeholder="0.00" 
               class="form-input monto-input" required>
        <button type="button" class="btn-eliminar-concepto" title="Eliminar concepto">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Agregar event listeners a los nuevos inputs
    const inputs = nuevo.querySelectorAll('input');
    inputs.forEach(input => {
        input.addEventListener('input', actualizarMensaje);
    });
    
    // Agregar event listener al botón de eliminar
    const btnEliminar = nuevo.querySelector('.btn-eliminar-concepto');
    btnEliminar.addEventListener('click', function() {
        eliminarConcepto(this);
    });
    
    container.appendChild(nuevo);
    actualizarMensaje();
}

function eliminarConcepto(element) {
    const conceptoItem = element.closest('.concepto-item');
    const container = document.getElementById("conceptos-container");
    const items = container.getElementsByClassName('concepto-item');
    
    if (items.length > 1) {
        container.removeChild(conceptoItem);
        actualizarMensaje();
    } else {
        mostrarNotificacion('Debe haber al menos un concepto de cobro registrado.', 'warning');
    }
}

function eliminarUltimoConcepto() {
    const container = document.getElementById("conceptos-container");
    const items = container.getElementsByClassName('concepto-item');
    
    if (items.length > 1) {
        const ultimoItem = items[items.length - 1];
        const btnEliminar = ultimoItem.querySelector('.btn-eliminar-concepto');
        eliminarConcepto(btnEliminar);
    } else {
        mostrarNotificacion('Debe haber al menos un concepto de cobro registrado.', 'warning');
    }
}

function actualizarMensaje() {
    const selectResidente = document.getElementById("select-residente");
    if (!selectResidente) return;
    
    const nombreResidente = selectResidente.options[selectResidente.selectedIndex].text;
    const conceptos = document.querySelectorAll("input[name='concepto[]']");
    const montos = document.querySelectorAll("input[name='monto[]']");
    
    let total = 0;
    let conceptosValidos = [];
    
    // Procesar conceptos y montos
    for (let i = 0; i < conceptos.length; i++) {
        const concepto = conceptos[i].value.trim();
        const monto = parseFloat(montos[i].value);
        
        if (concepto && !isNaN(monto) && monto > 0) {
            conceptosValidos.push({ concepto, monto });
            total += monto;
        }
    }
    
    // Generar mensaje
    let mensaje = `Estimado/a ${nombreResidente},\n\n`;
    mensaje += `Se han registrado los siguientes cobros por uso del edificio:\n\n`;
    
    if (conceptosValidos.length > 0) {
        conceptosValidos.forEach(item => {
            mensaje += `• ${item.concepto}: Bs ${item.monto.toFixed(2)}\n`;
        });
        
        mensaje += `\n💰 Total a pagar: Bs ${total.toFixed(2)}\n\n`;
        mensaje += `Fecha límite de pago: ${obtenerFechaLimite()}\n\n`;
        mensaje += `Métodos de pago disponibles:\n`;
        mensaje += `• Transferencia bancaria\n`;
        mensaje += `• Efectivo en administración\n`;
        mensaje += `• QR de pago\n\n`;
    } else {
        mensaje += `No se han registrado conceptos de cobro válidos.\n\n`;
    }
    
    mensaje += `Agradecemos su puntualidad en el pago.\n\n`;
    mensaje += `Atentamente,\n`;
    mensaje += `Administración del Edificio`;
    
    const mensajeTextarea = document.getElementById("mensaje-residente");
    if (mensajeTextarea) {
        mensajeTextarea.value = mensaje;
    }
}

function obtenerFechaLimite() {
    const hoy = new Date();
    const fechaLimite = new Date(hoy);
    fechaLimite.setDate(hoy.getDate() + 7);
    
    return fechaLimite.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

function registrarYEnviar() {
    const formCobros = document.getElementById('form-cobros');
    const selectResidente = document.getElementById("select-residente");
    
    if (!formCobros || !selectResidente) return;
    
    const idUsuario = selectResidente.value;
    const mensajeTextarea = document.getElementById("mensaje-residente");
    const mensaje = mensajeTextarea ? mensajeTextarea.value.trim() : '';
    
    // Validaciones
    if (!mensaje) {
        mostrarNotificacion('El mensaje está vacío. Por favor, agregue conceptos de cobro primero.', 'error');
        return false;
    }
    
    const conceptos = document.querySelectorAll("input[name='concepto[]']");
    let conceptosValidos = false;
    
    for (let i = 0; i < conceptos.length; i++) {
        const concepto = conceptos[i].value.trim();
        const monto = parseFloat(document.querySelectorAll("input[name='monto[]']")[i].value);
        
        if (concepto && !isNaN(monto) && monto > 0) {
            conceptosValidos = true;
            break;
        }
    }
    
    if (!conceptosValidos) {
        mostrarNotificacion('Debe agregar al menos un concepto de cobro válido antes de enviar.', 'warning');
        return false;
    }
    
    // Primero registrar los cobros
    mostrarNotificacion('Registrando cobros...', 'info');
    
    // Crear un formulario temporal para enviar el mensaje
    const formData = new FormData();
    formData.append('id_usuario', idUsuario);
    formData.append('mensaje', mensaje);
    
    // Enviar primero el formulario de cobros
    fetch(formCobros.action, {
        method: 'POST',
        body: new FormData(formCobros)
    })
    .then(response => {
        if (response.ok) {
            // Si los cobros se registran bien, enviar el mensaje
            return fetch(formCobros.dataset.urlEnviarMensaje || "/enviar_mensaje_residente", {
                method: 'POST',
                body: formData
            });
        } else {
            throw new Error('Error al registrar cobros');
        }
    })
    .then(response => {
        if (response.ok) {
            mostrarNotificacion('✅ Cobros registrados y mensaje enviado correctamente', 'success');
            // Recargar después de 2 segundos
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            throw new Error('Error al enviar mensaje');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarNotificacion('❌ Error en el proceso: ' + error.message, 'error');
    });
}

function validarFormularioCobros(e) {
    const conceptos = document.querySelectorAll("input[name='concepto[]']");
    let conceptosValidos = false;
    
    for (let i = 0; i < conceptos.length; i++) {
        const concepto = conceptos[i].value.trim();
        const monto = parseFloat(document.querySelectorAll("input[name='monto[]']")[i].value);
        
        if (concepto && !isNaN(monto) && monto > 0) {
            conceptosValidos = true;
            break;
        }
    }
    
    if (!conceptosValidos) {
        e.preventDefault();
        mostrarNotificacion('Debe agregar al menos un concepto de cobro válido antes de registrar.', 'warning');
    } else {
        mostrarNotificacion('Registrando cobros...', 'info');
    }
}

// =============================================
// SISTEMA DE NOTIFICACIONES
// =============================================

function mostrarNotificacion(mensaje, tipo = 'info') {
    // Buscar si ya existe una notificación
    const notificacionesExistentes = document.querySelectorAll('.toast-notification');
    notificacionesExistentes.forEach(notif => notif.remove());
    
    // Crear notificación
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${tipo}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas ${obtenerIconoTipo(tipo)}"></i>
            <span>${mensaje}</span>
        </div>
        <button class="toast-close">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Agregar event listener al botón de cerrar
    const btnCerrar = toast.querySelector('.toast-close');
    btnCerrar.addEventListener('click', function() {
        toast.remove();
    });
    
    document.body.appendChild(toast);
    
    // Auto-eliminar después de 5 segundos
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 5000);
}

function obtenerIconoTipo(tipo) {
    const iconos = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    };
    return iconos[tipo] || 'fa-info-circle';
}

// =============================================
// INICIALIZACIÓN GENERAL
// =============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando sistema de finanzas...');
    
    // Inicializar sistema de empleados
    inicializarSistemaEmpleados();
    
    // Inicializar sistema de cobros
    inicializarSistemaCobros();
    
    console.log('Sistema de finanzas inicializado correctamente');
});