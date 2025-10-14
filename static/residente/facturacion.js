// facturacion.js - Gestión de facturación del residente
document.addEventListener('DOMContentLoaded', function() {
    inicializarFacturacion();
    inicializarFiltros();
    inicializarGraficosFacturacion();
});

function inicializarFacturacion() {
    console.log('Sistema de facturación inicializado');
}

function inicializarFiltros() {
    // Event listeners para filtros
    const filtros = ['filtroAnio', 'filtroMes', 'filtroEstado', 'filtroTipo'];
    
    filtros.forEach(filtroId => {
        const elemento = document.getElementById(filtroId);
        if (elemento) {
            elemento.addEventListener('change', aplicarFiltrosFacturas);
        }
    });
}

function aplicarFiltrosFacturas() {
    const anio = document.getElementById('filtroAnio').value;
    const mes = document.getElementById('filtroMes').value;
    const estado = document.getElementById('filtroEstado').value;
    const tipo = document.getElementById('filtroTipo').value;
    
    console.log('Aplicando filtros:', { anio, mes, estado, tipo });
    
    // Aquí iría la lógica para filtrar las facturas
    // Por ahora simulamos el filtrado
    const facturas = document.querySelectorAll('.factura-card');
    
    facturas.forEach(factura => {
        let mostrar = true;
        
        // Filtrar por estado
        if (estado && !factura.classList.contains(estado)) {
            mostrar = false;
        }
        
        // Filtrar por tipo (simulado)
        if (tipo) {
            const concepto = factura.querySelector('h3').textContent.toLowerCase();
            if (tipo === 'alquiler' && !concepto.includes('alquiler')) {
                mostrar = false;
            } else if (tipo === 'servicios' && !concepto.includes('servicio')) {
                mostrar = false;
            }
        }
        
        factura.style.display = mostrar ? 'block' : 'none';
    });
    
    // Mostrar mensaje si no hay resultados
    const facturasVisibles = document.querySelectorAll('.factura-card[style="display: block"]');
    const mensajeNoResultados = document.getElementById('mensajeNoResultados');
    
    if (facturasVisibles.length === 0) {
        if (!mensajeNoResultados) {
            const mensaje = document.createElement('div');
            mensaje.id = 'mensajeNoResultados';
            mensaje.className = 'no-resultados';
            mensaje.innerHTML = `
                <i class="fas fa-search"></i>
                <h4>No se encontraron facturas</h4>
                <p>No hay facturas que coincidan con los filtros aplicados</p>
            `;
            document.querySelector('.facturas-list').appendChild(mensaje);
        }
    } else if (mensajeNoResultados) {
        mensajeNoResultados.remove();
    }
}

// Funciones para acciones de facturas
function realizarPago(idFactura) {
    if (!idFactura || idFactura === 0) {
        mostrarAlertaFactura('Error: ID de factura no válido', 'error');
        return;
    }
    
    console.log('Iniciando pago para factura:', idFactura);
    
    // Simular integración con pasarela de pago
    const metodosPago = [
        { id: 'tigo_money', nombre: 'Tigo Money', icono: 'fa-mobile-alt' },
        { id: 'billetera_virtual', nombre: 'Billetera Virtual', icono: 'fa-wallet' },
        { id: 'criptomoneda', nombre: 'Criptomoneda', icono: 'fa-coins' },
        { id: 'tarjeta', nombre: 'Tarjeta', icono: 'fa-credit-card' }
    ];
    
    // Crear modal de selección de método de pago
    const modalHTML = `
        <div class="modal" id="modalMetodoPago">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Seleccionar Método de Pago</h3>
                    <button class="btn-icon" onclick="cerrarModal('modalMetodoPago')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <div class="metodos-pago-grid">
                        ${metodosPago.map(metodo => `
                            <div class="metodo-pago-item" onclick="procesarPago(${idFactura}, '${metodo.id}')">
                                <div class="metodo-icon">
                                    <i class="fas ${metodo.icono}"></i>
                                </div>
                                <span>${metodo.nombre}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="cerrarModal('modalMetodoPago')">
                        Cancelar
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Agregar modal al DOM
    if (!document.getElementById('modalMetodoPago')) {
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }
    
    document.getElementById('modalMetodoPago').style.display = 'flex';
}

function cerrarModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

async function procesarPago(idFactura, metodo) {
    console.log('Procesando pago:', { idFactura, metodo });
    
    // Cerrar modal de selección
    cerrarModal('modalMetodoPago');
    
    // Mostrar loader
    mostrarAlertaFactura('Procesando pago...', 'info', 0);
    
    try {
        const response = await fetch('/residentes/api/realizar_pago', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id_factura: idFactura,
                metodo: metodo,
                monto: obtenerMontoFactura(idFactura)
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarAlertaFactura('Pago realizado exitosamente', 'success');
            
            // Actualizar UI
            setTimeout(() => {
                location.reload();
            }, 2000);
            
        } else {
            throw new Error(data.message || 'Error al procesar el pago');
        }
        
    } catch (error) {
        console.error('Error procesando pago:', error);
        mostrarAlertaFactura(error.message, 'error');
    }
}

function obtenerMontoFactura(idFactura) {
    // Buscar el monto en la factura correspondiente
    const factura = document.querySelector(`[data-factura-id="${idFactura}"]`);
    if (factura) {
        const montoText = factura.querySelector('.monto').textContent;
        return parseFloat(montoText.replace('$', '').replace(',', ''));
    }
    return 0;
}

function descargarFactura(idFactura) {
    if (!idFactura || idFactura === 0) {
        mostrarAlertaFactura('Error: ID de factura no válido', 'error');
        return;
    }
    
    console.log('Descargando factura:', idFactura);
    
    // Simular descarga
    mostrarAlertaFactura('Generando PDF de factura...', 'info');
    
    setTimeout(() => {
        // En un caso real, esto descargaría el archivo
        const enlace = document.createElement('a');
        enlace.href = `/residentes/descargar_factura/${idFactura}`;
        enlace.download = `factura_${idFactura}.pdf`;
        enlace.click();
        
        mostrarAlertaFactura('Factura descargada exitosamente', 'success');
    }, 1500);
}

function verQR(idFactura) {
    if (!idFactura || idFactura === 0) {
        mostrarAlertaFactura('Error: ID de factura no válido', 'error');
        return;
    }
    
    console.log('Mostrando QR para factura:', idFactura);
    
    // Obtener datos de la factura
    const factura = document.querySelector(`.factura-card[data-factura-id="${idFactura}"]`);
    if (!factura) {
        mostrarAlertaFactura('No se encontró la factura', 'error');
        return;
    }
    
    const numero = factura.querySelector('.factura-nro').textContent;
    const monto = factura.querySelector('.monto').textContent;
    const vencimiento = factura.querySelector('.factura-vencimiento').textContent.replace('Vence: ', '');
    
    // Actualizar información en el modal
    document.getElementById('qrFacturaNumero').textContent = numero;
    document.getElementById('qrFacturaMonto').textContent = monto.replace('$', '');
    document.getElementById('qrFacturaVencimiento').textContent = vencimiento;
    
    // Generar QR
    generarQR(idFactura, numero, monto);
    
    // Mostrar modal
    document.getElementById('modalQR').style.display = 'flex';
}

function generarQR(idFactura, numero, monto) {
    const canvas = document.getElementById('qrCanvas');
    const contexto = canvas.getContext('2d');
    
    // Limpiar canvas
    contexto.clearRect(0, 0, canvas.width, canvas.height);
    
    // Datos para el QR
    const qrData = {
        factura: numero,
        monto: monto,
        id: idFactura,
        timestamp: new Date().toISOString()
    };
    
    const qrTexto = JSON.stringify(qrData);
    
    // Simular generación de QR (en un caso real usarías una librería como qrcode.js)
    contexto.fillStyle = '#264653';
    contexto.font = '16px Arial';
    contexto.textAlign = 'center';
    contexto.fillText('CÓDIGO QR', canvas.width / 2, 30);
    
    contexto.font = '12px Arial';
    contexto.fillText(`Factura: ${numero}`, canvas.width / 2, 60);
    contexto.fillText(`Monto: ${monto}`, canvas.width / 2, 80);
    contexto.fillText('(Simulación QR)', canvas.width / 2, 120);
    
    // Dibujar un QR simulado
    contexto.strokeStyle = '#264653';
    contexto.lineWidth = 2;
    contexto.strokeRect(50, 100, 100, 100);
    
    // Patrón de puntos simulado
    contexto.fillStyle = '#264653';
    for (let i = 0; i < 7; i++) {
        for (let j = 0; j < 7; j++) {
            if (Math.random() > 0.5) {
                contexto.fillRect(60 + i * 12, 110 + j * 12, 8, 8);
            }
        }
    }
}

