"""
Servicio de clasificación de programas NGX.

Este servicio proporciona funcionalidades para clasificar usuarios en los diferentes
tipos de programas ofrecidos por NGX (PRIME, LONGEVITY, etc.) utilizando tanto
reglas basadas en palabras clave como modelos de lenguaje natural.
"""

import hashlib
import json
import logging
import os
import re
from typing import Dict, Any, Optional, List

from clients.gemini_client import GeminiClient
from clients.vertex_ai.cache import CacheManager
from agents.shared.program_definitions import (
    get_program_definition,
    get_program_keywords,
    get_age_range,
    get_all_program_types,
)

# Configurar logger
logger = logging.getLogger(__name__)


class ProgramClassificationService:
    """
    Servicio centralizado para la clasificación de programas.
    Proporciona métodos para clasificar usuarios en tipos de programas
    utilizando tanto LLM como reglas basadas en palabras clave.
    Incluye un sistema de caché para mejorar el rendimiento.
    """

    def __init__(
        self, gemini_client: Optional[GeminiClient] = None, use_cache: bool = True
    ):
        """
        Inicializa el servicio de clasificación de programas.

        Args:
            gemini_client: Cliente de Gemini para clasificación basada en LLM
            use_cache: Si se debe utilizar el sistema de caché
        """
        self.gemini_client = gemini_client
        self.logger = logging.getLogger(__name__)
        self.use_cache = use_cache

        # Inicializar sistema de caché
        use_redis = os.environ.get("USE_REDIS_CACHE", "false").lower() == "true"
        redis_url = os.environ.get("REDIS_URL")
        cache_ttl = int(
            os.environ.get("PROGRAM_CACHE_TTL", "3600")
        )  # 1 hora por defecto

        self.cache_manager = CacheManager(
            use_redis=use_redis,
            redis_url=redis_url,
            ttl=cache_ttl,
            max_memory_size=100,  # 100MB para caché en memoria
            compression_threshold=512,  # Comprimir valores mayores a 512 bytes
        )

        # Almacenar en caché las definiciones de programas para un acceso más rápido
        self._program_definitions_cache = {}
        for program_type in get_all_program_types():
            self._program_definitions_cache[program_type] = get_program_definition(
                program_type
            )

        # Estadísticas de caché
        self.cache_stats = {"hits": 0, "misses": 0, "total_requests": 0}

    def _generate_cache_key(self, data: Any) -> str:
        """
        Genera una clave de caché para los datos proporcionados.

        Args:
            data: Datos para generar la clave

        Returns:
            str: Clave de caché
        """
        # Serializar datos a JSON
        try:
            serialized = json.dumps(data, sort_keys=True)
        except (TypeError, ValueError):
            # Si no se puede serializar, usar representación de string
            serialized = str(data)

        # Generar hash
        key = hashlib.md5(serialized.encode("utf-8")).hexdigest()
        return f"program_classification:{key}"

    async def classify_program_type(
        self, context: Dict[str, Any], use_llm: bool = True
    ) -> str:
        """
        Clasifica el tipo de programa basado en el contexto del usuario.
        Utiliza un enfoque híbrido: primero verifica si el tipo está explícitamente definido,
        luego intenta usar LLM para clasificación avanzada, y finalmente cae en reglas basadas en keywords.

        Args:
            context: Contexto del usuario que puede incluir program_type, user_profile, goals, etc.
            use_llm: Si se debe usar LLM para la clasificación

        Returns:
            str: Tipo de programa (PRIME, LONGEVITY, STRENGTH, HYPERTROPHY, ENDURANCE, ATHLETIC, PERFORMANCE)
        """
        self.logger.debug(f"Clasificando tipo de programa desde contexto: {context}")

        # 1. Verificar si 'program_type' está explícitamente en el contexto
        program_type = context.get("program_type")
        if program_type and isinstance(program_type, str):
            standardized_type = program_type.upper()
            valid_types = get_all_program_types()
            if standardized_type in valid_types:
                self.logger.info(
                    f"Tipo de programa encontrado explícitamente en contexto: {standardized_type}"
                )
                return standardized_type

        # Verificar caché si está habilitado
        if self.use_cache:
            # Crear una clave de caché basada en el contexto y configuración
            cache_key = self._generate_cache_key(
                {"context": context, "use_llm": use_llm}
            )

            # Intentar obtener resultado de caché
            self.cache_stats["total_requests"] += 1
            cached_result = await self.cache_manager.get(cache_key)

            if cached_result:
                self.cache_stats["hits"] += 1
                self.logger.info(f"Tipo de programa obtenido de caché: {cached_result}")
                return cached_result
            else:
                self.cache_stats["misses"] += 1
                self.logger.debug("Caché miss para clasificación de programa")

        # 2. Usar LLM para clasificación avanzada si está disponible y habilitado
        if use_llm and self.gemini_client:
            try:
                llm_program_type = await self._classify_with_llm(context)
                if llm_program_type:
                    self.logger.info(
                        f"Tipo de programa determinado por LLM: {llm_program_type}"
                    )

                    # Guardar en caché si está habilitado
                    if self.use_cache:
                        await self.cache_manager.set(cache_key, llm_program_type)

                    return llm_program_type
            except Exception as e:
                self.logger.error(
                    f"Error al clasificar tipo de programa con LLM: {e}", exc_info=True
                )
                # Continuar con enfoque basado en reglas si falla LLM
        elif use_llm and not self.gemini_client:
            self.logger.warning(
                "GeminiClient no disponible para clasificación avanzada de tipo de programa"
            )

        # 3. Enfoque basado en reglas como fallback
        rule_based_type = self._classify_with_rules(context)
        self.logger.info(f"Tipo de programa determinado por reglas: {rule_based_type}")

        # Guardar en caché si está habilitado
        if self.use_cache:
            await self.cache_manager.set(cache_key, rule_based_type)

        return rule_based_type

    def enrich_query_with_program_context(self, query: str, program_type: str) -> str:
        """
        Enriquece una consulta con información específica del programa.
        Añade contexto relevante sobre el programa para mejorar las respuestas de otros agentes.

        Args:
            query: La consulta original
            program_type: El tipo de programa (PRIME, LONGEVITY, etc.)

        Returns:
            str: La consulta enriquecida con contexto del programa
        """
        if not program_type or program_type not in self._program_definitions_cache:
            self.logger.warning(
                f"Tipo de programa no reconocido para enriquecer consulta: {program_type}"
            )
            return query

        # Obtener la definición del programa
        program_def = self._program_definitions_cache.get(program_type)
        if not program_def:
            program_def = get_program_definition(program_type)
            self._program_definitions_cache[program_type] = program_def

        if not program_def:
            return query

        # Extraer información clave para enriquecer la consulta
        enrichment = f"""\n\nContexto del programa {program_type}:\n"""

        # Añadir descripción y objetivo si están disponibles
        if program_def.get("description"):
            enrichment += f"- {program_def['description']}\n"
        if program_def.get("objective"):
            enrichment += f"- Objetivo: {program_def['objective']}\n"

        # Añadir pilares si están disponibles (máximo 3 para mantener la consulta concisa)
        if program_def.get("pillars") and len(program_def["pillars"]) > 0:
            pillars = program_def["pillars"][:3]  # Limitar a 3 pilares
            enrichment += f"- Pilares: {', '.join(pillars)}\n"

        # Añadir protocolos clave si están disponibles
        if program_def.get("key_protocols"):
            # Verificar si key_protocols es un diccionario o una lista
            if isinstance(program_def["key_protocols"], dict):
                # Si es un diccionario, tomar las primeras 2 claves
                protocol_keys = list(program_def["key_protocols"].keys())[:2]
                protocols = [f"{k}" for k in protocol_keys]
                enrichment += f"- Protocolos clave: {', '.join(protocols)}\n"
            elif (
                isinstance(program_def["key_protocols"], list)
                and len(program_def["key_protocols"]) > 0
            ):
                # Si es una lista, tomar los primeros 2 elementos
                protocols = program_def["key_protocols"][:2]
                enrichment += f"- Protocolos clave: {', '.join(protocols)}\n"

        # Verificar si la consulta ya contiene instrucciones específicas
        has_instructions = re.search(
            r"(considera|ten en cuenta|basado en|enfocado en|para el programa)",
            query.lower(),
        )

        # Si ya hay instrucciones, añadir el contexto al final
        # Si no, añadir una instrucción para considerar el contexto
        if has_instructions:
            enriched_query = f"{query}{enrichment}"
        else:
            enriched_query = f"{query}\n\nPor favor, considera el siguiente contexto al responder:{enrichment}"

        self.logger.debug(
            f"Consulta enriquecida con información del programa {program_type}"
        )
        return enriched_query

    async def _classify_with_llm(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Utiliza el LLM para clasificar el perfil y objetivos del usuario en un tipo de programa.
        Incorpora conocimiento detallado sobre los programas para una clasificación precisa.

        Args:
            context: Contexto del usuario que puede incluir user_profile, goals, etc.

        Returns:
            Optional[str]: Tipo de programa determinado por el LLM, o None si no se pudo determinar
        """
        user_profile = context.get("user_profile", {})
        goals = context.get("goals", [])
        if isinstance(goals, str):
            goals = [goals]

        # Extraer información relevante del perfil
        age = user_profile.get("age", "No especificado")
        experience_level = user_profile.get("experience_level", "No especificado")
        limitations = user_profile.get("limitations", [])
        if isinstance(limitations, str):
            limitations = [limitations]
        professional_role = user_profile.get("professional_role", "No especificado")

        # Construir prompt para el LLM con definiciones detalladas de los programas
        prompt = f"""
        Eres un experto en clasificación de programas de entrenamiento y bienestar. 
        Tu tarea es analizar el perfil del usuario y determinar qué tipo de programa se ajusta mejor a sus necesidades y características.
        
        DEFINICIONES DETALLADAS DE PROGRAMAS:
        """

        # Añadir definiciones de todos los programas disponibles
        for program_type in get_all_program_types():
            program_def = self._program_definitions_cache.get(program_type, {})
            if not program_def:
                program_def = get_program_definition(program_type)
                self._program_definitions_cache[program_type] = program_def

            prompt += f"""
        
        {program_type} - {program_def.get('description', '')}:
           - {program_def.get('objective', '')}
           - Pilares: {', '.join(program_def.get('pillars', []))}
           - Características del usuario: {', '.join(program_def.get('user_characteristics', []))}
           - Necesidades: {', '.join(program_def.get('user_needs', []))}
           - Protocolos: {', '.join(program_def.get('key_protocols', []) if isinstance(program_def.get('key_protocols', []), list) else list(program_def.get('key_protocols', {}).keys()))}
        """

            # Añadir rango de edad si está definido
            age_range = get_age_range(program_type)
            if age_range:
                min_age, max_age = age_range
                if min_age is not None and max_age is not None:
                    prompt += (
                        f"           - Rango de edad típico: {min_age}-{max_age} años\n"
                    )
                elif min_age is not None:
                    prompt += f"           - Edad mínima recomendada: {min_age} años\n"
                elif max_age is not None:
                    prompt += f"           - Edad máxima recomendada: {max_age} años\n"

        prompt += f"""
        
        PERFIL DEL USUARIO:
        - Edad: {age}
        - Nivel de experiencia: {experience_level}
        - Rol profesional: {professional_role}
        - Limitaciones: {', '.join(limitations) if limitations else 'Ninguna especificada'}
        - Objetivos: {', '.join(goals) if goals else 'No especificados'}
        - Contexto adicional: {json.dumps(context, indent=2, ensure_ascii=False)}
        
        INSTRUCCIONES:
        1. Analiza cuidadosamente el perfil y determina qué tipo de programa se ajusta mejor.
        2. Considera especialmente la edad, rol profesional y objetivos para determinar el programa más adecuado.
        3. Si no hay suficiente información o el perfil no se ajusta claramente a ninguna categoría específica, clasifica como PERFORMANCE.
        4. Devuelve SOLO el nombre del programa en mayúsculas, sin explicaciones adicionales.
        
        TIPO DE PROGRAMA:
        """

        try:
            # Intentar primero con generate_structured_output si está disponible
            if hasattr(self.gemini_client, "generate_structured_output"):
                self.logger.debug(
                    "Usando generate_structured_output para clasificar tipo de programa"
                )
                classification = await self.gemini_client.generate_structured_output(
                    prompt
                )
            else:
                # Fallback a generate_text con temperatura baja para mayor consistencia
                self.logger.debug(
                    "Usando generate_text para clasificar tipo de programa"
                )
                response = await self.gemini_client.generate_text(
                    prompt, temperature=0.1
                )
                classification = response.strip()

            # Extraer y validar el tipo de programa
            if isinstance(classification, str):
                program_type = classification.strip().upper()
            else:
                program_type = str(classification).strip().upper()

            valid_types = get_all_program_types()

            if program_type in valid_types:
                return program_type
            else:
                # Intentar extraer un tipo válido de la respuesta
                for valid_type in valid_types:
                    if valid_type in program_type:
                        return valid_type

                self.logger.warning(
                    f"LLM devolvió un tipo de programa no reconocido: {program_type}"
                )
                return None

        except Exception as e:
            self.logger.error(
                f"Error al clasificar tipo de programa con LLM: {e}", exc_info=True
            )
            return None

    def _classify_with_rules(self, context: Dict[str, Any]) -> str:
        """
        Clasifica a un usuario en un tipo de programa utilizando reglas basadas en palabras clave y edad.

        Args:
            context: Contexto del usuario que puede incluir user_profile, goals, etc.

        Returns:
            str: Tipo de programa (PRIME, LONGEVITY, STRENGTH, etc.)
        """
        user_profile = context.get("user_profile", {})
        goals = context.get("goals", [])
        if isinstance(goals, str):  # Manejar caso donde goals podría ser un string
            goals = [goals]

        # Combinar texto de perfil y objetivos para buscar palabras clave
        profile_description = str(user_profile.get("description", "")).lower()
        profile_tags = [str(tag).lower() for tag in user_profile.get("tags", [])]
        # Incluir rol profesional si existe
        profile_role = str(user_profile.get("professional_role", "")).lower()
        goals_str = " ".join(goals).lower()
        combined_text = (
            f"{profile_description} {' '.join(profile_tags)} {profile_role} {goals_str}"
        )
        age = user_profile.get("age")  # Obtener edad

        # Verificar PRIME (ejecutivos/profesionales alto rendimiento, 30-55 años)
        prime_keywords = get_program_keywords("PRIME")
        is_prime_profile = any(kw.lower() in combined_text for kw in prime_keywords)

        if is_prime_profile:
            # Considerar PRIME si las palabras clave coinciden Y la edad está en el rango o no se especifica
            if age is None or (isinstance(age, (int, float)) and 30 <= age <= 55):
                logger.info(
                    "Tipo de programa determinado como PRIME basado en perfil/objetivos y/o edad."
                )
                return "PRIME"
            else:
                logger.info(
                    f"Palabras clave PRIME encontradas, pero edad ({age}) fuera de rango (30-55). Verificando otros tipos."
                )

        # Verificar LONGEVITY (priorizar edad si > 55)
        if age and isinstance(age, (int, float)) and age > 55:
            logger.info(
                f"Tipo de programa determinado como LONGEVITY basado en edad ({age})."
            )
            return "LONGEVITY"

        # Verificar tipos específicos basados en objetivos
        if goals:
            for program_type in ["STRENGTH", "HYPERTROPHY", "ENDURANCE", "ATHLETIC"]:
                keywords = get_program_keywords(program_type)
                if any(kw.lower() in goals_str for kw in keywords):
                    logger.info(
                        f"Tipo de programa determinado como {program_type} basado en objetivos."
                    )
                    return program_type

        # Valor por defecto
        logger.info(
            "No se pudo determinar un tipo de programa específico, usando PERFORMANCE por defecto."
        )
        return "PERFORMANCE"

    async def get_program_specific_recommendations(
        self, program_type: str, category: str
    ) -> List[str]:
        """
        Obtiene recomendaciones específicas para un tipo de programa y categoría.

        Args:
            program_type: Tipo de programa (PRIME, LONGEVITY, etc.)
            category: Categoría de recomendaciones (training, nutrition, recovery, biohacking)

        Returns:
            List[str]: Lista de recomendaciones específicas
        """
        try:
            # Verificar caché si está habilitado
            if self.use_cache:
                cache_key = self._generate_cache_key(
                    {
                        "program_type": program_type,
                        "category": category,
                        "operation": "get_recommendations",
                    }
                )

                # Intentar obtener resultado de caché
                self.cache_stats["total_requests"] += 1
                cached_result = await self.cache_manager.get(cache_key)

                if cached_result:
                    self.cache_stats["hits"] += 1
                    self.logger.debug(
                        f"Recomendaciones obtenidas de caché para {program_type}/{category}"
                    )
                    return cached_result
                else:
                    self.cache_stats["misses"] += 1

            # Obtener recomendaciones
            program_def = get_program_definition(program_type)
            protocols = program_def.get("key_protocols", {})
            recommendations = protocols.get(category.lower(), [])

            # Guardar en caché si está habilitado
            if self.use_cache:
                await self.cache_manager.set(cache_key, recommendations)

            return recommendations
        except (ValueError, KeyError):
            logger.warning(
                f"No se encontraron recomendaciones para {program_type}/{category}"
            )
            return []

    async def classify_profile(self, profile: Dict[str, Any]) -> str:
        """
        Clasifica un perfil de usuario en un tipo de programa.

        Este método es utilizado por los adaptadores de agentes para determinar
        el tipo de programa basado en el perfil del usuario.

        Args:
            profile: Perfil del usuario

        Returns:
            str: Tipo de programa (PRIME, LONGEVITY, STRENGTH, etc.)
        """
        # Crear contexto a partir del perfil
        context = {"user_profile": profile}

        # Si el perfil tiene objetivos, añadirlos al contexto
        if "goals" in profile:
            context["goals"] = profile["goals"]

        # Clasificar tipo de programa
        program_type = await self.classify_program_type(context)

        self.logger.info(f"Perfil clasificado como tipo de programa: {program_type}")
        return program_type

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del sistema de caché.

        Returns:
            Dict[str, Any]: Estadísticas de caché
        """
        if not self.use_cache:
            return {"enabled": False, "stats": self.cache_stats}

        # Obtener estadísticas detalladas del gestor de caché
        cache_manager_stats = await self.cache_manager.get_stats()

        # Calcular tasa de aciertos
        hit_rate = 0
        if self.cache_stats["total_requests"] > 0:
            hit_rate = self.cache_stats["hits"] / self.cache_stats["total_requests"]

        return {
            "enabled": True,
            "stats": {**self.cache_stats, "hit_rate": hit_rate},
            "cache_manager": cache_manager_stats,
        }

    async def flush_cache(self) -> bool:
        """
        Limpia la caché del servicio.

        Returns:
            bool: True si se limpió correctamente
        """
        if not self.use_cache:
            return False

        try:
            await self.cache_manager.flush()

            # Resetear estadísticas
            self.cache_stats = {"hits": 0, "misses": 0, "total_requests": 0}

            self.logger.info(
                "Caché del servicio de clasificación de programas limpiada correctamente"
            )
            return True
        except Exception as e:
            self.logger.error(f"Error al limpiar caché: {e}")
            return False
