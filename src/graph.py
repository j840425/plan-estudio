"""
Construcción del grafo agéntico con LangGraph.
"""
from langgraph.graph import StateGraph, END
from src.state import GraphState, QUALITY_THRESHOLD

# Importar todos los nodos
from src.nodes.analysis_nodes import analizador_tema, evaluador_nivel
from src.nodes.planning_nodes import (
    estructurador_plan,
    selector_etapa,
    replanificador
)
from src.nodes.book_search_nodes import (
    investigador_libros,
    validador_calidad,
    detector_gaps
)
from src.nodes.validation_nodes import (
    validador_global,
    formateador_salida,
    salida_forzada
)
from src.nodes.decision_nodes import (
    decision_busqueda_libros,
    decision_cobertura_etapas,
    decision_validacion
)


def create_study_plan_graph():
    """
    Crea y configura el grafo completo del workflow agéntico para generar planes de estudio.

    Esta función construye un grafo de flujo de trabajo usando LangGraph que coordina todos los
    nodos del sistema. El grafo implementa tres ciclos principales:
    1. Ciclo de búsqueda de libros por etapa (con reintentos y búsquedas específicas)
    2. Ciclo de cobertura de todas las etapas del plan
    3. Ciclo de validación y refinamiento global

    El flujo completo es:
    - Análisis inicial: Analizar tema → Evaluar nivel de usuario
    - Planificación: Estructurar plan en etapas
    - Búsqueda por etapa: Para cada etapa, buscar libros → validar calidad → detectar gaps
    - Validación global: Validar coherencia del plan completo
    - Salida: Formatear documento final o generar salida forzada con disclaimer

    Returns:
        CompiledGraph: Grafo compilado de LangGraph listo para ejecutar con el método invoke().
                       Requiere un estado inicial de tipo GraphState.

    Examples:
        >>> app = create_study_plan_graph()
        >>> initial_state = initialize_state("Machine Learning", "beginner")
        >>> final_state = app.invoke(initial_state, config={"recursion_limit": 100})
    """
    # Crear el grafo con el estado compartido
    workflow = StateGraph(GraphState)

    # =========================================================================
    # AGREGAR NODOS
    # =========================================================================

    # Nodos de análisis inicial
    workflow.add_node("analizador_tema", analizador_tema)
    workflow.add_node("evaluador_nivel", evaluador_nivel)

    # Nodos de planificación
    workflow.add_node("estructurador_plan", estructurador_plan)
    workflow.add_node("selector_etapa", selector_etapa)
    workflow.add_node("replanificador", replanificador)

    # Nodos de búsqueda de libros
    workflow.add_node("investigador_libros", investigador_libros)
    workflow.add_node("validador_calidad", validador_calidad)
    workflow.add_node("detector_gaps", detector_gaps)

    # Nodos de validación y salida
    workflow.add_node("validador_global", validador_global)
    workflow.add_node("formateador_salida", formateador_salida)
    workflow.add_node("salida_forzada", salida_forzada)

    # =========================================================================
    # DEFINIR FLUJO LINEAL INICIAL
    # =========================================================================

    # Entry point: START → Analizador_Tema
    workflow.set_entry_point("analizador_tema")

    # Flujo inicial: Análisis → Evaluación → Estructuración → Selección
    workflow.add_edge("analizador_tema", "evaluador_nivel")
    workflow.add_edge("evaluador_nivel", "estructurador_plan")
    workflow.add_edge("estructurador_plan", "selector_etapa")

    # =========================================================================
    # CICLO DE BÚSQUEDA DE LIBROS (por etapa)
    # =========================================================================

    # Selector_Etapa → Investigador_Libros
    workflow.add_edge("selector_etapa", "investigador_libros")

    # Investigador → Validador → Detector → Decision_Busqueda
    workflow.add_edge("investigador_libros", "validador_calidad")
    workflow.add_edge("validador_calidad", "detector_gaps")

    # Decision_Busqueda_Libros (CONDICIONAL)
    workflow.add_conditional_edges(
        "detector_gaps",
        decision_busqueda_libros,
        {
            "reintentar_busqueda": "investigador_libros",      # CICLO 1: Reintentar
            "busqueda_especifica": "investigador_libros",       # CICLO 1: Búsqueda refinada
            "aceptar_libros_actuales": "decision_cobertura",   # Siguiente decisión
            "libros_suficientes": "decision_cobertura"          # Siguiente decisión
        }
    )

    # Nodo auxiliar para decisión de cobertura
    workflow.add_node("decision_cobertura", lambda state: state)

    # =========================================================================
    # CICLO DE COBERTURA DE ETAPAS
    # =========================================================================

    # Decision_Cobertura_Etapas (CONDICIONAL)
    workflow.add_conditional_edges(
        "decision_cobertura",
        decision_cobertura_etapas,
        {
            "siguiente_etapa": "selector_etapa",      # CICLO 2: Procesar siguiente etapa
            "validacion_global": "validador_global"   # Ir a validación
        }
    )

    # =========================================================================
    # VALIDACIÓN Y REFINAMIENTO GLOBAL
    # =========================================================================

    # Validador_Global → Decision_Validacion (CONDICIONAL)
    workflow.add_conditional_edges(
        "validador_global",
        decision_validacion,
        {
            "forzar_salida": "salida_forzada",        # Salida con disclaimer
            "replantear": "replanificador",           # CICLO 3: Replantear
            "formatear": "formateador_salida"         # Salida normal
        }
    )

    # Replanificador → Selector_Etapa (vuelve a procesar)
    workflow.add_edge("replanificador", "selector_etapa")

    # =========================================================================
    # NODOS DE SALIDA → END
    # =========================================================================

    workflow.add_edge("formateador_salida", END)
    workflow.add_edge("salida_forzada", END)

    # =========================================================================
    # COMPILAR GRAFO
    # =========================================================================

    app = workflow.compile()

    return app


