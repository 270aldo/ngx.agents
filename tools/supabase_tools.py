"""
Habilidades para interactuar con Supabase.

Este módulo implementa skills que permiten realizar operaciones CRUD
en tablas de Supabase y ejecutar consultas SQL personalizadas.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from clients.supabase_client import supabase_client
from core.skill import Skill, skill_registry


class SupabaseQueryInput(BaseModel):
    """Esquema de entrada para la skill de consulta a Supabase."""

    table: str = Field(..., description="Nombre de la tabla a consultar")
    select: str = Field("*", description="Columnas a seleccionar (formato PostgreSQL)")
    filters: Optional[Dict[str, Any]] = Field(
        None, description="Filtros para la consulta"
    )
    order: Optional[str] = Field(None, description="Ordenamiento (formato PostgreSQL)")
    limit: Optional[int] = Field(None, description="Límite de resultados")
    offset: Optional[int] = Field(None, description="Offset para paginación")


class SupabaseQueryOutput(BaseModel):
    """Esquema de salida para la skill de consulta a Supabase."""

    results: List[Dict[str, Any]] = Field(..., description="Resultados de la consulta")
    count: int = Field(..., description="Número de resultados")


class SupabaseQuerySkill(Skill):
    """
    Skill para consultar datos en Supabase.

    Permite realizar consultas en tablas de Supabase con filtros,
    ordenamiento y paginación.
    """

    def __init__(self):
        """Inicializa la skill de consulta a Supabase."""
        super().__init__(
            name="supabase_query",
            description="Consulta datos en tablas de Supabase",
            version="1.0.0",
            input_schema=SupabaseQueryInput,
            output_schema=SupabaseQueryOutput,
            categories=["database", "query", "storage"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una consulta en Supabase.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Resultados de la consulta
        """
        # Extraer parámetros
        table = input_data["table"]
        select = input_data.get("select", "*")
        filters = input_data.get("filters")
        order = input_data.get("order")
        limit = input_data.get("limit")
        offset = input_data.get("offset")

        # Ejecutar consulta
        results = await supabase_client.query(
            table_name=table,
            select=select,
            filters=filters,
            order=order,
            limit=limit,
            offset=offset,
        )

        # Construir resultado
        return {"results": results, "count": len(results)}


class SupabaseInsertInput(BaseModel):
    """Esquema de entrada para la skill de inserción en Supabase."""

    table: str = Field(..., description="Nombre de la tabla donde insertar")
    data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(
        ..., description="Datos a insertar"
    )
    upsert: bool = Field(
        False, description="Si es True, actualiza registros existentes"
    )


class SupabaseInsertOutput(BaseModel):
    """Esquema de salida para la skill de inserción en Supabase."""

    results: List[Dict[str, Any]] = Field(..., description="Registros insertados")
    count: int = Field(..., description="Número de registros insertados")


