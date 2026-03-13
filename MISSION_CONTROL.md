# AVENGERS — MISSION CONTROL
> **El mapa de ruta completo de la Factoría de Software Autónoma**
> **Versión**: 0.3.0 · Estado: Backlog Activo · Última actualización: 2026-03-13

---

## 🛡️ Enmiendas de Resiliencia y Seguridad (v0.3.0)

Aplicadas a los prompts 03-16. Cada prompt afectado las declara explícitamente.

| ID | Nombre | Prompts Afectados | Descripción |
|---|---|---|---|
| **AMD-01** | Root Jail | 11, 12, 13, 16 | Toda I/O de archivos restringida al `PROJECT_ROOT`. `RootJailViolationError` en violación. `tools/file_tools.resolve_safe_path()` es la única puerta de entrada. |
| **AMD-02** | Fury Retry Logic | 03, 04, 05 | Nick Fury reintenta agentes fallidos hasta 3 veces con backoff exponencial (2s, 4s, 8s). Al agotar → `status=FAILED` + Checkpoint `[👤 HUMANO]`. Modelo `RetryPolicy` en `core/models.py`. |
| **AMD-03** | Cap's MAP.yaml | 09, 10 | Cap. América genera `missions/{id}/MAP.yaml` con `FileEntry` "pending" por módulo. Nick Fury verifica su existencia antes de avanzar a Fase 3. Hulk actualiza `line_count` al crear cada archivo. |
| **AMD-04** | API-Fabricator Invocation | 12, 16 | Iron-Coder detecta `ApiEndpoint.known_api=False` en el Blueprint → invoca `ApiFabricatorAgent.generate_connector()` antes de generar el módulo. Nunca improvisa un conector. |
| **AMD-05** | Strict Persistence | 02, 03, 04 | El State Log NO es efímero. Cada `append()` o cambio de `mission.status` dispara `await repo.save_mission(mission)`. `StatePersistenceError` si falla. Recovery via `resume_from_checkpoint()`. |

---

## 🗺️ Visión de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────────┐
│  INTERNET PROFUNDO                                                  │
│  (foros, Discord, Reddit, X, GitHub Issues)                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ señales
                               ▼
┌──────────── FASE 1 ───────────────────────────────────────────────┐
│  SISTEMA NERVIOSO CENTRAL                                          │
│  Nick Fury (Orquestador) · State Log · Token Budget · Checkpoints │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ misión asignada
                               ▼
┌──────────── FASE 2 ───────────────────────────────────────────────┐
│  EQUIPO DE ESTRATEGIA                                              │
│  Thor (Scraping) ──► Cap. América (Blueprint JSON)                │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ blueprint aprobado
                               ▼
┌──────────── FASE 3 ───────────────────────────────────────────────┐
│  LA FÁBRICA                        [paralelo]                      │
│  Iron-Coder (Backend/Tools) ◄──────────────► Vision-UI (Frontend) │
│  API-Fabricator (Conectores)                                       │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ artefactos generados
                               ▼
┌──────────── FASE 4 ───────────────────────────────────────────────┐
│  SISTEMA DE CALIDAD                                                │
│  Black Widow (Refactor/QA) · Hulk (Guardrail 300L · Anti-Alucin.) │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ código aprobado
                               ▼
┌──────────── FASE 5 ───────────────────────────────────────────────┐
│  CICLO DE CIERRE                                                   │
│  Deploy (Vercel/Cloud) · El Infiltrado (Growth) · Feedback Loop   │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ nueva señal de mercado
                               └──────────────────► FASE 1 (∞)
