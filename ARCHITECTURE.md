# AVENGERS — Arquitectura de la Factoría de Software Autónoma

> **Versión**: 0.1.0 · **Estado**: Bootstrap / Infraestructura

---

## 1. Visión General

AVENGERS es una **Factoría de Software Autónoma** que transforma una idea de mercado en código
desplegable y documentado, sin intervención humana en el ciclo interno.
El sistema orquesta un pipeline de agentes LLM especializados que se pasan artefactos concretos
entre sí, manteniendo un **State Log** como única fuente de verdad compartida.

```
        ┌─────────────────────────────────────────────────────┐
        │                    NICK FURY                        │
        │              (Orquestador Central)                  │
        │   Gestiona misiones · Asigna agentes · State Log    │
        └──────────────────────┬──────────────────────────────┘
                               │
          ┌────────────────────▼────────────────────┐
          │            BUCLE INFINITO               │
          │                                         │
          │  ① THOR          → Brief de Mercado     │
          │  ② CAP. AMERICA  → Blueprint Técnico    │
          │  ③ IRON-CODER    → Código / Artefacto   │
          │  ④ BLACK WIDOW   → Refactorización      │
          │  ⑤ EL INFILTRADO → Auditoría Final      │
          │         │                               │
          │         └──── ¿Aprobado? ──No──► ①     │
          │                      │                  │
          │                     Sí                  │
          └──────────────────────┼──────────────────┘
                                 ▼
                         output/ (Artefacto Final)
```

---

## 2. El Bucle Infinito: Detalle de Cada Fase

### Fase 1 — Thor: Investigación de Mercado
- **Entrada**: Idea o keyword del usuario.
- **Proceso**: Consulta fuentes (Reddit, X/Twitter, APIs de tendencias).
- **Salida**: `brief.yaml` — Documento con problema, audiencia, competidores y puntos de dolor.
- **Protocolo JIT**: Solo recibe el brief inicial + herramientas de scraping.

### Fase 2 — Captain America: Planificación Técnica
- **Entrada**: `brief.yaml` de Thor.
- **Proceso**: Descompone el problema en módulos, define contratos de API, prioriza features (MoSCoW).
- **Salida**: `blueprint.yaml` — Especificación técnica con endpoints, modelos de datos y criterios de aceptación.
- **Protocolo JIT**: Solo recibe `brief.yaml` + plantilla de blueprint.

### Fase 3 — Iron-Coder: Implementación
- **Entrada**: `blueprint.yaml` de Cap.
- **Proceso**: Genera código Python/FastAPI siguiendo el Blueprint al pie de la letra.
  Respeta el límite de 300 líneas por archivo (Protocolo Hulk).
- **Salida**: Archivos `.py`, tests unitarios, `requirements` actualizados.
- **Protocolo JIT**: Solo recibe el blueprint del módulo en curso + State Log (últimas 50 entradas).

### Fase 4 — Black Widow: Refactorización
- **Entrada**: Output de Iron-Coder.
- **Proceso**: Ejecuta el **Protocolo Widow** — elimina código muerto, deduplica, corrige imports,
  verifica que ningún archivo supere 300 líneas.
- **Salida**: Código limpio, métricas de reducción de complejidad.
- **Protocolo JIT**: Solo recibe los archivos modificados por Iron-Coder en esta iteración.

### Fase 5 — El Infiltrado: Auditoría
- **Entrada**: Output de Black Widow.
- **Proceso**: Revisa regresiones, vulnerabilidades de seguridad (OWASP Top 10),
  alucinaciones de código (referencias a libs inexistentes, endpoints inventados) y cobertura de tests.
- **Salida**: `audit_report.yaml` — Aprobado (→ `output/`) o Rechazado (→ regresa a Fase 1 con notas).
- **Protocolo JIT**: Solo recibe el diff de la iteración + checklist de auditoría.

---

## 3. Higiene de Contexto: Prevención de Alucinaciones

### El Problema
Los LLMs alucinan cuando reciben contexto masivo, contradictorio o irrelevante.
En un sistema multi-agente mal diseñado, el contexto crece exponencialmente entre fases,
acumulando "ruido" que degrada la calidad de las respuestas.

