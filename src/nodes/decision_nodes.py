"""
Nodos de decisión condicionales para el flujo del grafo.
"""
from typing import Literal
from src.state import (
    GraphState,
    MAX_BOOK_SEARCHES_PER_STAGE,
    MAX_VALIDATION_CYCLES,
    MAX_PLAN_REFINEMENTS,
    MIN_BOOKS_PER_STAGE
)


def decision_busqueda_libros(state: GraphState) -> Literal[
    "reintentar_busqueda",
    "busqueda_especifica",
    "aceptar_libros_actuales",
    "libros_suficientes"
]:
    """
    Nodo de decisión: Determina si continuar buscando libros o avanzar a la siguiente etapa.

    Este nodo condicional evalúa el estado de la búsqueda de libros para la etapa actual
    y decide la acción apropiada basándose en múltiples criterios. Implementa la lógica
    del primer ciclo del workflow (búsqueda de libros por etapa).

    Lógica de decisión (en orden de evaluación):

    1. Si se alcanzó MAX_BOOK_SEARCHES_PER_STAGE (3 intentos):
       → "aceptar_libros_actuales" (termina búsqueda con lo disponible)

    2. Si hay menos de MIN_BOOKS_PER_STAGE (2) libros:
       → "reintentar_busqueda" (vuelve a investigador_libros)

    3. Si hay gaps relacionados a la etapa actual y quedan intentos:
       → "busqueda_especifica" (búsqueda refinada en investigador_libros)

    4. Si hay suficientes libros (>=2) y calidad aceptable:
       → "libros_suficientes" (avanza a decision_cobertura)

    Campos del estado que LEE:
        - stage_being_processed: Etapa actual
        - book_search_iterations: Contador de intentos de búsqueda
        - books_by_stage: Libros asignados por etapa
        - knowledge_gaps: Lista de gaps para detectar problemas relacionados

    Returns:
        str: Una de las cuatro opciones literales que determina el siguiente nodo:
            - "reintentar_busqueda": Vuelve a investigador_libros (intento general)
            - "busqueda_especifica": Vuelve a investigador_libros (búsqueda refinada)
            - "aceptar_libros_actuales": Va a decision_cobertura (límite alcanzado)
            - "libros_suficientes": Va a decision_cobertura (calidad suficiente)
    """
    stage = state.get("stage_being_processed")
    if not stage:
        return "libros_suficientes"

    iterations = state.get("book_search_iterations", 0)
    books = state.get("books_by_stage", {}).get(stage, [])
    gaps = state.get("knowledge_gaps", [])

    print(f"\n[Decision_Busqueda_Libros] Evaluando: {len(books)} libros, iteración {iterations}")

    # 1. Si se alcanzó el límite de búsquedas
    if iterations >= MAX_BOOK_SEARCHES_PER_STAGE:
        print(f"[Decision] → aceptar_libros_actuales (límite alcanzado)")
        return "aceptar_libros_actuales"

    # 2. Si no hay suficientes libros
    if len(books) < MIN_BOOKS_PER_STAGE:
        print(f"[Decision] → reintentar_busqueda (solo {len(books)} libros)")
        return "reintentar_busqueda"

    # 3. Si hay gaps relacionados a la etapa actual
    stage_related_gaps = [g for g in gaps if stage.lower() in g.lower() or "need" in g.lower()]
    if stage_related_gaps and iterations < MAX_BOOK_SEARCHES_PER_STAGE - 1:
        print(f"[Decision] → busqueda_especifica (gaps detectados)")
        return "busqueda_especifica"

    # 4. Si ya hay suficientes libros
    print(f"[Decision] → libros_suficientes ({len(books)} libros)")
    return "libros_suficientes"


def decision_cobertura_etapas(state: GraphState) -> Literal[
    "siguiente_etapa",
    "validacion_global"
]:
    """
    Nodo de decisión: Determina si procesar más etapas o avanzar a validación global.

    Este nodo condicional evalúa si todas las etapas del plan tienen suficientes libros
    asignados. Implementa la lógica del segundo ciclo del workflow (cobertura de etapas).

    Verifica cada etapa en study_plan_structure para contar cuántos libros tiene en
    books_by_stage. Si alguna etapa tiene menos de MIN_BOOKS_PER_STAGE (2) libros,
    se considera que aún hay etapas sin cobertura suficiente.

    Lógica de decisión:

    1. Si hay etapas con menos de MIN_BOOKS_PER_STAGE libros:
       → "siguiente_etapa" (vuelve a selector_etapa para procesarlas)
       → Actualiza all_stages_covered = False

    2. Si todas las etapas tienen al menos MIN_BOOKS_PER_STAGE libros:
       → "validacion_global" (avanza a validador_global)
       → Actualiza all_stages_covered = True

    Campos del estado que LEE:
        - study_plan_structure: Diccionario de todas las etapas del plan
        - books_by_stage: Libros asignados por etapa

    Campos del estado que MODIFICA:
        - all_stages_covered: Se actualiza según el resultado de la evaluación

    Returns:
        str: Una de las dos opciones literales:
            - "siguiente_etapa": Vuelve a selector_etapa (hay etapas sin cubrir)
            - "validacion_global": Va a validador_global (todas cubiertas)
    """
    stages = state["study_plan_structure"]
    books_by_stage = state.get("books_by_stage", {})

    print(f"\n[Decision_Cobertura_Etapas] Evaluando cobertura")

    # Verificar si todas las etapas tienen al menos MIN_BOOKS_PER_STAGE libros
    uncovered_stages = []
    for stage_name in stages.keys():
        num_books = len(books_by_stage.get(stage_name, []))
        if num_books < MIN_BOOKS_PER_STAGE:
            uncovered_stages.append(stage_name)
            print(f"[Decision] Etapa '{stage_name}' tiene {num_books} libros (necesita {MIN_BOOKS_PER_STAGE})")

    if uncovered_stages:
        print(f"[Decision] → siguiente_etapa ({len(uncovered_stages)} etapas con libros insuficientes)")
        state["all_stages_covered"] = False
        return "siguiente_etapa"
    else:
        print(f"[Decision] → validacion_global (todas las etapas cubiertas)")
        state["all_stages_covered"] = True
        return "validacion_global"


