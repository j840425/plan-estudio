# 📚 Sistema Workflow Agéntico de Generación de Planes de Estudio

Sistema inteligente que genera **planes de estudio personalizados** utilizando **LangGraph**, **Gemini 2.5 Flash** y **Google Search Grounding** en Google Vertex AI. Construye roadmaps de aprendizaje estructurados con libros recomendados, duraciones estimadas y objetivos específicos mediante un workflow agéntico que toma decisiones autónomas en tiempo real.

## ✨ Características Principales

- **Workflow Agéntico con LangGraph**: Sistema de 15 nodos que toma decisiones dinámicas en cada etapa
- **Búsquedas Web en Tiempo Real**: Google Search Grounding integrado para encontrar libros actualizados
- **Planes Adaptativos**: Genera entre 3-7 etapas según la complejidad del tema
- **Validación de Calidad**: Filtra libros con ratings >4.0 y valida coherencia del plan
- **Auto-refinamiento**: Replantea automáticamente la estructura si detecta problemas críticos
- **Salida Profesional**: Documentos formateados guardados automáticamente con timestamp
- **Control de Límites**: Mecanismos de seguridad para evitar loops infinitos y costos excesivos

## 🏗️ Arquitectura del Workflow

El sistema implementa un grafo de estado con **15 nodos** organizados en 3 ciclos principales:

### Nodos de Procesamiento

```
1. Analizador_Tema        → Descompone tema en áreas de conocimiento (4-7 áreas)
2. Evaluador_Nivel        → Ajusta contenido según nivel (beginner/intermediate/advanced)
3. Estructurador_Plan     → Crea roadmap de 3-7 etapas con LLM + parsing robusto
4. Selector_Etapa         → Itera sobre etapas que necesitan libros
5. Investigador_Libros    → Busca libros con Google Search + filtrado
6. Validador_Calidad      → Filtra por rating >4.0 y elimina duplicados
7. Detector_Gaps          → Identifica lagunas de conocimiento sin cubrir
8. Validador_Global       → Evalúa coherencia y calidad del plan completo (score 1-10)
9. Replanificador         → Ajusta estructura según feedback de validación
10. Formateador_Salida    → Genera documento final con roadmap y detalles
11. Salida_Forzada        → Genera salida con disclaimer si se alcanzan límites
```

### Nodos de Decisión Condicional

```
12. Decision_Busqueda_Libros   → reintentar | busqueda_especifica | aceptar | suficientes
13. Decision_Cobertura_Etapas  → siguiente_etapa | validacion_global
14. Decision_Validacion        → forzar_salida | replantear | formatear
15. Should_Continue_Or_End     → continue | end (auxiliar, no usado actualmente)
```

### Ciclos Controlados

| Ciclo | Propósito | Límite | Trigger |
|-------|-----------|--------|---------|
| **Búsqueda de Libros** | Encontrar recursos de calidad por etapa | 3 búsquedas/etapa | MIN_BOOKS_PER_STAGE (2) |
| **Cobertura de Etapas** | Procesar todas las etapas del plan | 1 iteración/etapa | Todas las etapas cubiertas |
| **Refinamiento Global** | Validar y replantear estructura | 2 replaneaciones | Problemas críticos detectados |

### Controles de Seguridad

- `MAX_BOOK_SEARCHES_PER_STAGE = 3`: Límite de búsquedas por etapa
- `MAX_VALIDATION_CYCLES = 5`: Máximo de validaciones totales
- `MAX_PLAN_REFINEMENTS = 2`: Máximo de replaneaciones completas
- `MIN_BOOKS_PER_STAGE = 2`: Mínimo de libros requeridos por etapa
- `QUALITY_THRESHOLD = 4.0`: Rating mínimo aceptable para libros

## 🚀 Instalación

### Requisitos Previos

- **Python 3.9+**
- **Cuenta de Google Cloud** con Vertex AI habilitado
- **Service Account** con permisos de Vertex AI

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/j840425/plan-estudio.git
cd plan-estudio
```

2. **Crear entorno virtual**
```bash
python -m venv venv

# Linux/Mac:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar Google Cloud**
```bash
# Autenticación local
gcloud auth application-default login

# Configurar proyecto
gcloud config set project TU-PROJECT-ID

# Habilitar API de Vertex AI
gcloud services enable aiplatform.googleapis.com
```

5. **Configurar variables de entorno**

Copiar archivo de ejemplo:
```bash
cp .env.example .env
```

Editar `.env`:
```env
GOOGLE_CLOUD_PROJECT=tu-proyecto-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/tu/service-account-key.json
MODEL_NAME=gemini-2.5-flash
```

6. **Verificar instalación**
```bash
python test_simple.py
```

## 📖 Uso

### Uso Básico

