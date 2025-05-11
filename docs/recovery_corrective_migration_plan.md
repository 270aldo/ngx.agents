# Plan de Migración para Recovery Corrective Agent

## Descripción General

El agente Recovery Corrective es el último agente pendiente de migrar al sistema A2A optimizado. Este documento detalla el plan de implementación del adaptador correspondiente, siguiendo los patrones establecidos en las migraciones previas.

## Estado Actual

- ✅ Todos los demás agentes han sido migrados (Biohacking Innovator, Elite Training Strategist, Precision Nutrition Architect, Progress Tracker, Motivation Behavior Coach, Client Success Liaison, Security Compliance Guardian, Systems Integration Ops)
- ✅ El Orchestrator está al 85% de su migración
- ⏳ Recovery Corrective no ha iniciado su migración (0%)

## Objetivos

1. Implementar el adaptador para Recovery Corrective
2. Integrar con el sistema A2A optimizado
3. Mantener todas las funcionalidades existentes
4. Mejorar el rendimiento y la resiliencia
5. Implementar pruebas exhaustivas

## Arquitectura del Adaptador

```
RecoveryCorrective Agent
        ↓
RecoveryCorrective Adapter
        ↓
A2A Adapter → A2A Optimized Server
```

## Plan de Implementación

### Fase 1: Análisis y Preparación (1 día)

1. **Análisis del agente actual**
   - Revisar la implementación actual
   - Identificar dependencias y patrones de comunicación
   - Documentar funcionalidades críticas

2. **Preparación del entorno de desarrollo**
   - Configurar entorno de pruebas
   - Preparar herramientas de monitoreo
   - Establecer métricas de referencia

### Fase 2: Implementación del Adaptador (2 días)

1. **Crear estructura básica**
   ```python
   # infrastructure/adapters/recovery_corrective_adapter.py
   from infrastructure.adapters.a2a_adapter import A2AAdapter
   from clients.vertex_ai_client_adapter import VertexAIClientAdapter
   
   class RecoveryCorrectiveAdapter:
       def __init__(self, a2a_client, vertex_client):
           self.a2a_client = a2a_client
           self.vertex_client = vertex_client
           
       @classmethod
       async def create(cls):
           a2a_client = await A2AAdapter.create()
           vertex_client = VertexAIClientAdapter()
           return cls(a2a_client, vertex_client)
   ```

2. **Implementar métodos principales**
   - `analyze_recovery_needs`
   - `generate_recovery_plan`
   - `adjust_training_program`
   - `provide_recovery_guidance`

3. **Integrar con A2A optimizado**
   - Implementar comunicación con otros agentes
   - Configurar manejo de prioridades
   - Implementar mecanismos de reintentos

4. **Implementar telemetría**
   - Integrar con el sistema de telemetría
   - Configurar métricas específicas
   - Implementar logging estructurado

### Fase 3: Pruebas (2 días)

1. **Crear pruebas unitarias**
   ```python
   # tests/adapters/test_recovery_corrective_adapter.py
   import pytest
   from unittest.mock import AsyncMock, patch
   from infrastructure.adapters.recovery_corrective_adapter import RecoveryCorrectiveAdapter
   
   @pytest.mark.asyncio
   async def test_analyze_recovery_needs():
       # Implementación de la prueba
       pass
   
   @pytest.mark.asyncio
   async def test_generate_recovery_plan():
       # Implementación de la prueba
       pass
   ```

2. **Implementar pruebas de integración**
   - Pruebas con A2A Server
   - Pruebas con Vertex AI Client
   - Pruebas de comunicación con otros agentes

3. **Pruebas de rendimiento**
   - Latencia bajo diferentes cargas
   - Consumo de recursos
   - Manejo de errores y recuperación

### Fase 4: Integración y Validación (1 día)

1. **Integrar con el sistema completo**
   - Configurar en el entorno de desarrollo
   - Validar comunicación con todos los agentes
   - Verificar flujos de trabajo completos

2. **Validación de funcionalidades**
   - Verificar todas las funcionalidades existentes
   - Validar nuevas capacidades
   - Confirmar mejoras de rendimiento

3. **Documentación**
   - Actualizar documentación técnica
   - Documentar patrones de uso
   - Actualizar diagramas de arquitectura

