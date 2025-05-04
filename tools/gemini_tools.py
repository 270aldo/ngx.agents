"""
Habilidades basadas en Gemini API.

Este módulo implementa skills que utilizan la API de Gemini para
generar texto, responder preguntas y analizar contenido.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from prototipo.clients.gemini_client import gemini_client
from prototipo.core.skill import Skill, skill_registry


class GeminiChatInput(BaseModel):
    """Esquema de entrada para la skill de chat con Gemini."""
    prompt: str = Field(..., description="Texto de entrada para generar la respuesta")
    temperature: float = Field(0.7, description="Control de aleatoriedad (0.0-1.0)")
    max_tokens: int = Field(1024, description="Longitud máxima de la respuesta")
    context: Optional[str] = Field(None, description="Contexto adicional para la generación")
    history: Optional[List[Dict[str, str]]] = Field(None, description="Historial de conversación")


class GeminiChatOutput(BaseModel):
    """Esquema de salida para la skill de chat con Gemini."""
    text: str = Field(..., description="Texto generado")
    usage: Dict[str, int] = Field(default_factory=dict, description="Información de uso de tokens")


class GeminiChatSkill(Skill):
    """
    Skill para generar texto utilizando Gemini.
    
    Permite enviar prompts a Gemini y obtener respuestas generadas.
    """
    
    def __init__(self):
        """Inicializa la skill de chat con Gemini."""
        super().__init__(
            name="gemini_chat",
            description="Genera texto utilizando el modelo Gemini de Google",
            version="1.0.0",
            input_schema=GeminiChatInput,
            output_schema=GeminiChatOutput,
            categories=["nlp", "generation", "ai"],
            is_async=True
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la generación de texto con Gemini.
        
        Args:
            input_data: Datos de entrada validados
            
        Returns:
            Texto generado y metadatos
        """
        # Extraer parámetros
        prompt = input_data["prompt"]
        temperature = input_data.get("temperature", 0.7)
        max_tokens = input_data.get("max_tokens", 1024)
        context = input_data.get("context")
        history = input_data.get("history")
        
        # Construir prompt completo si hay contexto
        full_prompt = prompt
        if context:
            full_prompt = f"{prompt}\n\nContexto: {context}"
        
        # Ejecutar generación
        if history:
            # Usar el modo chat si hay historial
            text = await gemini_client.chat(history + [{"role": "user", "content": full_prompt}], temperature)
        else:
            # Usar generación simple
            text = await gemini_client.generate_text(
                full_prompt,
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        
        # Construir resultado
        return {
            "text": text,
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(text.split()),
                "total_tokens": len(prompt.split()) + len(text.split())
            }
        }


class GeminiSummarizeInput(BaseModel):
    """Esquema de entrada para la skill de resumen con Gemini."""
    text: str = Field(..., description="Texto a resumir")
    max_words: int = Field(100, description="Longitud máxima aproximada del resumen en palabras")
    language: str = Field("es", description="Idioma del resumen")


class GeminiSummarizeOutput(BaseModel):
    """Esquema de salida para la skill de resumen con Gemini."""
    summary: str = Field(..., description="Resumen generado")
    word_count: int = Field(..., description="Número de palabras en el resumen")