def decision_validacion(state: GraphState) -> Literal[
    "forzar_salida",
    "replantear",
    "formatear"
]:
    """
    Nodo de decisión: Determina qué hacer después de la validación global del plan.

    Este nodo condicional evalúa el feedback de la validación global y decide si el
    plan está listo para formatear, necesita replaneación, o se debe forzar la salida
    por alcanzar límites. Implementa la lógica del tercer ciclo del workflow
    (validación y refinamiento).

    Lógica de decisión (en orden de evaluación):

    1. Si validation_iterations >= MAX_VALIDATION_CYCLES (5):
       → "forzar_salida" (genera salida con disclaimer)

    2. Si hay problemas críticos en validation_feedback
       ("critical", "major issue", "low quality") Y
       refinement_iterations < MAX_PLAN_REFINEMENTS (2):
       → "replantear" (va a replanificador para ajustar estructura)

    3. Si hay etapas con menos de MIN_BOOKS_PER_STAGE libros Y
       refinement_iterations < MAX_PLAN_REFINEMENTS:
       → "replantear" (necesita mejorar cobertura)

    4. Si todo está bien o ya se agotaron los refinamientos:
       → "formatear" (va a formateador_salida para generar documento final)

    Campos del estado que LEE:
        - validation_iterations: Contador de ciclos de validación
        - plan_refinement_iterations: Contador de replaneaciones
        - validation_feedback: Retroalimentación de validación (últimas 3 entradas)
        - study_plan_structure: Etapas del plan
        - books_by_stage: Libros por etapa (para verificar cobertura)

    Returns:
        str: Una de las tres opciones literales:
            - "forzar_salida": Va a salida_forzada (límite alcanzado)
            - "replantear": Va a replanificador (necesita ajustes)
            - "formatear": Va a formateador_salida (listo para output)
    """
    validation_iterations = state.get("validation_iterations", 0)
    refinement_iterations = state.get("plan_refinement_iterations", 0)
    feedback = state.get("validation_feedback", [])

    print(f"\n[Decision_Validacion] Validaciones: {validation_iterations}, Refinamientos: {refinement_iterations}")

    # 1. Si se alcanzó el límite de validaciones
    if validation_iterations >= MAX_VALIDATION_CYCLES:
        print(f"[Decision] → forzar_salida (límite de validaciones)")
        return "forzar_salida"

    # 2. Detectar problemas críticos en el feedback
    critical_issues = False
    recent_feedback = feedback[-3:] if feedback else []

    for fb in recent_feedback:
        if any(word in fb.lower() for word in ["critical", "major issue", "low quality"]):
            critical_issues = True
            break

    # 3. Si hay problemas críticos y aún se puede replantear
    if critical_issues and refinement_iterations < MAX_PLAN_REFINEMENTS:
        print(f"[Decision] → replantear (problemas críticos detectados)")
        return "replantear"

    # 4. Verificar que todas las etapas tengan libros mínimos
    stages = state["study_plan_structure"]
    books_by_stage = state.get("books_by_stage", {})

    insufficient_stages = []
    for stage_name in stages.keys():
        if len(books_by_stage.get(stage_name, [])) < MIN_BOOKS_PER_STAGE:
            insufficient_stages.append(stage_name)

    if insufficient_stages and refinement_iterations < MAX_PLAN_REFINEMENTS:
        print(f"[Decision] → replantear ({len(insufficient_stages)} etapas con pocos libros)")
        return "replantear"

    # 5. Si todo está bien, formatear salida
    print(f"[Decision] → formatear (calidad suficiente)")
    return "formatear"


def should_continue_or_end(state: GraphState) -> Literal["continue", "end"]:
    """
    Función auxiliar de decisión binaria simple: continuar o terminar el grafo.

    Esta función proporciona una decisión binaria básica basada en si ya existe
    un output final generado. Se puede usar en casos donde se necesita una decisión
    condicional simple sin la complejidad de los otros nodos de decisión.

    NOTA: Esta función está definida pero actualmente NO se usa en el grafo principal.
    Se mantiene como utilidad para posibles extensiones futuras o workflows alternativos.

    Campos del estado que LEE:
        - final_output: Documento final del plan (si existe)

    Args:
        state: Estado actual del grafo

    Returns:
        str: Una de las dos opciones literales:
            - "end": Si ya hay final_output generado
            - "continue": Si todavía no hay output final
    """
    if state.get("final_output"):
        return "end"
    return "continue"
