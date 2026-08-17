"""OpenAPI metadata: rich description and per-tag documentation.

Kept separate from the app factory to keep ``main.py`` focused on wiring.
"""

from __future__ import annotations

API_DESCRIPTION = """
API del backend de **Sevanna** — academia de cosmética natural.

Sevanna funciona como **catálogo de cursos**. La inscripción y el pago se
gestionan **por WhatsApp** (fuera del backend): en el frontend, al querer
inscribirse, el usuario ve un botón para escribir por WhatsApp, y por ese medio
se hace el registro, el pago y el envío de enlaces de clases y grupos.

Superficie activa del API:
- **Público:** catálogo de cursos (`/courses`, `/categories`) con filtros,
  búsqueda y paginación.
- **Admin:** gestión de cursos y categorías (`/admin/...`), previa autenticación.

> Los módulos de **cuentas de estudiante** y de **pagos/compras/inscripciones**
> están desactivados por defecto (se conservan en el código y se reactivan con
> las flags `ENABLE_ACCOUNTS` / `ENABLE_COMMERCE`).

### Cómo probar el admin desde esta interfaz

1. Inicia sesión en **`POST /api/v1/auth/login`** con el admin sembrado y copia
   el `access_token` (`data.access_token`).
2. Pulsa **Authorize** 🔒 y pega el token.
3. Gestiona el catálogo desde **`/api/v1/admin/courses`** y consulta el catálogo
   público en **`/api/v1/courses`**.

### Formato de respuestas

- Éxito: `{ "success": true, "data": ..., "message": "..." }`
- Error: `{ "success": false, "error": { "code": "...", "message": "..." } }`

Los valores de enums (nivel, modalidad, estados) son el contrato estable; el
frontend los traduce para mostrar.
"""

OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "Registro, login, refresh, logout, verificación y "
        "recuperación de contraseña.",
    },
    {
        "name": "users",
        "description": "Perfil propio, cursos adquiridos e historial de compras "
        "(identidad tomada del token).",
    },
    {
        "name": "courses",
        "description": "Catálogo público: listado con filtros, búsqueda y "
        "paginación, destacados y detalle por slug.",
    },
    {"name": "categories", "description": "Categorías públicas del catálogo."},
    {
        "name": "purchases",
        "description": "Creación y consulta de compras (precio congelado por el backend).",
    },
    {
        "name": "payments",
        "description": "Creación de pagos y webhook del proveedor (fuente de verdad, idempotente).",
    },
    {
        "name": "enrollments",
        "description": "Inscripciones y acceso a enlaces privados (WhatsApp/Google Meet).",
    },
    {
        "name": "admin",
        "description": "Gestión de catálogo, categorías, usuarios, compras e inscripciones "
        "(requiere rol ADMIN).",
    },
    {"name": "health", "description": "Sondeos de estado y disponibilidad."},
    {"name": "root", "description": "Información básica del servicio."},
]