```

---

## 📋 Backlog de Ejecución — Índice Maestro

Cada prompt está guardado en `docs/backlog/`. Lee el prompt completo antes de ejecutar.
**Regla absoluta**: ejecutar en orden. No saltar fases. Los checkpoints `[👤 HUMANO]` requieren tu aprobación.

---

### FASE 1 — Sistema Nervioso Central

| # | Archivo | Descripción | Agente | Checkpoint |
|---|---|---|---|---|
| 01 | `prompt_01_settings.md` | Config global: `pydantic-settings`, `.env`, constantes del sistema | Core | — |
| 02 | `prompt_02_db_layer.md` | Capa de datos: modelos MongoDB + repositorio async (motor) | Core | — |
| 03 | `prompt_03_fury_core.md` | **El Corazón de Nick Fury**: modelos Pydantic del State Log y MissionBlueprint | Nick Fury | — |
| 04 | `prompt_04_fury_orchestrator.md` | Motor del orquestador: ciclo de vida de misiones, token budget, dispatcher | Nick Fury | **[👤 HUMANO]** |
| 05 | `prompt_05_fury_checkpoints.md` | Sistema de Checkpoints: pausar ejecución, notificación, esperar aprobación | Nick Fury | **[👤 HUMANO]** |

---

### FASE 2 — Equipo de Estrategia

| # | Archivo | Descripción | Agente | Checkpoint |
|---|---|---|---|---|
| 06 | `prompt_06_thor_scraper.md` | Thor Base: motor de scraping dinámico con httpx + HTML parser | Thor | — |
| 07 | `prompt_07_thor_sources.md` | Thor Sources: conectores Reddit, X/Twitter, foros HackerNews | Thor | — |
| 08 | `prompt_08_thor_pain_extractor.md` | Thor LLM: extractor de "dolores" con prompt estructurado → `brief.yaml` | Thor | **[👤 HUMANO]** |
| 09 | `prompt_09_cap_blueprint_schema.md` | Cap Esquema: definir el schema JSON del Blueprint (Pydantic v2) | Cap. América | — |
| 10 | `prompt_10_cap_blueprint_generator.md` | Cap Generator: LLM que convierte `brief.yaml` → `blueprint.yaml` validado | Cap. América | **[👤 HUMANO]** |

---

### FASE 3 — La Fábrica

| # | Archivo | Descripción | Agente | Checkpoint |
|---|---|---|---|---|
| 11 | `prompt_11_iron_tools_base.md` | Iron-Coder Tools: herramientas atómicas (leer/escribir archivos, ejecutar comandos) | Iron-Coder | — |
| 12 | `prompt_12_iron_backend_gen.md` | Iron-Coder Backend: generador de módulos FastAPI a partir del Blueprint | Iron-Coder | — |
| 13 | `prompt_13_iron_test_gen.md` | Iron-Coder Tests: generador automático de tests pytest por módulo | Iron-Coder | — |
| 14 | `prompt_14_vision_ui_base.md` | Vision-UI Base: setup Atomic Design (atoms/molecules/organisms) | Vision-UI | **[👤 HUMANO]** |
| 15 | `prompt_15_vision_ui_gen.md` | Vision-UI Generator: generador de componentes React a partir del Blueprint | Vision-UI | — |
| 16 | `prompt_16_api_fabricator.md` | API-Fabricator: lector de OpenAPI/README → conector Python auto-generado | API-Fabricator | — |

---

### FASE 4 — Sistema de Calidad

| # | Archivo | Descripción | Agente | Checkpoint |
|---|---|---|---|---|
| 17 | `prompt_17_hulk_guardrail.md` | Hulk Guardrail: validador de 300 líneas, detector de imports no usados | Hulk | — |
| 18 | `prompt_18_hulk_hallucination.md` | Hulk Anti-Alucinación: validador de referencias, libs y endpoints inventados | Hulk | — |
| 19 | `prompt_19_widow_refactor.md` | Widow Refactor: fragmentador automático de archivos masivos | Black Widow | — |
| 20 | `prompt_20_widow_qa.md` | Widow QA: runner de tests, reporte de cobertura, PR check | Black Widow | **[👤 HUMANO]** |

---

### FASE 5 — Ciclo de Cierre

| # | Archivo | Descripción | Agente | Checkpoint |
|---|---|---|---|---|
| 21 | `prompt_21_deploy_pipeline.md` | Pipeline CI/CD: GitHub Actions → Vercel/Railway deploy automático | Core | **[👤 HUMANO]** |
| 22 | `prompt_22_infiltrado_social.md` | Infiltrado Social: poster automático en X y Reddit con el producto | El Infiltrado | **[👤 HUMANO]** |
| 23 | `prompt_23_infiltrado_feedback.md` | Infiltrado Feedback: colector de métricas y comentarios → nuevo `brief.yaml` | El Infiltrado | — |
| 24 | `prompt_24_loop_close.md` | Loop Closure: Nick Fury procesa el feedback y lanza la siguiente misión (∞) | Nick Fury | **[👤 HUMANO]** |

---

## 🔴 Checkpoints Humanos — Resumen

```
Fase 1 ──► [04] Orquestador listo         → Validar lógica de dispatch
            [05] Checkpoints activos       → Confirmar flujo de aprobación
Fase 2 ──► [08] Brief generado por Thor   → Validar calidad del research
            [10] Blueprint de Cap listo    → APROBAR ANTES DE CODEAR
Fase 3 ──► [14] UI Design System listo    → Validar identidad visual
Fase 4 ──► [20] QA report final           → Validar cobertura mínima (80%)
Fase 5 ──► [21] Deploy pipeline           → Confirmar destino de deploy
            [22] Social posting           → Aprobar mensajes de marketing
            [24] Nuevo ciclo              → Autorizar gasto de tokens
```

---

## 💡 Reglas de Ejecución del Backlog

1. **Un prompt = una sesión de Copilot**. No acumular prompts en una misma conversación.
2. **Cada sesión empieza con**: `"Lee .github/copilot-instructions.md y ARCHITECTURE.md"`
3. **Protocolo Hulk** activo en todo momento: rechazar > 300 líneas sin modularización previa.
4. **Protocolo Widow** al finalizar cada módulo: cero código muerto antes de pasar al siguiente.
5. **Sin Blueprint aprobado = sin código**. El Prompt #10 es el gating de todo el sistema.
6. **Los Checkpoints `[👤 HUMANO]` son bloqueantes**. El sistema no avanza sin tu `OK`.
7. **AMD-01 ROOT JAIL**: Todo I/O de archivos pasa por `tools/file_tools.resolve_safe_path()`.
8. **AMD-02 RETRY LOGIC**: Nick Fury reintenta hasta 3 veces (backoff 2s/4s/8s) antes de FAILED.
9. **AMD-03 CAP'S MAP**: `MAP.yaml` debe existir antes de despachar Fase 3.
10. **AMD-04 API-FABRICATOR**: `known_api=False` → invocar Fabricator, nunca improvisar.
11. **AMD-05 PERSISTENCIA**: `repo.save_mission()` es obligatorio tras cada cambio de estado.

---

## 📊 Métricas de Éxito del Sistema

| Métrica | Target |
|---|---|
| Tiempo Brief → Blueprint | < 5 min |
| Tiempo Blueprint → MVP Backend | < 30 min |
| Cobertura de tests | ≥ 80% |
| Archivos > 300 líneas | 0 |
| Código muerto post-Widow | 0% |
| Misiones completadas / semana | ≥ 3 |

---

*"El plan no es perfecto. Pero existe. Y eso ya es una ventaja táctica."* — Nick Fury
