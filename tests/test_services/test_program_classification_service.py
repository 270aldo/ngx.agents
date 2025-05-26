"""
Pruebas para el servicio de clasificación de programas.

Este módulo contiene pruebas unitarias para verificar el funcionamiento
del servicio de clasificación de programas.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from services.program_classification_service import ProgramClassificationService
from agents.shared.program_definitions import get_all_program_types


@pytest.fixture
def mock_gemini_client():
    """Fixture para crear un cliente Gemini simulado."""
    mock_client = MagicMock()
    mock_client.generate_text = MagicMock()
    # Hacer que los métodos async sean utilizables en pruebas
    mock_client.generate_text.return_value = "PERFORMANCE"
    mock_client.generate_structured_output = MagicMock()
    mock_client.generate_structured_output.return_value = "PERFORMANCE"
    return mock_client


@pytest.fixture
def program_classification_service(mock_gemini_client):
    """Fixture para crear una instancia del servicio de clasificación de programas."""
    # Crear servicio con caché desactivado para pruebas básicas
    service = ProgramClassificationService(
        gemini_client=mock_gemini_client, use_cache=False
    )
    # Mockear el cache_manager para evitar operaciones reales de caché
    service.cache_manager.get = AsyncMock(return_value=None)
    service.cache_manager.set = AsyncMock(return_value=True)
    service.cache_manager.flush = AsyncMock(return_value=True)
    service.cache_manager.get_stats = AsyncMock(return_value={})
    return service


@pytest.fixture
def cached_program_classification_service(mock_gemini_client):
    """Fixture para crear una instancia del servicio con caché activado."""
    # Crear servicio con caché activado para pruebas de caché
    service = ProgramClassificationService(
        gemini_client=mock_gemini_client, use_cache=True
    )
    # Mockear el cache_manager para simular operaciones de caché
    service.cache_manager.get = AsyncMock(
        return_value=None
    )  # Por defecto, no hay caché
    service.cache_manager.set = AsyncMock(return_value=True)
    service.cache_manager.flush = AsyncMock(return_value=True)
    service.cache_manager.get_stats = AsyncMock(
        return_value={"hits": 0, "misses": 0, "current_items": 0}
    )
    return service


class TestProgramClassificationService:
    """Pruebas para el servicio de clasificación de programas."""

    @pytest.mark.asyncio
    async def test_classify_program_type_explicit(self, program_classification_service):
        """Prueba la clasificación cuando el tipo de programa está explícitamente en el contexto."""
        # Preparar contexto con tipo de programa explícito
        context = {"program_type": "PRIME"}

        # Ejecutar clasificación
        result = await program_classification_service.classify_program_type(context)

        # Verificar resultado
        assert result == "PRIME"

    @pytest.mark.asyncio
    async def test_classify_program_type_with_llm(
        self, program_classification_service, mock_gemini_client
    ):
        """Prueba la clasificación utilizando LLM."""
        # Configurar mock para simular respuesta del LLM
        mock_gemini_client.generate_structured_output.return_value = "LONGEVITY"

        # Preparar contexto sin tipo de programa explícito
        context = {
            "user_profile": {
                "age": 60,
                "professional_role": "Retirado",
                "experience_level": "Intermedio",
            },
            "goals": ["Mantener movilidad", "Mejorar salud general"],
        }

        # Ejecutar clasificación
        result = await program_classification_service.classify_program_type(context)

        # Verificar que se llamó al método LLM
        mock_gemini_client.generate_structured_output.assert_called_once()

        # Verificar resultado
        assert result == "LONGEVITY"

    @pytest.mark.asyncio
    async def test_classify_program_type_with_rules(
        self, program_classification_service
    ):
        """Prueba la clasificación utilizando reglas basadas en palabras clave y edad."""
        # Desactivar LLM para forzar clasificación basada en reglas
        context = {
            "user_profile": {
                "age": 45,
                "professional_role": "CEO",
                "experience_level": "Principiante",
            },
            "goals": ["Optimizar rendimiento", "Mejorar productividad"],
        }

        # Ejecutar clasificación sin LLM
        result = await program_classification_service.classify_program_type(
            context, use_llm=False
        )

        # Verificar resultado (debería ser PRIME basado en edad y rol profesional)
        assert result == "PRIME"

    @pytest.mark.asyncio
    async def test_classify_program_type_fallback(
        self, program_classification_service, mock_gemini_client
    ):
        """Prueba el comportamiento de fallback cuando falla el LLM."""
        # Configurar mock para simular error en LLM
        mock_gemini_client.generate_structured_output.side_effect = Exception(
            "Error simulado"
        )

        # Contexto sin información clara para clasificación
        context = {
            "user_profile": {"age": 35, "experience_level": "Intermedio"},
            "goals": ["Mejorar condición física general"],
        }

        # Ejecutar clasificación
        result = await program_classification_service.classify_program_type(context)

        # Verificar que se intentó usar LLM
        mock_gemini_client.generate_structured_output.assert_called_once()

        # Verificar que se utilizó el fallback a reglas
        assert result in get_all_program_types()

    def test_enrich_query_with_program_context(self, program_classification_service):
        """Prueba el enriquecimiento de consultas con contexto del programa."""
        # Consulta original
        query = "¿Cuáles son los mejores ejercicios para mi perfil?"
        program_type = "PRIME"

        # Enriquecer consulta
        enriched_query = (
            program_classification_service.enrich_query_with_program_context(
                query, program_type
            )
        )

        # Verificar que la consulta fue enriquecida
        assert query in enriched_query
        assert program_type in enriched_query
        assert "Contexto del programa" in enriched_query

        # Verificar que se incluyó información relevante del programa
        assert "Objetivo:" in enriched_query or "Pilares:" in enriched_query

    @pytest.mark.asyncio
    async def test_get_program_specific_recommendations(
        self, program_classification_service
    ):
        """Prueba la obtención de recomendaciones específicas para un programa."""
        # Obtener recomendaciones para PRIME/training
        recommendations = (
            await program_classification_service.get_program_specific_recommendations(
                "PRIME", "training"
            )
        )

        # Verificar que se obtuvieron recomendaciones
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

    @pytest.mark.asyncio
    async def test_cache_functionality(self, cached_program_classification_service):
        """Prueba la funcionalidad de caché del servicio."""
        service = cached_program_classification_service

        # Configurar mock para simular hit de caché en la segunda llamada
        service.cache_manager.get = AsyncMock(side_effect=[None, "PRIME"])

        # Primera llamada (miss de caché)
        context = {
            "user_profile": {"age": 40, "professional_role": "CEO"},
            "goals": ["Optimizar rendimiento"],
        }
        result1 = await service.classify_program_type(context)

        # Segunda llamada (hit de caché)
        result2 = await service.classify_program_type(context)

        # Verificar que se llamó a cache_manager.get dos veces
        assert service.cache_manager.get.call_count == 2
        # Verificar que se llamó a cache_manager.set al menos una vez
        assert service.cache_manager.set.call_count >= 1
        # Verificar que la segunda llamada devolvió el valor cacheado
        assert result2 == "PRIME"

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, cached_program_classification_service):
        """Prueba la obtención de estadísticas de caché."""
        service = cached_program_classification_service

        # Simular algunas operaciones de caché
        service.cache_stats = {"hits": 5, "misses": 3, "total_requests": 8}

        # Obtener estadísticas
        stats = await service.get_cache_stats()

        # Verificar estructura de estadísticas
        assert stats["enabled"] is True
        assert "stats" in stats
        assert stats["stats"]["hits"] == 5
        assert stats["stats"]["misses"] == 3
        assert stats["stats"]["hit_rate"] == 5 / 8

    @pytest.mark.asyncio
    async def test_flush_cache(self, cached_program_classification_service):
        """Prueba la limpieza de caché."""
        service = cached_program_classification_service

        # Simular algunas operaciones de caché
        service.cache_stats = {"hits": 5, "misses": 3, "total_requests": 8}

        # Limpiar caché
        result = await service.flush_cache()

        # Verificar resultado
        assert result is True
        assert service.cache_manager.flush.call_count == 1
        assert service.cache_stats["hits"] == 0
        assert service.cache_stats["misses"] == 0
        assert service.cache_stats["total_requests"] == 0


if __name__ == "__main__":
    pytest.main(["-xvs", "test_program_classification_service.py"])
