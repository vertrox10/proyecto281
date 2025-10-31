// reservas.js - Funcionalidades del sistema de reservas

// Variables globales
let reservaActual = {
    area: null,
    nombre: null,
    precio: null,
    fecha: null,
    horas: 1
};

let boucherFile = null;

// Horarios de áreas
const horariosAreas = {
    'salon': 'Lunes a Domingo: 8:00 - 22:00',
    'piscina': 'Martes a Domingo: 9:00 - 19:00',
    'gimnasio': 'Lunes a Sábado: 6:00 - 22:00',
    'parqueo': 'Todos los días: 24 horas'
};

// Fecha actual para validaciones
const hoy = new Date().toISOString().split('T')[0];

document.addEventListener('DOMContentLoaded', function() {
    console.log('Sistema de reservas cargado - URLs corregidas');
    cargarReservasActivas();
});

function abrirModalReserva(area, nombre, precio) {
    console.log('Abriendo modal para:', area, nombre, precio);

    reservaActual = {
        area: area,
        nombre: nombre,
        precioBase: precio,
        precio: precio,
        fecha: null,
        horas: 1
    };

    const modal = document.getElementById('modalReserva');
    const titulo = document.getElementById('modalTitulo');
    const previewArea = document.getElementById('previewArea');
    const previewPrecio = document.getElementById('previewPrecio');
    const previewHorario = document.getElementById('previewHorario');
    const horasGimnasio = document.getElementById('horasGimnasio');

    titulo.textContent = `Reservar ${nombre}`;
    previewArea.textContent = nombre;
    previewPrecio.textContent = `Precio: ${precio} Bs${area === 'gimnasio' ? '/hora' : ''}`;
    previewHorario.textContent = `Horario: ${horariosAreas[area]}`;

    // Mostrar selector de horas solo para gimnasio
    if (area === 'gimnasio') {
        horasGimnasio.style.display = 'block';
        calcularMontoGimnasio();
    } else {
        horasGimnasio.style.display = 'none';
    }

    // Configurar fecha mínima
    document.getElementById('fechaReserva').min = hoy;
    document.getElementById('fechaReserva').value = '';
    document.getElementById('btnContinuar').disabled = true;
    document.getElementById('mensajeFecha').textContent = 'Selecciona una fecha disponible';

    modal.style.display = 'block';
}

function calcularMontoGimnasio() {
    if (reservaActual.area === 'gimnasio') {
        const horas = parseInt(document.getElementById('horasSeleccion').value);
        reservaActual.horas = horas;
        reservaActual.precio = reservaActual.precioBase * horas;

        document.getElementById('montoGimnasio').textContent =
            `Total: ${reservaActual.precio} Bs (${horas} hora${horas > 1 ? 's' : ''})`;
    }
}

function cerrarModal() {
    document.getElementById('modalReserva').style.display = 'none';
    reservaActual.fecha = null;
    boucherFile = null;
}

function validarFecha() {
    const fechaInput = document.getElementById('fechaReserva').value;
    const btnContinuar = document.getElementById('btnContinuar');
    const mensaje = document.getElementById('mensajeFecha');

    if (fechaInput) {
        const fechaSeleccionada = new Date(fechaInput);
        const hoy = new Date();
        const diaSemana = fechaSeleccionada.getDay(); // 0=Domingo, 1=Lunes...

        // Validar según el área
        let fechaValida = true;
        let mensajeError = '';

        switch (reservaActual.area) {
            case 'piscina':
                // Piscina: Martes a Domingo (1-6)
                if (diaSemana === 0) { // Domingo es 0
                    fechaValida = true;
                } else if (diaSemana >= 2 && diaSemana <= 6) { // Martes a Sábado
                    fechaValida = true;
                } else {
                    fechaValida = false;
                    mensajeError = '❌ La piscina no está disponible los Lunes';
                }
                break;

            case 'gimnasio':
                // Gimnasio: Lunes a Sábado (1-6)
                if (diaSemana >= 1 && diaSemana <= 6) {
                    fechaValida = true;
                } else {
                    fechaValida = false;
                    mensajeError = '❌ El gimnasio no está disponible los Domingos';
                }
                break;

            default:
                // Salón y Parqueo: todos los días
                fechaValida = true;
        }

        if (fechaSeleccionada < hoy) {
            mensaje.textContent = '❌ No puedes seleccionar fechas pasadas';
            mensaje.style.color = 'red';
            btnContinuar.disabled = true;
        } else if (!fechaValida) {
            mensaje.textContent = mensajeError;
            mensaje.style.color = 'red';
            btnContinuar.disabled = true;
        } else {
            reservaActual.fecha = fechaInput;
            mensaje.textContent = '✅ Fecha disponible';
            mensaje.style.color = 'green';
            btnContinuar.disabled = false;
        }
    } else {
        btnContinuar.disabled = true;
        mensaje.textContent = 'Selecciona una fecha disponible';
        mensaje.style.color = '#666';
    }
}

