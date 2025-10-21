// Esperar a que el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    inicializarReportes();
});

// Configuración base - USA 'empleados' (con s)
const API_BASE = '/empleados';

function inicializarReportes() {
    // Elementos del DOM
    const btnGenerar = document.getElementById('btn-generar-reporte');
    const btnDescargarPDF = document.getElementById('btn-descargar-pdf');
    const btnExportarExcel = document.getElementById('btn-exportar-excel');
    const filtroFecha = document.getElementById('filtro-fecha');
    const fechasPersonalizadas = document.getElementById('fechas-personalizadas');
    
    // Event Listeners
    btnGenerar.addEventListener('click', generarReporte);
    btnDescargarPDF.addEventListener('click', descargarPDF);
    btnExportarExcel.addEventListener('click', exportarExcel);
    
    // Mostrar/ocultar fechas personalizadas
    filtroFecha.addEventListener('change', function() {
        if (this.value === 'personalizado') {
            fechasPersonalizadas.style.display = 'block';
        } else {
            fechasPersonalizadas.style.display = 'none';
        }
    });
    
    // Cargar datos iniciales
    cargarEstadisticasIniciales();
}

// Datos globales para el reporte
let datosReporte = [];

async function generarReporte() {
    const btnGenerar = document.getElementById('btn-generar-reporte');
    const loadingOverlay = document.getElementById('loading-overlay');
    
    // Mostrar loading
    loadingOverlay.style.display = 'flex';
    btnGenerar.disabled = true;
    btnGenerar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando...';
    
    try {
        // Obtener filtros
        const filtros = obtenerFiltros();
        
        // Llamada REAL a la API - URL CORREGIDA
        const response = await fetch(`${API_BASE}/api/tickets-reporte?` + new URLSearchParams({
            estado: filtros.estado,
            prioridad: filtros.prioridad
        }), {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) {
            throw new Error(`Error HTTP: ${response.status}`);
        }
        
        const respuesta = await response.json();
        
        if (respuesta.success) {
            datosReporte = respuesta.data;
            mostrarResultados(datosReporte);
            actualizarEstadisticas(datosReporte);
            habilitarBotonesExportacion();
            
            mostrarNotificacion('Reporte generado exitosamente', 'success');
        } else {
            throw new Error(respuesta.error || 'Error al generar el reporte');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al generar el reporte: ' + error.message, 'error');
        datosReporte = [];
        mostrarResultados([]);
    } finally {
        // Ocultar loading
        loadingOverlay.style.display = 'none';
        btnGenerar.disabled = false;
        btnGenerar.innerHTML = '<i class="fas fa-sync-alt"></i> Generar Reporte';
    }
}

function obtenerFiltros() {
    return {
        estado: document.getElementById('filtro-estado').value,
        prioridad: document.getElementById('filtro-prioridad').value,
        rangoFecha: document.getElementById('filtro-fecha').value,
        fechaDesde: document.getElementById('fecha-desde')?.value || '',
        fechaHasta: document.getElementById('fecha-hasta')?.value || ''
    };
}

function mostrarResultados(datos) {
    const cuerpoTabla = document.getElementById('cuerpo-tabla');
    const estadoVacio = document.getElementById('estado-vacio');
    const contadorResultados = document.getElementById('contador-resultados');
    
    // Actualizar contador
    contadorResultados.textContent = `Mostrando ${datos.length} tickets`;
    
    if (datos.length === 0) {
        cuerpoTabla.innerHTML = '';
        estadoVacio.style.display = 'block';
        return;
    }
    
    estadoVacio.style.display = 'none';
    
    // Generar filas de la tabla
    cuerpoTabla.innerHTML = datos.map(ticket => {
        return `
        <tr>
            <td><strong>#${ticket.id}</strong></td>
            <td>${ticket.descripcion}</td>
            <td><span class="badge badge-${ticket.prioridad}">${ticket.prioridad.toUpperCase()}</span></td>
            <td><span class="badge badge-${ticket.estado}">${ticket.estado.replace('_', ' ').toUpperCase()}</span></td>
            <td>${ticket.area}</td>
            <td>${ticket.ubicacion}</td>
            <td>${formatearFecha(ticket.fecha_emision)}</td>
            <td>${ticket.fecha_finalizacion ? formatearFecha(ticket.fecha_finalizacion) : '-'}</td>
            <td>${ticket.tiempo_transcurrido}</td>
        </tr>`;
    }).join('');
}

function actualizarEstadisticas(datos) {
    const total = datos.length;
    const abiertos = datos.filter(t => t.estado === 'abierto').length;
    const enProgreso = datos.filter(t => t.estado === 'en_progreso').length;
    const cerrados = datos.filter(t => t.estado === 'cerrado').length;
    const urgentes = datos.filter(t => t.prioridad === 'urgente').length;
    
    // Actualizar valores en las tarjetas
    const valores = document.querySelectorAll('.estadistica-valor');
    if (valores.length >= 4) {
        valores[0].textContent = total;
        valores[1].textContent = abiertos;
        valores[2].textContent = enProgreso;
        valores[3].textContent = cerrados;
    }
}

function habilitarBotonesExportacion() {
    document.getElementById('btn-descargar-pdf').disabled = datosReporte.length === 0;
    document.getElementById('btn-exportar-excel').disabled = datosReporte.length === 0;
}

async function descargarPDF() {
    if (datosReporte.length === 0) {
        mostrarNotificacion('No hay datos para generar el PDF', 'error');
        return;
    }

    const btnDescargarPDF = document.getElementById('btn-descargar-pdf');
    const loadingOverlay = document.getElementById('loading-overlay');
    
    // Mostrar loading
    loadingOverlay.style.display = 'flex';
    btnDescargarPDF.disabled = true;
    btnDescargarPDF.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando PDF...';
    
    try {
        // Llamar al endpoint real de PDF - URL CORREGIDA
        const response = await fetch(`${API_BASE}/generar_reporte_pdf`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                filtros: obtenerFiltros()
            })
        });
        
        if (!response.ok) {
            throw new Error(`Error HTTP: ${response.status}`);
        }
        
        // Descargar el PDF
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `reporte_tickets_${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
        mostrarNotificacion('PDF descargado exitosamente', 'success');
        
    } catch (error) {
        console.error('Error:', error);
        
        // Fallback: generar PDF localmente si el endpoint falla
        mostrarNotificacion('Generando PDF localmente...', 'warning');
        setTimeout(() => generarPDFLocal(), 1000);
    } finally {
        // Ocultar loading
        loadingOverlay.style.display = 'none';
        btnDescargarPDF.disabled = false;
        btnDescargarPDF.innerHTML = '<i class="fas fa-file-pdf"></i> Descargar PDF';
    }
}

// Función de fallback para generar PDF localmente
function generarPDFLocal() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    
    // Título
    doc.setFontSize(20);
    doc.text('Reporte de Tickets', 105, 15, { align: 'center' });
    
    // Fecha de generación
    doc.setFontSize(10);
    doc.text(`Generado el: ${new Date().toLocaleDateString('es-ES')}`, 105, 22, { align: 'center' });
    
    // Tabla
    doc.autoTable({
        startY: 30,
        head: [['ID', 'Descripción', 'Prioridad', 'Estado', 'Área', 'Ubicación', 'Fecha Emisión']],
        body: datosReporte.map(ticket => [
            ticket.id,
            (ticket.descripcion || '').substring(0, 40) + '...',
            (ticket.prioridad || '').toUpperCase(),
            (ticket.estado || '').replace('_', ' ').toUpperCase(),
            ticket.area || '',
            ticket.ubicacion || '',
            formatearFecha(ticket.fecha_emision)
        ]),
        styles: { fontSize: 8 },
        headStyles: { fillColor: [52, 152, 219] }
    });
    
    // Guardar PDF
    doc.save(`reporte_tickets_${new Date().toISOString().split('T')[0]}.pdf`);
    mostrarNotificacion('PDF generado localmente', 'success');
}

function exportarExcel() {
    if (datosReporte.length === 0) {
        mostrarNotificacion('No hay datos para exportar', 'error');
        return;
    }

    try {
        // Crear workbook
        const wb = XLSX.utils.book_new();
        
        // Preparar datos
        const datosExcel = datosReporte.map(ticket => ({
            'ID': ticket.id,
            'Descripción': ticket.descripcion,
            'Prioridad': ticket.prioridad.toUpperCase(),
            'Estado': ticket.estado.replace('_', ' ').toUpperCase(),
            'Área': ticket.area,
            'Ubicación': ticket.ubicacion,
            'Fecha Emisión': formatearFecha(ticket.fecha_emision),
            'Fecha Finalización': ticket.fecha_finalizacion ? formatearFecha(ticket.fecha_finalizacion) : 'N/A',
            'Duración': ticket.tiempo_transcurrido
        }));
        
        // Crear worksheet
        const ws = XLSX.utils.json_to_sheet(datosExcel);
        
        // Agregar worksheet al workbook
        XLSX.utils.book_append_sheet(wb, ws, 'Reporte Tickets');
        
        // Descargar archivo
        XLSX.writeFile(wb, `reporte_tickets_${new Date().toISOString().split('T')[0]}.xlsx`);
        
        mostrarNotificacion('Excel exportado exitosamente', 'success');
    } catch (error) {
        console.error('Error exportando Excel:', error);
        mostrarNotificacion('Error al exportar Excel', 'error');
    }
}

async function cargarEstadisticasIniciales() {
    try {
        // Llamar al endpoint de estadísticas - URL CORREGIDA
        const response = await fetch(`${API_BASE}/api/estadisticas`);
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                actualizarEstadisticasDesdeAPI(data.data.tickets);
                return;
            }
        }
    } catch (error) {
        console.log('No se pudieron cargar estadísticas iniciales, usando valores por defecto');
    }
    
    // Valores por defecto
    actualizarEstadisticas([]);
}

function actualizarEstadisticasDesdeAPI(estadisticas) {
    const valores = document.querySelectorAll('.estadistica-valor');
    if (valores.length >= 4) {
        valores[0].textContent = estadisticas.total || 0;
        valores[1].textContent = estadisticas.abiertos || 0;
        valores[2].textContent = estadisticas.en_progreso || 0;
        valores[3].textContent = estadisticas.cerrados || 0;
    }
}

function formatearFecha(fechaStr) {
    if (!fechaStr) return '-';
    
    try {
        // Manejar diferentes formatos de fecha
        let fecha;
        if (fechaStr.includes('/')) {
            // Formato DD/MM/YYYY
            const [dia, mes, anioHora] = fechaStr.split('/');
            const [anio, hora] = anioHora.split(' ');
            fecha = new Date(`${anio}-${mes}-${dia}${hora ? 'T' + hora : ''}`);
        } else {
            // Formato ISO o YYYY-MM-DD
            fecha = new Date(fechaStr);
        }
        
        if (isNaN(fecha.getTime())) {
            return fechaStr; // Devolver original si no se puede parsear
        }
        
        return fecha.toLocaleDateString('es-ES', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    } catch (error) {
        return fechaStr; // Devolver original en caso de error
    }
}

function mostrarNotificacion(mensaje, tipo) {
    // Crear elemento de notificación
    const notificacion = document.createElement('div');
    notificacion.className = `notificacion notificacion-${tipo}`;
    notificacion.innerHTML = `
        <i class="fas fa-${tipo === 'success' ? 'check' : tipo === 'warning' ? 'exclamation-triangle' : 'exclamation'}-circle"></i>
        <span>${mensaje}</span>
    `;
    
    // Estilos básicos para la notificación
    notificacion.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${tipo === 'success' ? '#27ae60' : tipo === 'warning' ? '#f39c12' : '#e74c3c'};
        color: white;
        padding: 15px 20px;
        border-radius: 5px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 10px;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notificacion);
    
    // Remover después de 4 segundos
    setTimeout(() => {
        notificacion.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (notificacion.parentNode) {
                notificacion.parentNode.removeChild(notificacion);
            }
        }, 300);
    }, 4000);
}

// Agregar estilos para las animaciones de notificación
const estiloNotificacion = document.createElement('style');
estiloNotificacion.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(estiloNotificacion);