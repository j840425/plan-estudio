#!/usr/bin/env python3
"""
Script principal para ejecutar el sistema agéntico de generación de planes de estudio.

Uso:
    python main.py "Machine Learning"
    python main.py "Machine Learning" --level intermediate
    python main.py "Historia del Arte" --output plan_historia.txt
"""
import argparse
import sys
from src.graph import run_study_plan_workflow


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Sistema Agéntico de Generación de Planes de Estudio con LangGraph y Gemini"
    )

    parser.add_argument(
        "topic",
        type=str,
        help="Tema u objetivo de aprendizaje (ej: 'Machine Learning', 'Finanzas Corporativas')"
    )

    parser.add_argument(
        "--level",
        type=str,
        choices=["beginner", "intermediate", "advanced"],
        default="beginner",
        help="Nivel del estudiante (default: beginner)"
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Archivo de salida para guardar el plan (opcional)"
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Modo silencioso (solo muestra resultado final)"
    )

    args = parser.parse_args()

    # Validar que el tema no esté vacío
    if not args.topic.strip():
        print("Error: El tema no puede estar vacío")
        sys.exit(1)

    try:
        # Ejecutar el workflow
        final_state = run_study_plan_workflow(
            topic=args.topic,
            user_level=args.level,
            verbose=not args.quiet
        )

        # Obtener el plan generado
        plan = final_state.get("final_output", "")

        if not plan:
            print("\n⚠ No se pudo generar el plan de estudio.")
            sys.exit(1)

        # El archivo ya fue generado automáticamente por formateador_salida
        # Solo mostramos confirmación si el usuario especificó --output
        if args.output:
            print(f"\nGenerando archivo adicional...")
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(plan)
            print(f"Archivo: {args.output} generado")

    except KeyboardInterrupt:
        print("\n\n⚠ Proceso interrumpido por el usuario")
        sys.exit(1)

    except Exception as e:
        print(f"\n⚠ Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
