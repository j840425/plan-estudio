"""
Nodos de validación: Validador Global y nodos de salida.
"""
from src.state import GraphState, MIN_BOOKS_PER_STAGE
from src.config.llm_config import get_llm


def validador_global(state: GraphState) -> GraphState:
    """
    Nodo 9: Valida la calidad y coherencia del plan de estudio completo.

    Este nodo realiza una validación holística del plan después de que todas las
    etapas tienen libros asignados. Utiliza un LLM para evaluar cuatro aspectos clave:

    1. Coherencia: ¿Las etapas se construyen lógicamente una sobre otra?
    2. Completitud: ¿El plan cubre el tema de manera integral?
    3. Balance: ¿Hay buena distribución de dificultad y progresión?
    4. Calidad de recursos: ¿Los libros son de alta calidad suficiente?

    El LLM proporciona una puntuación de 1-10 y retroalimentación específica. Si la
    puntuación es baja (<6) o se detectan palabras como "critical" o "major issue"
    en el feedback, se identifican como problemas críticos que pueden requerir
    replantear el plan.

    La retroalimentación y score se agregan a validation_feedback para que el nodo
    de decisión decision_validacion determine si se debe replantear, forzar salida,
    o formatear el plan final.

    Campos del estado que LEE:
        - topic: Tema del plan
        - study_plan_structure: Estructura completa de etapas
        - books_by_stage: Libros asignados por etapa
        - user_level: Nivel del usuario

    Campos del estado que MODIFICA:
        - validation_iterations: Incrementa el contador
        - validation_feedback: Agrega score y problemas críticos detectados

    Args:
        state: Estado actual del grafo

    Returns:
        GraphState: Estado actualizado con validation_feedback y contador incrementado

    Raises:
        Exception: Si hay error, marca validación como "completed with warnings"
    """
    print("\n[Validador_Global] Validando plan completo")

    llm = get_llm(temperature=0.5)

    topic = state["topic"]
    stages = state["study_plan_structure"]
    books_by_stage = state.get("books_by_stage", {})

    # Preparar resumen para validación
    plan_summary = []
    for stage_name, stage_info in stages.items():
        num_books = len(books_by_stage.get(stage_name, []))
        avg_rating = 0
        if num_books > 0:
            ratings = [b['rating'] for b in books_by_stage[stage_name]]
            avg_rating = sum(ratings) / len(ratings)

        plan_summary.append(
            f"- {stage_name}: {num_books} books, avg rating: {avg_rating:.1f}"
        )

    prompt = f"""Evalúa este plan de aprendizaje para "{topic}":

Estructura del plan:
{chr(10).join(plan_summary)}

Total de etapas: {len(stages)}
Nivel del usuario: {state.get('user_level', 'beginner')}

Evalúa:
1. Coherencia: ¿Las etapas se construyen de forma lógica una sobre otra?
2. Completitud: ¿Esto cubre el tema de manera integral?
3. Balance: ¿Hay una buena distribución de dificultad?
4. Calidad de libros: ¿Hay suficientes recursos de alta calidad?

Identifica cualquier problema crítico que requiera reestructurar el plan.
Proporciona una puntuación de calidad del 1 al 10 y retroalimentación específica."""

    try:
        response = llm.invoke(prompt)

        validation_text = response.content if hasattr(response, 'content') else str(response)
        print(f"[Validador_Global] Feedback recibido")

        # Extraer score si está presente
        import re
        score_match = re.search(r'(\d+)/10|score[:\s]+(\d+)', validation_text, re.IGNORECASE)
        quality_score = 7  # default
        if score_match:
            quality_score = int(score_match.group(1) or score_match.group(2))

        # Identificar problemas críticos
        critical_issues = []
        if "critical" in validation_text.lower() or "major issue" in validation_text.lower():
            critical_issues.append("Critical issues detected in plan structure")

        if quality_score < 6:
            critical_issues.append(f"Low quality score: {quality_score}/10")

        # Actualizar estado
        state["validation_iterations"] = state.get("validation_iterations", 0) + 1
        feedback_list = state.get("validation_feedback", [])
        feedback_list.append(f"Validation {state['validation_iterations']}: Score {quality_score}/10")

        if critical_issues:
            feedback_list.extend(critical_issues)

        state["validation_feedback"] = feedback_list

        print(f"[Validador_Global] Score: {quality_score}/10")
        if critical_issues:
            print(f"[Validador_Global] Problemas: {len(critical_issues)}")

    except Exception as e:
        print(f"[Validador_Global] Error: {e}")
        state["validation_iterations"] = state.get("validation_iterations", 0) + 1
        state["validation_feedback"] = state.get("validation_feedback", [])
        state["validation_feedback"].append(f"Validation {state['validation_iterations']}: Completed with warnings")

    return state


