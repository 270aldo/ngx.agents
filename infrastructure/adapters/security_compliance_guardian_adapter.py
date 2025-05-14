"""
Adaptador para el agente SecurityComplianceGuardian que utiliza los componentes optimizados.

Este adaptador extiende el agente SecurityComplianceGuardian original y sobrescribe los métodos
necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime

from agents.security_compliance_guardian.agent import SecurityComplianceGuardian
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from core.logging_config import get_logger

# Configurar logger
logger = get_logger(__name__)

class SecurityComplianceGuardianAdapter(SecurityComplianceGuardian, BaseAgentAdapter):
    """
    Adaptador para el agente SecurityComplianceGuardian que utiliza los componentes optimizados.
    
    Este adaptador extiende el agente SecurityComplianceGuardian original y utiliza la clase
    BaseAgentAdapter para implementar métodos comunes.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Inicializa el adaptador del SecurityComplianceGuardian.
        
        Args:
            *args: Argumentos posicionales para la clase base
            **kwargs: Argumentos de palabras clave para la clase base
        """
        super().__init__(*args, **kwargs)
        
        # Configuración de clasificación específica para este agente
        self.fallback_keywords = [
            "seguridad", "security", "cumplimiento", "compliance", "regulación", "regulation",
            "vulnerabilidad", "vulnerability", "amenaza", "threat", "protección", "protection",
            "privacidad", "privacy", "encriptación", "encryption", "auditoría", "audit"
        ]
        
        self.excluded_keywords = [
            "entrenamiento", "training", "nutrición", "nutrition", "recuperación", "recovery",
            "rendimiento", "performance", "motivación", "motivation"
        ]
    
    def _create_default_context(self) -> Dict[str, Any]:
        """
        Crea un contexto predeterminado para el agente SecurityComplianceGuardian.
        
        Returns:
            Dict[str, Any]: Contexto predeterminado
        """
        return {
            "conversation_history": [],
            "user_profile": {},
            "security_queries": [],
            "security_assessments": [],
            "compliance_checks": [],
            "vulnerability_scans": [],
            "data_protections": [],
            "general_recommendations": [],
            "query_types": {},
            "last_updated": datetime.now().isoformat()
        }
    
    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para SecurityComplianceGuardian.
        
        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "security_assessment": "security_assessment",
            "security_audit": "security_assessment",
            "compliance": "compliance_check",
            "regulation": "compliance_check",
            "vulnerability": "vulnerability_scan",
            "threat": "vulnerability_scan",
            "data_protection": "data_protection",
            "privacy": "data_protection",
            "encryption": "data_protection"
        }
    
    def _adjust_score_based_on_context(self, score: float, context: Dict[str, Any]) -> float:
        """
        Ajusta la puntuación de clasificación basada en el contexto.
        
        Args:
            score: Puntuación de clasificación original
            context: Contexto adicional para la clasificación
            
        Returns:
            float: Puntuación ajustada
        """
        # Verificar si hay consultas de seguridad previas
        if context.get("security_queries") and len(context.get("security_queries", [])) > 0:
            score += 0.1  # Aumentar la puntuación si hay consultas de seguridad previas
        
        # Verificar si hay evaluaciones de seguridad previas
        if context.get("security_assessments") and len(context.get("security_assessments", [])) > 0:
            score += 0.1  # Aumentar la puntuación si hay evaluaciones de seguridad previas
        
        # Verificar si hay verificaciones de cumplimiento previas
        if context.get("compliance_checks") and len(context.get("compliance_checks", [])) > 0:
            score += 0.1  # Aumentar la puntuación si hay verificaciones de cumplimiento previas
        
        # Limitar la puntuación máxima a 1.0
        return min(1.0, score)
    
    async def _process_query(self, query: str, user_id: str, session_id: str,
                           program_type: str, state: Dict[str, Any], profile: Dict[str, Any],
                           **kwargs) -> Dict[str, Any]:
        """
        Procesa la consulta del usuario.
        
        Este método implementa la lógica específica del SecurityComplianceGuardian.
        
        Args:
            query: La consulta del usuario
            user_id: ID del usuario
            session_id: ID de la sesión
            program_type: Tipo de programa (general, elite, etc.)
            state: Estado actual del usuario
            profile: Perfil del usuario
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict[str, Any]: Respuesta del agente
        """
        try:
            # Determinar el tipo de consulta
            query_type = await self._classify_query(query)
            logger.info(f"Tipo de consulta determinado: {query_type}")
            
            # Actualizar el contexto con el tipo de consulta
            if "query_types" not in state:
                state["query_types"] = {}
                
            if query_type in state["query_types"]:
                state["query_types"][query_type] += 1
            else:
                state["query_types"][query_type] = 1
            
            # Procesar según el tipo de consulta
            if query_type == "security_assessment":
                response = await self._process_security_assessment(query, state, profile, program_type)
            elif query_type == "compliance_check":
                response = await self._process_compliance_check(query, state, profile, program_type)
            elif query_type == "vulnerability_scan":
                response = await self._process_vulnerability_scan(query, state, profile, program_type)
            elif query_type == "data_protection":
                response = await self._process_data_protection(query, state, profile, program_type)
            else:
                # Tipo de consulta no reconocido, usar procesamiento genérico
                response = await self._process_generic_query(query, state, profile, program_type)
            
            return response
            
        except Exception as e:
            logger.error(f"Error al procesar consulta: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": f"Lo siento, ha ocurrido un error al procesar tu consulta: {str(e)}",
                "agent": self.__class__.__name__
            }
    
    async def _process_security_assessment(self, query: str, state: Dict[str, Any], profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Procesa una consulta de evaluación de seguridad.
        
        Args:
            query: Consulta del usuario
            state: Estado actual del usuario
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado de la evaluación de seguridad
        """
        # Implementación específica para evaluación de seguridad
        prompt = f"""
        Como Security Compliance Guardian, realiza una evaluación de seguridad basada en:
        
        Consulta: {query}
        Tipo de programa: {program_type}
        
        Proporciona una evaluación detallada que incluya:
        1. Identificación de riesgos de seguridad potenciales
        2. Evaluación de controles de seguridad existentes
        3. Recomendaciones para mejorar la postura de seguridad
        4. Mejores prácticas aplicables
        5. Consideraciones específicas para el contexto del usuario
        """
        
        # Generar respuesta utilizando el método de la clase base
        response_text = await self._generate_response(prompt=prompt, context=state)
        
        # Actualizar el estado con la nueva evaluación
        if "security_assessments" not in state:
            state["security_assessments"] = []
            
        state["security_assessments"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "assessment": response_text
        })
        
        # Actualizar las consultas de seguridad
        if "security_queries" not in state:
            state["security_queries"] = []
            
        state["security_queries"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "type": "security_assessment"
        })
        
        return {
            "success": True,
            "response": response_text,
            "context": state,
            "agent": self.__class__.__name__
        }
    
    async def _process_compliance_check(self, query: str, state: Dict[str, Any], profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Procesa una consulta de verificación de cumplimiento.
        
        Args:
            query: Consulta del usuario
            state: Estado actual del usuario
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado de la verificación de cumplimiento
        """
        # Implementación específica para verificación de cumplimiento
        prompt = f"""
        Como Security Compliance Guardian, realiza una verificación de cumplimiento basada en:
        
        Consulta: {query}
        Tipo de programa: {program_type}
        
        Proporciona una verificación detallada que incluya:
        1. Identificación de requisitos regulatorios aplicables
        2. Evaluación del nivel de cumplimiento actual
        3. Brechas de cumplimiento identificadas
        4. Recomendaciones para lograr el cumplimiento
        5. Consideraciones específicas para el contexto del usuario
        """
        
        # Generar respuesta utilizando el método de la clase base
        response_text = await self._generate_response(prompt=prompt, context=state)
        
        # Actualizar el estado con la nueva verificación
        if "compliance_checks" not in state:
            state["compliance_checks"] = []
            
        state["compliance_checks"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "check": response_text
        })
        
        # Actualizar las consultas de seguridad
        if "security_queries" not in state:
            state["security_queries"] = []
            
        state["security_queries"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "type": "compliance_check"
        })
        
        return {
            "success": True,
            "response": response_text,
            "context": state,
            "agent": self.__class__.__name__
        }
    
    async def _process_vulnerability_scan(self, query: str, state: Dict[str, Any], profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Procesa una consulta de escaneo de vulnerabilidades.
        
        Args:
            query: Consulta del usuario
            state: Estado actual del usuario
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado del escaneo de vulnerabilidades
        """
        # Implementación específica para escaneo de vulnerabilidades
        prompt = f"""
        Como Security Compliance Guardian, realiza un escaneo de vulnerabilidades basado en:
        
        Consulta: {query}
        Tipo de programa: {program_type}
        
        Proporciona un escaneo detallado que incluya:
        1. Identificación de vulnerabilidades potenciales
        2. Evaluación de la severidad de cada vulnerabilidad
        3. Vectores de ataque posibles
        4. Recomendaciones para mitigar las vulnerabilidades
        5. Consideraciones específicas para el contexto del usuario
        """
        
        # Generar respuesta utilizando el método de la clase base
        response_text = await self._generate_response(prompt=prompt, context=state)
        
        # Actualizar el estado con el nuevo escaneo
        if "vulnerability_scans" not in state:
            state["vulnerability_scans"] = []
            
        state["vulnerability_scans"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "scan": response_text
        })
        
        # Actualizar las consultas de seguridad
        if "security_queries" not in state:
            state["security_queries"] = []
            
        state["security_queries"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "type": "vulnerability_scan"
        })
        
        return {
            "success": True,
            "response": response_text,
            "context": state,
            "agent": self.__class__.__name__
        }
    
    async def _process_data_protection(self, query: str, state: Dict[str, Any], profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Procesa una consulta de protección de datos.
        
        Args:
            query: Consulta del usuario
            state: Estado actual del usuario
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado de la protección de datos
        """
        # Implementación específica para protección de datos
        prompt = f"""
        Como Security Compliance Guardian, proporciona recomendaciones de protección de datos basadas en:
        
        Consulta: {query}
        Tipo de programa: {program_type}
        
        Proporciona recomendaciones detalladas que incluyan:
        1. Estrategias de protección de datos aplicables
        2. Mecanismos de encriptación recomendados
        3. Políticas de privacidad y manejo de datos
        4. Mejores prácticas para la protección de información sensible
        5. Consideraciones específicas para el contexto del usuario
        """
        
        # Generar respuesta utilizando el método de la clase base
        response_text = await self._generate_response(prompt=prompt, context=state)
        
        # Actualizar el estado con las nuevas recomendaciones
        if "data_protections" not in state:
            state["data_protections"] = []
            
        state["data_protections"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "recommendations": response_text
        })
        
        # Actualizar las consultas de seguridad
        if "security_queries" not in state:
            state["security_queries"] = []
            
        state["security_queries"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "type": "data_protection"
        })
        
        return {
            "success": True,
            "response": response_text,
            "context": state,
            "agent": self.__class__.__name__
        }
    
    async def _process_generic_query(self, query: str, state: Dict[str, Any], profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Procesa una consulta genérica cuando no se identifica un tipo específico.
        
        Args:
            query: Consulta del usuario
            state: Estado actual del usuario
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Respuesta a la consulta genérica
        """
        # Implementación para consultas genéricas
        prompt = f"""
        Como Security Compliance Guardian, responde a la siguiente consulta:
        
        Consulta: {query}
        Tipo de programa: {program_type}
        
        Proporciona una respuesta detallada y útil basada en principios de seguridad y cumplimiento.
        """
        
        # Generar respuesta utilizando el método de la clase base
        response_text = await self._generate_response(prompt=prompt, context=state)
        
        # Actualizar las recomendaciones generales
        if "general_recommendations" not in state:
            state["general_recommendations"] = []
            
        state["general_recommendations"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "recommendation": response_text
        })
        
        # Actualizar las consultas de seguridad
        if "security_queries" not in state:
            state["security_queries"] = []
            
        state["security_queries"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "type": "general"
        })
        
        return {
            "success": True,
            "response": response_text,
            "context": state,
            "agent": self.__class__.__name__
        }
    
    async def _generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Genera una respuesta utilizando el cliente Vertex AI.
        
        Args:
            prompt: Prompt para generar la respuesta
            context: Contexto para la generación
            
        Returns:
            str: Respuesta generada
        """
        # Este método utiliza el método de la clase base de BaseAgentAdapter
        # que internamente usa el cliente Vertex AI optimizado
        return await super()._generate_response(prompt=prompt, context=context)