function mostrarFormularioPago() {
    if (!reservaActual.fecha) {
        alert('Por favor selecciona una fecha válida.');
        return;
    }

    // DEBUG: Verificar el formato de fecha
    console.log('📅 Fecha seleccionada (raw):', reservaActual.fecha);
    console.log('📅 Fecha como Date object:', new Date(reservaActual.fecha));
    console.log('📅 Fecha formateada:', new Date(reservaActual.fecha).toISOString().split('T')[0]);

    cerrarModal();

    // Mostrar opción de pago
    const opcionPago = confirm(`¿Cómo deseas proceder con el pago de ${reservaActual.precio} Bs?\n\nOK - Pago con QR\nCancelar - Facturación Manual`);

    if (opcionPago) {
        mostrarModalPagoQR();
    } else {
        mostrarModalFacturacion();
    }
}

function mostrarModalPagoQR() {
    const modal = document.getElementById('modalPagoQR');
    document.getElementById('pagoArea').textContent = reservaActual.nombre;
    document.getElementById('pagoFecha').textContent = new Date(reservaActual.fecha).toLocaleDateString('es-ES');
    document.getElementById('pagoMonto').textContent = `${reservaActual.precio} Bs`;

    // Resetear boucher
    boucherFile = null;
    document.getElementById('boucherFile').value = '';
    document.getElementById('boucherPreview').style.display = 'none';

    modal.style.display = 'block';
}

function cerrarModalPagoQR() {
    document.getElementById('modalPagoQR').style.display = 'none';
    boucherFile = null;
}

function previewBoucher(input) {
    if (input.files && input.files[0]) {
        boucherFile = input.files[0];
        document.getElementById('boucherPreview').style.display = 'block';
        console.log('Boucher seleccionado:', boucherFile.name);
    }
}

function confirmarPagoRealizado() {
    if (!boucherFile) {
        alert('Por favor sube el comprobante de pago antes de confirmar.');
        return;
    }

    if (confirm('¿Confirmas que ya realizaste el pago y subiste el comprobante?')) {
        procesarReservaConBoucher();
    }
}

// Procesar reserva con boucher - URL CORREGIDA
async function procesarReservaConBoucher() {
    console.log('Procesando reserva con boucher:', reservaActual);
    console.log('🔍 DEBUG - Fecha que se enviará:', reservaActual.fecha);
    console.log('🔍 DEBUG - Tipo de fecha:', typeof reservaActual.fecha);

    const formData = new FormData();
    formData.append('area', reservaActual.area);
    formData.append('nombre_area', reservaActual.nombre);
    formData.append('fecha', reservaActual.fecha);
    formData.append('monto', reservaActual.precio);
    formData.append('metodo_pago', 'qr');
    formData.append('horas', reservaActual.horas);
    formData.append('boucher', boucherFile);

    // Debug: mostrar contenido del FormData
    console.log('📦 DEBUG - Contenido del FormData:');
    for (let pair of formData.entries()) {
        console.log('  ', pair[0] + ': ' + pair[1]);
    }

    try {
        console.log('Enviando datos al servidor...');
        
        const response = await fetch('/residentes/api/procesar_reserva', {
            method: 'POST',
            body: formData
        });

        console.log('Respuesta recibida, status:', response.status);
        
        const result = await response.json();
        console.log('Respuesta del servidor:', result);

        if (result.success) {
            mostrarConfirmacionPago(result.pago_id);
        } else {
            alert('Error: ' + result.message);
        }
    } catch (error) {
        console.error('Error completo:', error);
        alert('Error al procesar la reserva: ' + error.message);
    }
}