```bash
python main.py "Machine Learning"
```

Genera automáticamente:
```
plan_estudio_Machine_Learning_20250131_143022.txt
```

### Opciones Avanzadas

**Especificar nivel del usuario:**
```bash
python main.py "Machine Learning" --level intermediate
```

Niveles disponibles:
- `beginner`: Plan completo desde fundamentos (default)
- `intermediate`: Excluye contenido muy básico
- `advanced`: Solo temas complejos y especializados

**Modo silencioso:**
```bash
python main.py "Finanzas Corporativas" --quiet
```
Solo muestra resultado final sin logs de progreso.

**Guardar en ubicación específica (adicional):**
```bash
python main.py "Deep Learning" --output mi_plan.txt
```
Genera archivo adicional además del automático con timestamp.

### Ejemplos Completos

```bash
# Plan para principiantes en Deep Learning
python main.py "Deep Learning" --level beginner

# Plan avanzado de Quantum Computing
python main.py "Quantum Computing" --level advanced

# Plan intermedio de Data Science (modo silencioso)
python main.py "Data Science" --level intermediate --quiet

# Plan de Historia del Arte con archivo personalizado
python main.py "Historia del Arte" --output historia_arte_plan.txt
```

### Archivos Generados

El sistema guarda automáticamente dos tipos de archivos:

| Tipo | Formato | Descripción |
|------|---------|-------------|
| **Normal** | `plan_estudio_[tema]_[timestamp].txt` | Plan completado exitosamente |
| **Limitado** | `plan_estudio_[tema]_[timestamp]_LIMITED.txt` | Plan con recursos limitados (límites alcanzados) |

Los archivos se guardan en el directorio actual de ejecución.

## 🛠️ Tecnologías

| Componente | Tecnología | Versión | Propósito |
|------------|-----------|---------|-----------|
| Workflow Engine | LangGraph | 0.2.45 | StateGraph con nodos y edges condicionales |
| LLM | Gemini 2.5 Flash | GA 2025 | Modelo multimodal con Search grounding |
| LLM Framework | LangChain | 0.3+ | Integración con Vertex AI |
| Cloud Platform | Google Vertex AI | - | Plataforma de ML administrada |
| Web Search | Google Search Grounding | - | Búsqueda web en tiempo real integrada |
| Language | Python | 3.9+ | Type hints y async support |
| Data Validation | TypedDict | stdlib | GraphState, StageInfo, BookInfo |

## 📂 Estructura del Proyecto

```
plan-estudio/
├── src/
│   ├── __init__.py
│   ├── state.py                    # TypedDicts: GraphState, StageInfo, BookInfo
│   ├── graph.py                    # Construcción del StateGraph + edges
│   ├── config/
│   │   ├── __init__.py
│   │   └── llm_config.py          # ChatVertexAI + configuración
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── analysis_nodes.py      # analizador_tema, evaluador_nivel
│   │   ├── planning_nodes.py      # estructurador_plan, selector_etapa, replanificador
│   │   ├── book_search_nodes.py   # investigador_libros, validador_calidad, detector_gaps
│   │   ├── validation_nodes.py    # validador_global, formateador_salida, salida_forzada
│   │   └── decision_nodes.py      # Nodos condicionales (4 funciones)
│   └── utils/
│       ├── __init__.py
│       └── web_search.py          # search_books_with_grounding()
├── main.py                         # CLI con argparse
├── test_simple.py                  # Test rápido de componentes
├── test_workflow.py                # Test end-to-end
├── requirements.txt                # langchain-google-vertexai, langgraph, etc.
├── .env.example                    # Template de configuración
├── .env                           # Credenciales (no commitear)
├── .gitignore                     # *.json, .env, __pycache__, etc.
├── LICENSE                        # MIT License
└── README.md                      # Este archivo
```

## 🔑 Características Técnicas Destacadas

### Workflow Agéntico con Estado Compartido

El sistema utiliza **LangGraph StateGraph** con un `GraphState` compartido que fluye entre nodos:

```python
class GraphState(TypedDict):
    topic: str                          # Tema de aprendizaje
    user_level: str                     # beginner/intermediate/advanced
    study_plan_structure: dict          # {stage_name: StageInfo}
    books_by_stage: dict                # {stage_name: [BookInfo]}
    knowledge_gaps: List[str]           # Áreas sin cubrir
    validation_feedback: List[str]      # Feedback de validaciones
    stage_being_processed: Optional[str]
    book_search_iterations: int
    validation_iterations: int
    plan_refinement_iterations: int
    all_stages_covered: bool
    final_output: str
```

### Google Search Grounding

Integración nativa con búsqueda web mediante el parámetro `search_tool_use=True` en Gemini:

```python
llm = ChatVertexAI(
    model_name="gemini-2.5-flash-002",
    search_tool_use=True,  # Activa Google Search
    temperature=0.7
)
```

Beneficios:
- Ratings y reviews actualizados
- Información de múltiples fuentes validada
- Fechas de publicación recientes
- Recomendaciones basadas en popularidad actual

### Parsing Robusto con Regex

Sistema de parsing de etapas con **regex estricto** para evitar falsos positivos:

```python
# Solo detecta "Stage 1-7:" o "Phase 1-7:"
stage_pattern = re.compile(r'^(Stage|Phase)\s+([1-7]):\s*(.+)', re.IGNORECASE)
```

Si el LLM falla, genera etapas por defecto adaptadas al nivel del usuario.

### Decisiones Condicionales

Cada nodo de decisión implementa lógica multi-criterio:

**Decision_Busqueda_Libros** (4 salidas):
1. `reintentar_busqueda`: < 2 libros y no alcanzó límite
2. `busqueda_especifica`: Hay gaps relacionados y quedan intentos
3. `aceptar_libros_actuales`: Alcanzó MAX_BOOK_SEARCHES_PER_STAGE
4. `libros_suficientes`: >= 2 libros con calidad aceptable

**Decision_Validacion** (3 salidas):
1. `forzar_salida`: >= MAX_VALIDATION_CYCLES
2. `replantear`: Problemas críticos Y < MAX_PLAN_REFINEMENTS
3. `formatear`: Calidad suficiente o refinamientos agotados

### Manejo de Errores y Validación

- Validación de **ratings** con threshold configurable
- Eliminación de **duplicados** por título exacto
- Extracción de ratings desde texto con regex: `r'(\d+(?:\.\d+)?)\s*(?:/5|out of 5|stars)'`
- Manejo de excepciones con fallback a valores por defecto
- Logs detallados en cada nodo para debugging

## 🧪 Testing

### Test Rápido de Componentes

```bash
python test_simple.py
```

Verifica:
- ✅ Conexión con Gemini 2.5 Flash
- ✅ Búsqueda de libros con Google Search grounding
- ✅ Parsing de ratings y títulos
- ✅ Configuración de credenciales

### Test Completo del Workflow

```bash
python test_workflow.py
```

Ejecuta workflow end-to-end con tema de prueba y valida:
- ✅ Número de etapas generadas (3-7)
- ✅ Libros encontrados por etapa (mínimo 2)
- ✅ Control de iteraciones (sin loops infinitos)
- ✅ Generación de archivo final
- ✅ Tiempos de ejecución (típicamente 60-180s según complejidad)

## 💡 Ejemplo de Salida

```
================================================================================
PLAN DE ESTUDIO: MACHINE LEARNING
================================================================================

Nivel del estudiante: Beginner
Total de etapas: 4
Duración total estimada: 24 semanas (6 meses)

--------------------------------------------------------------------------------

ROADMAP DE APRENDIZAJE
--------------------------------------------------------------------------------

1. Fundamentals of Machine Learning
   Duración: 4 semanas
   Recursos: 5 libros recomendados

2. Intermediate Machine Learning
   Duración: 6 semanas
   Recursos: 5 libros recomendados

3. Advanced Machine Learning
   Duración: 8 semanas
   Recursos: 5 libros recomendados

4. Specialized Topics and Applications
   Duración: 6 semanas
   Recursos: 5 libros recomendados

================================================================================

ETAPA 1: Fundamentals of Machine Learning
================================================================================

Descripción:
  Introduction to basic concepts of Machine Learning including supervised
  and unsupervised learning, model evaluation, and common algorithms.

Duración estimada: 4 weeks

Prerrequisitos:
  - Basic Python programming
  - Linear algebra fundamentals
  - Basic statistics

Objetivos de aprendizaje:
  - Understand core ML concepts and terminology
  - Learn supervised learning algorithms (regression, classification)
  - Master model evaluation techniques
  - Implement basic ML algorithms from scratch
  - Use scikit-learn for practical applications

Libros recomendados (5):

  1. "Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow"
     Autor: Aurélien Géron
     Año: 2023
     Rating: 4.6/5.0 (2847 reviews)
     Por qué se recomienda: Practical approach with code examples, covers
     fundamentals to deep learning, widely used in industry and academia.

  2. "Pattern Recognition and Machine Learning"
     Autor: Christopher Bishop
     Año: 2006
     Rating: 4.5/5.0 (1234 reviews)
     Por qué se recomienda: Comprehensive mathematical foundation, covers
     Bayesian methods, probabilistic graphical models...

  [... más libros ...]

--------------------------------------------------------------------------------

CONSEJOS FINALES
================================================================================
- Sigue el orden de las etapas para un aprendizaje progresivo
- Complementa los libros con práctica y proyectos
- Ajusta el ritmo según tu disponibilidad de tiempo
- Busca comunidades y foros para resolver dudas

Plan generado con Gemini 2.5 Flash + Google Search
================================================================================
```