## Estructura de Archivos

```
infrastructure/
  adapters/
    recovery_corrective_adapter.py
    
tests/
  adapters/
    test_recovery_corrective_adapter.py
  integration/
    test_recovery_corrective_integration.py
    
docs/
  progress_recovery_corrective_migration.md
  
scripts/
  test_recovery_corrective_adapter.sh
```

## Implementación Detallada

### RecoveryCorrectiveAdapter

```python
class RecoveryCorrectiveAdapter:
    def __init__(self, a2a_client, vertex_client):
        self.a2a_client = a2a_client
        self.vertex_client = vertex_client
        self.logger = logging.getLogger("recovery_corrective_adapter")
        
    @classmethod
    async def create(cls):
        a2a_client = await A2AAdapter.create()
        vertex_client = VertexAIClientAdapter()
        return cls(a2a_client, vertex_client)
        
    async def analyze_recovery_needs(self, user_data, training_history):
        """
        Analiza las necesidades de recuperación basadas en datos del usuario y su historial de entrenamiento.
        
        Args:
            user_data (dict): Datos del usuario incluyendo métricas biométricas
            training_history (list): Historial de entrenamientos recientes
            
        Returns:
            dict: Análisis de necesidades de recuperación
        """
        try:
            # Implementación optimizada
            prompt = self._build_recovery_analysis_prompt(user_data, training_history)
            response = await self.vertex_client.generate_text(prompt)
            
            # Procesamiento y estructuración de la respuesta
            analysis = self._parse_recovery_analysis(response)
            
            # Telemetría
            telemetry.record_event("recovery_corrective", "analysis_completed", {
                "user_id": user_data.get("user_id"),
                "analysis_factors": len(analysis.get("factors", [])),
                "response_time_ms": telemetry.get_current_span().duration_ms
            })
            
            return analysis
        except Exception as e:
            self.logger.error(f"Error analyzing recovery needs: {str(e)}")
            telemetry.record_error("recovery_corrective", "analysis_failed", {
                "error": str(e)
            })
            raise
            
    async def generate_recovery_plan(self, recovery_needs, user_preferences):
        """
        Genera un plan de recuperación personalizado.
        
        Args:
            recovery_needs (dict): Análisis de necesidades de recuperación
            user_preferences (dict): Preferencias del usuario
            
        Returns:
            dict: Plan de recuperación estructurado
        """
        # Implementación similar a analyze_recovery_needs
        pass
        
    async def adjust_training_program(self, current_program, recovery_plan):
        """
        Ajusta el programa de entrenamiento actual basado en el plan de recuperación.
        
        Args:
            current_program (dict): Programa de entrenamiento actual
            recovery_plan (dict): Plan de recuperación
            
        Returns:
            dict: Programa de entrenamiento ajustado
        """
        # Implementación
        pass
        
    async def provide_recovery_guidance(self, user_id, context=None):
        """
        Proporciona orientación de recuperación en tiempo real.
        
        Args:
            user_id (str): ID del usuario
            context (dict, optional): Contexto adicional
            
        Returns:
            dict: Orientación de recuperación
        """
        # Implementación
        pass
        
    async def _consult_other_agent(self, agent_name, query, context=None):
        """
        Consulta a otro agente para obtener información adicional.
        
        Args:
            agent_name (str): Nombre del agente a consultar
            query (str): Consulta para el agente
            context (dict, optional): Contexto adicional
            
        Returns:
            dict: Respuesta del agente consultado
        """
        try:
            return await self.a2a_client.call_agent(agent_name, query, context)
        except Exception as e:
            self.logger.error(f"Error consulting agent {agent_name}: {str(e)}")
            # Implementar fallback
            return {"status": "error", "message": f"Failed to consult {agent_name}"}
            
    def _build_recovery_analysis_prompt(self, user_data, training_history):
        """Construye el prompt para el análisis de recuperación."""
        # Implementación
        pass
        
    def _parse_recovery_analysis(self, response):
        """Procesa y estructura la respuesta del modelo."""
        # Implementación
        pass
```

## Pruebas

### Pruebas Unitarias

