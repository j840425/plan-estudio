"""
Nodos de análisis inicial: Analizador de Tema y Evaluador de Nivel.
"""
from src.state import GraphState
from src.config.llm_config import get_llm


def analizador_tema(state: GraphState) -> GraphState:
    """
    Nodo 1: Analiza el tema de aprendizaje y lo descompone en áreas de conocimiento.

    Este es el primer nodo del workflow. Utiliza un LLM para realizar un análisis
    exhaustivo del tema proporcionado por el usuario, identificando las áreas clave,
    prerrequisitos, y conceptos fundamentales a avanzados. El análisis sirve como
    base para estructurar el plan de estudio en etapas posteriores.

    El nodo descompone el objetivo en:
    - Áreas de conocimiento principales (4-7 áreas clave)
    - Prerrequisitos potenciales necesarios
    - Conceptos fundamentales para principiantes
    - Conceptos intermedios que se construyen sobre los fundamentos
    - Conceptos avanzados más complejos
    - Brechas de conocimiento comunes que deben abordarse

    Campos del estado que LEE:
        - topic: Tema a analizar

    Campos del estado que MODIFICA:
        - knowledge_gaps: Se llena con las áreas clave identificadas
        - validation_feedback: Se agrega el análisis inicial (primeros 200 chars)

    Args:
        state: Estado actual del grafo conteniendo el tema a analizar

    Returns:
        GraphState: Estado actualizado con knowledge_gaps y validation_feedback

    Raises:
        Exception: Si hay error en la invocación del LLM, se asignan gaps por defecto
                  (Foundational, Intermediate, Advanced + topic)
    """
    print(f"\n[Analizador_Tema] Analizando: {state['topic']}")

    llm = get_llm(temperature=0.7)

    prompt = f"""Analiza el tema de aprendizaje: "{state['topic']}"

Por favor proporciona un análisis exhaustivo que incluya:

1. Áreas de conocimiento principales: Lista 4-7 áreas clave o subtemas que este tema abarca
2. Prerrequisitos potenciales: ¿Qué conocimiento fundamental deberían tener los estudiantes?
3. Conceptos fundamentales: ¿Cuáles son los conceptos básicos principales para principiantes?
4. Conceptos intermedios: ¿Qué conceptos se construyen sobre los fundamentos?
5. Conceptos avanzados: ¿Cuáles son los temas más complejos en este campo?
6. Brechas de conocimiento a abordar: ¿Cuáles son las brechas comunes al entender este tema?

Proporciona un análisis estructurado que ayudará a crear una hoja de ruta de aprendizaje completa."""

    try:
        response = llm.invoke(prompt)

        analysis_text = response.content if hasattr(response, 'content') else str(response)

        # Extraer knowledge gaps iniciales del análisis
        gaps = []
        if "gap" in analysis_text.lower():
            # Parsear gaps mencionados
            lines = analysis_text.split('\n')
            for line in lines:
                if 'gap' in line.lower() or 'lack' in line.lower() or 'missing' in line.lower():
                    gaps.append(line.strip())

        if not gaps:
            gaps = [f"Complete coverage of {state['topic']}"]

        # Actualizar estado
        state["knowledge_gaps"] = gaps
        state["validation_feedback"] = [f"Análisis inicial: {analysis_text[:200]}..."]

        print(f"[Analizador_Tema] Identificadas {len(gaps)} áreas clave")

    except Exception as e:
        print(f"[Analizador_Tema] Error: {e}")
        state["knowledge_gaps"] = [f"Foundational {state['topic']}",
                                   f"Intermediate {state['topic']}",
                                   f"Advanced {state['topic']}"]

    return state


def evaluador_nivel(state: GraphState) -> GraphState:
    """
    Nodo 2: Evalúa y ajusta el contenido según el nivel de experiencia del usuario.

    Este nodo toma el nivel del usuario (beginner/intermediate/advanced) y ajusta
    los knowledge_gaps identificados para enfocarse en contenido apropiado a su nivel.
    Por ejemplo, usuarios avanzados no necesitan cubrir contenido muy básico.

    Lógica de ajuste por nivel:
    - Beginner: Mantiene todos los gaps, incluyendo fundamentos
    - Intermediate: Filtra gaps muy básicos (que contengan "foundational")
    - Advanced: Solo mantiene gaps avanzados/complejos/expertos

    En una implementación completa, este nodo podría hacer preguntas interactivas
    al usuario para evaluar su nivel real mediante un cuestionario o análisis de
    experiencia previa.

    Campos del estado que LEE:
        - user_level: Nivel del usuario ("beginner", "intermediate", "advanced")
        - knowledge_gaps: Lista de gaps identificados en el análisis previo

    Campos del estado que MODIFICA:
        - user_level: Se valida y establece a "beginner" si es inválido o vacío
        - knowledge_gaps: Se filtra según el nivel para enfocarse en contenido apropiado

    Args:
        state: Estado actual del grafo con nivel de usuario y gaps identificados

    Returns:
        GraphState: Estado actualizado con user_level validado y knowledge_gaps ajustados
    """
    print("\n[Evaluador_Nivel] Evaluando nivel del usuario")

    # En esta implementación, asumimos nivel beginner
    # En producción, aquí podrías:
    # 1. Hacer preguntas al usuario
    # 2. Analizar su experiencia previa
    # 3. Ajustar basado en input adicional

    level = state.get("user_level", "beginner")

    if not level or level not in ["beginner", "intermediate", "advanced"]:
        level = "beginner"

    state["user_level"] = level

    # Ajustar knowledge_gaps según nivel
    if level == "beginner":
        print("[Evaluador_Nivel] Nivel: Principiante - cubrirá fundamentos")
    elif level == "intermediate":
        print("[Evaluador_Nivel] Nivel: Intermedio - enfocará en profundización")
        # Filtrar gaps muy básicos
        state["knowledge_gaps"] = [g for g in state["knowledge_gaps"]
                                   if "foundational" not in g.lower()]
    else:  # advanced
        print("[Evaluador_Nivel] Nivel: Avanzado - enfocará en temas avanzados")
        # Enfocarse solo en gaps avanzados
        state["knowledge_gaps"] = [g for g in state["knowledge_gaps"]
                                   if any(word in g.lower() for word in ["advanced", "complex", "expert"])]

    return state
