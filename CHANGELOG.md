# Registro de Cambios (CHANGELOG)

## [No publicado]

### Añadido
- Clase base `BaseAgentAdapter` para reducir duplicación de código en adaptadores
- Script unificado `setup_unified_env.sh` para configuración de entornos
- Script `scripts/clean_pyproject_files.sh` para consolidar dependencias
- Implementación completa de `_get_program_type_from_profile` en `ProgramClassificationService`
- Pruebas para verificar la inicialización condicional de telemetría
- Documentación detallada sobre las mejoras en `docs/refactorizacion_y_optimizacion.md`
- Soporte para configuración condicional de telemetría
- Pruebas completas para el cliente Vertex AI optimizado
- Soporte para OpenTelemetry en el cliente Vertex AI
- Script `scripts/verify_adapter_inheritance.py` para identificar adaptadores que necesitan migración
- Implementación del adaptador `RecoveryCorrectiveAdapter` con herencia de `BaseAgentAdapter`
- Pruebas unitarias completas para `RecoveryCorrectiveAdapter`

### Corregido
- Errores de importación en las pruebas del cliente Vertex AI
- Problemas con la caché en memoria en el cliente Vertex AI
- Problemas con el pool de conexiones en el cliente Vertex AI
- Errores de importación de StateManager en pruebas unitarias
- Problemas de inicialización de TestClient en pruebas de autenticación
- Actualización de adaptadores para utilizar la clase base BaseAgentAdapter

### Cambiado
- Refactorización del cliente Vertex AI para usar una estructura modular
- Mejora en la gestión de errores y telemetría

## [0.1.0] - 2025-05-11

### Añadido
- Versión inicial del proyecto NGX Agents
- Implementación de agentes básicos
- Integración con Vertex AI
- Sistema de caché en memoria y pool de conexiones
