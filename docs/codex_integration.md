# Integración con OpenAI Codex

Este documento describe la integración del proyecto NGX Agents con OpenAI Codex para desarrollo asistido por IA.

## Objetivos

- Utilizar Codex para mejorar la productividad en el desarrollo
- Mantener la consistencia del código con los estándares del proyecto
- Facilitar la implementación de nuevas características

## Estructura del proyecto

El proyecto NGX Agents sigue una arquitectura modular basada en:

- **Agentes**: Implementados en el directorio `agents/`
- **Clientes para servicios externos**: Implementados en `clients/`
- **Infraestructura A2A**: Implementada en `infrastructure/`
- **API FastAPI**: Implementada en `app/`

## Guías para trabajar con Codex

1. **Mantén los comentarios descriptivos**: Codex utiliza los comentarios para entender el contexto
2. **Usa docstrings completos**: Incluye parámetros, tipos y descripciones
3. **Sigue la estructura existente**: Mantén la coherencia con el código actual
4. **Verifica las dependencias**: Asegúrate de que las nuevas implementaciones respeten las dependencias existentes

## Áreas de enfoque recomendadas

- Mejoras en el cliente de Vertex AI
- Optimización de la comunicación entre agentes
- Implementación de nuevas capacidades en agentes existentes
- Mejoras en la telemetría y monitoreo

## Flujo de trabajo recomendado

1. Describe claramente lo que quieres implementar en comentarios
2. Deja que Codex genere una implementación inicial
3. Revisa y ajusta el código generado
4. Ejecuta pruebas unitarias para verificar la funcionalidad
5. Refactoriza según sea necesario
