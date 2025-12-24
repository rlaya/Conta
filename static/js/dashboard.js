// Dashboard JavaScript
class DashboardManager {
    constructor() {
        this.initEventListeners();
        this.initCharts();
    }
    
    initEventListeners() {
        // Botón para refrescar datos
        document.getElementById('refresh-btn')?.addEventListener('click', () => this.refreshData());
        
        // Filtros de fecha
        document.querySelectorAll('.date-filter').forEach(filter => {
            filter.addEventListener('change', () => this.applyFilters());
        });
    }
    
    initCharts() {
        // Inicializar gráficos adicionales si es necesario
        this.initMiniCharts();
    }
    
    initMiniCharts() {
        // Gráficos mini para tarjetas de resumen
        const miniCharts = document.querySelectorAll('.mini-chart');
        miniCharts.forEach(chart => {
            this.createMiniChart(chart);
        });
    }
    
    createMiniChart(container) {
        // Implementar gráficos mini con Chart.js si es necesario
    }
    
    async refreshData() {
        try {
            // Mostrar loader
            this.showLoading(true);
            
            const response = await fetch('/api/dashboard-data');
            const data = await response.json();
            
            if (data.success) {
                this.updateUI(data);
                this.showNotification('Datos actualizados correctamente', 'success');
            } else {
                throw new Error(data.error || 'Error al actualizar datos');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('Error al actualizar datos: ' + error.message, 'danger');
        } finally {
            this.showLoading(false);
        }
    }
    
    updateUI(data) {
        // Actualizar elementos de la UI con nuevos datos
        // Esto es solo un ejemplo, implementa según necesites
        
        // Actualizar timestamp
        const now = new Date();
        document.getElementById('last-update').textContent = 
            now.toLocaleTimeString('es-ES');
        
        // Actualizar tarjetas de resumen si existen
        this.updateSummaryCards(data.summary);
    }
    
    updateSummaryCards(summary) {
        // Implementar actualización de tarjetas de resumen
    }
    
    showNotification(message, type = 'info') {
        // Crear notificación Bootstrap
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.top = '20px';
        alertDiv.style.right = '20px';
        alertDiv.style.zIndex = '9999';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-remover después de 5 segundos
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    showLoading(show) {
        const loader = document.getElementById('loader') || this.createLoader();
        loader.style.display = show ? 'block' : 'none';
    }
    
    createLoader() {
        const loader = document.createElement('div');
        loader.id = 'loader';
        loader.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
        loader.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
        loader.style.zIndex = '9999';
        loader.style.display = 'none';
        loader.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Cargando...</span>
            </div>
        `;
        document.body.appendChild(loader);
        return loader;
    }
    
    applyFilters() {
        // Aplicar filtros y recargar datos
        this.refreshData();
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardManager = new DashboardManager();
});