"""
Analizador de prompts para reducción de tokens.

Este módulo proporciona funcionalidades para analizar y optimizar prompts
con el objetivo de reducir el número de tokens utilizados, manteniendo
la calidad de las respuestas.
"""

import re
import logging
from typing import Dict, List, Any
import json

# Configurar logger
logger = logging.getLogger(__name__)


class PromptAnalyzer:
    """
    Analizador de prompts para reducción de tokens.

    Esta clase proporciona métodos para analizar y optimizar prompts
    con el objetivo de reducir el número de tokens utilizados.
    """

    def __init__(self):
        """Inicializa el analizador de prompts."""
        # Patrones comunes que pueden ser optimizados
        self.patterns = {
            "repeticiones": r"(\b\w+\b)(\s+\1\b)+",
            "espacios_extra": r"\s{2,}",
            "puntuacion_repetida": r"([.!?])\1+",
            "frases_innecesarias": r"\b(por favor|como puedes ver|como mencioné anteriormente|como se mencionó|en otras palabras)\b",
            "palabras_relleno": r"\b(básicamente|literalmente|actualmente|realmente|simplemente|solo|muy|bastante|algo|un poco)\b",
        }

    def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Analiza un prompt y proporciona métricas y sugerencias de optimización.

        Args:
            prompt: Texto del prompt a analizar

        Returns:
            Diccionario con métricas y sugerencias
        """
        if not prompt:
            return {
                "original_length": 0,
                "estimated_tokens": 0,
                "issues": [],
                "optimized_prompt": "",
                "token_reduction": 0,
                "percentage_reduction": 0.0,
            }

        # Calcular métricas básicas
        char_count = len(prompt)
        word_count = len(prompt.split())
        estimated_tokens = self._estimate_tokens(prompt)

        # Encontrar problemas
        issues = self._find_issues(prompt)

        # Generar prompt optimizado
        optimized_prompt = self._optimize_prompt(prompt, issues)
        optimized_tokens = self._estimate_tokens(optimized_prompt)

        # Calcular reducción
        token_reduction = estimated_tokens - optimized_tokens
        percentage_reduction = (
            (token_reduction / estimated_tokens) * 100 if estimated_tokens > 0 else 0
        )

        return {
            "original_length": char_count,
            "word_count": word_count,
            "estimated_tokens": estimated_tokens,
            "issues": issues,
            "optimized_prompt": optimized_prompt,
            "optimized_tokens": optimized_tokens,
            "token_reduction": token_reduction,
            "percentage_reduction": percentage_reduction,
        }

    def _estimate_tokens(self, text: str) -> int:
        """
        Estima el número de tokens en un texto.

        Esta es una estimación aproximada basada en palabras y caracteres.
        Para una estimación más precisa, se debería usar un tokenizador real.

        Args:
            text: Texto a analizar

        Returns:
            Número estimado de tokens
        """
        if not text:
            return 0

        # Estimación simple: aproximadamente 4 caracteres por token en promedio
        # Esta es una aproximación muy básica y puede variar según el modelo y el idioma
        char_count = len(text)
        estimated_tokens = max(1, char_count // 4)

        return estimated_tokens

    def _find_issues(self, prompt: str) -> List[Dict[str, Any]]:
        """
        Encuentra problemas en el prompt que pueden ser optimizados.

        Args:
            prompt: Texto del prompt a analizar

        Returns:
            Lista de problemas encontrados
        """
        issues = []

        # Verificar longitud
        if len(prompt) > 4000:
            issues.append(
                {
                    "type": "longitud_excesiva",
                    "description": "El prompt es demasiado largo (>4000 caracteres)",
                    "severity": "alta",
                }
            )

        # Buscar patrones problemáticos
        for pattern_name, pattern in self.patterns.items():
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            if matches:
                unique_matches = set(
                    matches if isinstance(matches[0], str) else [m[0] for m in matches]
                )
                if unique_matches:
                    issues.append(
                        {
                            "type": pattern_name,
                            "description": f"Se encontraron {len(unique_matches)} instancias de {pattern_name}",
                            "matches": list(unique_matches)[:5],  # Limitar a 5 ejemplos
                            "severity": "media",
                        }
                    )

        # Verificar formato JSON
        if prompt.strip().startswith("{") and prompt.strip().endswith("}"):
            try:
                json_obj = json.loads(prompt)
                # Verificar si hay campos innecesariamente largos
                for key, value in json_obj.items():
                    if isinstance(value, str) and len(value) > 500:
                        issues.append(
                            {
                                "type": "json_campo_largo",
                                "description": f"El campo JSON '{key}' es muy largo ({len(value)} caracteres)",
                                "severity": "media",
                            }
                        )
            except json.JSONDecodeError:
                # No es JSON válido, ignorar
                pass

        # Verificar instrucciones redundantes
        instruction_patterns = [
            r"(?i)responde (en|con) (español|inglés|francés|alemán|italiano|portugués)",
            r"(?i)responde de (manera|forma) (concisa|breve|detallada|completa)",
            r"(?i)tu respuesta debe ser (concisa|breve|detallada|completa)",
            r"(?i)responde como (un|una) (experto|profesional|especialista)",
        ]

        for pattern in instruction_patterns:
            matches = re.findall(pattern, prompt)
            if matches:
                issues.append(
                    {
                        "type": "instruccion_redundante",
                        "description": "Instrucciones redundantes que pueden ser omitidas",
                        "matches": [
                            re.search(pattern, prompt).group(0)
                            for _ in range(min(len(matches), 3))
                        ],
                        "severity": "baja",
                    }
                )

        return issues

    def _optimize_prompt(self, prompt: str, issues: List[Dict[str, Any]]) -> str:
        """
        Optimiza el prompt basado en los problemas encontrados.

        Args:
            prompt: Texto del prompt original
            issues: Lista de problemas encontrados

        Returns:
            Prompt optimizado
        """
        optimized = prompt

        # Aplicar optimizaciones basadas en los problemas encontrados
        for issue in issues:
            if issue["type"] == "repeticiones":
                # Eliminar palabras repetidas
                optimized = re.sub(self.patterns["repeticiones"], r"\1", optimized)

            elif issue["type"] == "espacios_extra":
                # Normalizar espacios
                optimized = re.sub(self.patterns["espacios_extra"], " ", optimized)

            elif issue["type"] == "puntuacion_repetida":
                # Normalizar puntuación repetida
                optimized = re.sub(
                    self.patterns["puntuacion_repetida"], r"\1", optimized
                )

            elif issue["type"] == "frases_innecesarias":
                # Eliminar frases innecesarias
                optimized = re.sub(self.patterns["frases_innecesarias"], "", optimized)
                # Normalizar espacios después de eliminar frases
                optimized = re.sub(r"\s{2,}", " ", optimized)

            elif issue["type"] == "palabras_relleno":
                # Eliminar palabras de relleno
                optimized = re.sub(self.patterns["palabras_relleno"], "", optimized)
                # Normalizar espacios después de eliminar palabras
                optimized = re.sub(r"\s{2,}", " ", optimized)

        # Normalizar espacios finales
        optimized = optimized.strip()

        return optimized

    def optimize_json_prompt(self, json_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimiza un prompt en formato JSON.

        Args:
            json_obj: Objeto JSON a optimizar

        Returns:
            Objeto JSON optimizado
        """
        if not isinstance(json_obj, dict):
            return json_obj

        optimized = {}

        for key, value in json_obj.items():
            if isinstance(value, str):
                # Optimizar strings
                analysis = self.analyze_prompt(value)
                optimized[key] = analysis["optimized_prompt"]
            elif isinstance(value, list):
                # Optimizar listas recursivamente
                optimized[key] = [
                    (
                        self.optimize_json_prompt(item)
                        if isinstance(item, dict)
                        else (
                            self.analyze_prompt(item)["optimized_prompt"]
                            if isinstance(item, str)
                            else item
                        )
                    )
                    for item in value
                ]
            elif isinstance(value, dict):
                # Optimizar diccionarios recursivamente
                optimized[key] = self.optimize_json_prompt(value)
            else:
                # Mantener otros tipos de datos sin cambios
                optimized[key] = value

        return optimized

    def optimize_chat_messages(
        self, messages: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Optimiza una lista de mensajes de chat.

        Args:
            messages: Lista de mensajes en formato [{"role": "user|model", "content": "texto"}]

        Returns:
            Lista de mensajes optimizada
        """
        if not messages:
            return []

        optimized = []

        for msg in messages:
            if not isinstance(msg, dict) or "content" not in msg or "role" not in msg:
                # Mantener mensajes inválidos sin cambios
                optimized.append(msg)
                continue

            # Solo optimizar mensajes del usuario, no del modelo
            if msg["role"] == "user":
                analysis = self.analyze_prompt(msg["content"])
                optimized.append(
                    {"role": msg["role"], "content": analysis["optimized_prompt"]}
                )
            else:
                # Mantener mensajes del modelo sin cambios
                optimized.append(msg)

        return optimized


# Instancia global para uso en toda la aplicación
prompt_analyzer = PromptAnalyzer()
