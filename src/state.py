"""
Estado compartido del grafo agéntico para el sistema de planes de estudio.
"""
from typing import TypedDict, List, Dict, Optional


class BookInfo(TypedDict):
    """
    Información estructurada de un libro recomendado para el plan de estudio.

    Esta clase TypedDict define el formato estándar para almacenar información
    sobre libros encontrados durante la búsqueda. Incluye metadatos del libro
    y métricas de calidad usadas para ranking y selección.

    Attributes:
        title: Título completo del libro
        author: Nombre del autor o autores principales
        year: Año de publicación (puede ser None si no está disponible)
        rating: Calificación promedio del libro en escala 0-5
        num_reviews: Número total de reseñas o calificaciones
        reason: Justificación de por qué se recomienda este libro para la etapa específica
        score: Score ponderado calculado como rating * log(num_reviews + 1).
               Usado para ordenar libros por calidad y popularidad.
    """
    title: str
    author: str
    year: Optional[str]
    rating: float
    num_reviews: int
    reason: str  # Por qué se recomienda
    score: float  # Score ponderado


class StageInfo(TypedDict):
    """
    Información estructurada de una etapa del plan de estudio.

    Cada etapa representa una fase del aprendizaje con objetivos específicos,
    duración estimada y prerrequisitos. Las etapas se ordenan secuencialmente
    para construir conocimiento de forma progresiva.

    Attributes:
        description: Descripción detallada de lo que se aprenderá en esta etapa (1-2 oraciones)
        duration: Duración estimada de la etapa (ej: "4 semanas", "2 meses")
        prerequisites: Lista de conocimientos o etapas previas necesarias.
                      Puede contener ["None"] para la primera etapa.
        objectives: Lista de objetivos de aprendizaje específicos que el estudiante
                   debe lograr al completar esta etapa (típicamente 3-5 objetivos)
    """
    description: str
    duration: str  # ej: "4 semanas"
    prerequisites: List[str]
    objectives: List[str]


class GraphState(TypedDict):
    """
    Estado global compartido entre todos los nodos del grafo agéntico.

    Este TypedDict define la estructura completa del estado que se pasa
    entre todos los nodos del workflow. Contiene la entrada del usuario,
    estructuras de datos intermedias, contadores de control, y el output final.

    El estado se modifica incrementalmente por cada nodo mientras avanza
    por el grafo, permitiendo que los nodos subsecuentes accedan a los
    resultados de nodos anteriores.

    Attributes:
        topic: Tema u objetivo de aprendizaje proporcionado por el usuario
        user_level: Nivel de experiencia ("beginner", "intermediate", "advanced")

        knowledge_gaps: Lista de áreas de conocimiento o brechas identificadas
                       durante el análisis del tema
        study_plan_structure: Diccionario que mapea nombres de etapas a su información.
                             Estructura: {nombre_etapa: StageInfo}
        books_by_stage: Libros seleccionados finales organizados por etapa.
                       Estructura: {nombre_etapa: [BookInfo, BookInfo, ...]}
        book_candidates: Candidatos temporales de libros durante la búsqueda,
                        antes de la validación final por etapa

        book_search_iterations: Contador de iteraciones de búsqueda de libros
                               para la etapa actual
        validation_iterations: Contador de ciclos de validación global realizados
        plan_refinement_iterations: Contador de veces que se ha refinado/replanificado
                                   la estructura del plan

        quality_threshold: Umbral mínimo de rating (típicamente 4.0 de 5.0)
                          para considerar un libro como de calidad suficiente

        stage_being_processed: Nombre de la etapa que se está procesando actualmente,
                              o None si no hay etapa en proceso
        all_stages_covered: Flag que indica si todas las etapas ya tienen
                           suficientes libros asignados

        final_output: Documento final formateado con el plan completo de estudio
        validation_feedback: Lista de mensajes de retroalimentación generados
                           durante las validaciones (útil para debugging y refinamiento)
    """
    # Input del usuario
    topic: str

    # Información del usuario
    user_level: str  # "beginner", "intermediate", "advanced"

    # Análisis y estructura
    knowledge_gaps: List[str]
    study_plan_structure: Dict[str, StageInfo]  # {stage_name: StageInfo}
    books_by_stage: Dict[str, List[BookInfo]]  # {stage_name: [BookInfo]}
    book_candidates: Dict[str, List[BookInfo]]  # Candidatos temporales por etapa

    # Control de iteraciones
    book_search_iterations: int
    validation_iterations: int
    plan_refinement_iterations: int

    # Configuración
    quality_threshold: float  # 4.0 rating mínimo

    # Estado actual
    stage_being_processed: Optional[str]
    all_stages_covered: bool

    # Output final
    final_output: str
    validation_feedback: List[str]  # Feedback de validaciones


# Constantes de límites del workflow
# Estas constantes controlan los límites de iteración para evitar ciclos infinitos
# y garantizar que el workflow termine en tiempo razonable

MAX_BOOK_SEARCHES_PER_STAGE = 3
"""Número máximo de intentos de búsqueda de libros por etapa antes de aceptar resultados actuales"""

MAX_VALIDATION_CYCLES = 5
"""Número máximo de ciclos de validación global antes de forzar la salida con disclaimer"""

MAX_PLAN_REFINEMENTS = 2
"""Número máximo de veces que se puede replantear/refinar la estructura del plan completo"""

MIN_BOOKS_PER_STAGE = 2
"""Número mínimo de libros requeridos por etapa para considerar la cobertura suficiente"""

QUALITY_THRESHOLD = 4.0
"""Umbral de calidad mínimo (rating de 0-5) para considerar un libro como recomendable"""
