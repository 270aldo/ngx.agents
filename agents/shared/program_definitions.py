"""
Definiciones detalladas de los programas ofrecidos por NGX.

Este módulo centraliza las definiciones de los diferentes programas (PRIME, LONGEVITY, etc.)
para garantizar consistencia en cómo todos los agentes entienden y trabajan con estos programas.
"""

from typing import Dict, List, Any, Optional, Tuple

# Definiciones completas de los programas
PROGRAM_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "PRIME": {
        "name": "PRIME",
        "title": "Programa de Optimización Biológica para Ejecutivos",
        "description": "Programa especializado para ejecutivos y profesionales de alto rendimiento que buscan convertir su biología en una ventaja competitiva profesional.",
        "age_range": (30, 55),
        "target_audience": [
            "Ejecutivos de alto nivel",
            "Empresarios",
            "Profesionales de alto rendimiento",
            "Líderes",
            "Tomadores de decisiones",
            "Personas con carreras exigentes y alto nivel de responsabilidad",
        ],
        "objective": "Convertir la biología en ventaja competitiva profesional",
        "pillars": [
            "Optimización biológica avanzada",
            "Neuro-resiliencia ejecutiva",
            "Implementación estratégica",
        ],
        "user_characteristics": [
            "Carreras exigentes",
            "Alto nivel de responsabilidad",
            "Poco tiempo libre",
            "Necesidad de rendimiento cognitivo óptimo",
            "Exposición constante a estrés",
            "Viajes frecuentes",
            "Horarios irregulares",
        ],
        "user_needs": [
            "Optimización del rendimiento",
            "Eficiencia en tiempo",
            "Manejo del estrés",
            "Prevención y longevidad",
            "Energía sostenible",
            "Claridad mental",
            "Resiliencia",
        ],
        "key_protocols": {
            "training": [
                "Entrenamiento de precisión ejecutiva (30-45 min)",
                "Sesiones de alta eficiencia",
                "Enfoque en fuerza y potencia neural",
                "Protocolos de resistencia estratégica",
            ],
            "nutrition": [
                "Nutrición estratégica",
                "Protocolos de alimentación para optimización cognitiva",
                "Suplementación personalizada",
                "Estrategias de timing nutricional",
            ],
            "recovery": [
                "Optimización del sueño",
                "Técnicas de recuperación acelerada",
                "Manejo de estrés avanzado",
                "Protocolos de regeneración celular",
            ],
            "biohacking": [
                "Biohacking avanzado",
                "Monitoreo de biomarcadores",
                "Optimización hormonal",
                "Técnicas de mejora cognitiva",
                "Protocolos de longevidad preventiva",
            ],
        },
        "keywords": [
            "executive",
            "entrepreneur",
            "leader",
            "manager",
            "ceo",
            "founder",
            "high performer",
            "professional",
            "negocios",
            "business",
            "ejecutivo",
            "empresario",
            "líder",
            "director",
            "gerente",
            "fundador",
            "alto rendimiento",
            "executive performance",
            "rendimiento ejecutivo",
            "cognitive optimization",
            "optimizacion cognitiva",
            "resilience",
            "resiliencia",
            "biohacking",
            "peak performance",
            "leadership",
            "liderazgo",
            "decision making",
            "toma decisiones",
            "stress management",
            "manejo estres",
            "focus",
            "enfoque",
            "clarity",
            "claridad",
            "eficiencia",
            "efficiency",
            "productividad",
            "productivity",
        ],
    },
    "LONGEVITY": {
        "name": "LONGEVITY",
        "title": "Programa de Longevidad y Vitalidad",
        "description": "Programa especializado para adultos mayores enfocado en mantener independencia, funcionalidad y calidad de vida a través de intervenciones basadas en evidencia.",
        "age_range": (55, 100),
        "target_audience": [
            "Adultos mayores de 55 años",
            "Personas preocupadas por el envejecimiento saludable",
            "Individuos buscando mantener independencia funcional",
            "Personas con historial familiar de enfermedades relacionadas con la edad",
        ],
        "objective": "Revitalizar cuerpo, fortalecer mente y expandir vida",
        "pillars": [
            "Salud muscular",
            "Función cognitiva",
            "Movilidad funcional",
            "Prevención de declive",
        ],
        "user_characteristics": [
            "Etapa de vida enfocada en mantener independencia",
            "Preocupación por pérdida de capacidades",
            "Posibles condiciones crónicas existentes",
            "Cambios hormonales relacionados con la edad",
            "Cambios en composición corporal",
        ],
        "user_needs": [
            "Funcionalidad",
            "Movilidad",
            "Prevención de enfermedades",
            "Salud cognitiva",
            "Energía y vitalidad",
            "Independencia",
            "Calidad de vida",
        ],
        "key_protocols": {
            "training": [
                "Enfoque 'Muscle-First'",
                "Entrenamiento de fuerza adaptado",
                "Ejercicios de movilidad y equilibrio",
                "Protocolos de resistencia cardiovascular moderada",
            ],
            "nutrition": [
                "Nutrición pro-muscular",
                "Estrategias anti-inflamatorias",
                "Optimización de proteínas",
                "Nutrientes neuroprotectores",
            ],
            "recovery": [
                "Protocolos de recuperación adaptados",
                "Optimización del sueño para adultos mayores",
                "Técnicas de manejo de dolor",
                "Estrategias de regeneración tisular",
            ],
            "biohacking": [
                "Entrenamiento neurocognitivo integrado",
                "Monitoreo de biomarcadores de envejecimiento",
                "Intervenciones hormonales apropiadas para la edad",
                "Protocolos de longevidad basados en evidencia",
            ],
        },
        "keywords": [
            "longevity",
            "longevidad",
            "aging",
            "envejecimiento",
            "senior",
            "elderly",
            "adulto mayor",
            "tercera edad",
            "retirement",
            "jubilación",
            "functional independence",
            "independencia funcional",
            "cognitive health",
            "salud cognitiva",
            "muscle health",
            "salud muscular",
            "bone health",
            "salud ósea",
            "mobility",
            "movilidad",
            "balance",
            "equilibrio",
            "fall prevention",
            "prevención de caídas",
            "vitality",
            "vitalidad",
            "quality of life",
            "calidad de vida",
            "healthy aging",
            "envejecimiento saludable",
        ],
    },
    "STRENGTH": {
        "name": "STRENGTH",
        "title": "Programa de Desarrollo de Fuerza",
        "description": "Programa especializado en el desarrollo de fuerza máxima y potencia.",
        "age_range": None,  # Aplicable a cualquier edad con adaptaciones
        "target_audience": [
            "Personas interesadas en aumentar su fuerza",
            "Practicantes de powerlifting",
            "Atletas de fuerza",
            "Individuos buscando mejorar su rendimiento físico",
        ],
        "objective": "Desarrollar fuerza máxima y potencia",
        "pillars": [
            "Progresión de carga",
            "Técnica óptima",
            "Periodización efectiva",
            "Recuperación adecuada",
        ],
        "key_protocols": {
            "training": [
                "Entrenamientos con cargas altas",
                "Baja-media repetición",
                "Enfoque en levantamientos compuestos",
                "Progresión sistemática de carga",
            ],
            "nutrition": [
                "Nutrición enfocada en rendimiento",
                "Optimización de proteínas",
                "Estrategias de nutrición peri-entrenamiento",
            ],
        },
        "keywords": [
            "fuerza",
            "strength",
            "powerlifting",
            "strongman",
            "power",
            "potencia",
            "levantamiento",
            "lifting",
            "carga",
            "load",
            "peso",
            "weight",
        ],
    },
    "HYPERTROPHY": {
        "name": "HYPERTROPHY",
        "title": "Programa de Desarrollo Muscular",
        "description": "Programa especializado en el crecimiento muscular y mejora estética.",
        "age_range": None,  # Aplicable a cualquier edad con adaptaciones
        "target_audience": [
            "Personas interesadas en aumentar su masa muscular",
            "Culturistas",
            "Individuos buscando mejorar su composición corporal",
            "Personas interesadas en estética física",
        ],
        "objective": "Aumentar masa muscular y mejorar composición corporal",
        "pillars": [
            "Volumen de entrenamiento óptimo",
            "Estimulación muscular efectiva",
            "Nutrición para crecimiento",
            "Recuperación adecuada",
        ],
        "key_protocols": {
            "training": [
                "Volumen moderado-alto",
                "Rango medio de repeticiones (8-15)",
                "Variedad de ejercicios",
                "Técnicas de intensificación",
            ],
            "nutrition": [
                "Superávit calórico moderado",
                "Alta ingesta de proteínas",
                "Nutrición peri-entrenamiento optimizada",
            ],
        },
        "keywords": [
            "hipertrofia",
            "hypertrophy",
            "muscle",
            "músculo",
            "bodybuilding",
            "fisicoculturismo",
            "masa muscular",
            "muscle mass",
            "volumen",
            "volume",
            "estética",
            "aesthetics",
            "composición corporal",
            "body composition",
        ],
    },
    "ENDURANCE": {
        "name": "ENDURANCE",
        "title": "Programa de Resistencia",
        "description": "Programa especializado en resistencia cardiovascular y/o muscular.",
        "age_range": None,  # Aplicable a cualquier edad con adaptaciones
        "target_audience": [
            "Corredores",
            "Ciclistas",
            "Triatletas",
            "Deportistas de resistencia",
            "Personas buscando mejorar su capacidad aeróbica",
        ],
        "objective": "Mejorar capacidad aeróbica, resistencia muscular y rendimiento en eventos de larga duración",
        "pillars": [
            "Desarrollo cardiovascular",
            "Eficiencia energética",
            "Resistencia muscular",
            "Recuperación optimizada",
        ],
        "key_protocols": {
            "training": [
                "Entrenamiento cardiovascular",
                "Intervalos de alta intensidad",
                "Volumen alto con intensidad moderada",
                "Entrenamiento específico por zonas",
            ],
            "nutrition": [
                "Estrategias de nutrición para resistencia",
                "Protocolos de carga de carbohidratos",
                "Hidratación optimizada",
                "Suplementación para resistencia",
            ],
        },
        "keywords": [
            "resistencia",
            "endurance",
            "cardio",
            "cardiovascular",
            "aeróbico",
            "aerobic",
            "maratón",
            "marathon",
            "triatlón",
            "triathlon",
            "running",
            "cycling",
            "ciclismo",
            "natación",
            "swimming",
            "ultra",
        ],
    },
    "ATHLETIC": {
        "name": "ATHLETIC",
        "title": "Programa de Rendimiento Deportivo",
        "description": "Programa especializado en mejorar rendimiento en deportes específicos.",
        "age_range": None,  # Aplicable a cualquier edad con adaptaciones
        "target_audience": [
            "Atletas de diversos deportes",
            "Deportistas competitivos",
            "Personas buscando mejorar habilidades atléticas específicas",
        ],
        "objective": "Desarrollar habilidades atléticas específicas y prevenir lesiones",
        "pillars": [
            "Rendimiento específico al deporte",
            "Desarrollo de habilidades",
            "Prevención de lesiones",
            "Periodización óptima",
        ],
        "key_protocols": {
            "training": [
                "Entrenamiento funcional",
                "Desarrollo de potencia",
                "Trabajo de agilidad y velocidad",
                "Entrenamiento específico al deporte",
            ],
            "nutrition": [
                "Nutrición periodizada según fase de entrenamiento",
                "Estrategias de nutrición para competición",
                "Recuperación nutricional optimizada",
            ],
        },
        "keywords": [
            "atlético",
            "athletic",
            "deporte",
            "sport",
            "competitivo",
            "competitive",
            "performance",
            "rendimiento",
            "habilidad",
            "skill",
            "agilidad",
            "agility",
            "velocidad",
            "speed",
            "potencia",
            "power",
            "específico",
            "specific",
        ],
    },
    "PERFORMANCE": {
        "name": "PERFORMANCE",
        "title": "Programa General de Rendimiento",
        "description": "Programa equilibrado para mejorar rendimiento físico general.",
        "age_range": None,  # Aplicable a cualquier edad con adaptaciones
        "target_audience": [
            "Personas buscando un enfoque equilibrado de fitness",
            "Individuos con múltiples objetivos físicos",
            "Personas que desean mejorar su condición física general",
        ],
        "objective": "Mejorar fuerza, resistencia y composición corporal de forma balanceada",
        "pillars": [
            "Desarrollo físico integral",
            "Equilibrio entre capacidades",
            "Adaptabilidad y variedad",
            "Progresión sostenible",
        ],
        "key_protocols": {
            "training": [
                "Combinación de modalidades de entrenamiento",
                "Equilibrio entre trabajo de fuerza y resistencia",
                "Adaptable a diferentes niveles",
                "Variedad de estímulos",
            ],
            "nutrition": [
                "Nutrición balanceada",
                "Enfoque en alimentos integrales",
                "Hidratación adecuada",
                "Suplementación básica según necesidades",
            ],
        },
        "keywords": [
            "rendimiento",
            "performance",
            "general",
            "balanced",
            "equilibrado",
            "fitness",
            "condición física",
            "physical condition",
            "integral",
            "comprehensive",
            "versatilidad",
            "versatility",
        ],
    },
}


