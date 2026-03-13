# AVENGERS — Ancla de Realidad para GitHub Copilot
# Archivo: .github/copilot-instructions.md
# ⚠️  Este archivo es la fuente de verdad para todo agente de IA que trabaje en este repo.
#     Consulta este documento ANTES de generar cualquier código.

---

## 🎯 Visión del Proyecto

**AVENGERS** es una Factoría de Software Autónoma basada en un pipeline de agentes LLM especializados.
Cada agente tiene un rol único, un Blueprint de entrada y produce un artefacto concreto.
El sistema opera en un "Bucle Infinito" descrito en `ARCHITECTURE.md`.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Runtime | Python 3.12+ |
| API Framework | FastAPI + Uvicorn |
| Validación/Config | Pydantic v2 + pydantic-settings |
| HTTP Client | httpx (async) |
| Base de Datos | MongoDB (motor async) / PostgreSQL (SQLAlchemy async) |
| LLMs | OpenAI API · Anthropic API |
| Testing | pytest + pytest-asyncio |
| Linting | Ruff · mypy (strict) |

---

## 📐 Convenciones de Código

### Nomenclatura
- **snake_case** → variables, funciones, módulos, parámetros (`mission_id`, `run_pipeline`)
- **PascalCase** → clases, modelos Pydantic, excepciones (`NickFuryAgent`, `MissionBlueprint`)
- **SCREAMING_SNAKE_CASE** → constantes y vars de entorno (`MAX_CONTEXT_LINES`, `OPENAI_API_KEY`)
- **kebab-case** → nombres de archivo YAML/JSON de blueprints (`iron-coder-blueprint.yaml`)

### Estructura de Módulos
```
agents/         # Un archivo por agente (≤ 300 líneas)
blueprints/     # YAML/JSON con el contrato de cada agente
missions/       # State Logs de misiones activas
core/           # Router, orquestador, modelos base
tools/          # Herramientas atómicas (HTTP, DB, parsers)
docs/           # Documentación técnica
output/         # Artefactos generados (gitignored)
```

### Imports
```python
# 1. Stdlib
# 2. Third-party
# 3. Local — siempre absolutos desde raíz del proyecto
from agents.nick_fury import NickFuryAgent
from core.models import MissionBlueprint
```

---

## 🔴 PROTOCOLO WIDOW (Refactorización Obligatoria)

Activa cuando detectas cualquiera de las siguientes condiciones:

1. **Código muerto**: funciones/variables definidas pero nunca llamadas → **eliminar sin piedad**.
2. **Duplicación**: lógica idéntica en ≥ 2 lugares → **extraer a `tools/` o `core/`**.
3. **Comentarios obsoletos**: `# TODO`, `# FIXME`, `# old` sin fecha ni ticket → **eliminar o resolver**.
4. **Imports no utilizados**: ruff los detecta; corrígelos antes de cualquier PR.
5. **God Objects**: clases con >5 responsabilidades → **dividir siguiendo Single Responsibility**.

> Widow no pide permiso. Widow limpia.

---

## 🟢 PROTOCOLO HULK (Rechazo de Archivos Masivos)

**Regla absoluta: ningún archivo `.py` puede superar las 300 líneas.**

Si una tarea requiere generar o modificar un archivo que superaría este límite:

1. **DETENTE**. No escribas el archivo completo.
2. **PLANIFICA** la modularización: identifica responsabilidades separables.
3. **PROPÓN** una estructura de sub-módulos antes de implementar.
4. **ESPERA** confirmación antes de proceder.

Además, **rechaza** implementar:
- Lógica que no esté descrita en el Blueprint del agente correspondiente.
- Features que no existan en el State Log de la misión activa.
- Cambios que rompan el contrato de la API pública de un agente.

> Hulk no construye. Hulk aplasta lo que no cabe.

---

## 🤖 Agentes del Sistema

| Agente | Archivo | Responsabilidad |
|---|---|---|
| **Nick Fury** | `agents/nick_fury.py` | Orquestador. Asigna misiones, gestiona el State Log |
| **Thor** | `agents/thor.py` | Investigación. Analiza el mercado y genera el Brief |
| **Captain America** | `agents/captain_america.py` | Planificador. Convierte el Brief en Blueprint técnico |
| **Iron-Coder** | `agents/iron_coder.py` | Implementador. Genera código siguiendo el Blueprint |
| **Black Widow** | `agents/black_widow.py` | Refactorizador. Ejecuta el Protocolo Widow post-codificación |
| **El Infiltrado** | `agents/infiltrado.py` | Auditor. Busca regresiones, seguridad y alucinaciones |

---

## 📋 Inyección Just-In-Time (JIT Context)

Cada agente **SOLO debe recibir**:
1. Su `Blueprint` (el contrato de lo que debe hacer).
2. El `StateLog` actual de la misión (máx. últimas 50 entradas).

**Nunca** inyectar:
- El historial completo de conversación.
- Código de otros agentes no relacionados.
- Variables de entorno en crudo (usar `pydantic-settings`).

---

## ✅ Checklist Pre-Commit

- [ ] `ruff check . --fix` sin errores residuales
- [ ] `mypy .` sin errores en modo strict
- [ ] Ningún archivo `.py` > 300 líneas
- [ ] Tests nuevos para lógica nueva (`pytest -v`)
- [ ] Blueprint actualizado si cambió la interfaz del agente
- [ ] State Log de misión cerrado correctamente