function descargarQR() {
    const canvas = document.getElementById('qrCanvas');
    const enlace = document.createElement('a');
    
    enlace.href = canvas.toDataURL('image/png');
    enlace.download = `qr_factura_${document.getElementById('qrFacturaNumero').textContent}.png`;
    enlace.click();
    
    mostrarAlertaFactura('QR descargado exitosamente', 'success');
}

function cerrarModalQR() {
    document.getElementById('modalQR').style.display = 'none';
}

function descargarComprobante(idPago) {
    if (!idPago || idPago === 0) {
        mostrarAlertaFactura('Error: ID de pago no válido', 'error');
        return;
    }
    
    console.log('Descargando comprobante de pago:', idPago);
    
    // Simular descarga
    mostrarAlertaFactura('Generando comprobante...', 'info');
    
    setTimeout(() => {
        const enlace = document.createElement('a');
        enlace.href = `/residentes/descargar_comprobante/${idPago}`;
        enlace.download = `comprobante_pago_${idPago}.pdf`;
        enlace.click();
        
        mostrarAlertaFactura('Comprobante descargado exitosamente', 'success');
    }, 1000);
}

function descargarTodasFacturas() {
    console.log('Descargando todas las facturas');
    
    mostrarAlertaFactura('Preparando descarga de todas las facturas...', 'info');
    
    // Simular proceso de compresión y descarga
    setTimeout(() => {
        const enlace = document.createElement('a');
        enlace.href = '#';
        enlace.download = `facturas_${new Date().toISOString().split('T')[0]}.zip`;
        enlace.click();
        
        mostrarAlertaFactura('Todas las facturas han sido descargadas', 'success');
    }, 2000);
}

function inicializarGraficosFacturacion() {
    // Solo inicializar gráficos si existen los canvas
    if (document.getElementById('consumoChart') && typeof Chart !== 'undefined') {
        inicializarGraficoConsumos();
    }
    if (document.getElementById('pagosChart') && typeof Chart !== 'undefined') {
        inicializarGraficoPagos();
    }
}

function inicializarGraficoConsumos() {
    const ctx = document.getElementById('consumoChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Ene', 'Feb', 'Mar', 'Abr'],
            datasets: [{
                label: 'Consumo Luz (kWh)',
                data: [142, 149, 153, 150],
                backgroundColor: '#FFD700'
            }, {
                label: 'Consumo Agua (m³)',
                data: [11, 12, 13, 13],
                backgroundColor: '#A3C8D6'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Evolución de Consumos'
                }
            }
        }
    });
}

function inicializarGraficoPagos() {
    const ctx = document.getElementById('pagosChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Ene', 'Feb', 'Mar', 'Abr'],
            datasets: [{
                label: 'Monto Pagado ($)',
                data: [850, 865, 872, 880],
                borderColor: '#7A8C6E',
                backgroundColor: 'rgba(122, 140, 110, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Evolución de Pagos'
                }
            }
        }
    });
}

// Sistema de alertas para facturación
function mostrarAlertaFactura(mensaje, tipo = 'info', duracion = 3000) {
    // Remover alertas existentes
    const alertasExistentes = document.querySelectorAll('.alert-facturacion');
    alertasExistentes.forEach(alerta => alerta.remove());
    
    const alerta = document.createElement('div');
    alerta.className = `alert-facturacion alert-${tipo}`;
    alerta.innerHTML = `
        <div class="alert-content">
            <i class="fas ${getIconoAlertaFactura(tipo)}"></i>
            <span>${mensaje}</span>
            ${duracion === 0 ? '<div class="spinner"></div>' : ''}
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

function getIconoAlertaFactura(tipo) {
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