def formateador_salida(state: GraphState) -> GraphState:
    """
    Nodo 10: Genera el documento final del plan de estudio y lo guarda en un archivo.

    Este nodo toma toda la información recopilada (etapas, libros, duraciones, objetivos)
    y genera un documento de texto formateado y estructurado que se guarda automáticamente
    en un archivo. El documento incluye:

    - Header con título y nivel del estudiante
    - Duración total estimada del plan (suma de todas las etapas)
    - Roadmap visual con lista numerada de etapas
    - Detalle completo de cada etapa:
        * Descripción
        * Duración estimada
        * Prerrequisitos
        * Objetivos de aprendizaje (máximo 5)
        * Libros recomendados con título, autor, año, rating y justificación
    - Consejos finales para el estudiante
    - Footer con información de generación

    El documento se guarda en el campo final_output del estado y automáticamente
    se escribe en un archivo .txt con el nombre basado en el tema.

    Campos del estado que LEE:
        - topic: Tema del plan (usado también para nombre del archivo)
        - user_level: Nivel del estudiante
        - study_plan_structure: Diccionario completo de etapas
        - books_by_stage: Libros organizados por etapa

    Campos del estado que MODIFICA:
        - final_output: Se establece con el documento formateado completo

    Args:
        state: Estado actual del grafo

    Returns:
        GraphState: Estado actualizado con final_output conteniendo el documento completo
    """
    print("\n[Formateador_Salida] Generando documento final")

    topic = state["topic"]
    level = state.get("user_level", "beginner")
    stages = state["study_plan_structure"]
    books_by_stage = state.get("books_by_stage", {})

    # Generar documento formateado
    output_lines = []

    # Header
    output_lines.append("=" * 80)
    output_lines.append(f"PLAN DE ESTUDIO: {topic.upper()}")
    output_lines.append("=" * 80)
    output_lines.append("")
    output_lines.append(f"Nivel del estudiante: {level.capitalize()}")
    output_lines.append(f"Total de etapas: {len(stages)}")
    output_lines.append("")

    # Calcular duración total
    total_weeks = 0
    for stage_info in stages.values():
        duration = stage_info.get('duration', '4 weeks')
        # Extraer número
        import re
        weeks_match = re.search(r'(\d+)', duration)
        if weeks_match:
            weeks = int(weeks_match.group(1))
            if 'month' in duration.lower():
                weeks *= 4
            total_weeks += weeks

    output_lines.append(f"Duración total estimada: {total_weeks} semanas ({total_weeks//4} meses)")
    output_lines.append("")
    output_lines.append("-" * 80)

    # Roadmap visual
    output_lines.append("\nROADMAP DE APRENDIZAJE")
    output_lines.append("-" * 80)
    for i, (stage_name, stage_info) in enumerate(stages.items(), 1):
        output_lines.append(f"\n{i}. {stage_name}")
        output_lines.append(f"   Duración: {stage_info.get('duration', 'N/A')}")
        num_books = len(books_by_stage.get(stage_name, []))
        output_lines.append(f"   Recursos: {num_books} libros recomendados")

    output_lines.append("\n" + "=" * 80)

    # Detalle de cada etapa
    for i, (stage_name, stage_info) in enumerate(stages.items(), 1):
        output_lines.append(f"\n\nETAPA {i}: {stage_name}")
        output_lines.append("=" * 80)

        # Descripción
        output_lines.append(f"\nDescripción:")
        output_lines.append(f"  {stage_info.get('description', 'N/A')}")

        # Duración
        output_lines.append(f"\nDuración estimada: {stage_info.get('duration', 'N/A')}")

        # Prerrequisitos
        prereqs = stage_info.get('prerequisites', [])
        if prereqs and prereqs != ['None']:
            output_lines.append(f"\nPrerrequisitos:")
            for prereq in prereqs:
                output_lines.append(f"  - {prereq}")

        # Objetivos
        objectives = stage_info.get('objectives', [])
        if objectives:
            output_lines.append(f"\nObjetivos de aprendizaje:")
            for obj in objectives[:5]:  # Max 5
                output_lines.append(f"  - {obj}")

        # Libros recomendados
        books = books_by_stage.get(stage_name, [])
        if books:
            output_lines.append(f"\nLibros recomendados ({len(books)}):")
            output_lines.append("")

            for j, book in enumerate(books, 1):
                output_lines.append(f"  {j}. \"{book['title']}\"")
                output_lines.append(f"     Autor: {book['author']}")
                if book.get('year'):
                    output_lines.append(f"     Año: {book['year']}")
                output_lines.append(f"     Rating: {book['rating']:.1f}/5.0 ({book['num_reviews']} reviews)")
                output_lines.append(f"     Por qué se recomienda: {book['reason'][:150]}")
                output_lines.append("")
        else:
            output_lines.append(f"\n⚠ No se encontraron libros para esta etapa")

        output_lines.append("-" * 80)

    # Consejos finales
    output_lines.append("\n\nCONSEJOS FINALES")
    output_lines.append("=" * 80)
    output_lines.append("- Sigue el orden de las etapas para un aprendizaje progresivo")
    output_lines.append("- Complementa los libros con práctica y proyectos")
    output_lines.append("- Ajusta el ritmo según tu disponibilidad de tiempo")
    output_lines.append("- Busca comunidades y foros para resolver dudas")
    output_lines.append("")
    output_lines.append(f"Plan generado con Gemini 2.5 Flash + Google Search")
    output_lines.append("=" * 80)

    final_output = "\n".join(output_lines)
    state["final_output"] = final_output

    # Guardar automáticamente en archivo (a menos que esté deshabilitado)
    if not state.get("_skip_auto_save", False):
        import re
        from datetime import datetime

        print("\nGenerando archivo...")

        # Generar nombre de archivo seguro basado en el tema
        safe_topic = re.sub(r'[^\w\s-]', '', topic).strip().replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"plan_estudio_{safe_topic}_{timestamp}.txt"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(final_output)
            print(f"Archivo: {filename} generado")
        except Exception as e:
            print(f"⚠ Error al guardar archivo: {e}")

    return state


