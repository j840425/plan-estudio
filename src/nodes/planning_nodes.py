"""
Nodos de planificación: Estructurador de Plan, Selector de Etapa y Replanificador.
"""
import re
import math
from src.state import GraphState, StageInfo, MAX_PLAN_REFINEMENTS
from src.config.llm_config import get_llm


def estructurador_plan(state: GraphState) -> GraphState:
    """
    Nodo 3: Crea la estructura del plan de estudio organizada en etapas secuenciales.

    Este nodo utiliza un LLM para generar una hoja de ruta de aprendizaje estructurada
    en 3-7 etapas (según complejidad del tema), donde cada etapa tiene nombre, descripción,
    duración estimada, prerrequisitos y objetivos de aprendizaje específicos. Las etapas
    progresan de temas principiantes a avanzados.

    El prompt al LLM incluye restricciones estrictas de formato para facilitar el
    parsing posterior. Se espera que cada etapa comience con "Stage [número]:" y
    siga un formato específico con campos como Duration, Prerequisites, Objectives.

    Si el LLM no responde correctamente o hay error, se genera un plan por defecto
    usando create_default_stages().

    Campos del estado que LEE:
        - topic: Tema del plan de estudio
        - user_level: Nivel del usuario (afecta el enfoque del plan)
        - knowledge_gaps: Áreas a cubrir (máximo primeras 5)

    Campos del estado que MODIFICA:
        - study_plan_structure: Diccionario {nombre_etapa: StageInfo} con 3-7 etapas
        - plan_refinement_iterations: Incrementa el contador
        - books_by_stage: Inicializa como diccionario vacío si no existe

    Args:
        state: Estado actual del grafo

    Returns:
        GraphState: Estado actualizado con la estructura del plan generada
    """
    print("\n[Estructurador_Plan] Creando estructura del plan de estudio")

    llm = get_llm(temperature=0.7)

    topic = state["topic"]
    level = state["user_level"]
    gaps = state.get("knowledge_gaps", [])

    prompt = f"""Crea una hoja de ruta de aprendizaje estructurada para: "{topic}"

Nivel del usuario: {level}
Áreas de conocimiento a cubrir: {', '.join(gaps[:5])}

RESTRICCIONES CRÍTICAS:
1. DEBES crear entre 3 y 7 etapas según la complejidad del tema (ni más, ni menos)
2. Cada etapa DEBE comenzar con "Stage [número]:" donde número es del 1 al 7
3. NO incluyas sub-listas numeradas bajo los objetivos - usa solo viñetas con "-"
4. NO crees fases, niveles o secciones - SOLO etapas numeradas 1-7
5. Progresa de temas principiantes a avanzados
6. Usa más etapas (5-7) para temas complejos, menos etapas (3-4) para temas simples

Para cada etapa proporciona:
- Nombre de etapa (ej: "Fundamentos de {topic}", "Intermedio de {topic}", "Avanzado de {topic}")
- Descripción clara de lo que se aprenderá (1-2 oraciones)
- Duración estimada (ej: "4 semanas", "6 semanas")
- Prerrequisitos necesarios para esta etapa
- Objetivos de aprendizaje (3-5 metas específicas) usando SOLO viñetas que empiecen con "-"

DEBES usar este formato EXACTO (no te desvíes):

Stage 1: Fundamentos de [Tema]
Description: [qué se aprenderá en 1-2 oraciones]
Duration: 4 weeks
Prerequisites: None
Objectives:
- Objetivo 1
- Objetivo 2
- Objetivo 3

Stage 2: Intermedio de [Tema]
Description: [qué se aprenderá en 1-2 oraciones]
Duration: 6 weeks
Prerequisites: Fundamentals
Objectives:
- Objetivo 1
- Objetivo 2

Stage 3: Avanzado de [Tema]
Description: [qué se aprenderá en 1-2 oraciones]
Duration: 8 weeks
Prerequisites: Intermediate knowledge
Objectives:
- Objetivo 1
- Objetivo 2

IMPORTANTE: Crea entre 3 y 7 etapas según la complejidad. No incluyas ningún otro elemento numerado o sub-secciones."""

    try:
        response = llm.invoke(prompt)

        plan_text = response.content if hasattr(response, 'content') else str(response)

        # Parsear las etapas del plan
        stages = parse_stages_from_text(plan_text, topic, level)

        state["study_plan_structure"] = stages
        state["plan_refinement_iterations"] = state.get("plan_refinement_iterations", 0) + 1

        print(f"[Estructurador_Plan] Creadas {len(stages)} etapas")

    except Exception as e:
        print(f"[Estructurador_Plan] Error: {e}")
        # Plan por defecto en caso de error
        stages = create_default_stages(topic, level)
        state["study_plan_structure"] = stages
        state["plan_refinement_iterations"] = 1

    # Inicializar books_by_stage si no existe
    if "books_by_stage" not in state:
        state["books_by_stage"] = {}

    return state