**Nota:** El sistema genera entre 3-7 etapas automáticamente. Temas simples generan 3-4 etapas, mientras que temas complejos como "Quantum Computing" o "Computational Neuroscience" pueden generar 6-7 etapas.

## 🔒 Seguridad

### Variables de Entorno

**NUNCA subas archivos sensibles a Git:**
```gitignore
.env
*.json
data/
__pycache__/
plan_*.txt
```

### Autenticación

**Desarrollo local:**
```bash
gcloud auth application-default login
```

**Producción (Cloud Run, Compute Engine):**
- Usa Service Accounts sin claves JSON
- Configura IAM roles: `roles/aiplatform.user`

### Límites y Costos

- **Google Search**: ~1 millón de queries/día (gratuito con Gemini)
- **Vertex AI**: Facturación por tokens de entrada/salida
- **Control de costos**: Los límites de iteración previenen gastos excesivos

## ⚠️ Troubleshooting

### Error: "GOOGLE_CLOUD_PROJECT no está configurado"

**Solución:**
1. Verifica que el archivo `.env` existe
2. Asegúrate de tener las variables correctas
3. Reinicia el terminal para cargar nuevas variables

### Error de autenticación con Vertex AI

**Checklist:**
- [ ] Archivo JSON de credenciales existe en la ruta especificada
- [ ] Service Account tiene rol `roles/aiplatform.user`
- [ ] API de Vertex AI está habilitada: `gcloud services enable aiplatform.googleapis.com`
- [ ] Proyecto correcto configurado: `gcloud config get-value project`

### Resultados vacíos o incompletos

**Posibles causas:**
1. **Sin conexión a internet**: Google Search grounding requiere conectividad
2. **Límites de API alcanzados**: Revisa cuotas en Cloud Console
3. **Tema demasiado amplio**: Intenta con tema más específico
   - ❌ "Ciencia" → ✅ "Machine Learning para NLP"
4. **Nivel inadecuado**: Advanced con tema simple puede no encontrar libros

### Archivo _LIMITED.txt generado

**Significado:**
El sistema alcanzó límites máximos sin lograr calidad ideal.

**Acciones recomendadas:**
1. Ejecuta nuevamente con tema más específico
2. Ajusta nivel del usuario (`--level`)
3. Complementa manualmente con búsqueda adicional de libros

## 📝 Licencia

Este proyecto está bajo la **Licencia MIT**. Ver el archivo [LICENSE](LICENSE) para más detalles.

```
MIT License

Copyright (c) 2025 Plan de Estudio Agéntico

Se concede permiso para usar, copiar, modificar, fusionar, publicar,
distribuir, sublicenciar y/o vender copias del software sin restricciones.
```

## 👤 Autoría y Desarrollo

**Diseño y Arquitectura:** Jean Carlo Gómez Ponce
- Conceptualización del sistema agéntico
- Diseño de workflow con LangGraph
- Decisiones de arquitectura y flujo
- Dirección del desarrollo
- Especificaciones técnicas y correcciones

**Implementación:** Código generado con Claude AI (Anthropic) bajo supervisión y especificaciones del autor

**Nota sobre el uso de IA:** Este proyecto fue desarrollado mediante pair programming con IA. El diseño, la arquitectura, las decisiones técnicas y la lógica del workflow son del autor humano. La implementación del código fue asistida por Claude AI siguiendo las especificaciones proporcionadas.

**Repositorio:** [https://github.com/j840425/plan-estudio](https://github.com/j840425/plan-estudio)

## 🙏 Agradecimientos

- [Anthropic](https://anthropic.com) por Claude AI, asistente en el desarrollo del código
- [LangChain](https://langchain.com) por el framework de LLMs y herramientas
- [LangGraph](https://github.com/langchain-ai/langgraph) por el sistema de workflows con estado
- [Google Cloud](https://cloud.google.com) por Vertex AI y Gemini 2.5 Flash
- [Google Search](https://developers.google.com/) por la integración de búsqueda en tiempo real
- Comunidad de open source por librerías fundamentales

## 📧 Contacto

**¿Preguntas o problemas?**
- Abre un **issue** en el [repositorio](https://github.com/j840425/plan-estudio/issues)
- Revisa la sección de **Troubleshooting** más arriba
- Consulta la documentación de [LangGraph](https://langchain-ai.github.io/langgraph/)

---

⭐ Si este proyecto te fue útil, considera darle una **estrella** en GitHub

**Versión:** 1.0.0 | **Última actualización:** Octubre 2025
