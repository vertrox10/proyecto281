// Funciones para la gestión de pagos
function realizarPago(idFactura) {
    // Simular integración con pasarela de pago
    const metodoPago = prompt('Seleccione método de pago:\n1. Tigo Money\n2. Billetera Virtual\n3. Criptomoneda');
    
    if (metodoPago) {
        fetch('/residentes/realizar_pago', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id_factura: idFactura,
                metodo: metodoPago
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Pago realizado exitosamente');
                location.reload();
            } else {
                alert('Error al procesar el pago');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al procesar el pago');
        });
    }
}

function mostrarModalMetodos() {
    document.getElementById('modalMetodos').style.display = 'flex';
}

function cerrarModalMetodos() {
    document.getElementById('modalMetodos').style.display = 'none';
    document.getElementById('formMetodoPago').reset();
}

function guardarMetodoPago() {
    const formData = new FormData(document.getElementById('formMetodoPago'));
    const data = Object.fromEntries(formData);
    
    fetch('/residentes/agregar_metodo_pago', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Método de pago agregado exitosamente');
            cerrarModalMetodos();
            location.reload();
        } else {
            alert('Error al agregar método de pago');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al agregar método de pago');
    });
}

function editarMetodo(id) {
    // Lógica para editar método de pago
    alert(`Editar método ${id}`);
}

function eliminarMetodo(id) {
    if (confirm('¿Está seguro de eliminar este método de pago?')) {
        // Lógica para eliminar método de pago
        alert(`Método ${id} eliminado`);
        location.reload();
    }
}

function descargarComprobante(idPago) {
    // Lógica para descargar comprobante
    alert(`Descargando comprobante del pago ${idPago}`);
}

// Filtros del historial
document.getElementById('filtroMes')?.addEventListener('change', filtrarHistorial);
document.getElementById('filtroEstado')?.addEventListener('change', filtrarHistorial);

function filtrarHistorial() {
    const mes = document.getElementById('filtroMes').value;
    const estado = document.getElementById('filtroEstado').value;
    
    // Lógica para filtrar la tabla
    console.log('Filtrando por:', {mes, estado});
}

// Cerrar modal al hacer clic fuera
window.onclick = function(event) {
    const modal = document.getElementById('modalMetodos');
    if (event.target === modal) {
        cerrarModalMetodos();
    }
}