def parse_stages_from_text(text: str, topic: str, level: str) -> dict:
    """
    Parsea el texto de respuesta del LLM para extraer etapas estructuradas del plan.

    Utiliza regex estricto para detectar solo etapas numeradas del 1 al 7 con el
    formato "Stage [1-7]:" o "Phase [1-7]:". Extrae para cada etapa su nombre,
    descripción, duración, prerrequisitos y objetivos.

    El parsing es robusto y maneja diferentes formatos de líneas. Si detecta campos
    como "Duration:", "Prerequisites:", "Objectives:" extrae su valor. Los objetivos
    se identifican como líneas que empiezan con viñetas (-, •, *, o números).

    Si no se puede parsear nada del texto, retorna un plan por defecto usando
    create_default_stages().

    Args:
        text: Texto de respuesta del LLM conteniendo las etapas
        topic: Tema del plan (usado para plan por defecto)
        level: Nivel del usuario (usado para plan por defecto)

    Returns:
        dict: Diccionario {nombre_etapa: StageInfo} con las etapas parseadas.
              Típicamente contiene 3-7 etapas según complejidad del tema.
    """
    stages = {}
    lines = text.split('\n')

    # Regex estricto: solo detecta "Stage [1-7]:" o "Phase [1-7]:" al inicio de línea
    stage_pattern = re.compile(r'^(Stage|Phase)\s+([1-7]):\s*(.+)', re.IGNORECASE)

    current_stage_name = None
    current_stage = {}
    objectives = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detectar nombre de etapa usando regex estricto
        stage_match = stage_pattern.match(line)
        if stage_match:
            # Guardar etapa anterior
            if current_stage_name and current_stage:
                current_stage['objectives'] = objectives
                stages[current_stage_name] = current_stage

            # Nueva etapa
            stage_number = stage_match.group(2)
            current_stage_name = stage_match.group(3).strip()

            current_stage = {
                'description': '',
                'duration': '4 weeks',
                'prerequisites': [],
                'objectives': []
            }
            objectives = []

            print(f"[Parser] Detectada etapa {stage_number}: {current_stage_name}")

        # Extraer información
        elif current_stage_name:
            if 'duration' in line.lower() or 'time' in line.lower():
                # Extraer duración
                duration_match = line.split(':', 1)
                if len(duration_match) > 1:
                    current_stage['duration'] = duration_match[1].strip()

            elif 'prerequisite' in line.lower():
                # Extraer prerequisitos
                prereq_match = line.split(':', 1)
                if len(prereq_match) > 1:
                    current_stage['prerequisites'] = [p.strip() for p in prereq_match[1].split(',')]

            elif 'objective' in line.lower() or 'goal' in line.lower():
                # Siguiente línea puede tener objetivos
                continue

            elif line.startswith(('-', '•', '*')) or line[0].isdigit():
                # Es un objetivo listado
                objectives.append(line.lstrip('-•* 0123456789.'))

            elif 'description' in line.lower():
                desc_match = line.split(':', 1)
                if len(desc_match) > 1:
                    current_stage['description'] = desc_match[1].strip()
            else:
                # Agregar a descripción si está vacía
                if not current_stage['description']:
                    current_stage['description'] = line

    # Guardar última etapa
    if current_stage_name and current_stage:
        current_stage['objectives'] = objectives
        stages[current_stage_name] = current_stage

    # Si no se parseó nada, crear etapas por defecto
    if not stages:
        stages = create_default_stages(topic, level)

    return stages


