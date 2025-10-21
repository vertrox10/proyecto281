// static/empleado/empleado.js
const COLORS = {
    agua: 'rgba(79, 195, 247, 0.8)',
    luz: 'rgba(255, 213, 79, 0.8)', 
    gas: 'rgba(255, 138, 101, 0.8)',
    aguaBorder: 'rgb(79, 195, 247)',
    luzBorder: 'rgb(255, 213, 79)',
    gasBorder: 'rgb(255, 138, 101)'
};

class DashboardManager {
    constructor() {
        this.consumosChart = null;
        this.distribucionChart = null;
        this.comparacionChart = null;
        this.initialData = { agua: 0, luz: 0, gas: 0 };
        
        this.init();
    }

    init() {
        console.log('🚀 Inicializando Dashboard Manager...');
        
        document.addEventListener('DOMContentLoaded', () => {
            console.log('📅 Año de datos: 2024');
            this.verificarElementos();
            this.obtenerDatosIniciales();
            this.inicializarEventListeners();
            this.inicializarGraficos();
            
            // Cargar datos de la API después de inicializar gráficos
            setTimeout(() => this.cargarDatosConsumos(), 500);
        });
    }

    verificarElementos() {
        console.log('🔍 Verificando elementos del DOM...');
        const elementos = ['initial-data', 'consumosChart', 'distribucionChart', 'comparacionChart'];
        
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
            gas: parseFloat(initialDataElement.dataset.gas) || 0
        };

