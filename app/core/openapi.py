"""OpenAPI metadata: rich description and per-tag documentation.

Kept separate from the app factory to keep ``main.py`` focused on wiring.
"""

from __future__ import annotations

API_DESCRIPTION = """
API del backend de **Sevanna** — academia de cosmética natural.

### Cómo probar desde esta interfaz

1. Crea una cuenta en **`POST /api/v1/auth/register`** (o usa el admin sembrado).
2. Inicia sesión en **`POST /api/v1/auth/login`**: copia el `access_token` de la
   respuesta (`data.access_token`).
3. Pulsa el botón **Authorize** 🔒 (arriba a la derecha) y pega el token.
   A partir de ahí, las peticiones protegidas usarán tu sesión.
4. Explora el catálogo, crea una compra, simula el pago y obtén el acceso.

> Con el proveedor de pagos en modo **`fake`** (desarrollo), el webhook se
> confirma enviando `POST /api/v1/payments/webhook` con el header
> `X-Fake-Signature: fake-secret` y body
> `{"reference": "<ref del pago>", "status": "APPROVED"}`.

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