def get_program_definition(program_type: str) -> Dict[str, Any]:
    """
    Obtiene la definición completa de un programa específico.

    Args:
        program_type: Tipo de programa (PRIME, LONGEVITY, etc.)

    Returns:
        Dict[str, Any]: Definición completa del programa
    """
    program_type = program_type.upper()
    if program_type not in PROGRAM_DEFINITIONS:
        raise ValueError(f"Tipo de programa no reconocido: {program_type}")

    return PROGRAM_DEFINITIONS[program_type]


def get_program_keywords(program_type: str) -> List[str]:
    """
    Obtiene las palabras clave asociadas a un programa específico.

    Args:
        program_type: Tipo de programa (PRIME, LONGEVITY, etc.)

    Returns:
        List[str]: Lista de palabras clave
    """
    program_type = program_type.upper()
    if program_type not in PROGRAM_DEFINITIONS:
        raise ValueError(f"Tipo de programa no reconocido: {program_type}")

    return PROGRAM_DEFINITIONS[program_type].get("keywords", [])


def get_age_range(program_type: str) -> Optional[Tuple[int, int]]:
    """
    Obtiene el rango de edad recomendado para un programa específico.

    Args:
        program_type: Tipo de programa (PRIME, LONGEVITY, etc.)

    Returns:
        Optional[Tuple[int, int]]: Rango de edad (min, max) o None si no aplica
    """
    program_type = program_type.upper()
    if program_type not in PROGRAM_DEFINITIONS:
        raise ValueError(f"Tipo de programa no reconocido: {program_type}")

    return PROGRAM_DEFINITIONS[program_type].get("age_range")