def create_default_stages(topic: str, level: str) -> dict:
    """
    Crea etapas por defecto cuando falla el parsing del texto del LLM.

    Genera un plan de estudio básico pero funcional basado en el nivel del usuario:
    - Beginner: 3 etapas (Fundamentals, Intermediate, Advanced)
    - Intermediate/Advanced: 2 etapas (Core, Advanced)

    Cada etapa incluye descripción genérica, duración estimada, prerrequisitos
    y objetivos básicos adaptados al tema.

    Args:
        topic: Tema del plan de estudio
        level: Nivel del usuario ("beginner", "intermediate", "advanced")

    Returns:
        dict: Diccionario {nombre_etapa: StageInfo} con etapas por defecto.
              3 etapas para principiantes, 2 para niveles superiores.
    """
    if level == "beginner":
        return {
            f"Fundamentals of {topic}": {
                "description": f"Introduction to basic concepts of {topic}",
                "duration": "4 weeks",
                "prerequisites": ["None"],
                "objectives": [f"Understand core concepts", f"Build foundation"]
            },
            f"Intermediate {topic}": {
                "description": f"Deeper dive into {topic} topics",
                "duration": "6 weeks",
                "prerequisites": ["Fundamentals"],
                "objectives": [f"Apply concepts", f"Solve intermediate problems"]
            },
            f"Advanced {topic}": {
                "description": f"Advanced topics and applications in {topic}",
                "duration": "8 weeks",
                "prerequisites": ["Intermediate knowledge"],
                "objectives": [f"Master advanced concepts", f"Complete projects"]
            }
        }
    else:
        return {
            f"Core {topic}": {
                "description": f"Essential concepts in {topic}",
                "duration": "6 weeks",
                "prerequisites": ["Basic knowledge"],
                "objectives": [f"Consolidate understanding"]
            },
            f"Advanced {topic}": {
                "description": f"Advanced and specialized topics",
                "duration": "8 weeks",
                "prerequisites": ["Core knowledge"],
                "objectives": [f"Expert-level mastery"]
            }
        }


def selector_etapa(state: GraphState) -> GraphState:
    """
    Nodo 4: Selecciona la próxima etapa del plan que necesita búsqueda de libros.

    Este nodo itera sobre las etapas del plan y selecciona la primera que no tiene
    suficientes libros asignados (menos de MIN_BOOKS_PER_STAGE = 2 libros). Actualiza
    el campo stage_being_processed con el nombre de la etapa seleccionada.

    Comportamiento del contador book_search_iterations:
    - SOLO se resetea a 0 cuando cambia la etapa que se está procesando
    - NO se resetea si se continúa con la misma etapa (para permitir reintentos)
    - Esto evita ciclos infinitos de búsqueda en la misma etapa

    Si todas las etapas ya tienen suficientes libros, marca all_stages_covered=True
    y establece stage_being_processed=None, lo que señala al flujo que debe pasar
    a la validación global.

    Campos del estado que LEE:
        - study_plan_structure: Diccionario de etapas del plan
        - books_by_stage: Libros asignados por etapa
        - stage_being_processed: Etapa que se estaba procesando previamente

    Campos del estado que MODIFICA:
        - stage_being_processed: Se actualiza con la próxima etapa o None
        - book_search_iterations: Se resetea a 0 solo si cambió la etapa
        - all_stages_covered: Se marca True si todas las etapas tienen libros suficientes

    Args:
        state: Estado actual del grafo

    Returns:
        GraphState: Estado actualizado con la próxima etapa seleccionada
    """
    print("\n[Selector_Etapa] Seleccionando próxima etapa")

    stages = state["study_plan_structure"]
    books_by_stage = state.get("books_by_stage", {})
    previous_stage = state.get("stage_being_processed")

    # Encontrar primera etapa sin libros o con libros insuficientes
    next_stage = None
    for stage_name in stages.keys():
        if stage_name not in books_by_stage or len(books_by_stage[stage_name]) < 2:
            next_stage = stage_name
            break

    if next_stage:
        # Solo resetear el contador si la etapa cambió
        if next_stage != previous_stage:
            state["book_search_iterations"] = 0
            print(f"[Selector_Etapa] Nueva etapa: {next_stage} (contador reseteado)")
        else:
            print(f"[Selector_Etapa] Continuando con: {next_stage} (iteración {state.get('book_search_iterations', 0)})")

        state["stage_being_processed"] = next_stage
    else:
        state["stage_being_processed"] = None
        state["all_stages_covered"] = True
        print("[Selector_Etapa] Todas las etapas cubiertas")

    return state