### La Solución: Inyección JIT

```
❌ MALO  — Contexto Acumulativo
   Agente recibe: historial completo (fase 1 + 2 + 3 + todos los errores anteriores)
   Resultado: confusión, contradicciones, código que mezcla contextos

✅ BUENO — Inyección Just-In-Time
   Agente recibe: Blueprint propio (contrato) + State Log (últimas 50 entradas)
   Resultado: foco absoluto, output predecible, trazable
```

### Mecanismos de Higiene

| Mecanismo | Descripción |
|---|---|
| **Límite 300 líneas** | Fuerza modularidad; ningún archivo puede volverse un "god file" |
| **Blueprints como contratos** | Cada agente sabe exactamente qué input espera y qué output produce |
| **State Log con TTL** | El historial se trunca a las últimas 50 entradas para evitar context overflow |
| **Protocolo Widow** | Limpieza activa de código muerto que podría confundir al siguiente agente |
| **Protocolo Hulk** | Rechaza generar archivos masivos antes de que contaminan el repo |
| **Auditor Independiente** | El Infiltrado nunca vio las fases anteriores; sus ojos son frescos |

---

## 4. Estructura de Directorios

```
avengers/
├── .github/
│   ├── copilot-instructions.md   # ← Ancla de Realidad (fuente de verdad para Copilot)
│   └── workflows/                # CI/CD pipelines
├── agents/                       # Un archivo por agente (≤ 300 líneas c/u)
│   ├── nick_fury.py
│   ├── thor.py
│   ├── captain_america.py
│   ├── iron_coder.py
│   ├── black_widow.py
│   └── infiltrado.py
├── blueprints/                   # Contratos YAML por agente y misión
├── missions/                     # State Logs de misiones activas
├── core/                         # Orquestador, modelos base, router
├── tools/                        # Herramientas atómicas reutilizables
├── docs/                         # Documentación técnica extendida
├── output/                       # Artefactos finales (gitignored)
├── .env.example                  # Plantilla de variables de entorno
├── pyproject.toml                # Dependencias y configuración de tooling
├── .gitignore
└── ARCHITECTURE.md               # Este archivo
```

---

## 5. Flujo de Datos: State Log

El **State Log** es un documento JSON/YAML versionado que actúa como memoria compartida mínima:

```yaml
# missions/mission-001.yaml (ejemplo)
mission_id: "mission-001"
status: "in_progress"          # idle | in_progress | review | done | failed
current_phase: 3               # 1=Thor 2=Cap 3=IronCoder 4=Widow 5=Infiltrado
created_at: "2026-03-12T00:00:00Z"
updated_at: "2026-03-12T23:00:00Z"
brief_ref: "briefings/001-brief.yaml"
blueprint_ref: "blueprints/001-blueprint.yaml"
log:                           # Últimas 50 entradas (TTL)
  - ts: "2026-03-12T20:00:00Z"
    agent: "thor"
    event: "brief_generated"
    artifact: "briefings/001-brief.yaml"
  - ts: "2026-03-12T21:00:00Z"
    agent: "captain_america"
    event: "blueprint_created"
    artifact: "blueprints/001-blueprint.yaml"
```

---

## 6. Decisiones de Diseño (ADRs)

### ADR-001: Motor async para MongoDB
**Decisión**: Usar `motor` (async driver) en lugar de `pymongo` síncrono.
**Razón**: FastAPI es async-first; bloquear el event loop con pymongo destruiría el rendimiento.

### ADR-002: Pydantic v2 para Blueprints
**Decisión**: Los Blueprints se modelan como clases Pydantic v2.
**Razón**: Validación estricta en runtime evita que Iron-Coder reciba un Blueprint malformado.

### ADR-003: Límite duro de 300 líneas
**Decisión**: Rechazar (no solo advertir) archivos que superen 300 líneas.
**Razón**: La modularidad forzada es el mecanismo principal de Higiene de Contexto.
Un archivo pequeño = un contexto coherente = menos alucinaciones.

---

*"No hay sistema perfecto. Hay sistemas con buena higiene."*
