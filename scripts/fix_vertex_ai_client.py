#!/usr/bin/env python3
"""
Script para corregir el archivo clients/vertex_ai_client_optimized.py
"""

import re


def fix_vertex_ai_client():
    """Corrige el archivo clients/vertex_ai_client_optimized.py"""

    # Ruta del archivo
    file_path = "clients/vertex_ai_client_optimized.py"

    # Leer el contenido del archivo
    with open(file_path, "r") as f:
        content = f.read()

    # Corregir el decorador with_retries
    with_retries_pattern = r"def with_retries.*?return decorator"
    with_retries_fixed = '''def with_retries(max_retries=3, base_delay=0.5, backoff_factor=2):
    """
    Decorador para implementar reintentos automáticos con backoff exponencial.
    
    Args:
        max_retries: Número máximo de reintentos
        base_delay: Retraso inicial entre reintentos (segundos)
        backoff_factor: Factor de incremento para el retraso
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (backoff_factor ** attempt)
                        logger.warning(f"Reintento {attempt+1}/{max_retries} para {func.__name__} después de {delay:.2f}s. Error: {str(e)}")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Máximo de reintentos alcanzado para {func.__name__}. Error: {str(e)}")
                        raise
            raise last_exception
        return wrapper
    return decorator'''

    # Reemplazar el decorador
    content = re.sub(with_retries_pattern, with_retries_fixed, content, flags=re.DOTALL)

    # Corregir la clase ConnectionPool
    connection_pool_pattern = r"class ConnectionPool:.*?async def execute\(.*?return await func\(\*args, \*\*kwargs\)"
    connection_pool_fixed = '''class ConnectionPool:
    """
    Pool de conexiones para servicios de Google Cloud.
    
    Gestiona conexiones a diferentes servicios para optimizar recursos.
    """
    
    def __init__(self, max_connections: int = 10):
        """
        Inicializa el pool de conexiones.
        
        Args:
            max_connections: Número máximo de conexiones por servicio
        """
        self.max_connections = max_connections
        self.pools = {}
        self.semaphores = {}
    
    def get_semaphore(self, service_name: str) -> asyncio.Semaphore:
        """
        Obtiene un semáforo para un servicio.
        
        Args:
            service_name: Nombre del servicio
            
        Returns:
            asyncio.Semaphore: Semáforo para el servicio
        """
        if service_name not in self.semaphores:
            self.semaphores[service_name] = asyncio.Semaphore(self.max_connections)
        
        return self.semaphores[service_name]
    
    async def execute(self, service_name: str, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta una función con control de concurrencia.
        
        Args:
            service_name: Nombre del servicio
            func: Función a ejecutar
            *args: Argumentos para la función
            **kwargs: Argumentos con nombre para la función
            
        Returns:
            Any: Resultado de la función
        """
        semaphore = self.get_semaphore(service_name)
        
        async with semaphore:
            return await func(*args, **kwargs)'''

    # Reemplazar la clase ConnectionPool
    content = re.sub(
        connection_pool_pattern, connection_pool_fixed, content, flags=re.DOTALL
    )

    # Corregir el método _update_latency_stats
    latency_stats_pattern = r"async def _update_latency_stats\(.*?latencies\.pop\(0\)"
    latency_stats_fixed = '''async def _update_latency_stats(self, operation: str, start_time: float):
        """
        Actualiza estadísticas de latencia.
        
        Args:
            operation: Nombre de la operación
            start_time: Tiempo de inicio de la operación
        """
        latency_ms = (time.time() - start_time) * 1000
        if operation in self.stats["latency_ms"]:
            # Mantener solo las últimas 100 mediciones
            latencies = self.stats["latency_ms"][operation]
            latencies.append(latency_ms)
            if len(latencies) > 100:
                latencies.pop(0)'''

    # Reemplazar el método _update_latency_stats
    content = re.sub(
        latency_stats_pattern, latency_stats_fixed, content, flags=re.DOTALL
    )

    # Guardar el archivo corregido
    with open(file_path, "w") as f:
        f.write(content)

    print(f"Archivo {file_path} corregido exitosamente.")


if __name__ == "__main__":
    fix_vertex_ai_client()