        console.log('🎯 Datos iniciales desde Flask:', this.initialData);
    }

    inicializarEventListeners() {
        // Botón de actualizar
        const btnRefresh = document.getElementById('btn-refresh');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', () => {
                console.log('🔄 Actualizando datos...');
                this.cargarDatosConsumos();
            });
        }

        // Botones de navegación
        const btnTickets = document.getElementById('btn-tickets');
        const btnMantenimientos = document.getElementById('btn-mantenimientos');
        
        if (btnTickets) {
            btnTickets.addEventListener('click', () => {
                window.location.href = "/empleados/tickets";
            });
        }
        
        if (btnMantenimientos) {
            btnMantenimientos.addEventListener('click', () => {
                window.location.href = "/empleados/mantenimientos";
            });
        }
    }

    // En la función inicializarGraficos, agrega un pequeño delay
    inicializarGraficos() {
        console.log('📈 Inicializando gráficos...');
        
        // Pequeño delay para asegurar que el CSS esté aplicado
        setTimeout(() => {
            try {
                this.inicializarGraficoConsumos();
                this.inicializarGraficoDistribucion();
                this.inicializarGraficoComparacion();
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
                        backgroundColor: 'transparent',
                        tension: 0.4,
                        borderWidth: 3,
                        fill: false
                    },
                    {
                        label: 'Luz (kWh)',
                        data: [0],
                        borderColor: COLORS.luzBorder,
                        backgroundColor: 'transparent',
                        tension: 0.4,
                        borderWidth: 3,
                        fill: false
                    },
                    {
                        label: 'Gas (m³)',
                        data: [0],
                        borderColor: COLORS.gasBorder,
                        backgroundColor: 'transparent',
                        tension: 0.4,
                        borderWidth: 3,
                        fill: false
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

    inicializarGraficoComparacion() {
        const ctx = document.getElementById('comparacionChart');
        if (!ctx) {
            console.error('❌ Canvas comparacionChart no encontrado');
            return;
        }

        this.comparacionChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Agua', 'Luz', 'Gas'],
                datasets: [{
                    label: 'Consumo Actual',
                    data: [this.initialData.agua, this.initialData.luz, this.initialData.gas],
                    backgroundColor: [COLORS.agua, COLORS.luz, COLORS.gas],
                    borderColor: [COLORS.aguaBorder, COLORS.luzBorder, COLORS.gasBorder],
                    borderWidth: 1
                }]
            },
            // En inicializarGraficoConsumos, mejora las opciones:
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Consumos Mensuales 2024',
                    font: { size: 16, weight: 'bold' },
                    padding: { top: 10, bottom: 20 }
                },
                legend: { 
                    position: 'top',
                    labels: { 
                        font: { size: 12 },
                        padding: 15
                    }
                }
            },
            scales: {
                y: { 
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Consumo',
                        font: { weight: 'bold' }
                    }
                },
                x: { 
                    title: {
                        display: true,
                        text: 'Meses 2024',
                        font: { weight: 'bold' }
                    }
                }
            },
            layout: {
                padding: {
                    top: 10,
                    right: 15,
                    bottom: 10,
                    left: 15
                }
            }
        }
        });
    }

    cargarDatosConsumos() {
        console.log('🌐 Solicitando datos a la API...');
        
        // Mostrar loading
        if (this.consumosChart) {
            this.consumosChart.options.plugins.title.text = 'Cargando datos...';
            this.consumosChart.update();
        }

        fetch('/empleados/api/consumos')
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
        if (!data.data || data.data.length === 0) {
            console.warn('⚠️ No hay datos en la respuesta, usando datos de prueba');
            this.usarDatosDePrueba();
            return;
        }

        console.log('🔄 Procesando datos para gráficos...');
        
        // Filtrar meses que tengan al menos algún consumo
        const datosConConsumo = data.data.filter(mes => 
            (mes.agua && mes.agua > 0) || 
            (mes.luz && mes.luz > 0) || 
            (mes.gas && mes.gas > 0)
        );
        
        if (datosConConsumo.length === 0) {
            console.warn('⚠️ Todos los consumos son cero, usando datos de prueba');
            this.usarDatosDePrueba();
            return;
        }

        // Ordenar datos por mes
        const datosOrdenados = datosConConsumo.sort((a, b) => a.mes.localeCompare(b.mes));
        
        // Preparar datos para el gráfico de líneas
        this.actualizarGraficoLineas(datosOrdenados);
        
        // Actualizar gráficos secundarios con datos actuales
        if (data.actual) {
            this.actualizarGraficosSecundarios(data.actual);
        } else {
            // Usar el último mes disponible
            const ultimoMes = datosOrdenados[datosOrdenados.length - 1];
            this.actualizarGraficosSecundarios(ultimoMes);
        }
        
        // Actualizar métricas
        this.actualizarMetricas(data.actual || datosOrdenados[datosOrdenados.length - 1]);
        
        console.log('✅ Gráficos actualizados correctamente');
    }

    actualizarGraficoLineas(datos) {
        if (!this.consumosChart) return;

        // Formatear meses (ej: "2024-01" -> "Ene 24")
        const meses = datos.map(item => {
            const [year, month] = item.mes.split('-');
            const monthNames = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
            return `${monthNames[parseInt(month) - 1]} ${year.slice(2)}`;
        });

        // Extraer datos para cada tipo
        const aguaData = datos.map(item => item.agua || 0);
        const luzData = datos.map(item => item.luz || 0);
        const gasData = datos.map(item => item.gas || 0);

        console.log('📈 Datos procesados:', { meses, aguaData, luzData, gasData });

        // Actualizar gráfico
        this.consumosChart.data.labels = meses;
        this.consumosChart.data.datasets[0].data = aguaData;
        this.consumosChart.data.datasets[1].data = luzData;
        this.consumosChart.data.datasets[2].data = gasData;
        
        // Cambiar a fill para mejor visualización
        this.consumosChart.data.datasets[0].fill = true;
        this.consumosChart.data.datasets[0].backgroundColor = COLORS.agua;
        this.consumosChart.data.datasets[1].fill = true;
        this.consumosChart.data.datasets[1].backgroundColor = COLORS.luz;
        this.consumosChart.data.datasets[2].fill = true;
        this.consumosChart.data.datasets[2].backgroundColor = COLORS.gas;
        
        this.consumosChart.options.plugins.title.text = `Consumos Mensuales (${datos.length} meses)`;
        this.consumosChart.update();
    }

    actualizarGraficosSecundarios(datosActuales) {
        console.log('📅 Actualizando gráficos secundarios:', datosActuales);

        if (this.distribucionChart) {
            this.distribucionChart.data.datasets[0].data = [
                datosActuales.agua || 0,
                datosActuales.luz || 0,
                datosActuales.gas || 0
            ];
            this.distribucionChart.update();
        }

        if (this.comparacionChart) {
            this.comparacionChart.data.datasets[0].data = [
                datosActuales.agua || 0,
                datosActuales.luz || 0,
                datosActuales.gas || 0
            ];
            this.comparacionChart.update();
        }
    }

    actualizarMetricas(datosActuales) {
        console.log('📊 Actualizando métricas:', datosActuales);
        
        // Actualizar las tarjetas de métricas
        const aguaElement = document.getElementById('consumo-agua');
        const luzElement = document.getElementById('consumo-luz');
        const gasElement = document.getElementById('consumo-gas');
        
        if (aguaElement) aguaElement.textContent = `${(datosActuales.agua || 0).toFixed(1)} m³`;
        if (luzElement) luzElement.textContent = `${(datosActuales.luz || 0).toFixed(0)} kWh`;
        if (gasElement) gasElement.textContent = `${(datosActuales.gas || 0).toFixed(1)} m³`;

        // Actualizar timestamp
        const trends = document.querySelectorAll('.consumo-trend span');
        const ahora = new Date().toLocaleTimeString();
        trends.forEach(trend => {
            trend.textContent = `Actualizado: ${ahora}`;
        });
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
        
        const datosPrueba = [
            { mes: '2024-01', agua: 120, luz: 850, gas: 45 },
            { mes: '2024-02', agua: 135, luz: 920, gas: 48 },
            { mes: '2024-03', agua: 125, luz: 890, gas: 46 },
            { mes: '2024-04', agua: 140, luz: 950, gas: 50 },
            { mes: '2024-05', agua: 130, luz: 910, gas: 47 },
            { mes: '2024-06', agua: 145, luz: 980, gas: 52 }
        ];

        this.actualizarGraficoLineas(datosPrueba);
        this.actualizarGraficosSecundarios(datosPrueba[datosPrueba.length - 1]);
        this.actualizarMetricas(datosPrueba[datosPrueba.length - 1]);
        
        if (this.consumosChart) {
            this.consumosChart.options.plugins.title.text = 'Consumos Mensuales';
            this.consumosChart.update();
        }
    }
}

// Inicializar el dashboard cuando se carga el script
const dashboardManager = new DashboardManager();