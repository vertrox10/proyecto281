 
document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
        });
    }
    
    // Para móviles - cerrar sidebar al hacer clic fuera
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 768 && 
            !sidebar.contains(event.target) && 
            !event.target.closest('.menu-icon-hamburguesa')) {
            sidebar.classList.remove('mobile-open');
        }
    });
    
    // Agregar tooltips a los enlaces
    const sidebarLinks = document.querySelectorAll('.sidebar a');
    sidebarLinks.forEach(link => {
        const text = link.querySelector('.sidebar-text').textContent;
        link.setAttribute('data-tooltip', text);
    });
});
  