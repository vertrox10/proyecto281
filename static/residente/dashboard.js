// dashboard.js - Funcionalidades del dashboard del residente
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard del residente cargado');
    
    // Aquí puedes agregar interactividad al dashboard si es necesario
    inicializarTooltips();
    inicializarAnimaciones();
});

function inicializarTooltips() {
    // Inicializar tooltips si se necesitan
    const tooltips = document.querySelectorAll('[data-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        // Implementar tooltips si es necesario
    });
}

function inicializarAnimaciones() {
    // Animaciones simples para las tarjetas
    const metricCards = document.querySelectorAll('.metric-card');
    
    metricCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}