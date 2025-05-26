"""
Define la clase base para las habilidades (skills) de los agentes.

Las skills son capacidades específicas que los agentes pueden registrar
y utilizar para procesar tareas. Cada skill define su esquema de entrada
y salida, así como la lógica para ejecutar la tarea.
"""

import abc
import asyncio
import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, get_type_hints

from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)


class SkillStatus(str, Enum):
    """Estados posibles de una tarea de skill."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SkillResult(BaseModel):
    """Resultado de la ejecución de una skill."""

    skill_id: str
    task_id: str
    status: SkillStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    execution_time: Optional[float] = None  # en segundos


class Skill(abc.ABC):
    """
    Clase base para todas las habilidades (skills) de los agentes.

    Una skill representa una capacidad específica que un agente puede ejecutar,
    como interactuar con un servicio externo, procesar datos o realizar una tarea.
    """

    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        input_schema: Optional[Type[BaseModel]] = None,
        output_schema: Optional[Type[BaseModel]] = None,
        categories: List[str] = None,
        requires_auth: bool = False,
        is_async: bool = True,
    ):
        """
        Inicializa una nueva skill.

        Args:
            name: Nombre único de la skill
            description: Descripción detallada de lo que hace la skill
            version: Versión de la skill
            input_schema: Modelo Pydantic que define el esquema de entrada
            output_schema: Modelo Pydantic que define el esquema de salida
            categories: Categorías a las que pertenece la skill
            requires_auth: Si la skill requiere autenticación
            is_async: Si la skill se ejecuta de forma asíncrona
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.version = version
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.categories = categories or []
        self.requires_auth = requires_auth
        self.is_async = is_async
        self.tasks: Dict[str, Dict[str, Any]] = {}

        # Inferir esquemas de entrada/salida si no se proporcionan
        if not self.input_schema or not self.output_schema:
            self._infer_schemas()

    def _infer_schemas(self) -> None:
        """
        Infiere los esquemas de entrada y salida a partir de las anotaciones
        de tipo del método execute.
        """
        if not hasattr(self, "execute"):
            logger.warning(f"La skill {self.name} no tiene un método execute")
            return

        # Obtener anotaciones de tipo
        hints = get_type_hints(self.execute)

        # Inferir esquema de entrada
        if not self.input_schema and "input_data" in hints:
            input_type = hints["input_data"]
            if hasattr(input_type, "__origin__") and input_type.__origin__ is dict:
                # Es un Dict[str, Any], crear un modelo dinámico
                self.input_schema = create_model(
                    f"{self.name.title()}Input",
                    __base__=BaseModel,
                    **{"data": (Dict[str, Any], Field(...))},
                )
            elif isinstance(input_type, type) and issubclass(input_type, BaseModel):
                # Ya es un modelo Pydantic
                self.input_schema = input_type

        # Inferir esquema de salida
        if not self.output_schema and "return" in hints:
            output_type = hints["return"]
            if hasattr(output_type, "__origin__") and output_type.__origin__ is dict:
                # Es un Dict[str, Any], crear un modelo dinámico
                self.output_schema = create_model(
                    f"{self.name.title()}Output",
                    __base__=BaseModel,
                    **{"result": (Dict[str, Any], Field(...))},
                )
            elif isinstance(output_type, type) and issubclass(output_type, BaseModel):
                # Ya es un modelo Pydantic
                self.output_schema = output_type

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la skill a un diccionario para serialización.

        Returns:
            Diccionario con los metadatos de la skill
        """
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "categories": self.categories,
            "requires_auth": self.requires_auth,
            "is_async": self.is_async,
        }

        # Agregar esquemas si están disponibles
        if self.input_schema:
            result["input_schema"] = json.loads(self.input_schema.schema_json())

        if self.output_schema:
            result["output_schema"] = json.loads(self.output_schema.schema_json())

        return result

    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida los datos de entrada según el esquema definido.

        Args:
            input_data: Datos de entrada a validar

        Returns:
            Datos validados y convertidos según el esquema

        Raises:
            ValueError: Si los datos no cumplen con el esquema
        """
        if not self.input_schema:
            return input_data

        try:
            validated = self.input_schema(**input_data)
            return validated.dict()
        except Exception as e:
            logger.error(f"Error validando entrada para skill {self.name}: {str(e)}")
            raise ValueError(f"Datos de entrada inválidos: {str(e)}")

    async def execute_task(
        self, task_id: str, input_data: Dict[str, Any]
    ) -> SkillResult:
        """
        Ejecuta la skill como una tarea y registra su estado.

        Args:
            task_id: ID único de la tarea
            input_data: Datos de entrada para la tarea

        Returns:
            Resultado de la ejecución
        """
        # Crear registro de tarea
        start_time = datetime.now()
        task = {
            "task_id": task_id,
            "skill_id": self.id,
            "status": SkillStatus.PENDING,
            "input": input_data,
            "start_time": start_time,
            "end_time": None,
            "result": None,
            "error": None,
        }
        self.tasks[task_id] = task

        # Validar entrada
        try:
            validated_input = self.validate_input(input_data)
        except ValueError as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # Actualizar registro de tarea
            self.tasks[task_id].update(
                {"status": SkillStatus.FAILED, "end_time": end_time, "error": str(e)}
            )

            return SkillResult(
                skill_id=self.id,
                task_id=task_id,
                status=SkillStatus.FAILED,
                error=str(e),
                start_time=start_time,
                end_time=end_time,
                execution_time=execution_time,
            )

        # Actualizar estado a RUNNING
        self.tasks[task_id]["status"] = SkillStatus.RUNNING

        try:
            # Ejecutar la skill
            if self.is_async:
                result = await self.execute(validated_input)
            else:
                # Ejecutar función sincrónica en un thread separado
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self.execute, validated_input)

            # Registrar finalización exitosa
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # Actualizar registro de tarea
            self.tasks[task_id].update(
                {
                    "status": SkillStatus.COMPLETED,
                    "end_time": end_time,
                    "result": result,
                }
            )

            return SkillResult(
                skill_id=self.id,
                task_id=task_id,
                status=SkillStatus.COMPLETED,
                result=result,
                start_time=start_time,
                end_time=end_time,
                execution_time=execution_time,
            )

        except Exception as e:
            # Registrar error
            logger.error(f"Error ejecutando skill {self.name}: {str(e)}")
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # Actualizar registro de tarea
            self.tasks[task_id].update(
                {"status": SkillStatus.FAILED, "end_time": end_time, "error": str(e)}
            )

            return SkillResult(
                skill_id=self.id,
                task_id=task_id,
                status=SkillStatus.FAILED,
                error=str(e),
                start_time=start_time,
                end_time=end_time,
                execution_time=execution_time,
            )

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado de una tarea.

        Args:
            task_id: ID de la tarea

        Returns:
            Estado de la tarea o None si no existe
        """
        return self.tasks.get(task_id)

    @abc.abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la lógica principal de la skill.

        Este método debe ser implementado por cada skill concreta.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Resultado de la ejecución
        """


