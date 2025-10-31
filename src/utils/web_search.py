"""
Utilidades para búsqueda web usando Google Search grounding con Vertex AI.
"""
import re
from typing import List, Dict, Optional
from src.config.llm_config import get_llm_with_search


def search_with_gemini(query: str, temperature: float = 1.0) -> Dict[str, any]:
    """
    Realiza una búsqueda usando Gemini con Google Search grounding habilitado.

    Esta función utiliza la capacidad de Google Search grounding de Vertex AI,
    que permite que Gemini busque información actualizada en tiempo real desde
    Google Search antes de generar su respuesta. Esto garantiza información
    fresca y precisa sobre libros, ratings y otros datos dinámicos.

    El grounding se habilita automáticamente al usar get_llm_with_search() que
    configura search_tool_use=True en el modelo Vertex AI.

    Args:
        query: Consulta de búsqueda en lenguaje natural. Puede incluir preguntas
               específicas sobre libros, ratings, autores, etc.
        temperature: Temperatura del modelo para controlar creatividad.
                    1.0 es recomendado para grounding (valor por defecto).
                    Valores más bajos (0.7) dan respuestas más determinísticas.

    Returns:
        Dict: Diccionario con tres claves:
            - 'text': Texto de la respuesta generada por Gemini
            - 'metadata': Diccionario con metadata de la respuesta (fuentes, etc.)
            - 'full_response': Objeto completo de respuesta del LLM

        En caso de error, retorna dict con claves 'text' (vacío), 'metadata' (vacío),
        y 'error' (mensaje del error).

    Raises:
        Exception: Los errores se capturan y retornan en el dict bajo clave 'error'
    """
    try:
        # Obtener LLM con Google Search habilitado
        llm = get_llm_with_search(temperature=temperature)

        # Invocar el modelo
        response = llm.invoke(query)

        # Extraer texto de respuesta
        text = response.content if hasattr(response, 'content') else str(response)

        # Extraer metadata si está disponible
        metadata = {}
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata

        return {
            "text": text,
            "metadata": metadata,
            "full_response": response
        }

    except Exception as e:
        print(f"Error en búsqueda con Gemini: {e}")
        return {
            "text": "",
            "metadata": {},
            "error": str(e)
        }


def search_books_for_topic(topic: str, stage_name: str = None) -> List[Dict[str, any]]:
    """
    Busca libros recomendados para un tema usando Google Search grounding de Vertex AI.

    Esta es la función principal de búsqueda de libros del sistema. Construye un
    prompt estructurado pidiendo al LLM que busque los 5 mejores libros para el tema,
    con formato específico que facilita el parsing posterior.

    El prompt solicita para cada libro:
    - Title: Título exacto del libro
    - Author: Nombre del autor
    - Year: Año de publicación
    - Rating: Calificación sobre 5
    - Reviews: Número de reseñas
    - Why: Justificación de la recomendación

    Los libros se separan con "---" para facilitar el parsing. Si se proporciona
    stage_name, la búsqueda se refina para esa etapa específica del plan.

    Args:
        topic: Tema principal del plan de estudio (ej: "Machine Learning")
        stage_name: Nombre de la etapa específica (ej: "Fundamentals of ML").
                   Si se proporciona, la búsqueda se enfoca en libros para esa etapa.
                   Si es None, busca libros generales del tema.

    Returns:
        List[Dict]: Lista de diccionarios, cada uno representando un libro con claves:
                   - title: str
                   - author: str
                   - year: Optional[str]
                   - rating: float
                   - num_reviews: int
                   - reason: str

        Lista vacía si hay error en la búsqueda.

    Examples:
        >>> books = search_books_for_topic("Python Programming")
        >>> books[0]['title']
        'Python Crash Course'

        >>> books = search_books_for_topic("Data Science", "Advanced Statistics")
        >>> len(books)
        5
    """
    # Construir query específico - más simple y directo
    if stage_name:
        query = f"""Lista los 5 mejores libros recomendados para aprender {stage_name} en {topic}.

Para CADA libro, proporciona el siguiente formato exacto:

Title: [título exacto del libro]
Author: [nombre del autor]
Year: [año de publicación]
Rating: [calificación sobre 5, ej., 4.5]
Reviews: [número de reseñas, ej., 1200]
Why: [explicación de una oración]

---

Asegúrate de incluir los 5 libros con información completa."""
    else:
        query = f"""Lista los 5 mejores libros recomendados para aprender {topic}.

Para CADA libro, proporciona el siguiente formato exacto:

Title: [título exacto del libro]
Author: [nombre del autor]
Year: [año de publicación]
Rating: [calificación sobre 5, ej., 4.5]
Reviews: [número de reseñas, ej., 1200]
Why: [explicación de una oración]

---

Asegúrate de incluir los 5 libros con información completa."""

    result = search_with_gemini(query, temperature=1.0)

    if "error" in result:
        return []

    # Parsear la respuesta para extraer libros estructurados
    books = parse_books_from_text(result["text"])

    return books


