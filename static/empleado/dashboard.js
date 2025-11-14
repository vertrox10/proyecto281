// static/empleado/dashboard.js - Dashboard con consumos y actividades
const COLORS = {
    agua: 'rgba(79, 195, 247, 0.8)',
    luz: 'rgba(255, 213, 79, 0.8)', 
    gas: 'rgba(255, 138, 101, 0.8)',
    mantenimientos: 'rgba(66, 133, 244, 0.8)',
    tickets: 'rgba(219, 68, 55, 0.8)',
    aguaBorder: 'rgb(79, 195, 247)',
    luzBorder: 'rgb(255, 213, 79)',
    gasBorder: 'rgb(255, 138, 101)'
};

class DashboardManager {
    constructor() {
        this.consumosChart = null;
        this.distribucionChart = null;
        this.mantenimientosChart = null;
        this.initialData = { 
            agua: 0, 
            luz: 0, 
            gas: 0,
            mantenimientos: 0,
            tickets: 0
        };
        
        this.init();
    }

    init() {
        console.log('🚀 Inicializando Dashboard Manager...');
        
        document.addEventListener('DOMContentLoaded', () => {
            console.log('📊 Cargando datos de consumos y actividades...');
            this.verificarElementos();
            this.obtenerDatosIniciales();
            this.inicializarEventListeners();
            this.inicializarGraficos();
            
            // Cargar datos de la API después de inicializar gráficos
            setTimeout(() => this.cargarDatosDashboard(), 500);
        });
    }

    verificarElementos() {
        console.log('🔍 Verificando elementos del DOM...');
        const elementos = ['initial-data', 'consumosChart', 'distribucionChart', 'mantenimientosChart'];
        
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

        this.initialData = {
            agua: parseFloat(initialDataElement.dataset.agua) || 0,
            luz: parseFloat(initialDataElement.dataset.luz) || 0,
            gas: parseFloat(initialDataElement.dataset.gas) || 0,
            mantenimientos: parseInt(initialDataElement.dataset.mantenimientos) || 0,
            tickets: parseInt(initialDataElement.dataset.tickets) || 0
        };

        console.log('🎯 Datos iniciales desde Flask:', this.initialData);
    }