def get_all_program_types() -> List[str]:
    """
    Obtiene la lista de todos los tipos de programa disponibles.

    Returns:
        List[str]: Lista de tipos de programa
    """
    return list(PROGRAM_DEFINITIONS.keys())


def get_program_by_age(age: int) -> List[str]:
    """
    Obtiene los programas recomendados para una edad específica.

    Args:
        age: Edad del usuario

    Returns:
        List[str]: Lista de tipos de programa recomendados para esa edad
    """
    recommended_programs = []

    for program_type, definition in PROGRAM_DEFINITIONS.items():
        age_range = definition.get("age_range")
        if age_range is None:
            # Programas sin restricción de edad
            recommended_programs.append(program_type)
        elif isinstance(age_range, tuple) and len(age_range) == 2:
            min_age, max_age = age_range
            if min_age <= age <= max_age:
                recommended_programs.append(program_type)

    return recommended_programs


def is_keyword_match(text: str, program_type: str) -> bool:
    """
    Verifica si un texto contiene palabras clave asociadas a un programa específico.

    Args:
        text: Texto a analizar
        program_type: Tipo de programa (PRIME, LONGEVITY, etc.)

    Returns:
        bool: True si hay coincidencia, False en caso contrario
    """
    program_type = program_type.upper()
    if program_type not in PROGRAM_DEFINITIONS:
        raise ValueError(f"Tipo de programa no reconocido: {program_type}")

    keywords = PROGRAM_DEFINITIONS[program_type].get("keywords", [])
    text = text.lower()

    return any(keyword.lower() in text for keyword in keywords)
