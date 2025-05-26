"""
Cliente para Supabase que proporciona acceso a la base de datos.

Este módulo implementa un cliente Singleton para Supabase que se
encarga de gestionar la conexión y proporcionar métodos para
interactuar con la base de datos.
"""

import logging
import time
from typing import Dict, Any, Optional, List

# Importar el cliente de Supabase
try:
    from supabase import Client, create_client

    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logging.warning("Supabase no está disponible. Se usará un cliente mock.")

from core.settings import settings
from core.logging_config import get_logger
from core.circuit_breaker import circuit_breaker, CircuitBreakerOpenError

# Configurar logger
logger = get_logger(__name__)


class SupabaseClient:
    """
    Cliente Singleton para Supabase.

    Este cliente proporciona métodos para interactuar con la base de datos
    Supabase y se encarga de gestionar la conexión.
    """

    def __init__(self):
        """
        Inicializa el cliente de Supabase.
        """
        self.url = settings.supabase_url
        self.key = settings.supabase_anon_key
        self.supabase: Optional[Client] = None
        self.is_initialized = False

        logger.info("Cliente de Supabase inicializado")

    async def initialize(self) -> None:
        """
        Inicializa la conexión con Supabase.
        """
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase no está disponible. Se usará un cliente mock.")
            self.supabase = MockSupabaseClient()
            self.is_initialized = True
            return

        try:
            # Crear cliente de Supabase
            self.supabase = create_client(self.url, self.key)

            # Verificar conexión
            await self.supabase.table("health_check").select("*").limit(1).execute()

            self.is_initialized = True
            logger.info("Conexión con Supabase establecida correctamente")

        except Exception as e:
            logger.error(f"Error al inicializar conexión con Supabase: {e}")
            raise

    async def get_client(self) -> Client:
        """
        Obtiene el cliente de Supabase.

        Si no se ha inicializado, lo inicializa.

        Returns:
            Client: Cliente de Supabase
        """
        if not self.is_initialized:
            await self.initialize()

        return self.supabase

    @circuit_breaker(
        name="supabase_query",
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=Exception,
    )
    async def _execute_db_operation(self, query):
        """
        Ejecuta una operación de base de datos con circuit breaker.

        Args:
            query: Query de Supabase preparada

        Returns:
            Resultado de la operación
        """
        result = await query.execute()
        return result

    async def execute_query(
        self, table: str, query_type: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Ejecuta una consulta en Supabase.

        Args:
            table: Nombre de la tabla
            query_type: Tipo de consulta (select, insert, update, delete)
            **kwargs: Argumentos adicionales para la consulta

        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        if not self.is_initialized:
            await self.initialize()

        try:
            # Construir consulta
            query = self.supabase.table(table)

            if query_type == "select":
                if "columns" in kwargs:
                    query = query.select(kwargs["columns"])
                else:
                    query = query.select("*")

                if "filters" in kwargs:
                    for filter_key, filter_value in kwargs["filters"].items():
                        if isinstance(filter_value, dict):
                            operator = filter_value.get("operator", "eq")
                            value = filter_value.get("value")

                            if operator == "eq":
                                query = query.eq(filter_key, value)
                            elif operator == "neq":
                                query = query.neq(filter_key, value)
                            elif operator == "gt":
                                query = query.gt(filter_key, value)
                            elif operator == "lt":
                                query = query.lt(filter_key, value)
                            elif operator == "gte":
                                query = query.gte(filter_key, value)
                            elif operator == "lte":
                                query = query.lte(filter_key, value)
                            elif operator == "in":
                                query = query.in_(filter_key, value)
                            elif operator == "is":
                                query = query.is_(filter_key, value)
                        else:
                            query = query.eq(filter_key, filter_value)

                if "limit" in kwargs:
                    query = query.limit(kwargs["limit"])

                if "order" in kwargs:
                    for order_key, order_dir in kwargs["order"].items():
                        if order_dir.lower() == "asc":
                            query = query.order(order_key, ascending=True)
                        else:
                            query = query.order(order_key, ascending=False)

                # Ejecutar consulta con circuit breaker
                try:
                    result = await self._execute_db_operation(query)
                    return result.dict()
                except CircuitBreakerOpenError:
                    logger.error("Circuit breaker abierto para Supabase")
                    raise

            elif query_type == "insert":
                data = kwargs.get("data", {})
                query_with_data = query.insert(data)
                try:
                    result = await self._execute_db_operation(query_with_data)
                    return result.dict()
                except CircuitBreakerOpenError:
                    logger.error("Circuit breaker abierto para Supabase")
                    raise

            elif query_type == "update":
                data = kwargs.get("data", {})
                filters = kwargs.get("filters", {})

                for filter_key, filter_value in filters.items():
                    if isinstance(filter_value, dict):
                        operator = filter_value.get("operator", "eq")
                        value = filter_value.get("value")

                        if operator == "eq":
                            query = query.eq(filter_key, value)
                        elif operator == "neq":
                            query = query.neq(filter_key, value)
                        # ... otros operadores
                    else:
                        query = query.eq(filter_key, filter_value)

                query_with_data = query.update(data)
                try:
                    result = await self._execute_db_operation(query_with_data)
                    return result.dict()
                except CircuitBreakerOpenError:
                    logger.error("Circuit breaker abierto para Supabase")
                    raise

            elif query_type == "delete":
                filters = kwargs.get("filters", {})

                for filter_key, filter_value in filters.items():
                    if isinstance(filter_value, dict):
                        operator = filter_value.get("operator", "eq")
                        value = filter_value.get("value")

                        if operator == "eq":
                            query = query.eq(filter_key, value)
                        # ... otros operadores
                    else:
                        query = query.eq(filter_key, filter_value)

                query_delete = query.delete()
                try:
                    result = await self._execute_db_operation(query_delete)
                    return result.dict()
                except CircuitBreakerOpenError:
                    logger.error("Circuit breaker abierto para Supabase")
                    raise

            else:
                raise ValueError(f"Tipo de consulta no soportado: {query_type}")

        except Exception as e:
            logger.error(f"Error al ejecutar consulta en Supabase: {e}")
            raise


class MockSupabaseClient:
    """
    Cliente mock para Supabase cuando no está disponible.

    Esta clase proporciona un cliente mock que implementa la misma
    interfaz que el cliente de Supabase, pero no realiza ninguna
    operación real.
    """

    def __init__(self):
        """
        Inicializa el cliente mock.
        """
        self.tables = {}
        logger.warning("Usando cliente mock para Supabase")

    def table(self, name: str):
        """
        Selecciona una tabla.

        Args:
            name: Nombre de la tabla

        Returns:
            self: Instancia del cliente para encadenar métodos
        """
        self.current_table = name
        return self

    def select(self, columns: str = "*"):
        """
        Selecciona columnas.

        Args:
            columns: Columnas a seleccionar

        Returns:
            self: Instancia del cliente para encadenar métodos
        """
        self.current_columns = columns
        return self

    def eq(self, column: str, value: Any):
        """
        Filtro de igualdad.

        Args:
            column: Nombre de la columna
            value: Valor a comparar

        Returns:
            self: Instancia del cliente para encadenar métodos
        """
        return self

    def neq(self, column: str, value: Any):
        """
        Filtro de desigualdad.

        Args:
            column: Nombre de la columna
            value: Valor a comparar

        Returns:
            self: Instancia del cliente para encadenar métodos
        """
        return self

    def limit(self, count: int):
        """
        Limita el número de resultados.

        Args:
            count: Número máximo de resultados

        Returns:
            self: Instancia del cliente para encadenar métodos
        """
        return self

    async def execute(self):
        """
        Ejecuta la consulta.

        Returns:
            MockSupabaseResult: Resultado mock
        """
        # Devolver resultado mock
        return MockSupabaseResult([])


class MockSupabaseResult:
    """
    Resultado mock para Supabase.

    Esta clase proporciona un resultado mock para simular
    las respuestas del cliente de Supabase.
    """

    def __init__(self, data: List[Dict[str, Any]]):
        """
        Inicializa el resultado mock.

        Args:
            data: Datos del resultado
        """
        self.data = data

    def dict(self) -> Dict[str, Any]:
        """
        Convierte el resultado a diccionario.

        Returns:
            Dict[str, Any]: Resultado en formato diccionario
        """
        return {"data": self.data, "count": len(self.data)}


# Crear instancia del cliente
supabase_client = SupabaseClient()


async def check_database_connection() -> Dict[str, Any]:
    """
    Verifica la conexión con la base de datos Supabase.

    Returns:
        Dict[str, Any]: Diccionario con el estado de la conexión
    """
    try:
        # Obtener instancia del cliente
        client = supabase_client

        # Verificar si el cliente está inicializado
        if not client.is_initialized:
            await client.initialize()

        # Hacer una consulta simple para verificar la conexión
        # Usamos una consulta que no acceda a datos sensibles
        result = (
            await client.supabase.table("health_check").select("*").limit(1).execute()
        )

        # Actualizar estado en el health tracker
        from core.telemetry import health_tracker

        health_tracker.update_status(
            component="database",
            status=True,
            details="Conexión a base de datos establecida correctamente",
            alert_on_degraded=True,
        )

        return {
            "status": "ok",
            "timestamp": time.time(),
            "details": {
                "url": client.url,
                "database_type": "Supabase",
                "connection_status": "Connected",
            },
        }
    except Exception as e:
        logging.error(f"Error al verificar conexión con base de datos: {e}")

        # Actualizar estado en el health tracker
        from core.telemetry import health_tracker

        health_tracker.update_status(
            component="database",
            status=False,
            details=f"Error en la conexión a base de datos: {str(e)}",
            alert_on_degraded=True,
        )

        return {
            "status": "error",
            "timestamp": time.time(),
            "details": {"error": str(e), "error_type": type(e).__name__},
        }