class GeminiSummarizeSkill(Skill):
    """
    Skill para resumir textos utilizando Gemini.
    
    Genera resúmenes concisos de textos largos.
    """
    
    def __init__(self):
        """Inicializa la skill de resumen con Gemini."""
        super().__init__(
            name="gemini_summarize",
            description="Resume textos largos utilizando el modelo Gemini de Google",
            version="1.0.0",
            input_schema=GeminiSummarizeInput,
            output_schema=GeminiSummarizeOutput,
            categories=["nlp", "summarization", "ai"],
            is_async=True
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el resumen de texto con Gemini.
        
        Args:
            input_data: Datos de entrada validados
            
        Returns:
            Resumen generado y metadatos
        """
        # Extraer parámetros
        text = input_data["text"]
        max_words = input_data.get("max_words", 100)
        language = input_data.get("language", "es")
        
        # Construir prompt
        prompt = f"""
        Resume el siguiente texto en aproximadamente {max_words} palabras en {language},
        manteniendo los puntos clave y la información más relevante:
        
        {text}
        """
        
        # Ejecutar generación
        summary = await gemini_client.generate_text(
            prompt,
            temperature=0.3,
            max_output_tokens=max_words * 5
        )
        
        # Contar palabras
        word_count = len(summary.split())
        
        # Construir resultado
        return {
            "summary": summary,
            "word_count": word_count
        }


class GeminiAnalyzeIntentInput(BaseModel):
    """Esquema de entrada para la skill de análisis de intención con Gemini."""
    text: str = Field(..., description="Texto a analizar")
    categories: Optional[List[str]] = Field(None, description="Categorías para clasificar")


class GeminiAnalyzeIntentOutput(BaseModel):
    """Esquema de salida para la skill de análisis de intención con Gemini."""
    intent: str = Field(..., description="Intención principal detectada")
    confidence: float = Field(..., description="Confianza en la detección (0.0-1.0)")
    categories: Dict[str, float] = Field(default_factory=dict, description="Puntuaciones por categoría")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="Entidades detectadas")


class GeminiAnalyzeIntentSkill(Skill):
    """
    Skill para analizar la intención en textos utilizando Gemini.
    
    Detecta la intención principal, entidades y categorías en un texto.
    """
    
    def __init__(self):
        """Inicializa la skill de análisis de intención con Gemini."""
        super().__init__(
            name="gemini_analyze_intent",
            description="Analiza la intención en textos utilizando el modelo Gemini de Google",
            version="1.0.0",
            input_schema=GeminiAnalyzeIntentInput,
            output_schema=GeminiAnalyzeIntentOutput,
            categories=["nlp", "analysis", "ai"],
            is_async=True
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el análisis de intención con Gemini.
        
        Args:
            input_data: Datos de entrada validados
            
        Returns:
            Análisis de intención y metadatos
        """
        # Extraer parámetros
        text = input_data["text"]
        categories = input_data.get("categories", [])
        
        # Construir prompt
        prompt = f"""
        Analiza la siguiente entrada de texto y determina:
        1. La intención principal
        2. El nivel de confianza (0.0-1.0)
        3. Entidades relevantes (personas, lugares, organizaciones, etc.)
        
        Devuelve un JSON con la siguiente estructura:
        {{
          "intent": "categoría de la intención",
          "confidence": float entre 0 y 1,
          "entities": [lista de entidades con tipo y valor],
          "categories": {{puntuaciones por categoría}}
        }}
        
        Texto: {text}
        """
        
        if categories:
            prompt += f"\n\nCategorías a considerar: {', '.join(categories)}"
        
        # Ejecutar generación
        result_text = await gemini_client.generate_text(prompt, temperature=0.1)
        
        # Extraer JSON de la respuesta
        try:
            import json
            import re
            
            # Buscar el primer { y el último }
            json_match = re.search(r'({.*})', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
            else:
                # Fallback si no se encuentra JSON válido
                result = {
                    "intent": "unknown",
                    "confidence": 0.0,
                    "entities": [],
                    "categories": {}
                }
                
            # Asegurarse de que todas las categorías solicitadas estén presentes
            if categories:
                for cat in categories:
                    if cat not in result.get("categories", {}):
                        result.setdefault("categories", {})[cat] = 0.0
            
            return result
            
        except Exception as e:
            # Fallback en caso de error
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "entities": [],
                "categories": {cat: 0.0 for cat in categories} if categories else {},
                "error": str(e)
            }


class GeminiTranslateInput(BaseModel):
    """Esquema de entrada para la skill de traducción con Gemini."""
    text: str = Field(..., description="Texto a traducir")
    target_language: str = Field(..., description="Idioma destino (código ISO o nombre del idioma)")
    source_language: Optional[str] = Field(None, description="Idioma origen (si se deja vacío, se detectará automáticamente)")
    preserve_formatting: bool = Field(True, description="Mantener el formato del texto original")


class GeminiTranslateOutput(BaseModel):
    """Esquema de salida para la skill de traducción con Gemini."""
    translated_text: str = Field(..., description="Texto traducido")
    detected_source_language: Optional[str] = Field(None, description="Idioma origen detectado (si no se especificó)")
    character_count: int = Field(..., description="Número de caracteres en el texto traducido")


class GeminiTranslateSkill(Skill):
    """
    Skill para traducir textos utilizando Gemini.
    
    Traduce texto entre diferentes idiomas manteniendo el contexto y significado.
    """
    
    def __init__(self):
        """Inicializa la skill de traducción con Gemini."""
        super().__init__(
            name="gemini_translate",
            description="Traduce texto entre diferentes idiomas utilizando el modelo Gemini de Google",
            version="1.0.0",
            input_schema=GeminiTranslateInput,
            output_schema=GeminiTranslateOutput,
            categories=["nlp", "translation", "ai"],
            is_async=True
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la traducción de texto con Gemini.
        
        Args:
            input_data: Datos de entrada validados
            
        Returns:
            Texto traducido y metadatos
        """
        # Extraer parámetros
        text = input_data["text"]
        target_language = input_data["target_language"]
        source_language = input_data.get("source_language")
        preserve_formatting = input_data.get("preserve_formatting", True)
        
        # Construir prompt para la traducción
        prompt = "Traduce el siguiente texto"
        
        if source_language:
            prompt += f" del {source_language}"
        
        prompt += f" al {target_language}."
        
        if preserve_formatting:
            prompt += " Mantén el formato original del texto, incluyendo párrafos, listas y estilos."
        
        prompt += f"\n\nTexto a traducir: {text}"
        
        # Ejecutar generación
        translated_text = await gemini_client.generate_text(
            prompt,
            temperature=0.1,  # Baja temperatura para traducciones más precisas
            max_output_tokens=2048
        )
        
        # Detección del idioma de origen si no se especificó
        detected_source = None
        if not source_language:
            detect_prompt = f"Detecta el idioma del siguiente texto y responde solo con el nombre del idioma en español: '{text[:100]}'"  # Primeros 100 caracteres para detección
            detected_source = await gemini_client.generate_text(detect_prompt, temperature=0.1, max_output_tokens=20)
            # Limpiar la respuesta (podría tener información adicional)
            detected_source = detected_source.strip().split('\n')[0].replace('.', '').strip()
        
        # Construir resultado
        return {
            "translated_text": translated_text,
            "detected_source_language": detected_source,
            "character_count": len(translated_text)
        }


# Registrar las skills
skill_registry.register_skill(GeminiChatSkill())
skill_registry.register_skill(GeminiSummarizeSkill())
skill_registry.register_skill(GeminiAnalyzeIntentSkill())
skill_registry.register_skill(GeminiTranslateSkill())

# Habilidades para análisis de sentimiento
class GeminiSentimentAnalysisInput(BaseModel):
    """Esquema de entrada para la skill de análisis de sentimiento con Gemini."""
    text: str = Field(..., description="Texto a analizar")
    detailed: bool = Field(False, description="Si es True, incluye análisis detallado de emociones")


class GeminiSentimentAnalysisOutput(BaseModel):
    """Esquema de salida para la skill de análisis de sentimiento con Gemini."""
    sentiment: str = Field(..., description="Sentimiento general: positivo, negativo o neutral")
    score: float = Field(..., description="Puntuación de sentimiento (-1.0 a 1.0)")
    confidence: float = Field(..., description="Confianza en la detección (0.0-1.0)")
    dominant_emotion: str = Field(..., description="Emoción dominante detectada")
    emotions: Optional[Dict[str, float]] = Field(None, description="Puntuaciones detalladas por emoción")


class GeminiSentimentAnalysisSkill(Skill):
    """
    Skill para analizar el sentimiento en textos utilizando Gemini.
    
    Detecta el tono emocional, polaridad y emociones dominantes en un texto.
    """
    
    def __init__(self):
        """Inicializa la skill de análisis de sentimiento con Gemini."""
        super().__init__(
            name="gemini_sentiment_analysis",
            description="Analiza el sentimiento y emociones en textos utilizando el modelo Gemini de Google",
            version="1.0.0",
            input_schema=GeminiSentimentAnalysisInput,
            output_schema=GeminiSentimentAnalysisOutput,
            categories=["nlp", "analysis", "sentiment", "ai"],
            is_async=True
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el análisis de sentimiento con Gemini.
        
        Args:
            input_data: Datos de entrada validados
            
        Returns:
            Análisis de sentimiento y metadatos
        """
        # Extraer parámetros
        text = input_data["text"]
        detailed = input_data.get("detailed", False)
        
        # Ejecutar análisis
        result = await gemini_client.analyze_sentiment(text, detailed)
        
        return result

# Habilidades para análisis de imágenes
class GeminiImageAnalysisInput(BaseModel):
    """Esquema de entrada para la skill de análisis de imágenes con Gemini."""
    image_path: str = Field(..., description="Ruta a la imagen a analizar")
    prompt: str = Field(..., description="Qué analizar o buscar en la imagen")


class GeminiImageAnalysisOutput(BaseModel):
    """Esquema de salida para la skill de análisis de imágenes con Gemini."""
    analysis: str = Field(..., description="Análisis descriptivo de la imagen")


class GeminiImageAnalysisSkill(Skill):
    """
    Skill para analizar imágenes utilizando Gemini.
    
    Permite extraer información visual, describir contenido y responder preguntas sobre imágenes.
    """
    
    def __init__(self):
        """Inicializa la skill de análisis de imágenes con Gemini."""
        super().__init__(
            name="gemini_image_analysis",
            description="Analiza y extrae información de imágenes utilizando el modelo Gemini Pro Vision de Google",
            version="1.0.0",
            input_schema=GeminiImageAnalysisInput,
            output_schema=GeminiImageAnalysisOutput,
            categories=["vision", "image", "analysis", "ai"],
            is_async=True
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el análisis de imagen con Gemini.
        
        Args:
            input_data: Datos de entrada validados
            
        Returns:
            Análisis de la imagen
        """
        # Extraer parámetros
        image_path = input_data["image_path"]
        prompt = input_data["prompt"]
        
        # Ejecutar análisis
        analysis = await gemini_client.analyze_image(image_path, prompt)
        
        return {
            "analysis": analysis
        }

# Habilidades para análisis de documentos PDFs
class GeminiPdfAnalysisInput(BaseModel):
    """Esquema de entrada para la skill de análisis de PDFs con Gemini."""
    pdf_path: str = Field(..., description="Ruta al archivo PDF a analizar")
    prompt: str = Field(..., description="Instrucción sobre qué analizar en el PDF")
    max_pages: int = Field(5, description="Número máximo de páginas a procesar")


class GeminiPdfAnalysisOutput(BaseModel):
    """Esquema de salida para la skill de análisis de PDFs con Gemini."""
    analysis: str = Field(..., description="Análisis del contenido del PDF")


class GeminiPdfAnalysisSkill(Skill):
    """
    Skill para analizar documentos PDF utilizando Gemini.
    
    Permite extraer información, responder preguntas y analizar el contenido de documentos PDF.
    """
    
    def __init__(self):
        """Inicializa la skill de análisis de PDFs con Gemini."""
        super().__init__(
            name="gemini_pdf_analysis",
            description="Analiza documentos PDF utilizando el modelo Gemini de Google",
            version="1.0.0",
            input_schema=GeminiPdfAnalysisInput,
            output_schema=GeminiPdfAnalysisOutput,
            categories=["document", "pdf", "analysis", "ai"],
            is_async=True
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el análisis de PDF con Gemini.
        
        Args:
            input_data: Datos de entrada validados
            
        Returns:
            Análisis del PDF
        """
        # Extraer parámetros
        pdf_path = input_data["pdf_path"]
        prompt = input_data["prompt"]
        max_pages = input_data.get("max_pages", 5)
        
        # Ejecutar análisis
        analysis = await gemini_client.analyze_pdf(pdf_path, prompt, max_pages)
        
        return {
            "analysis": analysis
        }

# Habilidades para análisis de CSVs
class GeminiCsvAnalysisInput(BaseModel):
    """Esquema de entrada para la skill de análisis de CSVs con Gemini."""
    csv_path: str = Field(..., description="Ruta al archivo CSV a analizar")
    prompt: str = Field(..., description="Instrucción sobre qué analizar en el CSV")
    sample_rows: int = Field(5, description="Número de filas a incluir como muestra")


class GeminiCsvAnalysisOutput(BaseModel):
    """Esquema de salida para la skill de análisis de CSVs con Gemini."""
    analysis: str = Field(..., description="Análisis del contenido del CSV")


class GeminiCsvAnalysisSkill(Skill):
    """
    Skill para analizar archivos CSV utilizando Gemini.
    
    Permite extraer insights, patrones y estadísticas de datos tabulares.
    """
    
    def __init__(self):
        """Inicializa la skill de análisis de CSVs con Gemini."""
        super().__init__(
            name="gemini_csv_analysis",
            description="Analiza datos tabulares en formato CSV utilizando el modelo Gemini de Google",
            version="1.0.0",
            input_schema=GeminiCsvAnalysisInput,
            output_schema=GeminiCsvAnalysisOutput,
            categories=["data", "csv", "analysis", "ai"],
            is_async=True
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el análisis de CSV con Gemini.
        
        Args:
            input_data: Datos de entrada validados
            
        Returns:
            Análisis del CSV
        """
        # Extraer parámetros
        csv_path = input_data["csv_path"]
        prompt = input_data["prompt"]
        sample_rows = input_data.get("sample_rows", 5)
        
        # Ejecutar análisis
        analysis = await gemini_client.analyze_csv(csv_path, prompt, sample_rows)
        
        return {
            "analysis": analysis
        }

# Registrar las nuevas skills
skill_registry.register_skill(GeminiSentimentAnalysisSkill())
skill_registry.register_skill(GeminiImageAnalysisSkill())
skill_registry.register_skill(GeminiPdfAnalysisSkill())
skill_registry.register_skill(GeminiCsvAnalysisSkill())
