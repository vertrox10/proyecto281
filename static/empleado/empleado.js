const EMPLOYEE_COLORS = {
    mantenimientos: 'rgba(66, 133, 244, 0.8)',
    tickets: 'rgba(219, 68, 55, 0.8)',
    pagos: 'rgba(15, 157, 88, 0.8)',
    asistencia: 'rgba(249, 171, 0, 0.8)',
    completado: 'rgba(15, 157, 88, 0.8)',
    pendiente: 'rgba(249, 171, 0, 0.8)',
    progreso: 'rgba(66, 133, 244, 0.8)'
};

class EmployeeDashboard {
    constructor() {
        this.mantenimientosChart = null;
        this.ticketsChart = null;
        this.empleadoId = null;
        this.initialData = {
            mantenimientos_activos: 0,
            tickets_asignados: 0
        };
        
        this.init();
    }

    init() {
        console.log('🚀 Inicializando Dashboard de Empleado...');
        
        document.addEventListener('DOMContentLoaded', () => {
            this.verificarElementos();
            this.obtenerDatosIniciales();
            this.inicializarEventListeners();
            this.inicializarGraficos();
            this.cargarDatosDashboard();
        });
    }

    verificarElementos() {
        console.log('🔍 Verificando elementos del DOM...');
        const elementos = ['initial-data', 'mantenimientosChart', 'ticketsChart', 'actividades-recientes'];
        
        elementos.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                console.log(`✅ ${id} encontrado`);
            } else {
                console.error(`❌ ${id} NO encontrado`);
            }
        });
    }

    obtenerDatosIniciales() {
        const initialDataElement = document.getElementById('initial-data');
        if (!initialDataElement) {
            console.error('❌ Elemento initial-data no encontrado');
            return;
        }

        this.empleadoId = initialDataElement.dataset.empleadoId;
        this.initialData = {
            mantenimientos_activos: parseInt(initialDataElement.dataset.mantenimientos) || 0,
            tickets_asignados: parseInt(initialDataElement.dataset.tickets) || 0
        };

        console.log('🎯 Datos iniciales:', this.initialData);
        console.log('👤 ID Empleado:', this.empleadoId);
    }

    inicializarEventListeners() {
        const btnRefresh = document.getElementById('btn-refresh');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', () => {
                console.log('🔄 Actualizando dashboard...');
                this.cargarDatosDashboard();
            });
        }
    }

    inicializarGraficos() {
        console.log('📈 Inicializando gráficos...');
        
        setTimeout(() => {
            try {
                this.inicializarGraficoMantenimientos();
                this.inicializarGraficoTickets();
                console.log('✅ Gráficos inicializados');
            } catch (error) {
                console.error('💥 Error inicializando gráficos:', error);
            }
        }, 100);
    }

    inicializarGraficoMantenimientos() {
        const ctx = document.getElementById('mantenimientosChart');
        if (!ctx) return;

        this.mantenimientosChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Cargando...'],
                datasets: [{
                    label: 'Mantenimientos Realizados',
                    data: [0],
                    backgroundColor: EMPLOYEE_COLORS.mantenimientos,
                    borderColor: 'rgb(66, 133, 244)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Mis Mantenimientos - Cargando...',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: { 
                        position: 'top',
                        labels: { font: { size: 12 } }
                    }
                },
                scales: {
                    y: { 
                        beginAtZero: true,
                        title: { display: true, text: 'Cantidad' }
                    },
                    x: { 
                        title: { display: true, text: 'Meses' }
                    }
                }
            }
        });
    }

    inicializarGraficoTickets() {
        const ctx = document.getElementById('ticketsChart');
        if (!ctx) return;

        this.ticketsChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Pendientes', 'En Progreso', 'Completados'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: [
                        EMPLOYEE_COLORS.pendiente,
                        EMPLOYEE_COLORS.progreso,
                        EMPLOYEE_COLORS.completado
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        position: 'bottom',
                        labels: { font: { size: 12 } }
                    },
                    title: {
                        display: true,
                        text: 'Estado de Tickets',
                        font: { size: 14, weight: 'bold' }
                    }
                }
            }
        });
    }

    cargarDatosDashboard() {
        console.log('🌐 Cargando datos del dashboard...');
        
        // Mostrar loading
        this.mostrarEstadoCarga(true);

        fetch(`/empleados/api/dashboard-data`)
            .then(response => {
                if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
                return response.json();
            })
            .then(data => {
                console.log('📊 Datos del dashboard:', data);
                if (data.success) {
                    this.procesarDatosDashboard(data.data);
                } else {
                    throw new Error(data.error || 'Error en los datos');
                }
            })
            .catch(error => {
                console.error('💥 Error cargando dashboard:', error);
                this.mostrarError('Error de conexión');
                this.usarDatosDePrueba();
            });
    }

    procesarDatosDashboard(data) {
        console.log('🔄 Procesando datos del dashboard...');

        // Actualizar métricas principales
        this.actualizarMetricasPrincipales(data.metricas);

        // Actualizar gráficos
        this.actualizarGraficoMantenimientos(data.mantenimientos_mensuales);
        this.actualizarGraficoTickets(data.estado_tickets);

        // Actualizar actividades recientes
        this.actualizarActividadesRecientes(data.actividades_recientes);

        this.mostrarEstadoCarga(false);
    }

    actualizarMetricasPrincipales(metricas) {
        console.log('📊 Actualizando métricas:', metricas);

        // Actualizar tarjetas
        const elementos = {
            'mantenimientos-activos': metricas.mantenimientos_activos,
            'tickets-asignados': metricas.tickets_asignados,
            'ultimo-pago': `S/. ${(metricas.ultimo_pago || 0).toFixed(2)}`,
            'dias-trabajados': `${metricas.dias_trabajados || 0}/${metricas.dias_laborales || 22}`
        };

        Object.entries(elementos).forEach(([id, valor]) => {
            const element = document.getElementById(id);
            if (element) element.textContent = valor;
        });
    }

    actualizarGraficoMantenimientos(datosMensuales) {
        if (!this.mantenimientosChart || !datosMensuales) return;

        const meses = datosMensuales.map(item => {
            const [year, month] = item.mes.split('-');
            const monthNames = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
            return `${monthNames[parseInt(month) - 1]} ${year.slice(2)}`;
        });

        const cantidades = datosMensuales.map(item => item.cantidad || 0);

        this.mantenimientosChart.data.labels = meses;
        this.mantenimientosChart.data.datasets[0].data = cantidades;
        this.mantenimientosChart.options.plugins.title.text = 'Mis Mantenimientos por Mes';
        this.mantenimientosChart.update();
    }

    actualizarGraficoTickets(estadoTickets) {
        if (!this.ticketsChart || !estadoTickets) return;

        this.ticketsChart.data.datasets[0].data = [
            estadoTickets.pendientes || 0,
            estadoTickets.en_progreso || 0,
            estadoTickets.completados || 0
        ];
        this.ticketsChart.update();
    }

    actualizarActividadesRecientes(actividades) {
        const container = document.getElementById('actividades-recientes');
        if (!container) return;

        if (!actividades || actividades.length === 0) {
            container.innerHTML = `
                <div class="activity-item empty">
                    <i class="fas fa-inbox"></i>
                    <span>No hay actividades recientes</span>
                </div>
            `;
            return;
        }

        const actividadesHTML = actividades.map(actividad => `
            <div class="activity-item">
                <div class="activity-icon ${actividad.tipo}">
                    <i class="fas fa-${this.obtenerIconoTipo(actividad.tipo)}"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">${actividad.titulo}</div>
                    <div class="activity-description">${actividad.descripcion}</div>
                    <div class="activity-time">${actividad.fecha}</div>
                </div>
                <div class="activity-status ${actividad.estado}">
                    ${actividad.estado}
                </div>
            </div>
        `).join('');

        container.innerHTML = actividadesHTML;
    }

    obtenerIconoTipo(tipo) {
        const iconos = {
            'mantenimiento': 'tools',
            'ticket': 'ticket-alt',
            'pago': 'money-bill-wave',
            'asistencia': 'user-clock'
        };
        return iconos[tipo] || 'tasks';
    }

    mostrarEstadoCarga(cargando) {
        // Implementar indicador de carga si es necesario
    }

    mostrarError(mensaje) {
        console.error('❌ Error:', mensaje);
    }

    usarDatosDePrueba() {
        console.log('🎯 Usando datos de prueba...');
        
        const datosPrueba = {
            metricas: {
                mantenimientos_activos: 5,
                tickets_asignados: 3,
                ultimo_pago: 2500.00,
                dias_trabajados: 18,
                dias_laborales: 22
            },
            mantenimientos_mensuales: [
                { mes: '2024-01', cantidad: 8 },
                { mes: '2024-02', cantidad: 12 },
                { mes: '2024-03', cantidad: 10 },
                { mes: '2024-04', cantidad: 15 },
                { mes: '2024-05', cantidad: 11 },
                { mes: '2024-06', cantidad: 14 }
            ],
            estado_tickets: {
                pendientes: 2,
                en_progreso: 1,
                completados: 8
            },
            actividades_recientes: [
                {
                    tipo: 'mantenimiento',
                    titulo: 'Mantenimiento Aire Acondicionado',
                    descripcion: 'Piso 3 - Oficina 301',
                    fecha: 'Hace 2 horas',
                    estado: 'completado'
                },
                {
                    tipo: 'ticket',
                    titulo: 'Reparación Luminaria',
                    descripcion: 'Área común - Pasillo principal',
                    fecha: 'Hace 1 día',
                    estado: 'en_progreso'
                }
            ]
        };

        this.procesarDatosDashboard(datosPrueba);
    }
}

// Inicializar el dashboard
const employeeDashboard = new EmployeeDashboard();