class SupabaseInsertSkill(Skill):
    """
    Skill para insertar datos en Supabase.

    Permite insertar uno o varios registros en una tabla de Supabase.
    """

    def __init__(self):
        """Inicializa la skill de inserción en Supabase."""
        super().__init__(
            name="supabase_insert",
            description="Inserta datos en tablas de Supabase",
            version="1.0.0",
            input_schema=SupabaseInsertInput,
            output_schema=SupabaseInsertOutput,
            categories=["database", "insert", "storage"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una inserción en Supabase.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Registros insertados
        """
        # Extraer parámetros
        table = input_data["table"]
        data = input_data["data"]
        upsert = input_data.get("upsert", False)

        # Ejecutar inserción
        results = await supabase_client.insert(
            table_name=table, data=data, upsert=upsert
        )

        # Construir resultado
        return {"results": results, "count": len(results)}


class SupabaseSQLInput(BaseModel):
    """Esquema de entrada para la skill de SQL personalizado en Supabase."""

    sql: str = Field(..., description="Consulta SQL a ejecutar")
    params: Optional[Dict[str, Any]] = Field(
        None, description="Parámetros para la consulta"
    )


class SupabaseSQLOutput(BaseModel):
    """Esquema de salida para la skill de SQL personalizado en Supabase."""

    results: List[Dict[str, Any]] = Field(..., description="Resultados de la consulta")
    count: int = Field(..., description="Número de resultados")


class SupabaseSQLSkill(Skill):
    """
    Skill para ejecutar SQL personalizado en Supabase.

    Permite ejecutar consultas SQL personalizadas en Supabase.
    """

    def __init__(self):
        """Inicializa la skill de SQL personalizado en Supabase."""
        super().__init__(
            name="supabase_sql",
            description="Ejecuta consultas SQL personalizadas en Supabase",
            version="1.0.0",
            input_schema=SupabaseSQLInput,
            output_schema=SupabaseSQLOutput,
            categories=["database", "sql", "storage"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una consulta SQL personalizada en Supabase.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Resultados de la consulta
        """
        # Extraer parámetros
        sql = input_data["sql"]
        params = input_data.get("params")

        # Validar que la consulta no sea peligrosa
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "GRANT"]
        for keyword in dangerous_keywords:
            if keyword in sql.upper() and not sql.upper().startswith("SELECT"):
                raise ValueError(
                    f"Consulta SQL potencialmente peligrosa. No se permiten operaciones {keyword}"
                )

        # Ejecutar consulta
        results = await supabase_client.execute_sql(sql=sql, params=params)

        # Construir resultado
        return {"results": results, "count": len(results)}


class SupabaseLogActivityInput(BaseModel):
    """Esquema de entrada para la skill de registro de actividad en Supabase."""

    agent_id: str = Field(..., description="ID del agente")
    activity_type: str = Field(..., description="Tipo de actividad")
    details: Dict[str, Any] = Field(..., description="Detalles de la actividad")


class SupabaseLogActivityOutput(BaseModel):
    """Esquema de salida para la skill de registro de actividad en Supabase."""

    success: bool = Field(..., description="Si el registro fue exitoso")
    activity_id: Optional[str] = Field(
        None, description="ID de la actividad registrada"
    )


class SupabaseLogActivitySkill(Skill):
    """
    Skill para registrar actividad de agentes en Supabase.

    Permite registrar eventos y acciones de los agentes para seguimiento.
    """

    def __init__(self):
        """Inicializa la skill de registro de actividad en Supabase."""
        super().__init__(
            name="supabase_log_activity",
            description="Registra actividad de agentes en Supabase",
            version="1.0.0",
            input_schema=SupabaseLogActivityInput,
            output_schema=SupabaseLogActivityOutput,
            categories=["logging", "monitoring", "storage"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el registro de actividad en Supabase.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Resultado del registro
        """
        # Extraer parámetros
        agent_id = input_data["agent_id"]
        activity_type = input_data["activity_type"]
        details = input_data["details"]

        # Registrar actividad
        try:
            result = await supabase_client.log_agent_activity(
                agent_id=agent_id, activity_type=activity_type, details=details
            )

            # Construir resultado exitoso
            return {"success": True, "activity_id": result.get("id")}
        except Exception as e:
            # Construir resultado fallido
            return {"success": False, "error": str(e)}


class SupabaseUpdateInput(BaseModel):
    """Esquema de entrada para la skill de actualización en Supabase."""

    table: str = Field(..., description="Nombre de la tabla donde actualizar")
    data: Dict[str, Any] = Field(..., description="Datos a actualizar")
    filters: Dict[str, Any] = Field(
        ..., description="Filtros para identificar registros"
    )


class SupabaseUpdateOutput(BaseModel):
    """Esquema de salida para la skill de actualización en Supabase."""

    results: List[Dict[str, Any]] = Field(..., description="Registros actualizados")
    count: int = Field(..., description="Número de registros actualizados")


class SupabaseUpdateSkill(Skill):
    """
    Skill para actualizar datos en Supabase.

    Permite actualizar registros existentes en una tabla de Supabase.
    """

    def __init__(self):
        """Inicializa la skill de actualización en Supabase."""
        super().__init__(
            name="supabase_update",
            description="Actualiza datos en tablas de Supabase",
            version="1.0.0",
            input_schema=SupabaseUpdateInput,
            output_schema=SupabaseUpdateOutput,
            categories=["database", "update", "storage"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una actualización en Supabase.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Registros actualizados
        """
        # Extraer parámetros
        table = input_data["table"]
        data = input_data["data"]
        filters = input_data["filters"]

        # Ejecutar actualización
        results = await supabase_client.update(
            table_name=table, data=data, filters=filters
        )

        # Construir resultado
        return {"results": results, "count": len(results)}


class SupabaseDeleteInput(BaseModel):
    """Esquema de entrada para la skill de eliminación en Supabase."""

    table: str = Field(..., description="Nombre de la tabla donde eliminar")
    filters: Dict[str, Any] = Field(
        ..., description="Filtros para identificar registros a eliminar"
    )
    confirm: bool = Field(False, description="Confirmación de eliminación")


class SupabaseDeleteOutput(BaseModel):
    """Esquema de salida para la skill de eliminación en Supabase."""

    results: List[Dict[str, Any]] = Field(..., description="Registros eliminados")
    count: int = Field(..., description="Número de registros eliminados")


class SupabaseDeleteSkill(Skill):
    """
    Skill para eliminar datos en Supabase.

    Permite eliminar registros existentes en una tabla de Supabase.
    """

    def __init__(self):
        """Inicializa la skill de eliminación en Supabase."""
        super().__init__(
            name="supabase_delete",
            description="Elimina datos en tablas de Supabase",
            version="1.0.0",
            input_schema=SupabaseDeleteInput,
            output_schema=SupabaseDeleteOutput,
            categories=["database", "delete", "storage"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una eliminación en Supabase.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Registros eliminados
        """
        # Extraer parámetros
        table = input_data["table"]
        filters = input_data["filters"]
        confirm = input_data.get("confirm", False)

        # Verificar confirmación
        if not confirm:
            raise ValueError(
                "Se requiere confirmación para eliminar datos. Establezca 'confirm' en True."
            )

        # Ejecutar eliminación
        results = await supabase_client.delete(table_name=table, filters=filters)

        # Construir resultado
        return {"results": results, "count": len(results)}


class SupabaseHealthCheckInput(BaseModel):
    """Esquema de entrada para la skill de verificación de estado de Supabase."""

    detailed: bool = Field(
        False, description="Si es True, devuelve información detallada"
    )


class SupabaseHealthCheckOutput(BaseModel):
    """Esquema de salida para la skill de verificación de estado de Supabase."""

    status: str = Field(
        ..., description="Estado de la conexión (online, offline, error)"
    )
    latency_ms: Optional[float] = Field(None, description="Latencia en milisegundos")
    details: Optional[Dict[str, Any]] = Field(None, description="Detalles adicionales")


class SupabaseHealthCheckSkill(Skill):
    """
    Skill para verificar el estado de la conexión con Supabase.

    Permite comprobar si la conexión con Supabase está funcionando
    correctamente y obtener métricas de rendimiento.
    """

    def __init__(self):
        """Inicializa la skill de verificación de estado de Supabase."""
        super().__init__(
            name="supabase_health_check",
            description="Verifica el estado de la conexión con Supabase",
            version="1.0.0",
            input_schema=SupabaseHealthCheckInput,
            output_schema=SupabaseHealthCheckOutput,
            categories=["monitoring", "health", "diagnostics"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una verificación de estado de Supabase.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Estado de la conexión
        """
        import time

        # Extraer parámetros
        detailed = input_data.get("detailed", False)

        # Verificar conexión
        try:
            # Medir tiempo de respuesta
            start_time = time.time()

            # Ejecutar una consulta simple para verificar la conexión
            await supabase_client.query(
                table_name="health_check", select="count(*)", limit=1
            )

            # Calcular latencia
            latency_ms = (time.time() - start_time) * 1000

            # Construir resultado básico
            result = {"status": "online", "latency_ms": latency_ms}

            # Añadir detalles si se solicitan
            if detailed:
                # Obtener estadísticas del cliente
                stats = (
                    supabase_client.get_stats()
                    if hasattr(supabase_client, "get_stats")
                    else {}
                )

                result["details"] = {
                    "api_calls": stats,
                    "timestamp": time.time(),
                    "client_info": {
                        "initialized": supabase_client._initialized,
                        "service_name": supabase_client.service_name,
                    },
                }

            return result

        except Exception as e:
            # En caso de error, reportar estado offline
            return {
                "status": "error",
                "details": {"error": str(e), "timestamp": time.time()},
            }


# Registrar las skills
skill_registry.register_skill(SupabaseQuerySkill())
skill_registry.register_skill(SupabaseInsertSkill())
skill_registry.register_skill(SupabaseSQLSkill())
skill_registry.register_skill(SupabaseLogActivitySkill())
skill_registry.register_skill(SupabaseUpdateSkill())
skill_registry.register_skill(SupabaseDeleteSkill())
skill_registry.register_skill(SupabaseHealthCheckSkill())