def initialize_state(topic: str, user_level: str = "beginner") -> GraphState:
    """
    Inicializa el estado del grafo con valores por defecto para comenzar el workflow.

    Crea un diccionario de estado con todos los campos requeridos por GraphState,
    estableciendo valores iniciales vacíos o en cero para todos los contadores,
    colecciones y flags de control.

    Args:
        topic: Tema u objetivo de aprendizaje del usuario (ej: "Machine Learning",
               "Python Programming", "Data Science")
        user_level: Nivel de experiencia del usuario. Debe ser uno de:
                   - "beginner": Principiante sin conocimientos previos
                   - "intermediate": Conocimiento básico del tema
                   - "advanced": Experiencia significativa en el área
                   Por defecto es "beginner".

    Returns:
        GraphState: Diccionario TypedDict con todos los campos inicializados:
                   - Campos de entrada: topic, user_level
                   - Colecciones vacías: knowledge_gaps, study_plan_structure, books_by_stage, etc.
                   - Contadores en 0: book_search_iterations, validation_iterations, etc.
                   - Configuración: quality_threshold con valor de QUALITY_THRESHOLD
                   - Flags: all_stages_covered en False, stage_being_processed en None

    Examples:
        >>> state = initialize_state("Deep Learning", "intermediate")
        >>> state["topic"]
        'Deep Learning'
        >>> state["book_search_iterations"]
        0
    """
    return {
        "topic": topic,
        "user_level": user_level,
        "knowledge_gaps": [],
        "study_plan_structure": {},
        "books_by_stage": {},
        "book_candidates": {},
        "book_search_iterations": 0,
        "validation_iterations": 0,
        "plan_refinement_iterations": 0,
        "quality_threshold": QUALITY_THRESHOLD,
        "stage_being_processed": None,
        "all_stages_covered": False,
        "final_output": "",
        "validation_feedback": []
    }


def run_study_plan_workflow(topic: str, user_level: str = "beginner", verbose: bool = True):
    """
    Ejecuta el workflow completo de generación de plan de estudio personalizado.

    Esta es la función principal de alto nivel que orquesta todo el proceso:
    1. Crea el grafo del workflow
    2. Inicializa el estado con el tema y nivel del usuario
    3. Ejecuta el grafo con límite de recursión aumentado
    4. Retorna el estado final con el plan completo

    El workflow incluye análisis del tema, estructuración del plan en etapas,
    búsqueda de libros recomendados para cada etapa, validación de calidad,
    y generación del documento final formateado.

    Args:
        topic: Tema u objetivo de aprendizaje del usuario. Puede ser amplio (ej: "Data Science")
               o específico (ej: "Neural Networks for Computer Vision").
        user_level: Nivel de experiencia del usuario. Opciones: "beginner", "intermediate", "advanced".
                   Por defecto es "beginner".
        verbose: Si es True, imprime información de progreso y estado en consola durante la ejecución.
                Por defecto es True.

    Returns:
        GraphState: Estado final del grafo conteniendo:
                   - final_output: Documento formateado del plan de estudio completo
                   - study_plan_structure: Estructura de etapas con objetivos y duración
                   - books_by_stage: Libros recomendados organizados por etapa
                   - validation_feedback: Retroalimentación del proceso de validación
                   - Todos los demás campos del estado actualizados

    Raises:
        ValueError: Si el topic está vacío o el user_level no es válido
        Exception: Si hay errores en la configuración de Google Cloud o Vertex AI

    Examples:
        >>> final_state = run_study_plan_workflow("Machine Learning", "beginner", verbose=True)
        >>> print(final_state["final_output"])
        ================================================================================
        PLAN DE ESTUDIO: MACHINE LEARNING
        ================================================================================
        ...
    """
    if verbose:
        print("=" * 80)
        print("SISTEMA AGÉNTICO DE GENERACIÓN DE PLANES DE ESTUDIO")
        print("=" * 80)
        print(f"\nTema: {topic}")
        print(f"Nivel: {user_level}")
        print("\nIniciando workflow...\n")

    # Crear el grafo
    app = create_study_plan_graph()

    # Inicializar estado
    initial_state = initialize_state(topic, user_level)

    # Ejecutar el grafo con límite de recursión aumentado
    final_state = app.invoke(
        initial_state,
        config={"recursion_limit": 100}
    )

    if verbose:
        print("\n" + "=" * 80)
        print("WORKFLOW COMPLETADO")
        print("=" * 80)

    return final_state