def parse_books_from_text(text: str) -> List[Dict[str, any]]:
    """
    Parsea el texto de respuesta del LLM para extraer información estructurada de libros.

    Esta función implementa dos estrategias de parsing:

    1. PARSING ESTRUCTURADO (preferido):
       Detecta campos con formato "Field: Value" como:
       - Title: [título]
       - Author: [autor]
       - Year: [año]
       - Rating: [rating]
       - Reviews: [número]
       - Why: [razón]
       - "---" como separador

    2. PARSING TRADICIONAL (fallback):
       Si el parsing estructurado no encuentra libros, intenta extraer información
       de texto menos estructurado usando regex para detectar:
       - Libros numerados o con viñetas
       - Autores mencionados con "by" o "author:"
       - Ratings con formato "X/5" o "X stars"
       - Número de reviews

    Aplica valores por defecto para campos faltantes:
    - author: "Unknown"
    - year: None
    - rating: 0.0
    - num_reviews: 0
    - reason: "Highly recommended resource"

    Args:
        text: Texto de respuesta del LLM conteniendo información de libros

    Returns:
        List[Dict]: Lista de diccionarios, cada uno con información de un libro.
                   Las claves son: title, author, year, rating, num_reviews, reason.
                   Lista vacía si no se puede parsear ningún libro.
    """
    books = []
    lines = text.split('\n')

    current_book = {}

    for line in lines:
        line = line.strip()

        # Detectar campos con formato "Field: Value"
        if line.startswith('Title:'):
            # Guardar libro anterior si existe
            if current_book and 'title' in current_book:
                books.append(current_book)
            current_book = {'title': line.replace('Title:', '').strip()}

        elif line.startswith('Author:') and current_book:
            current_book['author'] = line.replace('Author:', '').strip()

        elif line.startswith('Year:') and current_book:
            year_text = line.replace('Year:', '').strip()
            year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
            if year_match:
                current_book['year'] = year_match.group(0)
            else:
                current_book['year'] = None

        elif line.startswith('Rating:') and current_book:
            rating_text = line.replace('Rating:', '').strip()
            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
            if rating_match:
                try:
                    current_book['rating'] = float(rating_match.group(1))
                except:
                    current_book['rating'] = 0.0
            else:
                current_book['rating'] = 0.0

        elif line.startswith('Reviews:') and current_book:
            reviews_text = line.replace('Reviews:', '').strip()
            reviews_match = re.search(r'(\d+)', reviews_text.replace(',', ''))
            if reviews_match:
                try:
                    current_book['num_reviews'] = int(reviews_match.group(1))
                except:
                    current_book['num_reviews'] = 0
            else:
                current_book['num_reviews'] = 0

        elif line.startswith('Why:') and current_book:
            current_book['reason'] = line.replace('Why:', '').strip()

        elif line == '---' and current_book:
            # Separador de libros
            if 'title' in current_book:
                books.append(current_book)
            current_book = {}

    # Agregar último libro si existe
    if current_book and 'title' in current_book:
        books.append(current_book)

    # Fallback: parsing tradicional si el formato estructurado no funcionó
    if len(books) == 0:
        # Intentar parsing tradicional
        current_book = {}
        book_started = False

        for line in lines:
            line = line.strip()
            if not line:
                if current_book and book_started:
                    books.append(current_book)
                    current_book = {}
                    book_started = False
                continue

            # Detectar inicio de nuevo libro
            if re.match(r'^[\d\*\-•]+[\.\):]?\s+', line):
                if current_book and book_started:
                    books.append(current_book)
                current_book = {}
                book_started = True

                # Extraer título
                title_match = re.search(r'["\']([^"\']+)["\']|[\d\*\-•]+[\.\):]?\s+([^:\n]+?)(?:\s+by\s+|$)', line, re.IGNORECASE)
                if title_match:
                    current_book['title'] = (title_match.group(1) or title_match.group(2)).strip()

            # Extraer autor
            if book_started and ('by' in line.lower() or 'author' in line.lower()):
                author_match = re.search(r'(?:by|author[:\s]+)\s*([A-Z][^,\n\(\)]+?)(?:\s*\(|\s*,|\s*$)', line, re.IGNORECASE)
                if author_match:
                    current_book['author'] = author_match.group(1).strip()

            # Extraer rating
            if book_started:
                rating_match = re.search(r'(\d+\.?\d*)\s*(?:\/5|stars?|rating)', line, re.IGNORECASE)
                if rating_match:
                    try:
                        current_book['rating'] = float(rating_match.group(1))
                    except:
                        pass

            # Extraer número de reviews
            reviews_match = re.search(r'([\d,]+)\s*(?:reviews?|ratings?)', line, re.IGNORECASE)
            if reviews_match and book_started:
                try:
                    num_str = reviews_match.group(1).replace(',', '')
                    current_book['num_reviews'] = int(num_str)
                except:
                    pass

            # Acumular razón/descripción
            if book_started and not any(key in line.lower() for key in ['title', 'author', 'rating', 'year', 'publication']):
                if 'reason' not in current_book:
                    current_book['reason'] = line
                else:
                    current_book['reason'] += ' ' + line

        # Agregar último libro si existe
        if current_book and book_started:
            books.append(current_book)

    # Asegurar campos mínimos y valores por defecto
    for book in books:
        if 'title' not in book:
            continue
        book.setdefault('author', 'Unknown')
        book.setdefault('year', None)
        book.setdefault('rating', 0.0)
        book.setdefault('num_reviews', 0)
        book.setdefault('reason', 'Highly recommended resource')

    return books


