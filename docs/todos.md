# TODOs para Registrar como Issues

Este documento recopila los TODOs encontrados en el código para registrarlos como issues en GitHub.

## Categorías de TODOs

### 1. Refactorización de Adaptadores
- Actualizar los adaptadores restantes para que hereden de `BaseAgentAdapter`
- Eliminar código duplicado en los adaptadores existentes

### 2. Optimización de Caché
- Revisar la implementación de caché para asegurar que funciona correctamente en todos los entornos
- Considerar la migración a Redis para entornos de producción

### 3. Documentación
- Actualizar la documentación de la arquitectura para reflejar los cambios
- Crear diagramas de clases para los adaptadores

### 4. Pruebas
- Añadir pruebas para `BaseAgentAdapter`
- Verificar que todos los adaptadores funcionan correctamente con la nueva estructura

## TODOs Específicos Encontrados en el Código

1. **Implementar pruebas para BaseAgentAdapter**
   - Prioridad: Alta
   - Descripción: Crear pruebas unitarias para verificar el funcionamiento de la clase base `BaseAgentAdapter`
   - Archivos relacionados: `infrastructure/adapters/base_agent_adapter.py`

2. **Migrar adaptadores restantes a BaseAgentAdapter**
   - Prioridad: Alta
   - Descripción: Actualizar todos los adaptadores para que hereden de `BaseAgentAdapter`
   - Archivos relacionados: Todos los archivos en `infrastructure/adapters/` que terminan en `_adapter.py`

3. **Optimizar implementación de caché**
   - Prioridad: Media
   - Descripción: Revisar y mejorar la implementación actual de caché
   - Archivos relacionados: `clients/vertex_ai_client_adapter.py`

4. **Crear diagramas de clases para adaptadores**
   - Prioridad: Media
   - Descripción: Crear diagramas UML que muestren la relación entre `BaseAgentAdapter` y los adaptadores específicos
   - Archivos relacionados: `docs/refactorizacion_y_optimizacion.md`

5. **Eliminar scripts de configuración obsoletos**
   - Prioridad: Baja
   - Descripción: Eliminar los scripts de configuración antiguos ahora que tenemos `setup_unified_env.sh`
   - Archivos relacionados: `setup_env.sh`, `setup_dev_env.sh`, `setup_test_env.sh`

## Pasos para Registrar Issues

1. Acceder al repositorio en GitHub
2. Ir a la sección "Issues"
3. Crear un nuevo issue para cada TODO
4. Asignar etiquetas apropiadas (enhancement, bug, documentation, etc.)
5. Asignar a los responsables correspondientes
6. Establecer hitos si es necesario
