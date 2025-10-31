#!/usr/bin/env python3
"""
Test simple para verificar componentes básicos del sistema.

Este script verifica:
- Conexión con Gemini 2.5 Flash
- Google Search grounding
- Parsing de libros
- Configuración de credenciales
"""

import sys
import os


def test_imports():
    """Verifica que las importaciones necesarias funcionen."""
    print("🔍 Verificando imports...")
    try:
        from src.config.llm_config import get_llm
        from src.utils.web_search import parse_book_metadata, extract_books_from_search
        from src.state import GraphState
        print("   ✅ Imports correctos")
        return True
    except ImportError as e:
        print(f"   ❌ Error en imports: {e}")
        return False


def test_credentials():
    """Verifica que las credenciales estén configuradas."""
    print("\n🔍 Verificando credenciales...")

    project_id = os.getenv("GCP_PROJECT_ID")
    location = os.getenv("GCP_LOCATION")
    credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not project_id:
        print("   ❌ GCP_PROJECT_ID no configurado")
        return False

    if not location:
        print("   ❌ GCP_LOCATION no configurado")
        return False

    if not credentials:
        print("   ⚠ GOOGLE_APPLICATION_CREDENTIALS no configurado (puede usar default credentials)")
    elif not os.path.exists(credentials):
        print(f"   ❌ Archivo de credenciales no existe: {credentials}")
        return False

    print(f"   ✅ GCP_PROJECT_ID: {project_id}")
    print(f"   ✅ GCP_LOCATION: {location}")
    if credentials:
        print(f"   ✅ GOOGLE_APPLICATION_CREDENTIALS: {credentials}")

    return True


def test_llm_connection():
    """Verifica la conexión con Gemini 2.5 Flash."""
    print("\n🔍 Verificando conexión con Gemini 2.5 Flash...")
    try:
        from src.config.llm_config import get_llm

        llm = get_llm(temperature=0.5)
        print("   ✅ LLM inicializado correctamente")

        # Test simple de invocación
        print("   🔄 Probando invocación básica...")
        response = llm.invoke("Responde con una sola palabra: OK")

        if hasattr(response, 'content'):
            content = response.content
        else:
            content = str(response)

        print(f"   ✅ Respuesta recibida: {content[:50]}...")
        return True

    except Exception as e:
        print(f"   ❌ Error al conectar con Gemini: {e}")
        return False


def test_book_parsing():
    """Verifica el parsing de metadatos de libros."""
    print("\n🔍 Verificando parsing de libros...")
    try:
        from src.utils.web_search import parse_book_metadata

        # Test con datos simulados
        test_cases = [
            {
                "input": "Introduction to Algorithms (4.5/5, 1200 reviews)",
                "expected_rating": 4.5
            },
            {
                "input": "Clean Code by Robert Martin - Rating: 4.8",
                "expected_rating": 4.8
            },
            {
                "input": "Python Crash Course",
                "expected_rating": 0.0  # Sin rating
            }
        ]

        passed = 0
        for i, test in enumerate(test_cases, 1):
            metadata = parse_book_metadata(test["input"])
            if abs(metadata['rating'] - test["expected_rating"]) < 0.01:
                passed += 1
                print(f"   ✅ Test {i} pasado: rating={metadata['rating']}")
            else:
                print(f"   ❌ Test {i} fallido: esperado {test['expected_rating']}, obtenido {metadata['rating']}")

        if passed == len(test_cases):
            print(f"   ✅ Todos los tests de parsing pasaron ({passed}/{len(test_cases)})")
            return True
        else:
            print(f"   ⚠ Algunos tests fallaron ({passed}/{len(test_cases)})")
            return False

    except Exception as e:
        print(f"   ❌ Error en parsing: {e}")
        return False


def test_search_grounding():
    """Verifica Google Search grounding con una búsqueda real."""
    print("\n🔍 Verificando Google Search grounding...")
    try:
        from src.config.llm_config import get_llm

        # Usar search grounding para buscar libros reales
        llm = get_llm(temperature=0.5, search_grounding=True)
        print("   ✅ LLM con search grounding inicializado")

        print("   🔄 Buscando libros de Python...")
        prompt = """Encuentra 2 libros populares sobre Python programming.
Para cada libro proporciona: título completo, autor, año, y rating si está disponible.
Formato: "Título" por Autor (Año) - Rating: X/5"""

        response = llm.invoke(prompt)

        if hasattr(response, 'content'):
            content = response.content
        else:
            content = str(response)

        # Verificar que la respuesta contiene información de libros
        if any(word in content.lower() for word in ['python', 'author', 'book']):
            print(f"   ✅ Búsqueda exitosa (respuesta de {len(content)} caracteres)")
            print(f"   📚 Ejemplo de respuesta: {content[:150]}...")
            return True
        else:
            print(f"   ⚠ Respuesta recibida pero sin información clara de libros")
            return False

    except Exception as e:
        print(f"   ❌ Error en search grounding: {e}")
        return False


def main():
    """Ejecuta todos los tests."""
    print("=" * 80)
    print("TEST SIMPLE - Verificación de Componentes Básicos")
    print("=" * 80)

    results = {
        "Imports": test_imports(),
        "Credenciales": test_credentials(),
        "Conexión LLM": test_llm_connection(),
        "Parsing de libros": test_book_parsing(),
        "Search grounding": test_search_grounding()
    }

    print("\n" + "=" * 80)
    print("RESUMEN DE RESULTADOS")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {test_name}")

    total = len(results)
    passed = sum(results.values())

    print("\n" + "=" * 80)
    print(f"Total: {passed}/{total} tests pasados ({passed/total*100:.0f}%)")
    print("=" * 80)

    if passed == total:
        print("\n🎉 Todos los componentes funcionan correctamente!")
        return 0
    else:
        print(f"\n⚠ Algunos componentes fallaron. Por favor revisa la configuración.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
