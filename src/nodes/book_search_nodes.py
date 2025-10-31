"""
Nodos de búsqueda de libros: Investigador y Validador de Calidad.
"""
import math
from src.state import GraphState, BookInfo, MIN_BOOKS_PER_STAGE
from src.utils.web_search import (
    search_books_for_topic,
    validate_book_quality,
    search_specific_book_rating
)


def investigador_libros(state: GraphState) -> GraphState:
    """
    Nodo 6: Busca libros recomendados para la etapa actual usando Google Search grounding.

    Este nodo utiliza la funcionalidad de Google Search grounding de Vertex AI para
    buscar libros relevantes y de alta calidad para la etapa que se está procesando.
    La búsqueda considera tanto el tema general como el nombre específico de la etapa
    para encontrar recursos apropiados.

    Para cada libro encontrado, calcula un score ponderado usando la fórmula:
        score = rating * log(num_reviews + 1)

    Esto balancea la calidad (rating) con la popularidad/confiabilidad (reviews).

    Los libros encontrados se guardan temporalmente en book_candidates[etapa] para
    ser validados posteriormente por el nodo validador_calidad. También incrementa
    el contador book_search_iterations.

    Campos del estado que LEE:
        - stage_being_processed: Nombre de la etapa actual
        - topic: Tema general del plan
        - book_search_iterations: Contador actual (para logging)

    Campos del estado que MODIFICA:
        - book_candidates: Agrega lista de libros candidatos para la etapa
        - book_search_iterations: Incrementa el contador

    Args:
        state: Estado actual del grafo

    Returns:
        GraphState: Estado actualizado con book_candidates y contador incrementado

    Raises:
        Exception: Si hay error en la búsqueda, guarda lista vacía y continúa
    """
    stage = state.get("stage_being_processed")
    if not stage:
        return state

    print(f"\n[Investigador_Libros] Buscando libros para: {stage}")

    topic = state["topic"]
    iterations = state.get("book_search_iterations", 0)

    # Realizar búsqueda
    try:
        books_found = search_books_for_topic(topic, stage)

        print(f"[Investigador_Libros] Encontrados {len(books_found)} libros candidatos")

        # Convertir a formato BookInfo
        book_candidates = []
        for book in books_found:
            if 'title' in book and book['title']:
                # Calcular score ponderado
                rating = book.get('rating', 0.0)
                num_reviews = book.get('num_reviews', 1)
                score = rating * math.log(max(num_reviews, 1) + 1)

                # DEBUG: Mostrar primer libro para verificar
                if len(book_candidates) == 0:
                    print(f"[DEBUG] Primer libro: {book['title'][:50]}, Rating: {rating}, Reviews: {num_reviews}")

                book_info: BookInfo = {
                    'title': book['title'],
                    'author': book.get('author', 'Unknown'),
                    'year': book.get('year'),
                    'rating': rating,
                    'num_reviews': num_reviews,
                    'reason': book.get('reason', 'Recommended for this topic'),
                    'score': score
                }
                book_candidates.append(book_info)

        # Guardar candidatos temporales en el estado
        if 'book_candidates' not in state:
            state['book_candidates'] = {}
        state['book_candidates'][stage] = book_candidates

        # Incrementar contador
        state["book_search_iterations"] = iterations + 1

    except Exception as e:
        print(f"[Investigador_Libros] Error: {e}")
        state['book_candidates'] = state.get('book_candidates', {})
        state['book_candidates'][stage] = []
        state["book_search_iterations"] = iterations + 1

    return state