function mostrarConfirmacionPago(pagoId) {
    cerrarModalPagoQR();

    // Mostrar mensaje de éxito
    alert(`¡Reserva confirmada!\n\nÁrea: ${reservaActual.nombre}\nFecha: ${reservaActual.fecha}\nMonto: ${reservaActual.precio} Bs\nMétodo: QR\n\nID de Reserva: ${pagoId}`);

    // Generar y mostrar factura
    generarFactura(pagoId);

    // Recargar lista de reservas
    cargarReservasActivas();
}

function mostrarModalFacturacion() {
    const modal = document.getElementById('modalFacturacion');

    // Llenar datos automáticos
    document.getElementById('facturaArea').value = reservaActual.nombre;
    document.getElementById('facturaFecha').value = new Date(reservaActual.fecha).toLocaleDateString('es-ES');
    document.getElementById('facturaMonto').value = `${reservaActual.precio} Bs`;

    // Limpiar otros campos
    document.getElementById('facturaCI').value = '';
    document.getElementById('facturaNombre').value = '';
    document.getElementById('facturaDepartamento').value = '';
    document.getElementById('facturaMetodo').value = '';
    document.getElementById('facturaComprobante').value = '';

    modal.style.display = 'block';
}

function cerrarModalFacturacion() {
    document.getElementById('modalFacturacion').style.display = 'none';
}

function cerrarModalFactura() {
    document.getElementById('modalFactura').style.display = 'none';
}

// Manejar formulario de facturación
document.addEventListener('DOMContentLoaded', function() {
    const formFacturacion = document.getElementById('formFacturacion');
    if (formFacturacion) {
        formFacturacion.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const datosFactura = {
                ci: formData.get('ci'),
                nombre: formData.get('nombre'),
                departamento: formData.get('departamento'),
                area: reservaActual.area,
                nombre_area: reservaActual.nombre,
                fecha: reservaActual.fecha,
                monto: reservaActual.precio,
                metodo_pago: formData.get('metodo'),
                comprobante: formData.get('comprobante'),
                horas: reservaActual.horas
            };

            try {
                console.log('Enviando datos de facturación:', datosFactura);
                
                // URL CORREGIDA
                const response = await fetch('/residentes/api/procesar_reserva', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(datosFactura)
                });

                const result = await response.json();
                console.log('Respuesta del servidor:', result);

                if (result.success) {
                    cerrarModalFacturacion();
                    alert('¡Reserva y factura generadas exitosamente!');
                    generarFactura(result.pago_id);
                    cargarReservasActivas();
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error al procesar la factura: ' + error.message);
            }
        });
    }
});