def salida_forzada(state: GraphState) -> GraphState:
    """
    Nodo 11: Genera salida con disclaimer cuando se alcanzan límites de iteración.

    Este nodo se ejecuta cuando el workflow alcanza los límites máximos de búsqueda
    o validación (MAX_BOOK_SEARCHES_PER_STAGE, MAX_VALIDATION_CYCLES) sin lograr
    la calidad ideal. En lugar de fallar o quedar en loop infinito, genera un plan
    con los recursos disponibles pero agrega un disclaimer prominente al inicio.

    El disclaimer advierte al usuario que:
    - El plan fue generado con recursos limitados
    - Se alcanzaron límites de búsqueda/validación
    - Algunas etapas pueden tener menos libros de los recomendados
    - Se sugiere complementar con búsqueda manual adicional

    Internamente, primero genera el disclaimer, luego llama a formateador_salida()
    que genera el documento base (sin guardar archivo todavía), y finalmente
    guarda el documento completo con disclaimer en un archivo.

    Campos del estado que LEE:
        - Todos los leídos por formateador_salida() (topic, user_level, etc.)

    Campos del estado que MODIFICA:
        - final_output: Se establece con el documento formateado precedido por disclaimer

    Args:
        state: Estado actual del grafo

    Returns:
        GraphState: Estado actualizado con final_output conteniendo disclaimer + documento
    """
    print("\n[Salida_Forzada] Generando salida con recursos limitados")

    # Guardar referencia al topic antes de llamar formateador
    topic = state["topic"]

    # Usar el formateador normal pero deshabilitando guardado automático temporalmente
    # guardando el flag en el estado
    temp_flag = state.get("_skip_auto_save", False)
    state["_skip_auto_save"] = True

    state = formateador_salida(state)

    # Restaurar flag
    state["_skip_auto_save"] = temp_flag

    # Agregar disclaimer al inicio
    disclaimer = """
⚠⚠⚠ ADVERTENCIA ⚠⚠⚠
Este plan fue generado con recursos limitados debido a que se alcanzaron
los límites máximos de búsqueda o validación. Algunas etapas pueden tener
menos libros de los recomendados.

Se sugiere complementar con búsqueda manual de recursos adicionales.

"""

    state["final_output"] = disclaimer + state["final_output"]

    # Guardar archivo con disclaimer incluido
    import re
    from datetime import datetime

    print("\nGenerando archivo (con limitaciones)...")

    safe_topic = re.sub(r'[^\w\s-]', '', topic).strip().replace(' ', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"plan_estudio_{safe_topic}_{timestamp}_LIMITED.txt"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(state["final_output"])
        print(f"Archivo: {filename} generado (recursos limitados)")
    except Exception as e:
        print(f"⚠ Error al guardar archivo: {e}")

    return state
