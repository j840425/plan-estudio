"""
Configuración del LLM con Google Vertex AI y Gemini usando LangChain.
"""
import os
from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI

# Cargar variables de entorno
load_dotenv()


def get_llm(temperature: float = 0.7, model_name: str = None):
    """
    Obtiene una instancia del modelo Gemini configurado con Vertex AI sin grounding.

    Esta función crea y retorna un modelo de lenguaje ChatVertexAI configurado para
    usar Gemini a través de Google Cloud Vertex AI. Es la función base para obtener
    el LLM en tareas que NO requieren búsqueda en tiempo real (análisis, validación,
    generación de planes, etc.).

    La configuración se obtiene de variables de entorno:
    - GOOGLE_CLOUD_PROJECT: ID del proyecto de Google Cloud (REQUERIDO)
    - GOOGLE_CLOUD_LOCATION: Región (default: "us-central1")
    - MODEL_NAME: Modelo a usar (default: "gemini-2.5-flash")

    Args:
        temperature: Control de creatividad/aleatoriedad del modelo (0.0-1.0).
                    - 0.0: Muy determinístico, respuestas consistentes
                    - 0.7: Balance entre creatividad y coherencia (default)
                    - 1.0: Más creativo y variado
        model_name: Nombre específico del modelo Gemini a usar.
                   Si es None, usa el valor de MODEL_NAME del .env o "gemini-2.5-flash".
                   Opciones: "gemini-2.5-flash", "gemini-1.5-pro", etc.

    Returns:
        ChatVertexAI: Instancia configurada del modelo de lenguaje lista para
                     invocar con .invoke(prompt).

    Raises:
        ValueError: Si GOOGLE_CLOUD_PROJECT no está configurado en las variables
                   de entorno. Requiere archivo .env basado en .env.example.

    Examples:
        >>> llm = get_llm(temperature=0.5)
        >>> response = llm.invoke("¿Qué es Python?")
        >>> print(response.content)
        'Python es un lenguaje de programación...'
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    model = model_name or os.getenv("MODEL_NAME", "gemini-2.5-flash")

    if not project_id:
        raise ValueError(
            "GOOGLE_CLOUD_PROJECT no está configurado. "
            "Crea un archivo .env basado en .env.example"
        )

    llm = ChatVertexAI(
        model=model,
        project=project_id,
        location=location,
        temperature=temperature,
        max_tokens=8192,
    )

    return llm


def get_llm_with_search(temperature: float = 1.0, model_name: str = None):
    """
    Obtiene una instancia del LLM con Google Search grounding habilitado.

    Esta función crea un modelo ChatVertexAI con la capacidad de Google Search grounding,
    que permite que Gemini busque información actualizada en Google Search antes de
    responder. Es esencial para búsqueda de libros, ratings y cualquier información
    dinámica que cambia con el tiempo.

    El grounding se habilita mediante el parámetro search_tool_use=True en la
    configuración de Vertex AI. Esto indica al modelo que debe usar Google Search
    como herramienta durante la generación de respuestas.

    IMPORTANTE: Temperature de 1.0 es recomendado por Google para grounding, ya que
    permite al modelo integrar mejor la información de búsqueda con su conocimiento.

    La configuración se obtiene de las mismas variables de entorno que get_llm():
    - GOOGLE_CLOUD_PROJECT: ID del proyecto de Google Cloud (REQUERIDO)
    - GOOGLE_CLOUD_LOCATION: Región (default: "us-central1")
    - MODEL_NAME: Modelo a usar (default: "gemini-2.5-flash")

    Args:
        temperature: Control de creatividad del modelo (0.0-1.0).
                    1.0 es el valor RECOMENDADO para grounding (default).
                    Temperaturas más bajas pueden limitar la capacidad del modelo
                    para integrar información de búsqueda.
        model_name: Nombre específico del modelo Gemini a usar.
                   Si es None, usa el valor de MODEL_NAME del .env o "gemini-2.5-flash".

    Returns:
        ChatVertexAI: Instancia configurada del modelo con grounding habilitado.
                     Al invocar este modelo, Gemini automáticamente buscará en
                     Google Search información relevante antes de responder.

    Raises:
        ValueError: Si GOOGLE_CLOUD_PROJECT no está configurado en las variables
                   de entorno.

    Examples:
        >>> llm = get_llm_with_search()
        >>> response = llm.invoke("¿Cuál es el rating actual de Clean Code en Goodreads?")
        >>> print(response.content)
        'Según las búsquedas actuales, Clean Code tiene un rating de 4.4/5...'
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    model = model_name or os.getenv("MODEL_NAME", "gemini-2.5-flash")

    if not project_id:
        raise ValueError(
            "GOOGLE_CLOUD_PROJECT no está configurado. "
            "Crea un archivo .env basado en .env.example"
        )

    # Vertex AI con Google Search grounding
    llm = ChatVertexAI(
        model=model,
        project=project_id,
        location=location,
        temperature=temperature,
        max_tokens=8192,
        # Habilitar Google Search grounding
        search_tool_use=True,
    )

    return llm