```python
@pytest.mark.asyncio
async def test_analyze_recovery_needs():
    # Configurar mocks
    mock_vertex_client = AsyncMock()
    mock_vertex_client.generate_text.return_value = "Análisis de recuperación simulado"
    
    mock_a2a_client = AsyncMock()
    
    # Crear adaptador con mocks
    adapter = RecoveryCorrectiveAdapter(mock_a2a_client, mock_vertex_client)
    
    # Datos de prueba
    user_data = {"user_id": "test_user", "age": 30, "weight": 75}
    training_history = [{"date": "2025-10-01", "type": "strength", "intensity": "high"}]
    
    # Ejecutar función
    result = await adapter.analyze_recovery_needs(user_data, training_history)
    
    # Verificaciones
    assert mock_vertex_client.generate_text.called
    assert result is not None
    # Más verificaciones específicas
```

### Pruebas de Integración

```python
@pytest.mark.asyncio
async def test_integration_with_a2a_server():
    # Crear adaptador real
    adapter = await RecoveryCorrectiveAdapter.create()
    
    # Datos de prueba
    user_data = {"user_id": "test_user", "age": 30, "weight": 75}
    training_history = [{"date": "2025-10-01", "type": "strength", "intensity": "high"}]
    
    # Ejecutar función
    result = await adapter.analyze_recovery_needs(user_data, training_history)
    
    # Verificaciones
    assert result is not None
    assert "factors" in result
    # Más verificaciones específicas
```

## Script de Prueba

```bash
#!/bin/bash
# Script para probar el adaptador de Recovery Corrective

# Colores para la salida
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Iniciando pruebas del adaptador de Recovery Corrective...${NC}"

# Activar el entorno virtual si existe
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activando entorno virtual...${NC}"
    source venv/bin/activate
fi

# Ejecutar las pruebas unitarias
echo -e "${YELLOW}Ejecutando pruebas unitarias...${NC}"
python -m pytest tests/adapters/test_recovery_corrective_adapter.py -v

# Verificar el resultado
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Pruebas unitarias completadas con éxito.${NC}"
else
    echo -e "${RED}❌ Algunas pruebas unitarias fallaron.${NC}"
    exit 1
fi

# Ejecutar pruebas de integración si existen
if [ -f "tests/integration/test_recovery_corrective_integration.py" ]; then
    echo -e "${YELLOW}Ejecutando pruebas de integración...${NC}"
    python -m pytest tests/integration/test_recovery_corrective_integration.py -v
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Pruebas de integración completadas con éxito.${NC}"
    else
        echo -e "${RED}❌ Algunas pruebas de integración fallaron.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️ No se encontraron pruebas de integración.${NC}"
fi

echo -e "${GREEN}✅ Todas las pruebas completadas con éxito.${NC}"

# Desactivar el entorno virtual si se activó
if [ -d "venv" ]; then
    deactivate 2>/dev/null
fi

exit 0
```

## Cronograma

| Fase | Duración | Fecha Inicio | Fecha Fin |
|------|----------|--------------|-----------|
| Análisis y Preparación | 1 día | 16/10/2025 | 16/10/2025 |
| Implementación | 2 días | 17/10/2025 | 18/10/2025 |
| Pruebas | 2 días | 19/10/2025 | 20/10/2025 |
| Integración y Validación | 1 día | 21/10/2025 | 21/10/2025 |
| **Total** | **6 días** | **16/10/2025** | **21/10/2025** |

## Riesgos y Mitigaciones

| Riesgo | Impacto | Probabilidad | Mitigación |
|--------|---------|--------------|------------|
| Incompatibilidad con el sistema A2A optimizado | Alto | Baja | Seguir patrones establecidos en otros adaptadores |
| Regresión de funcionalidades | Alto | Media | Pruebas exhaustivas de todas las funcionalidades |
| Problemas de rendimiento | Medio | Baja | Pruebas de carga y optimización temprana |
| Dependencias no identificadas | Medio | Media | Análisis detallado en la fase inicial |

## Conclusión

La migración del agente Recovery Corrective completará la transición de todos los agentes al sistema A2A optimizado. Siguiendo los patrones y lecciones aprendidas de las migraciones anteriores, se espera que esta implementación sea eficiente y exitosa, permitiendo finalizar la optimización completa del sistema NGX Agents.