    inicializarEventListeners() {
        // Botón de actualizar
        const btnRefresh = document.getElementById('btn-refresh');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', () => {
                console.log('🔄 Actualizando datos...');
                this.cargarDatosDashboard();
            });
        }
    }

    inicializarGraficos() {
        console.log('📈 Inicializando gráficos...');
        
        setTimeout(() => {
            try {
                this.inicializarGraficoConsumos();
                this.inicializarGraficoDistribucion();
                this.inicializarGraficoMantenimientos();
                console.log('✅ Todos los gráficos inicializados');
            } catch (error) {
                console.error('💥 Error inicializando gráficos:', error);
            }
        }, 100);
    }

    inicializarGraficoConsumos() {
        const ctx = document.getElementById('consumosChart');
        if (!ctx) {
            console.error('❌ Canvas consumosChart no encontrado');
            return;
        }

        this.consumosChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Cargando...'],
                datasets: [
                    {
                        label: 'Agua (m³)',
                        data: [0],
                        borderColor: COLORS.aguaBorder,
                        backgroundColor: COLORS.agua,
                        tension: 0.4,
                        borderWidth: 3,
                        fill: true
                    },
                    {
                        label: 'Luz (kWh)',
                        data: [0],
                        borderColor: COLORS.luzBorder,
                        backgroundColor: COLORS.luz,
                        tension: 0.4,
                        borderWidth: 3,
                        fill: true
                    },
                    {
                        label: 'Gas (m³)',
                        data: [0],
                        borderColor: COLORS.gasBorder,
                        backgroundColor: COLORS.gas,
                        tension: 0.4,
                        borderWidth: 3,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Consumos Mensuales - Cargando...',
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
                        title: {
                            display: true,
                            text: 'Consumo'
                        }
                    },
                    x: { 
                        title: {
                            display: true,
                            text: 'Meses'
                        }
                    }
                }
            }
        });
    }

    inicializarGraficoDistribucion() {
        const ctx = document.getElementById('distribucionChart');
        if (!ctx) {
            console.error('❌ Canvas distribucionChart no encontrado');
            return;
        }

        this.distribucionChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Agua', 'Luz', 'Gas'],
                datasets: [{
                    data: [this.initialData.agua, this.initialData.luz, this.initialData.gas],
                    backgroundColor: [COLORS.agua, COLORS.luz, COLORS.gas],
                    borderColor: [COLORS.aguaBorder, COLORS.luzBorder, COLORS.gasBorder],
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
                        text: 'Distribución del Mes Actual',
                        font: { size: 14, weight: 'bold' }
                    }
                }
            }
        });
    }

    inicializarGraficoMantenimientos() {
        const ctx = document.getElementById('mantenimientosChart');
        if (!ctx) {
            console.error('❌ Canvas mantenimientosChart no encontrado');
            return;
        }

        this.mantenimientosChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Cargando...'],
                datasets: [{
                    label: 'Mantenimientos Realizados',
                    data: [0],
                    backgroundColor: COLORS.mantenimientos,
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
                        font: { size: 14, weight: 'bold' }
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

    cargarDatosDashboard() {
        console.log('🌐 Solicitando datos a la API...');
        
        // Mostrar loading
        if (this.consumosChart) {
            this.consumosChart.options.plugins.title.text = 'Cargando datos...';
            this.consumosChart.update();
        }

        fetch('/empleados/api/dashboard-data')
            .then(response => {
                console.log('📡 Estado de respuesta:', response.status);
                if (!response.ok) {
                    throw new Error(`Error HTTP: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('📊 Datos recibidos de la API:', data);
                
                if (data.success) {
                    this.procesarDatosAPI(data);
                } else {
                    console.error('❌ API reportó error:', data.error);
                    this.mostrarError('Error en los datos de la API');
                }
            })
            .catch(error => {
                console.error('💥 Error cargando datos:', error);
                this.mostrarError('Error de conexión');
                this.usarDatosDePrueba();
            });
    }

    procesarDatosAPI(data) {
        if (!data.data) {
            console.warn('⚠️ No hay datos en la respuesta, usando datos de prueba');
            this.usarDatosDePrueba();
            return;
        }

        console.log('🔄 Procesando datos para gráficos...');
        
        // Actualizar métricas principales
        this.actualizarMetricasPrincipales(data.data.metricas);
        
        // Actualizar gráficos de consumos
        if (data.data.consumos_mensuales && data.data.consumos_mensuales.length > 0) {
            this.actualizarGraficoConsumos(data.data.consumos_mensuales);
            this.actualizarGraficoDistribucion(data.data.actual);
        }
        
        // Actualizar gráfico de mantenimientos
        if (data.data.mantenimientos_mensuales && data.data.mantenimientos_mensuales.length > 0) {
            this.actualizarGraficoMantenimientos(data.data.mantenimientos_mensuales);
        }
        
        console.log('✅ Gráficos actualizados correctamente');
    }

    actualizarMetricasPrincipales(metricas) {
        console.log('📊 Actualizando métricas:', metricas);
        
        // Actualizar las tarjetas de métricas
        const elementos = {
            'consumo-agua': `${metricas.consumo_agua.toFixed(1)} m³`,
            'consumo-luz': `${metricas.consumo_luz.toFixed(0)} kWh`,
            'consumo-gas': `${metricas.consumo_gas.toFixed(1)} m³`,
            'mantenimientos-activos': metricas.mantenimientos_activos,
            'tickets-asignados': metricas.tickets_asignados,
            'dias-trabajados': `${metricas.dias_trabajados}/${metricas.dias_laborales}`
        };

        Object.entries(elementos).forEach(([id, valor]) => {
            const element = document.getElementById(id);
            if (element) element.textContent = valor;
        });

        // Actualizar timestamp
        const trends = document.querySelectorAll('.metric-trend span');
        const ahora = new Date().toLocaleTimeString();
        trends.forEach(trend => {
            if (trend.textContent.includes('Actualizado')) {
                trend.textContent = `Actualizado: ${ahora}`;
            }
        });
    }

    actualizarGraficoConsumos(datosConsumos) {
        if (!this.consumosChart) return;

        // Filtrar meses que tengan al menos algún consumo
        const datosConConsumo = datosConsumos.filter(mes => 
            (mes.agua && mes.agua > 0) || 
            (mes.luz && mes.luz > 0) || 
            (mes.gas && mes.gas > 0)
        );
        
        if (datosConConsumo.length === 0) {
            console.warn('⚠️ Todos los consumos son cero');
            return;
        }

        // Ordenar datos por mes
        const datosOrdenados = datosConConsumo.sort((a, b) => a.mes.localeCompare(b.mes));
        
        // Formatear meses (ej: "2024-01" -> "Ene 24")
        const meses = datosOrdenados.map(item => {
            const [year, month] = item.mes.split('-');
            const monthNames = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
            return `${monthNames[parseInt(month) - 1]} ${year.slice(2)}`;
        });

        // Extraer datos para cada tipo
        const aguaData = datosOrdenados.map(item => item.agua || 0);
        const luzData = datosOrdenados.map(item => item.luz || 0);
        const gasData = datosOrdenados.map(item => item.gas || 0);

        console.log('📈 Datos de consumos procesados:', { meses, aguaData, luzData, gasData });

        // Actualizar gráfico
        this.consumosChart.data.labels = meses;
        this.consumosChart.data.datasets[0].data = aguaData;
        this.consumosChart.data.datasets[1].data = luzData;
        this.consumosChart.data.datasets[2].data = gasData;
        this.consumosChart.options.plugins.title.text = `Consumos Mensuales (${datosOrdenados.length} meses)`;
        this.consumosChart.update();
    }

    actualizarGraficoDistribucion(datosActuales) {
        if (!this.distribucionChart) return;

        console.log('📅 Actualizando gráfico de distribución:', datosActuales);

        this.distribucionChart.data.datasets[0].data = [
            datosActuales.agua || 0,
            datosActuales.luz || 0,
            datosActuales.gas || 0
        ];
        this.distribucionChart.update();
    }

    actualizarGraficoMantenimientos(datosMensuales) {
        if (!this.mantenimientosChart) return;

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

    mostrarError(mensaje) {
        console.error('❌ Error:', mensaje);
        
        if (this.consumosChart) {
            this.consumosChart.options.plugins.title.text = `Error: ${mensaje}`;
            this.consumosChart.update();
        }
    }

    usarDatosDePrueba() {
        console.log('🎯 Usando datos de prueba...');
        
        const datosPrueba = {
            metricas: {
                mantenimientos_activos: 5,
                tickets_asignados: 3,
                ultimo_pago: 2500.00,
                dias_trabajados: 18,
                dias_laborales: 22,
                consumo_agua: 125.5,
                consumo_luz: 890,
                consumo_gas: 45.2
            },
            consumos_mensuales: [
                { mes: '2024-01', agua: 120, luz: 850, gas: 45 },
                { mes: '2024-02', agua: 135, luz: 920, gas: 48 },
                { mes: '2024-03', agua: 125, luz: 890, gas: 46 },
                { mes: '2024-04', agua: 140, luz: 950, gas: 50 },
                { mes: '2024-05', agua: 130, luz: 910, gas: 47 },
                { mes: '2024-06', agua: 145, luz: 980, gas: 52 }
            ],
            mantenimientos_mensuales: [
                { mes: '2024-01', cantidad: 8 },
                { mes: '2024-02', cantidad: 12 },
                { mes: '2024-03', cantidad: 10 },
                { mes: '2024-04', cantidad: 15 },
                { mes: '2024-05', cantidad: 11 },
                { mes: '2024-06', cantidad: 14 }
            ],
            actual: {
                agua: 145,
                luz: 980,
                gas: 52
            }
        };

        this.procesarDatosAPI({ data: datosPrueba });
    }
}

// Inicializar el dashboard cuando se carga el script
const dashboardManager = new DashboardManager();