# UI Style Guide — AVENGERS Design System

> **Vision-UI Memory** · Versión 1.0.0 · Enforced por Protocolo Hulk UI

---

## 1. Paleta de Colores

| Token CSS | Hex | Uso semántico |
|---|---|---|
| `--color-primary` | `#3B82F6` | Acciones principales, CTAs, links activos |
| `--color-secondary` | `#6B7280` | Textos secundarios, bordes, placeholders |
| `--color-danger` | `#EF4444` | Errores, alertas destructivas, validaciones fallidas |
| `--color-success` | `#10B981` | Confirmaciones, estados OK, badges positivos |

Variantes de brillo se derivan multiplicando la opacidad: `--color-primary` al 10% → fondos sutiles.

---

## 2. Tipografía

| Rol | Fuente | CSS Token |
|---|---|---|
| Cuerpo | Inter | `--font-body` |
| Código / Mono | JetBrains Mono | `--font-mono` |

### Escala de tamaños

| Alias | `font-size` | `line-height` | Uso |
|---|---|---|---|
| `xs` | 0.75 rem | 1 rem | Labels, badges |
| `sm` | 0.875 rem | 1.25 rem | Texto de apoyo, captions |
| `md` | 1 rem | 1.5 rem | Cuerpo de texto base |
| `lg` | 1.125 rem | 1.75 rem | Subtítulos de sección |
| `xl` | 1.25 rem | 1.75 rem | Títulos de card |
| `2xl` | 1.5 rem | 2 rem | Headings de página |

### Pesos

- **400** — Regular (cuerpo)
- **500** — Medium (labels, botones)
- **700** — Bold (headings)

---

## 3. Espaciado

Grid base de **8 px** (`--spacing-base: 8px`).

| Escala | Valor | CSS custom property |
|---|---|---|
| `1` | 8 px | `calc(var(--spacing-base) * 1)` |
| `2` | 16 px | `calc(var(--spacing-base) * 2)` |
| `3` | 24 px | `calc(var(--spacing-base) * 3)` |
| `4` | 32 px | `calc(var(--spacing-base) * 4)` |
| `6` | 48 px | `calc(var(--spacing-base) * 6)` |
| `8` | 64 px | `calc(var(--spacing-base) * 8)` |

### Breakpoints

| Alias | Min-width | Uso |
|---|---|---|
| `sm` | 640 px | Móvil landscape / tablet pequeña |
| `md` | 768 px | Tablet |
| `lg` | 1024 px | Desktop |
| `xl` | 1280 px | Desktop ancho |
| `2xl` | 1536 px | Pantallas ultra-wide |

---

## 4. Convenciones de Componentes React

### Naming

- **Componente**: `PascalCase` → `Button`, `SearchBar`, `DataTable`
- **Props**: `camelCase` → `onClick`, `isDisabled`, `labelText`
- **Eventos handler**: prefijo `on` → `onSubmit`, `onChange`
- **Booleanos**: prefijo `is` / `has` → `isLoading`, `hasError`

### Estructura de archivos

```
src/components/atoms/Button/
  ├── index.tsx          ← Implementación del componente
  └── Button.test.tsx    ← Tests unitarios (React Testing Library)
```

Cada componente vive en su propia carpeta con `index.tsx` como punto de entrada.

---

## 5. Regla Hulk para UI

> **Ningún componente React puede superar las 150 líneas.**

Si un componente crece:

1. **DETENTE** — no escribas más líneas.
2. **IDENTIFICA** responsabilidades separables (lógica, presentación, sub-secciones).
3. **EXTRAE** sub-componentes en la misma carpeta o en el nivel Atomic correspondiente.
4. El componente padre solo ensambla sub-componentes y gestiona estado de alto nivel.

Ejemplos de extracción:
- `DataTable` (organismo) → extrae `TableHeader`, `TableRow`, `Pagination` como moléculas.
- `Modal` (organismo) → extrae `ModalOverlay`, `ModalContent`, `ModalFooter`.

---

## 6. Design Tokens — `src/styles/tokens.css`

Generado automáticamente por `UIScaffolder.generate_design_tokens()`. No editar a mano.
Editar `StyleGuide` en la misión activa y re-generar.

```css
:root {
  --color-primary: #3B82F6;   /* brand */
  --color-secondary: #6B7280;
  --color-danger: #EF4444;
  --color-success: #10B981;
  --spacing-base: 8px;
  --font-body: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --border-radius: 0.5rem;
}
```

`StyleGuide` se serializa a `missions/{mission_id}/style_guide.yaml` vía `file_tools.write_file()`.
