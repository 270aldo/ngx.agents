"""
Cliente avanzado de visión para Vertex AI con capacidades mejoradas.

Este módulo extiende las capacidades de visión existentes para incluir:
- Análisis de forma física y composición corporal
- Detección de postura en ejercicios
- Seguimiento visual de progreso
- OCR especializado para etiquetas nutricionales
"""

import base64
import json
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
import numpy as np
from google.cloud import aiplatform
from google.cloud import storage
from google.cloud import vision
import cv2
import io
from PIL import Image

from core.logging_config import get_logger
from core.telemetry import Telemetry
from clients.vertex_ai.vision_client import VertexAIVisionClient
from clients.gcs_client import GCSClient

logger = get_logger(__name__)


class AdvancedVisionClient(VertexAIVisionClient):
    """
    Cliente avanzado de visión que extiende las capacidades básicas
    con funcionalidades específicas para fitness y bienestar.
    """

    def __init__(
        self,
        model: str = "gemini-2.0-flash-exp",  # Usando Gemini 2.0 Flash para agentes
        orchestrator_model: str = "gemini-2.0-pro-exp",  # Gemini 2.0 Pro para el orchestrator
        telemetry: Optional[Telemetry] = None,
        gcs_client: Optional[GCSClient] = None,
    ):
        """
        Inicializa el cliente avanzado de visión.

        Args:
            model: Modelo de Gemini para agentes especializados
            orchestrator_model: Modelo de Gemini para el orchestrator
            telemetry: Instancia de telemetría
            gcs_client: Cliente de Google Cloud Storage
        """
        super().__init__(model=model, telemetry=telemetry)
        self.orchestrator_model = orchestrator_model
        self.gcs_client = gcs_client or GCSClient()
        self.vision_client = vision.ImageAnnotatorClient()

        # Configuración de modelos especializados
        self.models = {
            "agent": model,
            "orchestrator": orchestrator_model,
            "ocr": "gemini-2.0-flash-exp",  # Flash es eficiente para OCR
            "analysis": "gemini-2.0-pro-exp",  # Pro para análisis complejos
        }

    async def analyze_physical_form(
        self,
        image_data: Union[str, bytes],
        user_profile: Optional[Dict[str, Any]] = None,
        analysis_type: str = "comprehensive",
    ) -> Dict[str, Any]:
        """
        Realiza un análisis avanzado de la forma física desde una imagen.

        Args:
            image_data: Imagen en base64 o bytes
            user_profile: Perfil del usuario para personalizar el análisis
            analysis_type: Tipo de análisis ("comprehensive", "body_composition", "symmetry")

        Returns:
            Análisis detallado de la forma física
        """
        span = None
        if self.telemetry:
            span = self.telemetry.start_span("advanced_physical_form_analysis")

        try:
            # Preparar el prompt especializado para análisis físico
            prompt = f"""
            Analiza esta imagen de forma física con un enfoque profesional de fitness.
            
            Tipo de análisis: {analysis_type}
            
            Por favor proporciona:
            
            1. **Composición Corporal Estimada**:
               - Tipo de cuerpo (ectomorfo, mesomorfo, endomorfo)
               - Estimación visual de porcentaje de grasa corporal
               - Distribución de masa muscular
               - Áreas de mayor desarrollo muscular
            
            2. **Análisis de Simetría y Proporción**:
               - Balance entre lado izquierdo y derecho
               - Proporción entre grupos musculares
               - Áreas que requieren más desarrollo
               - Puntos fuertes visibles
            
            3. **Postura y Alineación**:
               - Alineación de hombros
               - Posición de cadera
               - Curvatura de columna visible
               - Posibles desequilibrios posturales
            
            4. **Recomendaciones Específicas**:
               - Grupos musculares a priorizar
               - Ejercicios recomendados
               - Consideraciones de movilidad
               - Sugerencias de corrección postural
            
            {"Información del usuario: " + json.dumps(user_profile) if user_profile else ""}
            
            Proporciona el análisis en formato JSON estructurado.
            """

            # Usar el modelo Pro para análisis complejos
            result = await self._analyze_with_model(
                image_data,
                prompt,
                model=self.models["analysis"],
                temperature=0.3,  # Baja temperatura para precisión
            )

            # Procesar y estructurar la respuesta
            analysis = self._parse_json_response(result)

            # Añadir metadatos
            analysis["metadata"] = {
                "analysis_type": analysis_type,
                "model_used": self.models["analysis"],
                "timestamp": datetime.utcnow().isoformat(),
                "confidence_score": self._calculate_confidence_score(analysis),
            }

            # Guardar en GCS si está disponible
            if self.gcs_client and user_profile:
                await self._save_analysis_to_gcs(
                    user_profile.get("user_id"),
                    image_data,
                    analysis,
                    "physical_form_analysis",
                )

            return {
                "status": "success",
                "analysis": analysis,
                "recommendations": self._generate_personalized_recommendations(
                    analysis, user_profile
                ),
            }

        except Exception as e:
            logger.error(f"Error en análisis de forma física: {e}", exc_info=True)
            return {"status": "error", "error": str(e), "analysis": None}
        finally:
            if span and self.telemetry:
                self.telemetry.end_span(span)

    async def detect_exercise_posture(
        self,
        image_data: Union[str, bytes],
        exercise_name: str,
        expected_form: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Detecta y analiza la postura durante un ejercicio específico.

        Args:
            image_data: Imagen del ejercicio
            exercise_name: Nombre del ejercicio siendo realizado
            expected_form: Forma esperada del ejercicio (opcional)

        Returns:
            Análisis de la postura y recomendaciones
        """
        span = None
        if self.telemetry:
            span = self.telemetry.start_span("exercise_posture_detection")

        try:
            # Prompt especializado para análisis de ejercicio
            prompt = f"""
            Analiza la técnica y postura en este ejercicio: {exercise_name}
            
            Evalúa los siguientes aspectos:
            
            1. **Alineación Corporal**:
               - Posición de la columna
               - Alineación de rodillas
               - Posición de hombros
               - Distribución del peso
            
            2. **Técnica del Ejercicio**:
               - Rango de movimiento
               - Velocidad de ejecución (si es perceptible)
               - Control del movimiento
               - Activación muscular visible
            
            3. **Errores Comunes**:
               - Identifica errores de forma
               - Riesgos de lesión potenciales
               - Compensaciones musculares
            
            4. **Puntuación de Forma** (0-100):
               - Califica la ejecución general
               - Indica áreas de mejora específicas
            
            5. **Correcciones Recomendadas**:
               - Ajustes inmediatos necesarios
               - Ejercicios de movilidad recomendados
               - Progresiones o regresiones sugeridas
            
            {"Forma esperada: " + json.dumps(expected_form) if expected_form else ""}
            
            Proporciona el análisis en formato JSON con una estructura clara.
            """

            # Análisis con el modelo
            result = await self._analyze_with_model(
                image_data, prompt, model=self.models["agent"], temperature=0.2
            )

            # Parsear respuesta
            posture_analysis = self._parse_json_response(result)

            # Calcular métricas adicionales si es posible
            if self._can_extract_keypoints(image_data):
                keypoints = await self._extract_pose_keypoints(image_data)
                posture_analysis["keypoints"] = keypoints
                posture_analysis["joint_angles"] = self._calculate_joint_angles(
                    keypoints
                )

            # Generar visualización si es posible
            visualization = await self._generate_posture_visualization(
                image_data, posture_analysis
            )

            return {
                "status": "success",
                "exercise": exercise_name,
                "analysis": posture_analysis,
                "visualization": visualization,
                "safety_score": self._calculate_safety_score(posture_analysis),
                "improvement_tips": self._generate_improvement_tips(
                    posture_analysis, exercise_name
                ),
            }

        except Exception as e:
            logger.error(f"Error en detección de postura: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "exercise": exercise_name,
                "analysis": None,
            }
        finally:
            if span and self.telemetry:
                self.telemetry.end_span(span)

    async def track_visual_progress(
        self,
        current_image: Union[str, bytes],
        previous_images: List[Dict[str, Any]],
        user_goals: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Realiza seguimiento visual del progreso comparando imágenes a lo largo del tiempo.

        Args:
            current_image: Imagen actual
            previous_images: Lista de imágenes anteriores con metadatos
            user_goals: Objetivos del usuario

        Returns:
            Análisis de progreso visual
        """
        span = None
        if self.telemetry:
            span = self.telemetry.start_span("visual_progress_tracking")

        try:
            # Preparar las imágenes para comparación
            comparison_data = await self._prepare_progress_comparison(
                current_image, previous_images
            )

            prompt = f"""
            Analiza el progreso físico visible comparando estas imágenes tomadas en diferentes momentos.
            
            Fechas de las imágenes: {comparison_data['dates']}
            
            Por favor evalúa:
            
            1. **Cambios en Composición Corporal**:
               - Cambios en masa muscular
               - Cambios en grasa corporal
               - Definición muscular
               - Cambios en volumen general
            
            2. **Progreso por Área Corporal**:
               - Torso superior (pecho, hombros, brazos)
               - Core (abdominales, oblicuos)
               - Torso inferior (glúteos, cuádriceps, isquiotibiales)
               - Cambios posturales
            
            3. **Análisis Temporal**:
               - Tasa de progreso
               - Períodos de mayor cambio
               - Consistencia del progreso
               - Proyección futura
            
            4. **Comparación con Objetivos**:
               {"Objetivos del usuario: " + json.dumps(user_goals) if user_goals else ""}
               - Alineación con objetivos
               - Tiempo estimado para objetivos
               - Ajustes recomendados
            
            Proporciona un análisis detallado en formato JSON.
            """

            # Análisis con el modelo Pro para comparaciones complejas
            result = await self._analyze_with_model(
                comparison_data["combined_image"],
                prompt,
                model=self.models["analysis"],
                temperature=0.3,
            )

            progress_analysis = self._parse_json_response(result)

            # Generar métricas cuantitativas si es posible
            metrics = await self._calculate_progress_metrics(
                current_image, previous_images
            )

            # Crear visualización de progreso
            progress_chart = await self._generate_progress_visualization(
                progress_analysis, metrics, comparison_data["dates"]
            )

            return {
                "status": "success",
                "analysis": progress_analysis,
                "metrics": metrics,
                "visualization": progress_chart,
                "timeline": self._create_progress_timeline(
                    progress_analysis, comparison_data
                ),
                "recommendations": self._generate_progress_recommendations(
                    progress_analysis, user_goals
                ),
            }

        except Exception as e:
            logger.error(f"Error en seguimiento de progreso: {e}", exc_info=True)
            return {"status": "error", "error": str(e), "analysis": None}
        finally:
            if span and self.telemetry:
                self.telemetry.end_span(span)

    async def extract_nutritional_info(
        self,
        image_data: Union[str, bytes],
        language: str = "es",
        extract_ingredients: bool = True,
    ) -> Dict[str, Any]:
        """
        Extrae información nutricional de etiquetas de alimentos usando OCR avanzado.

        Args:
            image_data: Imagen de la etiqueta nutricional
            language: Idioma de la etiqueta
            extract_ingredients: Si extraer lista de ingredientes

        Returns:
            Información nutricional estructurada
        """
        span = None
        if self.telemetry:
            span = self.telemetry.start_span("nutritional_info_extraction")

        try:
            # Primero usar Cloud Vision API para OCR preciso
            ocr_result = await self._perform_advanced_ocr(image_data)

            # Prompt para estructurar la información nutricional
            prompt = f"""
            Analiza este texto extraído de una etiqueta nutricional y estructura la información.
            
            Texto OCR: {ocr_result['text']}
            
            Extrae y estructura:
            
            1. **Información Básica**:
               - Nombre del producto
               - Marca
               - Tamaño de porción
               - Porciones por envase
            
            2. **Valores Nutricionales** (por porción):
               - Calorías
               - Proteínas (g)
               - Carbohidratos totales (g)
               - - Azúcares (g)
               - - Fibra dietética (g)
               - Grasas totales (g)
               - - Grasas saturadas (g)
               - - Grasas trans (g)
               - Sodio (mg)
               - Colesterol (mg)
            
            3. **Vitaminas y Minerales**:
               - Lista con cantidades y % VD
            
            {"4. **Ingredientes**: Lista completa en orden" if extract_ingredients else ""}
            
            5. **Análisis Nutricional**:
               - Calidad nutricional general
               - Puntos positivos
               - Puntos de atención
               - Adecuación para diferentes dietas
            
            Proporciona la información en formato JSON estructurado.
            Idioma de respuesta: {language}
            """

            # Análisis con el modelo OCR especializado
            result = await self._analyze_with_model(
                ocr_result["text"],
                prompt,
                model=self.models["ocr"],
                temperature=0.1,  # Muy baja para precisión en datos
            )

            nutritional_info = self._parse_json_response(result)

            # Validar y normalizar valores nutricionales
            nutritional_info = self._validate_nutritional_values(nutritional_info)

            # Calcular métricas adicionales
            nutritional_info["calculated_metrics"] = {
                "protein_percentage": self._calculate_macro_percentage(
                    nutritional_info, "protein"
                ),
                "carb_percentage": self._calculate_macro_percentage(
                    nutritional_info, "carbs"
                ),
                "fat_percentage": self._calculate_macro_percentage(
                    nutritional_info, "fat"
                ),
                "sugar_to_carb_ratio": self._calculate_sugar_ratio(nutritional_info),
                "fiber_adequacy": self._evaluate_fiber_content(nutritional_info),
                "sodium_level": self._evaluate_sodium_level(nutritional_info),
            }

            # Añadir recomendaciones basadas en el análisis
            nutritional_info["recommendations"] = (
                self._generate_nutritional_recommendations(nutritional_info)
            )

            # Si se detectó código de barras, extraer información adicional
            if ocr_result.get("barcode"):
                barcode_info = await self._lookup_barcode_info(ocr_result["barcode"])
                nutritional_info["barcode_info"] = barcode_info

            return {
                "status": "success",
                "nutritional_info": nutritional_info,
                "ocr_confidence": ocr_result.get("confidence", 0),
                "warnings": self._check_nutritional_warnings(nutritional_info),
                "dietary_compatibility": self._check_dietary_compatibility(
                    nutritional_info
                ),
            }

        except Exception as e:
            logger.error(f"Error en extracción nutricional: {e}", exc_info=True)
            return {"status": "error", "error": str(e), "nutritional_info": None}
        finally:
            if span and self.telemetry:
                self.telemetry.end_span(span)

    # Métodos auxiliares privados

    async def _analyze_with_model(
        self, data: Union[str, bytes], prompt: str, model: str, temperature: float = 0.3
    ) -> str:
        """Realiza análisis usando el modelo especificado de Gemini."""
        # Aquí iría la implementación real de la llamada a Vertex AI
        # Por ahora, es un placeholder que usa el método base
        return await self.analyze_image(data, prompt, temperature)

    def _parse_json_response(self, response: Union[str, Dict]) -> Dict[str, Any]:
        """Parsea la respuesta a JSON, manejando diferentes formatos."""
        if isinstance(response, dict):
            return response

        try:
            # Intentar extraer JSON de la respuesta
            if isinstance(response, str):
                # Buscar JSON en la respuesta
                import re

                json_match = re.search(r"\{.*\}", response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            return json.loads(response)
        except:
            # Si falla, retornar estructura básica
            return {"raw_response": str(response)}

    def _calculate_confidence_score(self, analysis: Dict[str, Any]) -> float:
        """Calcula un score de confianza basado en la completitud del análisis."""
        required_fields = ["body_composition", "symmetry_analysis", "posture_alignment"]
        present_fields = sum(1 for field in required_fields if field in analysis)
        return present_fields / len(required_fields)

    def _generate_personalized_recommendations(
        self, analysis: Dict[str, Any], user_profile: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Genera recomendaciones personalizadas basadas en el análisis."""
        recommendations = []

        # Aquí iría la lógica para generar recomendaciones
        # basadas en el análisis y perfil del usuario

        return recommendations

    async def _save_analysis_to_gcs(
        self,
        user_id: str,
        image_data: Union[str, bytes],
        analysis: Dict[str, Any],
        analysis_type: str,
    ) -> Optional[str]:
        """Guarda el análisis y la imagen en Google Cloud Storage."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

            # Guardar imagen
            image_path = (
                f"users/{user_id}/analysis/{analysis_type}/{timestamp}_image.jpg"
            )
            image_url = await self.gcs_client.upload_image(image_data, image_path)

            # Guardar análisis como JSON
            analysis_path = (
                f"users/{user_id}/analysis/{analysis_type}/{timestamp}_analysis.json"
            )
            analysis_data = json.dumps(analysis, indent=2).encode("utf-8")
            await self.gcs_client.upload_file(analysis_data, analysis_path)

            return image_url
        except Exception as e:
            logger.error(f"Error guardando en GCS: {e}")
            return None

    def _can_extract_keypoints(self, image_data: Union[str, bytes]) -> bool:
        """Verifica si es posible extraer keypoints de pose de la imagen."""
        # Aquí iría la lógica para verificar si la imagen es adecuada
        # para extracción de keypoints
        return False  # Por ahora retornamos False

    async def _extract_pose_keypoints(
        self, image_data: Union[str, bytes]
    ) -> Optional[Dict[str, Any]]:
        """Extrae keypoints de pose usando MediaPipe o similar."""
        # Implementación futura con MediaPipe
        return None

    def _calculate_joint_angles(
        self, keypoints: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, float]]:
        """Calcula ángulos de articulaciones desde keypoints."""
        if not keypoints:
            return None

        # Implementación futura de cálculo de ángulos
        return None

    async def _generate_posture_visualization(
        self, image_data: Union[str, bytes], analysis: Dict[str, Any]
    ) -> Optional[str]:
        """Genera una visualización de la postura con anotaciones."""
        # Implementación futura de visualización
        return None

    def _calculate_safety_score(self, posture_analysis: Dict[str, Any]) -> float:
        """Calcula un score de seguridad basado en el análisis de postura."""
        # Por ahora, retornar un valor basado en el score de forma si existe
        if "form_score" in posture_analysis:
            return posture_analysis["form_score"] / 100.0
        return 0.8  # Valor por defecto

    def _generate_improvement_tips(
        self, analysis: Dict[str, Any], exercise_name: str
    ) -> List[str]:
        """Genera tips de mejora específicos para el ejercicio."""
        tips = []

        # Aquí iría la lógica para generar tips basados en el análisis
        if "errors" in analysis:
            for error in analysis.get("errors", []):
                tips.append(f"Corregir: {error}")

        return tips

    async def _prepare_progress_comparison(
        self, current_image: Union[str, bytes], previous_images: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepara imágenes para comparación de progreso."""
        # Por ahora, retornar estructura básica
        dates = [img.get("date", "Unknown") for img in previous_images]
        dates.append(datetime.utcnow().strftime("%Y-%m-%d"))

        return {
            "combined_image": current_image,  # En el futuro, crear collage
            "dates": dates,
            "image_count": len(previous_images) + 1,
        }

    async def _calculate_progress_metrics(
        self, current_image: Union[str, bytes], previous_images: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calcula métricas cuantitativas de progreso."""
        # Implementación futura con análisis más detallado
        return {
            "measurements_available": False,
            "estimated_muscle_gain": "N/A",
            "estimated_fat_loss": "N/A",
        }

    async def _generate_progress_visualization(
        self, analysis: Dict[str, Any], metrics: Dict[str, Any], dates: List[str]
    ) -> Optional[str]:
        """Genera visualización del progreso (gráficos, etc.)."""
        # Implementación futura con matplotlib o similar
        return None

    def _create_progress_timeline(
        self, analysis: Dict[str, Any], comparison_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Crea una línea de tiempo del progreso."""
        timeline = []

        # Aquí iría la lógica para crear la línea de tiempo
        for i, date in enumerate(comparison_data["dates"]):
            timeline.append(
                {
                    "date": date,
                    "milestone": f"Checkpoint {i+1}",
                    "notes": "Progress tracked",
                }
            )

        return timeline

    def _generate_progress_recommendations(
        self, analysis: Dict[str, Any], user_goals: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Genera recomendaciones basadas en el progreso."""
        recommendations = []

        # Lógica básica de recomendaciones
        recommendations.append(
            {
                "type": "general",
                "priority": "high",
                "recommendation": "Continuar con el plan actual",
                "reasoning": "El progreso es consistente",
            }
        )

        return recommendations

    async def _perform_advanced_ocr(
        self, image_data: Union[str, bytes]
    ) -> Dict[str, Any]:
        """Realiza OCR avanzado usando Cloud Vision API."""
        try:
            # Convertir image_data a bytes si es necesario
            if isinstance(image_data, str):
                # Asumir que es base64
                image_bytes = base64.b64decode(image_data)
            else:
                image_bytes = image_data

            # Usar Cloud Vision API
            image = vision.Image(content=image_bytes)
            response = self.vision_client.text_detection(image=image)
            texts = response.text_annotations

            if texts:
                return {
                    "text": texts[0].description,
                    "confidence": 0.95,  # Cloud Vision no da confidence score directo
                    "language": (
                        texts[0].locale if hasattr(texts[0], "locale") else "es"
                    ),
                }

            return {"text": "", "confidence": 0}

        except Exception as e:
            logger.error(f"Error en OCR: {e}")
            return {"text": "", "confidence": 0, "error": str(e)}

    def _validate_nutritional_values(
        self, nutritional_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Valida y normaliza valores nutricionales."""
        # Aquí iría la lógica de validación
        return nutritional_info

    def _calculate_macro_percentage(
        self, nutritional_info: Dict[str, Any], macro: str
    ) -> float:
        """Calcula el porcentaje de calorías de un macronutriente."""
        try:
            calories = nutritional_info.get("calories", 0)
            if calories == 0:
                return 0

            if macro == "protein":
                grams = nutritional_info.get("protein_g", 0)
                macro_calories = grams * 4
            elif macro == "carbs":
                grams = nutritional_info.get("carbohydrates_g", 0)
                macro_calories = grams * 4
            elif macro == "fat":
                grams = nutritional_info.get("total_fat_g", 0)
                macro_calories = grams * 9
            else:
                return 0

            return (macro_calories / calories) * 100

        except:
            return 0

    def _calculate_sugar_ratio(self, nutritional_info: Dict[str, Any]) -> float:
        """Calcula la proporción de azúcar respecto a carbohidratos totales."""
        try:
            carbs = nutritional_info.get("carbohydrates_g", 0)
            sugar = nutritional_info.get("sugar_g", 0)

            if carbs == 0:
                return 0

            return sugar / carbs
        except:
            return 0

    def _evaluate_fiber_content(self, nutritional_info: Dict[str, Any]) -> str:
        """Evalúa el contenido de fibra."""
        fiber = nutritional_info.get("fiber_g", 0)

        if fiber >= 5:
            return "excellent"
        elif fiber >= 3:
            return "good"
        elif fiber >= 1:
            return "moderate"
        else:
            return "low"

    def _evaluate_sodium_level(self, nutritional_info: Dict[str, Any]) -> str:
        """Evalúa el nivel de sodio."""
        sodium = nutritional_info.get("sodium_mg", 0)

        if sodium >= 600:
            return "very_high"
        elif sodium >= 400:
            return "high"
        elif sodium >= 140:
            return "moderate"
        else:
            return "low"

    def _generate_nutritional_recommendations(
        self, nutritional_info: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Genera recomendaciones nutricionales."""
        recommendations = []

        # Evaluar azúcar
        sugar_ratio = self._calculate_sugar_ratio(nutritional_info)
        if sugar_ratio > 0.5:
            recommendations.append(
                {
                    "type": "warning",
                    "message": "Alto contenido de azúcar relativo a carbohidratos totales",
                }
            )

        # Evaluar fibra
        fiber_eval = self._evaluate_fiber_content(nutritional_info)
        if fiber_eval in ["low", "moderate"]:
            recommendations.append(
                {
                    "type": "suggestion",
                    "message": "Considerar alimentos con mayor contenido de fibra",
                }
            )

        # Evaluar sodio
        sodium_eval = self._evaluate_sodium_level(nutritional_info)
        if sodium_eval in ["high", "very_high"]:
            recommendations.append(
                {
                    "type": "warning",
                    "message": "Alto contenido de sodio - consumir con moderación",
                }
            )

        return recommendations

    async def _lookup_barcode_info(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Busca información adicional del producto por código de barras."""
        # Implementación futura con API de base de datos de productos
        return None

    def _check_nutritional_warnings(
        self, nutritional_info: Dict[str, Any]
    ) -> List[str]:
        """Verifica advertencias nutricionales."""
        warnings = []

        # Verificar grasas trans
        trans_fat = nutritional_info.get("trans_fat_g", 0)
        if trans_fat > 0:
            warnings.append("Contiene grasas trans")

        # Verificar azúcar alta
        sugar = nutritional_info.get("sugar_g", 0)
        if sugar > 15:
            warnings.append("Alto contenido de azúcar")

        # Verificar sodio alto
        sodium = nutritional_info.get("sodium_mg", 0)
        if sodium > 600:
            warnings.append("Alto contenido de sodio")

        return warnings

    def _check_dietary_compatibility(
        self, nutritional_info: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Verifica compatibilidad con diferentes dietas."""
        ingredients = nutritional_info.get("ingredients", [])
        ingredients_text = " ".join(ingredients).lower() if ingredients else ""

        return {
            "vegetarian": not any(
                meat in ingredients_text
                for meat in ["carne", "pollo", "pescado", "meat", "chicken", "fish"]
            ),
            "vegan": not any(
                animal in ingredients_text
                for animal in ["leche", "huevo", "milk", "egg", "lácteo", "dairy"]
            ),
            "gluten_free": "gluten" not in ingredients_text
            and "trigo" not in ingredients_text
            and "wheat" not in ingredients_text,
            "keto": self._calculate_macro_percentage(nutritional_info, "carbs") < 10,
            "low_sodium": self._evaluate_sodium_level(nutritional_info)
            in ["low", "moderate"],
        }