class SkillRegistry:
    """
    Registro central de skills disponibles en el sistema.

    Permite registrar, descubrir y ejecutar skills por su nombre o categoría.
    """

    _instance = None

    def __new__(cls):
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(SkillRegistry, cls).__new__(cls)
            cls._instance.skills = {}
        return cls._instance

    def register_skill(self, skill: Skill) -> None:
        """
        Registra una nueva skill en el sistema.

        Args:
            skill: Instancia de la skill a registrar
        """
        if skill.name in self.skills:
            logger.warning(f"Skill {skill.name} ya está registrada. Sobrescribiendo.")

        self.skills[skill.name] = skill
        logger.info(f"Skill {skill.name} registrada con ID {skill.id}")

    def get_skill(self, skill_name: str) -> Optional[Skill]:
        """
        Obtiene una skill por su nombre.

        Args:
            skill_name: Nombre de la skill

        Returns:
            Instancia de la skill o None si no existe
        """
        return self.skills.get(skill_name)

    def get_skills_by_category(self, category: str) -> List[Skill]:
        """
        Obtiene todas las skills de una categoría.

        Args:
            category: Categoría de las skills

        Returns:
            Lista de skills que pertenecen a la categoría
        """
        return [skill for skill in self.skills.values() if category in skill.categories]

    def list_skills(self) -> List[Dict[str, Any]]:
        """
        Lista todas las skills registradas.

        Returns:
            Lista de diccionarios con metadatos de las skills
        """
        return [skill.to_dict() for skill in self.skills.values()]

    async def execute_skill(
        self, skill_name: str, input_data: Dict[str, Any], task_id: Optional[str] = None
    ) -> SkillResult:
        """
        Ejecuta una skill por su nombre.

        Args:
            skill_name: Nombre de la skill a ejecutar
            input_data: Datos de entrada para la skill
            task_id: ID opcional para la tarea (se genera uno si no se proporciona)

        Returns:
            Resultado de la ejecución

        Raises:
            ValueError: Si la skill no existe
        """
        skill = self.get_skill(skill_name)
        if not skill:
            raise ValueError(f"Skill {skill_name} no encontrada")

        # Generar ID de tarea si no se proporciona
        if not task_id:
            task_id = str(uuid.uuid4())

        # Ejecutar la skill
        return await skill.execute_task(task_id, input_data)


# Instancia global del registro de skills
skill_registry = SkillRegistry()