def validador_calidad(state: GraphState) -> GraphState:
    """
    Nodo 7: Valida la calidad de los libros candidatos y selecciona los mejores.

    Este nodo filtra los libros candidatos de la etapa actual aplicando un umbral
    de calidad mínimo (quality_threshold, típicamente 4.0/5.0). Solo los libros
    con rating >= threshold pasan el filtro.

    Si después del filtrado quedan pocos libros (menos de MIN_BOOKS_PER_STAGE = 2)
    y el threshold es mayor a 3.5, se aplica un threshold más permisivo (threshold - 0.3)
    para aumentar las opciones disponibles.

    Los libros que pasan el filtro se ordenan por su score ponderado (rating * log(reviews))
    de mayor a menor, y se seleccionan los top 3-5 mejores libros. Estos se guardan
    finalmente en books_by_stage[etapa].

    Campos del estado que LEE:
        - stage_being_processed: Nombre de la etapa actual
        - book_candidates: Diccionario con candidatos por etapa
        - quality_threshold: Umbral mínimo de rating (típicamente 4.0)

    Campos del estado que MODIFICA:
        - books_by_stage: Agrega los libros seleccionados para la etapa
                         (inicializa el diccionario si no existe)

    Args:
        state: Estado actual del grafo

    Returns:
        GraphState: Estado actualizado con books_by_stage conteniendo libros validados
    """
    stage = state.get("stage_being_processed")
    if not stage:
        return state

    print(f"\n[Validador_Calidad] Validando libros para: {stage}")

    threshold = state.get("quality_threshold", 4.0)
    candidates = state.get('book_candidates', {}).get(stage, [])

    # Filtrar por calidad
    quality_books = [book for book in candidates if validate_book_quality(book, threshold)]

    print(f"[Validador_Calidad] {len(quality_books)} libros cumplen threshold de {threshold}")

    # Si hay pocos libros de calidad, bajar threshold ligeramente
    if len(quality_books) < MIN_BOOKS_PER_STAGE and threshold > 3.5:
        print(f"[Validador_Calidad] Ajustando threshold a {threshold - 0.3}")
        quality_books = [book for book in candidates
                        if validate_book_quality(book, threshold - 0.3)]

    # Ordenar por score
    quality_books.sort(key=lambda x: x['score'], reverse=True)

    # Seleccionar top 3-5
    selected_books = quality_books[:5]

    # Actualizar estado
    if "books_by_stage" not in state:
        state["books_by_stage"] = {}

    state["books_by_stage"][stage] = selected_books

    print(f"[Validador_Calidad] Seleccionados {len(selected_books)} libros")

    return state


def detector_gaps(state: GraphState) -> GraphState:
    """
    Nodo 8: Detecta gaps y problemas en la cobertura de libros de la etapa actual.

    Este nodo analiza los libros asignados a la etapa actual y detecta tres tipos
    de problemas que podrían requerir búsquedas adicionales:

    1. Cobertura insuficiente: Si hay menos de MIN_BOOKS_PER_STAGE (2) libros
    2. Calidad baja: Si hay libros con rating < 3.8
    3. Confiabilidad dudosa: Si más de la mitad de los libros tienen < 50 reviews

    Cada problema detectado se agrega como un gap a la lista knowledge_gaps del
    estado, con un mensaje descriptivo del problema. Estos gaps son considerados
    posteriormente por el nodo de decisión decision_busqueda_libros para determinar
    si se debe reintentar la búsqueda.

    Si no se detectan gaps, simplemente imprime un mensaje de confirmación.

    Campos del estado que LEE:
        - stage_being_processed: Nombre de la etapa actual
        - books_by_stage: Libros asignados a cada etapa
        - knowledge_gaps: Lista actual de gaps (para agregar nuevos)

    Campos del estado que MODIFICA:
        - knowledge_gaps: Agrega nuevos gaps detectados en la etapa actual

    Args:
        state: Estado actual del grafo

    Returns:
        GraphState: Estado actualizado con knowledge_gaps expandidos si hay problemas
    """
    print("\n[Detector_Gaps] Analizando cobertura de libros")

    stage = state.get("stage_being_processed")
    if not stage:
        return state

    books = state.get("books_by_stage", {}).get(stage, [])
    gaps = state.get("knowledge_gaps", [])

    # Detectar problemas
    new_gaps = []

    # 1. Etapas sin suficientes libros
    if len(books) < MIN_BOOKS_PER_STAGE:
        gap = f"La etapa '{stage}' necesita más libros (actualmente {len(books)})"
        new_gaps.append(gap)
        print(f"[Detector_Gaps] {gap}")

    # 2. Libros con rating muy bajo
    low_rated = [b for b in books if b['rating'] < 3.8]
    if low_rated:
        gap = f"Algunos libros en '{stage}' tienen calificaciones bajas"
        new_gaps.append(gap)
        print(f"[Detector_Gaps] {gap}")

    # 3. Falta de reviews (poco confiables)
    low_reviews = [b for b in books if b['num_reviews'] < 50]
    if len(low_reviews) > len(books) // 2:
        gap = f"Muchos libros en '{stage}' carecen de suficientes reseñas"
        new_gaps.append(gap)
        print(f"[Detector_Gaps] {gap}")

    # Actualizar gaps
    if new_gaps:
        state["knowledge_gaps"] = gaps + new_gaps
    else:
        print("[Detector_Gaps] No se detectaron gaps en esta etapa")

    return state