// URL CORREGIDA
async function generarFactura(pagoId) {
    try {
        const response = await fetch(`/residentes/api/generar_factura/${pagoId}`);
        const result = await response.json();

        if (result.success) {
            mostrarFactura(result.factura);
        } else {
            alert('Error generando factura: ' + result.message);
            mostrarFacturaBasica(pagoId);
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarFacturaBasica(pagoId);
    }
}

function mostrarFactura(facturaData) {
    const modal = document.getElementById('modalFactura');
    const content = document.getElementById('facturaContent');

    content.innerHTML = `
        <div style="text-align: center; border-bottom: 2px solid #333; padding-bottom: 15px; margin-bottom: 20px;">
            <h2 style="color: var(--azul-profundo); margin: 0;">EDIFICIO SINCRONHOME</h2>
            <p style="margin: 5px 0;">Sistema de Gestión de Reservas</p>
            <h3 style="color: var(--verde-oliva); margin: 10px 0;">FACTURA</h3>
            <p style="margin: 0;"><strong>N°:</strong> ${facturaData.numero_factura}</p>
            <p style="margin: 0;"><strong>Fecha:</strong> ${facturaData.fecha_emision}</p>
        </div>
        
        <div style="margin-bottom: 20px;">
            <h4 style="color: var(--azul-profundo); border-bottom: 1px solid #ddd; padding-bottom: 5px;">DATOS DEL CLIENTE</h4>
            <p><strong>Nombre:</strong> ${facturaData.cliente.nombre}</p>
            <p><strong>CI:</strong> ${facturaData.cliente.ci}</p>
            <p><strong>Departamento:</strong> ${facturaData.cliente.departamento}</p>
        </div>
        
        <div style="margin-bottom: 20px;">
            <h4 style="color: var(--azul-profundo); border-bottom: 1px solid #ddd; padding-bottom: 5px;">DETALLES DEL SERVICIO</h4>
            <p><strong>Concepto:</strong> ${facturaData.concepto}</p>
            <p><strong>Método de Pago:</strong> ${facturaData.metodo_pago}</p>
            <p><strong>Comprobante:</strong> ${facturaData.comprobante}</p>
        </div>
        
        <div style="text-align: right; border-top: 2px solid #333; padding-top: 15px;">
            <h3 style="color: var(--verde-oliva); margin: 0;">TOTAL: ${facturaData.monto} Bs</h3>
            <p style="margin: 5px 0; font-size: 0.9rem;">${numeroALetras(facturaData.monto)} Bolivianos</p>
        </div>
        
        <div style="margin-top: 30px; text-align: center; border-top: 1px solid #ddd; padding-top: 15px;">
            <p style="font-size: 0.8rem; color: #666;">¡Gracias por su reserva!</p>
            <p style="font-size: 0.8rem; color: #666;">Edificio SincroHome - Todos los derechos reservados</p>
        </div>
    `;

    modal.style.display = 'block';
}

function mostrarFacturaBasica(pagoId) {
    const modal = document.getElementById('modalFactura');
    const content = document.getElementById('facturaContent');

    content.innerHTML = `
        <div style="text-align: center; border-bottom: 2px solid #333; padding-bottom: 15px; margin-bottom: 20px;">
            <h2 style="color: var(--azul-profundo); margin: 0;">EDIFICIO SINCRONHOME</h2>
            <h3 style="color: var(--verde-oliva); margin: 10px 0;">COMPROBANTE DE RESERVA</h3>
            <p style="margin: 0;"><strong>ID Reserva:</strong> ${pagoId}</p>
            <p style="margin: 0;"><strong>Fecha:</strong> ${new Date().toLocaleDateString('es-ES')}</p>
        </div>
        
        <div style="margin-bottom: 20px;">
            <h4 style="color: var(--azul-profundo); border-bottom: 1px solid #ddd; padding-bottom: 5px;">DETALLES DE LA RESERVA</h4>
            <p><strong>Área:</strong> ${reservaActual.nombre}</p>
            <p><strong>Fecha:</strong> ${reservaActual.fecha}</p>
            <p><strong>Monto:</strong> ${reservaActual.precio} Bs</p>
            ${reservaActual.area === 'gimnasio' ? `<p><strong>Horas:</strong> ${reservaActual.horas}</p>` : ''}
        </div>
        
        <div style="text-align: right; border-top: 2px solid #333; padding-top: 15px;">
            <h3 style="color: var(--verde-oliva); margin: 0;">TOTAL: ${reservaActual.precio} Bs</h3>
        </div>
    `;

    modal.style.display = 'block';
}

function imprimirFactura() {
    const facturaContent = document.getElementById('facturaContent').innerHTML;
    const ventanaImpresion = window.open('', '_blank');
    ventanaImpresion.document.write(`
        <html>
            <head>
                <title>Factura SincroHome</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    @media print {
                        body { margin: 0; }
                        .no-print { display: none; }
                    }
                </style>
            </head>
            <body>
                ${facturaContent}
                <div class="no-print" style="margin-top: 20px; text-align: center;">
                    <button onclick="window.print()">Imprimir</button>
                    <button onclick="window.close()">Cerrar</button>
                </div>
            </body>
        </html>
    `);
    ventanaImpresion.document.close();
}

// Función para convertir números a letras (simplificada)
function numeroALetras(numero) {
    return "** " + numero + " Bolivianos **";
}

// Función PARA EXPORTAR RESERVAS COMO PDF - VERSIÓN CORREGIDA
async function exportarReservasPDF() {
    try {
        console.log('Iniciando exportación de reservas a PDF...');
        
        // Obtener las reservas actuales
        const response = await fetch('/residentes/api/mis_reservas');
        const result = await response.json();
        
        if (!result.success || !result.reservas || result.reservas.length === 0) {
            alert('No hay reservas para exportar.');
            return;
        }

        // Crear contenido del PDF
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        
        let yPosition = 20;
        const pageWidth = doc.internal.pageSize.width;
        const pageHeight = doc.internal.pageSize.height;
        const margin = 20;
        const contentWidth = pageWidth - (margin * 2);

        // Logo y encabezado
        doc.setFontSize(20);
        doc.setTextColor(41, 128, 185);
        doc.text('EDIFICIO SINCRONHOME', pageWidth / 2, yPosition, { align: 'center' });
        
        yPosition += 10;
        doc.setFontSize(16);
        doc.setTextColor(86, 101, 115);
        doc.text('REPORTE DE RESERVAS', pageWidth / 2, yPosition, { align: 'center' });
        
        yPosition += 15;
        doc.setFontSize(10);
        doc.setTextColor(100, 100, 100);
        doc.text(`Generado el: ${new Date().toLocaleDateString('es-ES')}`, pageWidth / 2, yPosition, { align: 'center' });
        
        yPosition += 20;

        // Información del residente
        doc.setFontSize(12);
        doc.setTextColor(0, 0, 0);
        doc.text(`Residente: ${document.querySelector('.usuario-nombre')?.textContent || 'Residente'}`, margin, yPosition);
        yPosition += 8;
        doc.text(`Total de reservas: ${result.reservas.length}`, margin, yPosition);
        yPosition += 15;

        // Línea separadora
        doc.setDrawColor(200, 200, 200);
        doc.line(margin, yPosition, pageWidth - margin, yPosition);
        yPosition += 15;

        // Tabla de reservas
        doc.setFontSize(14);
        doc.setTextColor(41, 128, 185);
        doc.text('DETALLE DE RESERVAS', margin, yPosition);
        yPosition += 10;

        // Encabezados de tabla
        doc.setFillColor(240, 240, 240);
        doc.rect(margin, yPosition, contentWidth, 10, 'F');
        doc.setFontSize(10);
        doc.setTextColor(0, 0, 0);
        doc.setFont(undefined, 'bold');
        
        doc.text('DESCRIPCIÓN', margin + 5, yPosition + 7);
        doc.text('FECHA', margin + 80, yPosition + 7);
        doc.text('MONTO', margin + 120, yPosition + 7);
        doc.text('ESTADO', margin + 150, yPosition + 7);
        
        yPosition += 15;

        // Datos de las reservas - CORREGIDO
        doc.setFont(undefined, 'normal');
        let totalMonto = 0;
        
        result.reservas.forEach((reserva, index) => {
            // Verificar si necesita nueva página
            if (yPosition > pageHeight - 40) {
                doc.addPage();
                yPosition = 20;
            }
            
            // Fila de datos
            doc.setFontSize(9);
            doc.setTextColor(0, 0, 0);
            
            // Descripción (truncada si es muy larga)
            const descripcion = reserva.descripcion.length > 30 ? 
                reserva.descripcion.substring(0, 30) + '...' : reserva.descripcion;
            doc.text(descripcion, margin + 5, yPosition + 4);
            
            // Fecha
            doc.text(reserva.fecha, margin + 80, yPosition + 4);
            
            // Monto
            doc.text(`${reserva.monto} Bs`, margin + 120, yPosition + 4);
            
            // Estado
            const estado = reserva.estado.toUpperCase();
            doc.text(estado, margin + 150, yPosition + 4);
            
            totalMonto += parseFloat(reserva.monto);
            
            // Línea separadora entre filas
            yPosition += 10;
            if (index < result.reservas.length - 1) {
                doc.setDrawColor(240, 240, 240);
                doc.line(margin, yPosition, pageWidth - margin, yPosition);
                yPosition += 5;
            }
        });

        // Línea final
        doc.setDrawColor(200, 200, 200);
        doc.line(margin, yPosition, pageWidth - margin, yPosition);
        yPosition += 15;

        // Total
        doc.setFontSize(11);
        doc.setFont(undefined, 'bold');
        doc.text(`TOTAL GENERAL: ${totalMonto.toFixed(2)} Bs`, margin, yPosition);
        
        yPosition += 20;

        // Pie de página
        doc.setFontSize(8);
        doc.setFont(undefined, 'normal');
        doc.setTextColor(100, 100, 100);
        doc.text('Sistema de Gestión de Reservas - Edificio SincroHome', pageWidth / 2, pageHeight - 10, { align: 'center' });
        doc.text('Todos los derechos reservados', pageWidth / 2, pageHeight - 5, { align: 'center' });

        // Guardar el PDF
        const fecha = new Date().toISOString().split('T')[0];
        doc.save(`reservas_sincrohome_${fecha}.pdf`);
        
        console.log('PDF generado exitosamente');
        
    } catch (error) {
        console.error('Error generando PDF:', error);
        alert('Error al generar el PDF: ' + error.message);
    }
}

// URL CORREGIDA
async function cargarReservasActivas() {
    try {
        const response = await fetch('/residentes/api/mis_reservas');
        const result = await response.json();

        const lista = document.getElementById('listaReservas');
        
        if (result.success && result.reservas.length > 0) {
            let html = '';
            result.reservas.forEach(reserva => {
                html += `
                    <div class="reserva-item">
                        <div class="reserva-info">
                            <h4>${reserva.descripcion}</h4>
                            <p>Fecha: ${reserva.fecha}</p>
                            <p>Monto: ${reserva.monto} Bs</p>
                        </div>
                        <div class="reserva-status">
                            <span class="status-badge ${reserva.estado === 'completado' ? 'available' : 'occupied'}">
                                ${reserva.estado}
                            </span>
                        </div>
                    </div>
                `;
            });
            lista.innerHTML = html;
        } else {
            lista.innerHTML = `
                <div class="no-reservas">
                    <i class="fas fa-calendar-times"></i>
                    <p>No tienes reservas activas</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error cargando reservas:', error);
        const lista = document.getElementById('listaReservas');
        lista.innerHTML = `
            <div class="no-reservas">
                <i class="fas fa-calendar-times"></i>
                <p>No tienes reservas activas</p>
            </div>
        `;
    }
}

// Cerrar modales al hacer click fuera
window.onclick = function(event) {
    const modals = ['modalReserva', 'modalPagoQR', 'modalFacturacion', 'modalFactura'];
    modals.forEach(modalId => {
        const modal = document.getElementById(modalId);
        if (event.target === modal) {
            if (modalId === 'modalPagoQR') {
                cerrarModalPagoQR();
            } else if (modalId === 'modalFacturacion') {
                cerrarModalFacturacion();
            } else if (modalId === 'modalFactura') {
                cerrarModalFactura();
            } else {
                modal.style.display = 'none';
            }
        }
    });
}