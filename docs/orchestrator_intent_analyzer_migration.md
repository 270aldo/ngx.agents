# Plan de Migración del Orchestrator al Intent Analyzer Optimizado

> **Nota**: La migración del Intent Analyzer ha sido completada con éxito. Este documento se mantiene como referencia para la migración pendiente del Orchestrator.

## Objetivo

Migrar el agente Orchestrator para utilizar el adaptador del Intent Analyzer (`intent_analyzer_adapter.py`) en lugar del Intent Analyzer original. Esto permitirá aprovechar las mejoras de rendimiento y capacidades del nuevo Intent Analyzer optimizado.

## Análisis Previo

El agente Orchestrator actualmente utiliza una lógica simple de análisis de intención en su método `_skill_analyze_intent`. Esta lógica debe ser reemplazada por llamadas al adaptador del Intent Analyzer.

## Pasos de Implementación

1. **Importar el adaptador del Intent Analyzer**

   Añadir la importación del adaptador del Intent Analyzer al inicio del archivo:
   ```python
   from core.intent_analyzer_adapter import intent_analyzer_adapter
   ```

2. **Modificar el método `_skill_analyze_intent`**

   Actualizar el método para utilizar el adaptador del Intent Analyzer:
   ```python
   async def _skill_analyze_intent(self, prompt: str) -> Dict[str, Any]:
       """
       Skill para analizar la intención del usuario a partir de su entrada de texto.
       
       Args:
           prompt: El texto del usuario a analizar.
           
       Returns:
           Un diccionario con la intención primaria, intenciones secundarias y confianza.
       """
       try:
           # Utilizar el adaptador del Intent Analyzer
           intent_analysis = await intent_analyzer_adapter.analyze_intent(prompt)
           
           # Convertir el resultado al formato esperado por el orquestador
           result = {
               "primary_intent": intent_analysis.get("primary_intent", "general"),
               "secondary_intents": intent_analysis.get("secondary_intents", []),
               "confidence": intent_analysis.get("confidence", 0.5)
           }
           
           return result
       except Exception as e:
           logger.error(f"Error en skill_analyze_intent: {e}", exc_info=True)
           return {
               "primary_intent": "general",
               "secondary_intents": [],
               "confidence": 0.5,
               "error": str(e)
           }
   ```

3. **Actualizar el método `_process_request`**

   Asegurarse de que el método `_process_request` maneje correctamente el resultado del análisis de intención:
   ```python
   # Verificar que el procesamiento de intent_analysis_result sea compatible con el nuevo formato
   ```

4. **Pruebas**

   Crear pruebas para verificar que el agente Orchestrator funciona correctamente con el adaptador del Intent Analyzer:
   ```python
   # tests/test_orchestrator_intent_analyzer.py
   ```

## Consideraciones

- El adaptador del Intent Analyzer debe mantener la misma interfaz que el Intent Analyzer original para minimizar los cambios en el agente Orchestrator.
- Es importante verificar que el formato de los datos devueltos por el adaptador sea compatible con el esperado por el agente Orchestrator.
- Se deben manejar adecuadamente los errores que puedan surgir durante la migración.

## Validación

Para validar la migración, se deben realizar las siguientes pruebas:

1. Verificar que el agente Orchestrator pueda analizar correctamente diferentes tipos de intenciones.
2. Comprobar que las intenciones secundarias se detecten y procesen adecuadamente.
3. Asegurarse de que el nivel de confianza se calcule y utilice correctamente.
4. Verificar que el enrutamiento a los agentes especializados funcione como se espera.

## Próximos Pasos

1. La migración del Intent Analyzer ha sido completada al 100% (ver documento `progress_intent_analyzer_migration.md`).
2. Ahora se debe proceder con la migración del agente Orchestrator para que utilice el adaptador del Intent Analyzer.
3. Una vez completada la migración del Orchestrator, se deberán realizar pruebas de integración completas.

Para más detalles sobre el estado actual de la migración del Intent Analyzer, consultar el documento `progress_intent_analyzer_migration.md`.