def replanificador(state: GraphState) -> GraphState:
    """
    Nodo 5: Ajusta y refina la estructura del plan basado en feedback de validación.

    Este nodo se ejecuta cuando la validación global detecta problemas críticos con
    el plan (etapas con pocos libros, falta de coherencia, etc.). Utiliza un LLM
    para analizar el plan actual, los libros encontrados, y el feedback de validación,
    y sugiere mejoras como:
    - Fusionar o dividir etapas
    - Agregar etapas faltantes
    - Cambiar el orden de las etapas
    - Mejorar nombres de etapas para que sean más claros

    Después de recibir recomendaciones, incrementa el contador de refinamientos y
    resetea el flag all_stages_covered para que el flujo vuelva a procesar las etapas.
    También limpia los libros de etapas que tienen menos de 2 libros para forzar
    nueva búsqueda.

    NOTA: En la implementación actual, las recomendaciones se registran pero no se
    aplican automáticamente. En una implementación completa, se parsearían las
    recomendaciones y se modificaría study_plan_structure.

    Campos del estado que LEE:
        - topic: Tema del plan
        - study_plan_structure: Estructura actual del plan
        - books_by_stage: Libros encontrados por etapa
        - validation_feedback: Retroalimentación de validaciones (últimas 3)

    Campos del estado que MODIFICA:
        - plan_refinement_iterations: Incrementa el contador
        - validation_feedback: Agrega resumen de recomendaciones
        - all_stages_covered: Se resetea a False para reprocesar
        - books_by_stage: Limpia etapas con menos de 2 libros

    Args:
        state: Estado actual del grafo

    Returns:
        GraphState: Estado actualizado con refinamiento registrado y flags reseteados
    """
    print("\n[Replanificador] Ajustando estructura del plan")

    llm = get_llm(temperature=0.6)

    feedback = state.get("validation_feedback", [])
    current_structure = state["study_plan_structure"]
    books = state.get("books_by_stage", {})

    prompt = f"""El plan de aprendizaje actual para "{state['topic']}" necesita refinamiento.

Estructura del plan actual:
{list(current_structure.keys())}

Retroalimentación de validación:
{chr(10).join(feedback[-3:])}

Libros encontrados por etapa:
{', '.join([f"{stage}: {len(books.get(stage, []))} libros" for stage in current_structure.keys()])}

Por favor sugiere mejoras:
1. ¿Deben fusionarse o dividirse algunas etapas?
2. ¿Faltan etapas?
3. ¿Debe cambiar el orden?
4. ¿Los nombres de las etapas son claros y lógicos?

Proporciona recomendaciones específicas para la reestructuración."""

    try:
        response = llm.invoke(prompt)

        recommendations = response.content if hasattr(response, 'content') else str(response)
        print(f"[Replanificador] Recomendaciones: {recommendations[:200]}...")

        # En una implementación completa, parsear y aplicar cambios
        # Por ahora, simplemente marcar que se intentó replantear

        state["plan_refinement_iterations"] = state.get("plan_refinement_iterations", 0) + 1
        state["validation_feedback"].append(f"Replanificación #{state['plan_refinement_iterations']}: {recommendations[:100]}")

        # Resetear flags para reprocesar
        state["all_stages_covered"] = False

        # Limpiar libros de etapas que necesitan mejora
        for stage in current_structure.keys():
            if len(books.get(stage, [])) < 2:
                if stage in state["books_by_stage"]:
                    del state["books_by_stage"][stage]

    except Exception as e:
        print(f"[Replanificador] Error: {e}")
        state["plan_refinement_iterations"] = state.get("plan_refinement_iterations", 0) + 1

    return state
