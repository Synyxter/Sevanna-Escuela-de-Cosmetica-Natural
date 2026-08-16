# Sevanna Backend

API del núcleo de negocio de **Sevanna**, plataforma web de una academia de
cosmética natural. Construida con **Python + FastAPI**, PostgreSQL, SQLAlchemy 2
(async) y Alembic. Expone un contrato REST/JSON versionado (`/api/v1`) que el
frontend consume sin conocer nada de la base de datos, los proveedores de pago o
de correo, ni la lógica interna.

---

## Tabla de contenido
- [Requisitos](#requisitos)
- [Arquitectura](#arquitectura)
- [Instalación local](#instalación-local)
- [Variables de entorno](#variables-de-entorno)
- [Migraciones](#migraciones)
- [Datos de ejemplo (seed)](#datos-de-ejemplo-seed)
- [Ejecución](#ejecución)
- [Docker](#docker)
- [Tests](#tests)
- [Calidad de código](#calidad-de-código)
- [Endpoints principales](#endpoints-principales)
- [Decisiones de diseño](#decisiones-de-diseño)

---

## Requisitos
- Python **3.12+**
- PostgreSQL **14+** (para producción; los tests usan SQLite en memoria)
- Docker + Docker Compose (opcional)

## Arquitectura

Arquitectura por capas con separación estricta de responsabilidades:

```
API (routers)  ->  Services (lógica de negocio)  ->  Repositories  ->  Models  ->  PostgreSQL
                        │
                        └── Integrations (pagos / correo / almacenamiento) desacopladas por interfaz
```

- **Routers** (`app/api/v1`): controladores delgados; validan y delegan.
- **Services** (`app/services`): toda la lógica de negocio y las reglas críticas.
- **Repositories** (`app/repositories`): acceso a datos encapsulado.
- **Models** (`app/models`): SQLAlchemy 2 tipado (`Mapped` / `mapped_column`).
- **Schemas** (`app/schemas`): contratos Pydantic v2 de entrada/salida.
- **Integrations** (`app/integrations`): `PaymentProvider` (Wompi / fake),
  `EmailProvider` (SMTP / consola) y `StorageProvider` (local), seleccionados por
  factory según configuración. El código de negocio depende solo de las interfaces.

## Instalación local

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env    # y edita los valores
```

## Prueba rápida local (SQLite + Swagger UI)

Para probar la API **sin instalar PostgreSQL**, usa una base SQLite local. En tu
`.env` define:

```env
DATABASE_URL=sqlite+aiosqlite:///./sevanna_dev.db
PAYMENT_PROVIDER=fake
EMAIL_PROVIDER=console
```

Luego, desde la raíz del proyecto (con el entorno virtual activado):

```bash
alembic upgrade head          # crea el esquema en SQLite
python -m scripts.seed        # admin + curso de ejemplo
uvicorn app.main:app --reload # levanta la API
```

Abre **http://localhost:8000/docs** (Swagger UI) para probar:

1. `POST /api/v1/auth/login` con el admin sembrado
   (`admin@sevanna.co` / la contraseña de `FIRST_ADMIN_PASSWORD`).
2. Copia `data.access_token`, pulsa **Authorize 🔒** y pégalo.
3. Explora el catálogo, crea una compra y simula el pago.

**Simular un pago (proveedor `fake`)**: tras `POST /api/v1/payments/create`,
confirma con `POST /api/v1/payments/webhook` enviando el header
`X-Fake-Signature: fake-secret` y el body:

```json
{ "reference": "<external_reference del pago>", "status": "APPROVED" }
```

> La misma migración funciona en SQLite (dev) y PostgreSQL (producción). El
> índice único parcial de inscripciones activas solo aplica en PostgreSQL.

## Variables de entorno

Todas las variables están documentadas en [`.env.example`](.env.example).
Nunca subas tu `.env`. Claves relevantes:

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Cadena async de PostgreSQL (`postgresql+asyncpg://...`) |
| `JWT_SECRET_KEY` | Secreto para firmar JWT (genera uno largo y aleatorio) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | Vida de los tokens |
| `CORS_ORIGINS` | Orígenes del frontend permitidos (coma-separados) |
| `PAYMENT_PROVIDER` | `wompi` o `fake` |
| `PAYMENT_*` | Llaves de Wompi (privada, pública, integridad, eventos) |
| `EMAIL_PROVIDER` | `smtp` o `console` |
| `SMTP_*` | Credenciales SMTP si usas `smtp` |
| `FIRST_ADMIN_*` | Admin inicial para el seed |

## Migraciones

El esquema se gestiona **exclusivamente** con Alembic.

```bash
alembic upgrade head          # aplica todas las migraciones
alembic revision -m "mensaje" # crea una nueva revisión
alembic downgrade -1          # revierte la última
```

> La migración inicial (`0001_initial`) crea todas las tablas, índices y el
> índice único parcial que impide dos inscripciones **activas** para el mismo
> usuario y curso.

## Datos de ejemplo (seed)

Crea el admin inicial y un curso publicado de ejemplo (idempotente):

```bash
python -m scripts.seed
```

## Ejecución

```bash
uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Documentación OpenAPI: `http://localhost:8000/docs` y `/redoc`
- Esquema: `http://localhost:8000/openapi.json`

> En producción, `ENABLE_DOCS=false` oculta `/docs`, `/redoc` y `/openapi.json`.

## Docker

Levanta API + PostgreSQL (aplica migraciones automáticamente al iniciar):

```bash
docker compose up --build
```

Luego, para el seed:

```bash
docker compose exec api python -m scripts.seed
```

## Tests

Los tests corren contra SQLite en memoria (async) y usan los proveedores
`fake`/`console`, sin depender de servicios externos:

```bash
pytest
```

Incluye el **flujo completo de integración** (`tests/test_full_flow.py`):
registro → curso → compra → pago → webhook → inscripción → mis cursos → acceso,
más idempotencia del webhook y rechazo de firmas inválidas.

## Calidad de código

```bash
ruff check .
ruff format .
```

## Endpoints principales

Todos bajo el prefijo `/api/v1`. Respuestas con envelope consistente:

```json
{ "success": true, "data": { }, "message": "..." }
```

```json
{ "success": false, "error": { "code": "COURSE_NOT_FOUND", "message": "..." } }
```

**Auth**
```
POST /auth/register    POST /auth/login      POST /auth/refresh
POST /auth/logout      POST /auth/verify-email
POST /auth/forgot-password    POST /auth/reset-password
```

**Usuario** (identidad tomada del token, nunca del cliente)
```
GET   /users/me        PATCH /users/me
GET   /users/me/courses    GET /users/me/purchases
```

**Cursos públicos**
```
GET /courses            (paginación, búsqueda, filtros, orden)
GET /courses/featured
GET /courses/{slug}
GET /categories
```

**Compras / Pagos**
```
POST /purchases         GET /purchases/{id}
POST /payments/create   POST /payments/webhook   GET /payments/{id}
```

**Inscripciones**
```
GET /enrollments/{id}          GET /enrollments/{id}/access
```

**Administración** (requiere rol `ADMIN`)
```
GET/POST/GET/PATCH/DELETE /admin/courses[/{id}]
POST /admin/categories
GET  /admin/users     GET /admin/purchases     GET /admin/enrollments
```

**Health**
```
GET /health   GET /health/live   GET /health/ready
```

## Decisiones de diseño

- **Precio congelado**: la compra guarda el precio vigente al momento de comprar
  (`Purchase.amount`); cambios posteriores del curso no alteran compras históricas.
- **El backend es la fuente de verdad**: el estado definitivo del pago proviene
  del **webhook verificado** del proveedor, nunca del frontend.
- **Idempotencia**: un webhook repetido no crea compras, inscripciones ni correos
  duplicados (bloqueo de fila + verificación de estado + constraints únicos).
- **Transaccionalidad**: confirmar pago → `Purchase = PAID` → crear `Enrollment`
  ocurre en una sola transacción con `SELECT ... FOR UPDATE` sobre la compra.
- **Resiliencia a fallos externos**: si el correo falla, el pago y la inscripción
  permanecen válidos (`EmailLog` registra `PENDING/SENT/FAILED` con reintentos).
- **Seguridad**: Argon2id para contraseñas, JWT access/refresh con revocación,
  CORS restringido, rate limiting en endpoints sensibles, sin fugas de stack
  traces ni secretos, y protección contra enumeración de usuarios.
- **Desacople**: pagos, correo y almacenamiento tras interfaces; cambiar de
  proveedor no toca la lógica de negocio.
