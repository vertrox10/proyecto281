// Gráficos para la sección de consumos
let consumoCharts = {};

function inicializarGraficos() {
    // Gráfico de evolución de consumos
    const evolucionCtx = document.getElementById('evolucionConsumosChart').getContext('2d');
    consumoCharts.evolucion = new Chart(evolucionCtx, {
        type: 'line',
        data: {
            labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
            datasets: [
                {
                    label: 'Energía (kWh)',
                    data: [120, 150, 130, 160, 140, 155],
                    borderColor: '#FFD700',
                    backgroundColor: 'rgba(255, 215, 0, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Agua (m³)',
                    data: [10, 12, 11, 13, 12, 12.5],
                    borderColor: '#A3C8D6',
                    backgroundColor: 'rgba(163, 200, 214, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Gas (m³)',
                    data: [8, 9, 8.5, 9.2, 8.8, 8.7],
                    borderColor: '#E3A78C',
                    backgroundColor: 'rgba(227, 167, 140, 0.1)',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    // Gráfico de distribución
    const distribucionCtx = document.getElementById('distribucionConsumosChart').getContext('2d');
    consumoCharts.distribucion = new Chart(distribucionCtx, {
        type: 'doughnut',
        data: {
            labels: ['Energía', 'Agua', 'Gas'],
            datasets: [{
                data: [55, 25, 20],
                backgroundColor: ['#FFD700', '#A3C8D6', '#E3A78C'],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });

    // Gráfico comparativo
    const comparativaCtx = document.getElementById('comparativaMensualChart').getContext('2d');
    consumoCharts.comparativa = new Chart(comparativaCtx, {
        type: 'bar',
        data: {
            labels: ['Energía', 'Agua', 'Gas'],
            datasets: [
                {
                    label: 'Mes Actual',
                    data: [150, 12.3, 8.7],
                    backgroundColor: '#264653'
                },
                {
                    label: 'Mes Anterior',
                    data: [158, 12.1, 8.9],
                    backgroundColor: '#A3C8D6'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function exportarLecturas() {
    // Simular exportación de datos
    const enlace = document.createElement('a');
    enlace.href = 'data:text/csv;charset=utf-8,Concepto,Valor\nEnergía,150 kWh\nAgua,12.3 m³\nGas,8.7 m³';
    enlace.download = `consumos_${new Date().toISOString().split('T')[0]}.csv`;
    enlace.click();
}

// Cambiar período de visualización
document.getElementById('selectorPeriodo')?.addEventListener('change', function() {
    const periodo = this.value;
    // Aquí cargarías los datos del período seleccionado
    console.log('Cambiando a período:', periodo);
});

// Inicializar gráficos cuando se cargue la página
document.addEventListener('DOMContentLoaded', function() {
    inicializarGraficos();
});