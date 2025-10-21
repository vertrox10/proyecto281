// Función para filtrar reportes (ejemplo básico)
function filtrarReportes(meses) {
    // Implementar lógica de filtrado aquí
    console.log('Filtrando últimos', meses, 'meses');
}

// Inicializar gráficos con datos proporcionados por el template
function inicializarGraficos(deudas, reportes) {
    // deudas: objeto con propiedades como total_deudores, deuda_total, etc.
    // reportes: array de objetos mensuales

    // Valores seguros
    const totalDeudores = (deudas && deudas.total_deudores) ? Number(deudas.total_deudores) : 0;
    const pagadas = Math.round(totalDeudores * 0.3);
    const vencidas = Math.round(totalDeudores * 0.1);

    // Gráfico de distribución de deudas
    const deudasCanvas = document.getElementById('deudasChart');
    if (deudasCanvas) {
        const deudasCtx = deudasCanvas.getContext('2d');
        new Chart(deudasCtx, {
            type: 'doughnut',
            data: {
                labels: ['Deudas Activas', 'Pagadas', 'Vencidas'],
                datasets: [{
                    data: [totalDeudores, pagadas, vencidas],
                    backgroundColor: ['#ff6b6b', '#51cf66', '#ffd43b']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    // Gráfico de evolución mensual
    const evolucionCanvas = document.getElementById('evolucionChart');
    if (evolucionCanvas) {
        const evolucionCtx = evolucionCanvas.getContext('2d');

        // Preparar etiquetas y datos desde 'reportes' si vienen; sino usar valores demo
        let labels = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'];
        let ingresosData = [12000, 19000, 15000, 25000, 22000, 30000];
        let deudasData = [5000, 7000, 6000, 4000, 3000, 2000];

        if (Array.isArray(reportes) && reportes.length > 0) {
            labels = reportes.map(r => r.mes_label || r.mes);
            ingresosData = reportes.map(r => Number(r.total_monto || 0));
            deudasData = reportes.map(r => Number(r.deuda_total || 0));
        }

        new Chart(evolucionCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Ingresos',
                    data: ingresosData,
                    borderColor: '#4caf50',
                    tension: 0.1
                }, {
                    label: 'Deudas',
                    data: deudasData,
                    borderColor: '#ff6b6b',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true
            }
        });
    }
}

// Exportar la función al scope global para que el template la llame
window.inicializarGraficos = inicializarGraficos;
