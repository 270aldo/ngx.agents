# Plan de Migración del Orchestrator al A2A Optimizado

## Objetivo

Migrar el agente Orchestrator para utilizar el adaptador de A2A (`infrastructure/a2a_adapter.py`) en lugar del A2A original. Esto permitirá aprovechar las mejoras de rendimiento y capacidades del nuevo A2A optimizado, incluyendo la comunicación asíncrona entre agentes.

## Análisis Previo

El agente Orchestrator actualmente utiliza llamadas HTTP directas a través de httpx para comunicarse con otros agentes. Esta implementación debe ser reemplazada por llamadas al adaptador de A2A.

## Pasos de Implementación

1. **Importar el adaptador de A2A**

   Añadir la importación del adaptador de A2A al inicio del archivo:
   ```python
   from infrastructure.a2a_adapter import a2a_adapter
   ```

2. **Modificar el método `_get_agent_responses`**

   Actualizar el método para utilizar el adaptador de A2A:
   ```python
   async def _get_agent_responses(
       self,
       user_input: str,
       agent_ids: List[str],
       user_id: Optional[str] = None,
       context: Optional[Dict[str, Any]] = None,
       session_id: Optional[str] = None
   ) -> Dict[str, Dict[str, Any]]:
       agent_responses_map: Dict[str, Dict[str, Any]] = {}
       
       # Crear el contexto de la tarea
       task_context_data = A2ATaskContext(
           session_id=session_id, user_id=user_id, additional_context=context if context else {}
       )
       
       # Llamar a múltiples agentes en paralelo utilizando el adaptador de A2A
       try:
           responses = await a2a_adapter.call_multiple_agents(
               user_input=user_input,
               agent_ids=agent_ids,
               context=task_context_data
           )
           
           # Procesar las respuestas
           for agent_id, response in responses.items():
               if response.get("status") == "success":
                   agent_responses_map[agent_id] = {
                       "agent_id": response.get("agent_id", agent_id),
                       "agent_name": response.get("agent_name", agent_id),
                       "status": "success",
                       "output": response.get("output"),
                       "artifacts": response.get("artifacts", [])
                   }
               else:
                   agent_responses_map[agent_id] = {
                       "agent_id": agent_id,
                       "agent_name": agent_id,
                       "status": response.get("status", "error"),
                       "error": response.get("error", "Error desconocido"),
                       "output": response.get("output", "Error al procesar la solicitud."),
                       "artifacts": []
                   }
       except Exception as e:
           logger.error(f"Error al llamar a múltiples agentes: {e}", exc_info=True)
           for agent_id in agent_ids:
               agent_responses_map[agent_id] = {
                   "agent_id": agent_id,
                   "agent_name": agent_id,
                   "status": "error_communication",
                   "error": str(e),
                   "output": "Error de comunicación con el agente.",
                   "artifacts": []
               }
       
       return agent_responses_map
   ```

3. **Eliminar el método `_make_a2a_call`**

   Este método ya no será necesario, ya que el adaptador de A2A se encargará de las llamadas HTTP.

4. **Pruebas**

   Crear pruebas para verificar que el agente Orchestrator funciona correctamente con el adaptador de A2A:
   ```python
   # tests/test_orchestrator_a2a.py
   ```

## Consideraciones

- El adaptador de A2A debe mantener la misma interfaz que el A2A original para minimizar los cambios en el agente Orchestrator.
- Es importante verificar que el formato de los datos devueltos por el adaptador sea compatible con el esperado por el agente Orchestrator.
- Se deben manejar adecuadamente los errores que puedan surgir durante la migración.
- El adaptador de A2A debe implementar mecanismos de retry y circuit breaker para mejorar la resiliencia del sistema.

## Validación

Para validar la migración, se deben realizar las siguientes pruebas:

1. Verificar que el agente Orchestrator pueda comunicarse correctamente con otros agentes.
2. Comprobar que las respuestas de los agentes se procesen adecuadamente.
3. Asegurarse de que los errores se manejen correctamente.
4. Verificar que la comunicación asíncrona funcione como se espera.

## Próximos Pasos

Una vez completada la migración del agente Orchestrator, se procederá a migrar el resto de los agentes que utilicen el A2A.
