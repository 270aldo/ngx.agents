"""
Módulo de generación avanzada de respuestas.

Este módulo proporciona funcionalidades para generar respuestas más precisas
y contextuales, utilizando técnicas avanzadas como few-shot learning,
chain-of-thought, y generación estructurada.
"""

import hashlib
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from clients.vertex_ai import vertex_ai_client
from core.embeddings_manager import embeddings_manager
from core.logging_config import get_logger
from core.telemetry import telemetry_manager

# Configurar logger
logger = get_logger(__name__)


class AdvancedGeneration:
    """
    Generador avanzado de respuestas.

    Proporciona métodos para generar respuestas más precisas y contextuales,
    utilizando técnicas avanzadas como few-shot learning, chain-of-thought,
    y generación estructurada.
    """

    def __init__(
        self,
        cache_enabled: bool = True,
        cache_ttl: int = 3600,
        default_temperature: float = 0.7,
        default_max_tokens: int = 1024,
    ):
        """
        Inicializa el generador avanzado.

        Args:
            cache_enabled: Habilitar caché de resultados
            cache_ttl: Tiempo de vida del caché en segundos
            default_temperature: Temperatura predeterminada para generación
            default_max_tokens: Máximo de tokens predeterminado
        """
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens

        # Caché de respuestas
        self.response_cache = {}

        # Estadísticas
        self.stats = {
            "standard_requests": 0,
            "few_shot_requests": 0,
            "cot_requests": 0,
            "structured_requests": 0,
            "rag_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
        }

        logger.info("Generador avanzado inicializado")

    def _get_cache_key(self, data: Any) -> str:
        """
        Genera una clave de caché para los datos.

        Args:
            data: Datos para generar la clave

        Returns:
            str: Clave de caché
        """
        # Convertir a JSON y generar hash
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()

    def _clean_cache_if_needed(self) -> None:
        """Limpia la caché si hay demasiadas entradas."""
        max_cache_size = 1000

        if len(self.response_cache) > max_cache_size:
            # Ordenar por timestamp y eliminar los más antiguos
            sorted_items = sorted(
                self.response_cache.items(), key=lambda x: x[1]["timestamp"]
            )

            # Eliminar el 20% más antiguo
            items_to_remove = int(max_cache_size * 0.2)
            for i in range(items_to_remove):
                if i < len(sorted_items):
                    del self.response_cache[sorted_items[i][0]]

    async def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Genera una respuesta estándar.

        Args:
            prompt: Prompt para el modelo
            system_instruction: Instrucción de sistema (opcional)
            temperature: Temperatura para la generación (opcional)
            max_tokens: Máximo de tokens a generar (opcional)

        Returns:
            Dict[str, Any]: Respuesta generada
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="advanced_generate_response",
            attributes={
                "prompt_length": len(prompt),
                "temperature": temperature or self.default_temperature,
                "max_tokens": max_tokens or self.default_max_tokens,
            },
        )

        try:
            # Actualizar estadísticas
            self.stats["standard_requests"] += 1

            # Usar valores predeterminados si no se proporcionan
            temperature = (
                temperature if temperature is not None else self.default_temperature
            )
            max_tokens = (
                max_tokens if max_tokens is not None else self.default_max_tokens
            )

            # Verificar caché
            if self.cache_enabled:
                cache_key = self._get_cache_key(
                    {
                        "prompt": prompt,
                        "system_instruction": system_instruction,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                )

                if cache_key in self.response_cache:
                    cache_entry = self.response_cache[cache_key]
                    # Verificar TTL
                    if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                        self.stats["cache_hits"] += 1
                        telemetry_manager.set_span_attribute(span_id, "cache", "hit")
                        return cache_entry["result"]

            self.stats["cache_misses"] += 1

            # Generar respuesta con Vertex AI
            response = await vertex_ai_client.generate_content(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            # Guardar en caché
            if self.cache_enabled:
                self.response_cache[cache_key] = {
                    "result": response,
                    "timestamp": time.time(),
                }

                # Limpiar caché si es necesario
                self._clean_cache_if_needed()

            telemetry_manager.set_span_attribute(
                span_id, "response_length", len(response.get("text", ""))
            )
            return response

        except Exception as e:
            logger.error(f"Error al generar respuesta: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_manager.set_span_attribute(span_id, "error", str(e))

            return {"text": f"Error al generar respuesta: {str(e)}", "error": str(e)}

        finally:
            telemetry_manager.end_span(span_id)

    async def generate_with_few_shot(
        self,
        prompt: str,
        examples: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Genera una respuesta utilizando few-shot learning.

        Args:
            prompt: Prompt para el modelo
            examples: Lista de ejemplos (cada uno con "input" y "output")
            system_instruction: Instrucción de sistema (opcional)
            temperature: Temperatura para la generación (opcional)
            max_tokens: Máximo de tokens a generar (opcional)

        Returns:
            Dict[str, Any]: Respuesta generada
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="advanced_generate_few_shot",
            attributes={
                "prompt_length": len(prompt),
                "examples_count": len(examples),
                "temperature": temperature or self.default_temperature,
                "max_tokens": max_tokens or self.default_max_tokens,
            },
        )

        try:
            # Actualizar estadísticas
            self.stats["few_shot_requests"] += 1

            # Usar valores predeterminados si no se proporcionan
            temperature = (
                temperature if temperature is not None else self.default_temperature
            )
            max_tokens = (
                max_tokens if max_tokens is not None else self.default_max_tokens
            )

            # Verificar caché
            if self.cache_enabled:
                cache_key = self._get_cache_key(
                    {
                        "prompt": prompt,
                        "examples": examples,
                        "system_instruction": system_instruction,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                )

                if cache_key in self.response_cache:
                    cache_entry = self.response_cache[cache_key]
                    # Verificar TTL
                    if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                        self.stats["cache_hits"] += 1
                        telemetry_manager.set_span_attribute(span_id, "cache", "hit")
                        return cache_entry["result"]

            self.stats["cache_misses"] += 1

            # Construir prompt con ejemplos
            few_shot_prompt = ""

            # Añadir ejemplos
            for i, example in enumerate(examples):
                few_shot_prompt += f"Ejemplo {i+1}:\n"
                few_shot_prompt += f"Entrada: {example['input']}\n"
                few_shot_prompt += f"Salida: {example['output']}\n\n"

            # Añadir prompt actual
            few_shot_prompt += f"Ahora, responde a lo siguiente:\n"
            few_shot_prompt += f"Entrada: {prompt}\n"
            few_shot_prompt += f"Salida:"

            # Generar respuesta con Vertex AI
            response = await vertex_ai_client.generate_content(
                prompt=few_shot_prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            # Guardar en caché
            if self.cache_enabled:
                self.response_cache[cache_key] = {
                    "result": response,
                    "timestamp": time.time(),
                }

                # Limpiar caché si es necesario
                self._clean_cache_if_needed()

            telemetry_manager.set_span_attribute(
                span_id, "response_length", len(response.get("text", ""))
            )
            return response

        except Exception as e:
            logger.error(
                f"Error al generar respuesta con few-shot: {str(e)}", exc_info=True
            )
            self.stats["errors"] += 1
            telemetry_manager.set_span_attribute(span_id, "error", str(e))

            return {
                "text": f"Error al generar respuesta con few-shot: {str(e)}",
                "error": str(e),
            }

        finally:
            telemetry_manager.end_span(span_id)

    async def generate_with_chain_of_thought(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Genera una respuesta utilizando chain-of-thought.

        Args:
            prompt: Prompt para el modelo
            system_instruction: Instrucción de sistema (opcional)
            temperature: Temperatura para la generación (opcional)
            max_tokens: Máximo de tokens a generar (opcional)

        Returns:
            Dict[str, Any]: Respuesta generada con razonamiento paso a paso
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="advanced_generate_cot",
            attributes={
                "prompt_length": len(prompt),
                "temperature": temperature or self.default_temperature,
                "max_tokens": max_tokens or self.default_max_tokens,
            },
        )

        try:
            # Actualizar estadísticas
            self.stats["cot_requests"] += 1

            # Usar valores predeterminados si no se proporcionan
            temperature = (
                temperature if temperature is not None else self.default_temperature
            )
            max_tokens = (
                max_tokens if max_tokens is not None else self.default_max_tokens
            )

            # Verificar caché
            if self.cache_enabled:
                cache_key = self._get_cache_key(
                    {
                        "prompt": prompt,
                        "system_instruction": system_instruction,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "method": "cot",
                    }
                )

                if cache_key in self.response_cache:
                    cache_entry = self.response_cache[cache_key]
                    # Verificar TTL
                    if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                        self.stats["cache_hits"] += 1
                        telemetry_manager.set_span_attribute(span_id, "cache", "hit")
                        return cache_entry["result"]

            self.stats["cache_misses"] += 1

            # Modificar el prompt para inducir chain-of-thought
            cot_prompt = f"{prompt}\n\nVamos a pensar paso a paso para resolver esto:"

            # Generar respuesta con Vertex AI
            response = await vertex_ai_client.generate_content(
                prompt=cot_prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            # Extraer razonamiento y respuesta final
            full_text = response.get("text", "")

            # Intentar separar el razonamiento de la respuesta final
            parts = full_text.split("Por lo tanto,")

            if len(parts) > 1:
                reasoning = parts[0].strip()
                final_answer = "Por lo tanto," + parts[1].strip()
            else:
                # Si no hay "Por lo tanto", buscar otras frases de conclusión
                for phrase in ["En conclusión,", "Finalmente,", "La respuesta es"]:
                    parts = full_text.split(phrase)
                    if len(parts) > 1:
                        reasoning = parts[0].strip()
                        final_answer = phrase + parts[1].strip()
                        break
                else:
                    # Si no se encuentra ninguna frase de conclusión
                    reasoning = full_text
                    final_answer = ""

            # Crear respuesta estructurada
            structured_response = {
                "text": full_text,
                "reasoning": reasoning,
                "final_answer": final_answer,
                "finish_reason": response.get("finish_reason", ""),
                "usage": response.get("usage", {}),
            }

            # Guardar en caché
            if self.cache_enabled:
                self.response_cache[cache_key] = {
                    "result": structured_response,
                    "timestamp": time.time(),
                }

                # Limpiar caché si es necesario
                self._clean_cache_if_needed()

            telemetry_manager.set_span_attribute(
                span_id, "response_length", len(full_text)
            )
            return structured_response

        except Exception as e:
            logger.error(
                f"Error al generar respuesta con chain-of-thought: {str(e)}",
                exc_info=True,
            )
            self.stats["errors"] += 1
            telemetry_manager.set_span_attribute(span_id, "error", str(e))

            return {
                "text": f"Error al generar respuesta con chain-of-thought: {str(e)}",
                "error": str(e),
            }

        finally:
            telemetry_manager.end_span(span_id)

    async def generate_structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Genera una respuesta estructurada según un esquema.

        Args:
            prompt: Prompt para el modelo
            output_schema: Esquema de salida (formato JSON)
            system_instruction: Instrucción de sistema (opcional)
            temperature: Temperatura para la generación (opcional)
            max_tokens: Máximo de tokens a generar (opcional)

        Returns:
            Dict[str, Any]: Respuesta estructurada
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="advanced_generate_structured",
            attributes={
                "prompt_length": len(prompt),
                "temperature": temperature or self.default_temperature,
                "max_tokens": max_tokens or self.default_max_tokens,
            },
        )

        try:
            # Actualizar estadísticas
            self.stats["structured_requests"] += 1

            # Usar valores predeterminados si no se proporcionan
            temperature = (
                temperature if temperature is not None else self.default_temperature
            )
            max_tokens = (
                max_tokens if max_tokens is not None else self.default_max_tokens
            )

            # Verificar caché
            if self.cache_enabled:
                cache_key = self._get_cache_key(
                    {
                        "prompt": prompt,
                        "output_schema": output_schema,
                        "system_instruction": system_instruction,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                )

                if cache_key in self.response_cache:
                    cache_entry = self.response_cache[cache_key]
                    # Verificar TTL
                    if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                        self.stats["cache_hits"] += 1
                        telemetry_manager.set_span_attribute(span_id, "cache", "hit")
                        return cache_entry["result"]

            self.stats["cache_misses"] += 1

            # Convertir esquema a formato de texto
            schema_str = json.dumps(output_schema, indent=2)

            # Construir prompt para generación estructurada
            structured_prompt = f"""
            {prompt}
            
            Por favor, proporciona una respuesta en el siguiente formato JSON:
            {schema_str}
            
            Asegúrate de que tu respuesta sea un JSON válido que siga exactamente este esquema.
            """

            # Generar respuesta con Vertex AI
            response = await vertex_ai_client.generate_content(
                prompt=structured_prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            # Extraer y parsear JSON de la respuesta
            text_response = response.get("text", "")

            # Buscar JSON en la respuesta
            json_start = text_response.find("{")
            json_end = text_response.rfind("}")

            if json_start >= 0 and json_end >= 0:
                json_str = text_response[json_start : json_end + 1]
                try:
                    structured_data = json.loads(json_str)
                except json.JSONDecodeError:
                    # Si falla, intentar limpiar el JSON
                    cleaned_json = self._clean_json_string(json_str)
                    try:
                        structured_data = json.loads(cleaned_json)
                    except json.JSONDecodeError:
                        structured_data = {"error": "No se pudo parsear el JSON"}
            else:
                structured_data = {"error": "No se encontró JSON en la respuesta"}

            # Crear respuesta final
            result = {
                "text": text_response,
                "structured_data": structured_data,
                "finish_reason": response.get("finish_reason", ""),
                "usage": response.get("usage", {}),
            }

            # Guardar en caché
            if self.cache_enabled:
                self.response_cache[cache_key] = {
                    "result": result,
                    "timestamp": time.time(),
                }

                # Limpiar caché si es necesario
                self._clean_cache_if_needed()

            telemetry_manager.set_span_attribute(
                span_id, "response_length", len(text_response)
            )
            return result

        except Exception as e:
            logger.error(
                f"Error al generar respuesta estructurada: {str(e)}", exc_info=True
            )
            self.stats["errors"] += 1
            telemetry_manager.set_span_attribute(span_id, "error", str(e))

            return {
                "text": f"Error al generar respuesta estructurada: {str(e)}",
                "error": str(e),
                "structured_data": {},
            }

        finally:
            telemetry_manager.end_span(span_id)

    def _clean_json_string(self, json_str: str) -> str:
        """
        Limpia una cadena JSON para intentar hacerla válida.

        Args:
            json_str: Cadena JSON a limpiar

        Returns:
            str: Cadena JSON limpia
        """
        # Eliminar comillas simples y reemplazarlas por comillas dobles
        json_str = json_str.replace("'", '"')

        # Eliminar comentarios
        lines = json_str.split("\n")
        cleaned_lines = []
        for line in lines:
            if "//" in line:
                line = line.split("//")[0]
            cleaned_lines.append(line)

        json_str = "\n".join(cleaned_lines)

        # Eliminar comas finales en listas y objetos
        json_str = json_str.replace(",\n}", "\n}")
        json_str = json_str.replace(",\n]", "\n]")

        return json_str

    async def generate_with_rag(
        self,
        query: str,
        context_keys: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        top_k: int = 3,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Genera una respuesta utilizando Retrieval Augmented Generation (RAG).

        Args:
            query: Consulta del usuario
            context_keys: Claves de contexto específicas (opcional)
            search_query: Consulta de búsqueda alternativa (opcional)
            top_k: Número de resultados a recuperar
            system_instruction: Instrucción de sistema (opcional)
            temperature: Temperatura para la generación (opcional)
            max_tokens: Máximo de tokens a generar (opcional)

        Returns:
            Dict[str, Any]: Respuesta generada con contexto
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="advanced_generate_rag",
            attributes={
                "query_length": len(query),
                "top_k": top_k,
                "temperature": temperature or self.default_temperature,
                "max_tokens": max_tokens or self.default_max_tokens,
            },
        )

        try:
            # Actualizar estadísticas
            self.stats["rag_requests"] += 1

            # Usar valores predeterminados si no se proporcionan
            temperature = (
                temperature if temperature is not None else self.default_temperature
            )
            max_tokens = (
                max_tokens if max_tokens is not None else self.default_max_tokens
            )

            # Verificar caché
            if self.cache_enabled:
                cache_key = self._get_cache_key(
                    {
                        "query": query,
                        "context_keys": context_keys,
                        "search_query": search_query,
                        "top_k": top_k,
                        "system_instruction": system_instruction,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                )

                if cache_key in self.response_cache:
                    cache_entry = self.response_cache[cache_key]
                    # Verificar TTL
                    if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                        self.stats["cache_hits"] += 1
                        telemetry_manager.set_span_attribute(span_id, "cache", "hit")
                        return cache_entry["result"]

            self.stats["cache_misses"] += 1

            # Recuperar contexto relevante
            context_items = []

            if context_keys:
                # Si se proporcionan claves específicas
                for key in context_keys:
                    item = embeddings_manager.get_by_key(key)
                    if item:
                        context_items.append(item)
            else:
                # Buscar contexto similar
                search_text = search_query if search_query else query
                similar_items = await embeddings_manager.find_similar(
                    search_text, top_k=top_k
                )
                context_items = similar_items

            # Construir contexto para el prompt
            context_text = ""
            for i, item in enumerate(context_items):
                context_text += f"Contexto {i+1}:\n{item['text']}\n\n"

            # Construir prompt con contexto
            rag_prompt = f"""
            Contexto relevante:
            {context_text}
            
            Consulta del usuario:
            {query}
            
            Basándote en el contexto proporcionado, responde a la consulta del usuario.
            Si el contexto no contiene información relevante, indica que no tienes suficiente información.
            """

            # Generar respuesta con Vertex AI
            response = await vertex_ai_client.generate_content(
                prompt=rag_prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            # Crear respuesta final con metadatos
            result = {
                "text": response.get("text", ""),
                "context_items": [
                    {
                        "key": item.get("key", ""),
                        "text": (
                            item.get("text", "")[:100] + "..."
                            if len(item.get("text", "")) > 100
                            else item.get("text", "")
                        ),
                        "similarity": item.get("similarity", 0.0),
                    }
                    for item in context_items
                ],
                "finish_reason": response.get("finish_reason", ""),
                "usage": response.get("usage", {}),
            }

            # Guardar en caché
            if self.cache_enabled:
                self.response_cache[cache_key] = {
                    "result": result,
                    "timestamp": time.time(),
                }

                # Limpiar caché si es necesario
                self._clean_cache_if_needed()

            telemetry_manager.set_span_attribute(
                span_id, "response_length", len(result["text"])
            )
            telemetry_manager.set_span_attribute(
                span_id, "context_items_count", len(context_items)
            )
            return result

        except Exception as e:
            logger.error(f"Error al generar respuesta con RAG: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_manager.set_span_attribute(span_id, "error", str(e))

            return {
                "text": f"Error al generar respuesta con RAG: {str(e)}",
                "error": str(e),
                "context_items": [],
            }

        finally:
            telemetry_manager.end_span(span_id)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del generador avanzado.

        Returns:
            Dict[str, Any]: Estadísticas de uso
        """
        return {
            "stats": self.stats,
            "cache_size": len(self.response_cache),
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl,
            "default_temperature": self.default_temperature,
            "default_max_tokens": self.default_max_tokens,
            "timestamp": datetime.now().isoformat(),
        }


# Crear instancia única del generador avanzado
advanced_generation = AdvancedGeneration()