def validate_book_quality(book: Dict[str, any], quality_threshold: float = 4.0) -> bool:
    """
    Valida si un libro cumple con el umbral mínimo de calidad basado en su rating.

    Esta función simple compara el rating del libro contra un threshold mínimo.
    Se usa en el nodo validador_calidad para filtrar libros de baja calidad antes
    de agregarlos al plan de estudio.

    Args:
        book: Diccionario con información del libro. Debe contener la clave 'rating'.
              Si no existe 'rating', se asume 0.0.
        quality_threshold: Rating mínimo requerido en escala 0-5.
                          Por defecto es 4.0 (QUALITY_THRESHOLD global).

    Returns:
        bool: True si el rating del libro >= quality_threshold, False en caso contrario.

    Examples:
        >>> book = {'title': 'Python Book', 'rating': 4.5}
        >>> validate_book_quality(book, 4.0)
        True

        >>> book = {'title': 'Bad Book', 'rating': 3.2}
        >>> validate_book_quality(book, 4.0)
        False
    """
    rating = book.get('rating', 0.0)
    return rating >= quality_threshold


def search_specific_book_rating(title: str, author: str) -> Optional[Dict[str, any]]:
    """
    Busca información actualizada y específica sobre el rating de un libro conocido.

    Esta función realiza una búsqueda enfocada para obtener la calificación actual
    de un libro específico del que ya se conoce el título y autor. Consulta múltiples
    fuentes (Goodreads, Amazon, etc.) para obtener el rating promedio y número de
    reseñas más actualizado.

    Es útil cuando se tiene información básica de un libro pero se necesita validar
    o actualizar su rating antes de incluirlo en el plan de estudio.

    El prompt solicita explícitamente:
    1. Calificación promedio de plataformas principales
    2. Número total de reseñas/calificaciones
    3. Fuente de la calificación

    Extrae el rating y número de reviews del texto de respuesta usando regex.

    Args:
        title: Título exacto del libro a buscar
        author: Nombre del autor del libro

    Returns:
        Optional[Dict]: Diccionario con dos claves si se encuentra información:
                       - 'rating': float con calificación (0-5)
                       - 'num_reviews': int con número de reseñas

                       None si hay error en la búsqueda o no se puede extraer rating.

    Examples:
        >>> info = search_specific_book_rating("Clean Code", "Robert C. Martin")
        >>> info['rating']
        4.4
        >>> info['num_reviews']
        5200
    """
    query = f"""¿Cuál es la calificación promedio actual y el número de reseñas para el libro "{title}" de {author}?

Por favor proporciona:
1. Calificación promedio (de Goodreads, Amazon u otras plataformas principales)
2. Número total de reseñas/calificaciones
3. Fuente de la calificación"""

    result = search_with_gemini(query, temperature=0.7)

    if "error" in result:
        return None

    text = result["text"]

    # Extraer rating
    rating_match = re.search(r'(\d+\.?\d*)\s*(?:\/5|stars?|rating)', text, re.IGNORECASE)
    reviews_match = re.search(r'([\d,]+)\s*(?:reviews?|ratings?)', text, re.IGNORECASE)

    if rating_match:
        rating = float(rating_match.group(1))
        num_reviews = 0

        if reviews_match:
            num_str = reviews_match.group(1).replace(',', '')
            num_reviews = int(num_str)

        return {
            "rating": rating,
            "num_reviews": num_reviews
        }

    return None
