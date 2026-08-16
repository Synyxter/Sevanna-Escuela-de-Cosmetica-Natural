# Documento de Arquitectura — Sevanna Backend

> **Propósito de este documento**
> Es la fuente de verdad de la arquitectura del backend de Sevanna. Toda sesión
> de trabajo futura (humana o asistida por IA) debe leerlo antes de implementar
> cambios y **respetar las capas, convenciones y reglas de negocio aquí
> descritas**. Si un cambio requiere desviarse de este documento, primero se
> actualiza el documento y luego se implementa.

Última actualización: 2026-08-15 · Versión del backend: 0.1.0

---

## 1. Visión general

Sevanna es una plataforma web de una academia de cosmética natural. Este
repositorio es el **backend**: el núcleo de negocio que expone una API
REST/JSON versionada (`/api/v1`) consumida por el frontend. El frontend solo
presenta y consume el contrato; **toda la lógica de negocio vive en el backend**.

Prioridades de diseño (en orden):

> **Correctitud > Seguridad > Mantenibilidad > Escalabilidad > Rendimiento**

sin introducir complejidad innecesaria.

## 2. Stack técnico

| Área | Tecnología |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework | FastAPI |
| Servidor ASGI | Uvicorn |
| Validación / schemas | Pydantic v2 + pydantic-settings |
| ORM | SQLAlchemy 2.x (async, estilo `Mapped`/`mapped_column`) |
| Driver DB | asyncpg (PostgreSQL) · aiosqlite (solo tests) |
| Migraciones | Alembic (async) |
| Base de datos | PostgreSQL (producción) |
| Hashing | Argon2id (`argon2-cffi`) |
| Tokens | JWT (`PyJWT`) — access + refresh con revocación |
| HTTP externo | httpx (async) |
| Correo | aiosmtplib (SMTP async) |
| Tests | pytest + pytest-asyncio |
| Calidad | Ruff (lint + format) |
| Contenedores | Docker + docker-compose |

## 3. Arquitectura por capas

Regla de oro: **cada capa solo conoce a la inmediatamente inferior**. Los
endpoints son controladores delgados; no contienen lógica de negocio.

```
Cliente (Frontend)
      │  HTTPS · REST · JSON
      ▼
┌───────────────────────────────────────────────────────────┐
│ API  (app/api)                                             │
│   routers v1  →  validan entrada (schemas) y delegan       │
│   deps.py     →  sesión DB, usuario autenticado, guard admin│
├───────────────────────────────────────────────────────────┤
│ Services  (app/services)                                   │
│   TODA la lógica de negocio y las reglas críticas          │
├───────────────────────────────────────────────────────────┤
│ Repositories  (app/repositories)                           │
│   acceso a datos encapsulado (queries SQLAlchemy)          │
├───────────────────────────────────────────────────────────┤
│ Models  (app/models)  →  SQLAlchemy ORM  →  PostgreSQL     │
└───────────────────────────────────────────────────────────┘
      │
      └── Integrations (app/integrations): Pagos · Correo · Almacenamiento
          desacoplados por interfaz + factory (elegidos por configuración)
```

### Responsabilidad de cada capa

- **Routers** (`app/api/v1/*`): declaran método, ruta, entrada y `response_model`.
  Aplican autenticación/autorización y rate limiting vía dependencias. **No**
  acceden a la base de datos directamente ni contienen reglas de negocio.
- **Schemas** (`app/schemas/*`): contratos Pydantic de entrada y salida. Nunca
  se devuelven modelos SQLAlchemy directamente al cliente.
- **Services** (`app/services/*`): orquestan reglas de negocio, transacciones y
  llamadas a integraciones. Reciben una `AsyncSession` y repos.
- **Repositories** (`app/repositories/*`): construyen y ejecutan queries. Sin
  reglas de negocio.
- **Models** (`app/models/*`): entidades ORM con constraints e índices.
- **Integrations** (`app/integrations/*`): adaptadores a proveedores externos
  detrás de una interfaz abstracta.

## 4. Mapa del proyecto

```
app/
├── main.py                 # Application factory: middleware, CORS, errores, router
├── core/                   # Config, seguridad, DB, logging, middleware, rate limit, excepciones
├── api/
│   ├── deps.py             # Dependencias: get_db, get_current_user, get_current_admin
│   ├── router.py           # Agrega routers bajo /api/v1
│   └── v1/                 # auth, users, courses, categories, purchases, payments, enrollments, admin, health
├── models/                 # ORM + enums (vocabularios controlados)
├── schemas/                # Pydantic (contratos I/O) + common (envelope, paginación)
├── services/               # Lógica de negocio
├── repositories/           # Acceso a datos
└── integrations/
    ├── payments/           # base(interfaz) · wompi · fake · factory
    ├── email/              # base · smtp · console · factory
    └── storage/            # base · local · factory
migrations/                 # Alembic (env.py async + versions/)
scripts/seed.py             # Bootstrap admin + datos de ejemplo (idempotente)
tests/                      # Unit + integración (SQLite en memoria)
docs/                       # Este documento + flujo git + consideraciones
```

## 5. Ciclo de vida de una petición privada

```
Request → RequestContextMiddleware (asigna X-Request-ID, loguea)
        → CORS → Router
        → Depends(get_current_user)   # identidad SIEMPRE desde el token JWT
        → [Depends(rate_limit)]        # en endpoints sensibles
        → validación Pydantic
        → Service (lógica + transacción)
        → Repository → PostgreSQL
        → Service devuelve modelos
        → Router serializa con schema Pydantic → envelope JSON
        → Response (+ X-Request-ID)
```

Nunca `Request → Database` sin autenticación/validación.

## 6. Formato de respuesta (contrato)

Éxito:
```json
{ "success": true, "data": { }, "message": "Operación realizada correctamente" }
```
Error (nunca expone stack traces, SQL ni secretos):
```json
{ "success": false, "error": { "code": "COURSE_NOT_FOUND", "message": "..." }, "request_id": "..." }
```
Paginación (`data`):
```json
{ "items": [], "pagination": { "page": 1, "limit": 12, "total": 57, "total_pages": 5 } }
```

Los errores de negocio usan códigos HTTP correctos (400/401/403/404/409/422/429/5xx),
nunca `200` para un error. Ver `app/core/exceptions.py`.

## 7. Modelo de datos

Entidades y relaciones principales:

```
User 1───N Purchase N───1 Course N───1 Category
             │1
             │
             ▼1
          Payment

User 1───N Enrollment N───1 Course
                 │1
                 ▼1
             Purchase   (una inscripción se origina en una compra pagada)
```

Auxiliares: `RefreshToken`, `PasswordResetToken`, `EmailVerificationToken`,
`AuditLog`, `EmailLog`.

### Vocabularios controlados (`app/models/enums.py`)
Estos valores son **el contrato estable**; el frontend los traduce para mostrar.

- `UserRole`: STUDENT, ADMIN (+ reservados: TEACHER, MANAGER, SUPPORT)
- `CourseModality`: PRESENTIAL, ONLINE, HYBRID
- `CourseLevel`: BEGINNER, INTERMEDIATE, ADVANCED
- `CourseStatus`: DRAFT, PUBLISHED, ARCHIVED
- `PurchaseStatus`: PENDING, PAID, FAILED, CANCELLED, REFUNDED
- `PaymentStatus`: PENDING, APPROVED, DECLINED, ERROR, VOIDED, REFUNDED
- `EnrollmentStatus`: ACTIVE, CANCELLED, COMPLETED
- `EmailStatus`: PENDING, SENT, FAILED

### Integridad garantizada por la base de datos
- Email de usuario único; slug de curso único; `external_reference` de pago único.
- `external_transaction_id` de pago único (soporte de idempotencia).
- Índice único **parcial**: una sola inscripción `ACTIVE` por `(user, course)`.
- Dinero en `Numeric(12,2)` (`Decimal`), **nunca `float`**; moneda explícita.

## 8. Reglas críticas de negocio (obligatorias)

Están implementadas en la capa de servicios y **no deben romperse**:

1. No se puede comprar un curso inexistente. → `PurchaseService`
2. No se accede a un curso no adquirido (compra PAID + inscripción ACTIVE). → `EnrollmentService`
3. Un curso no publicado no aparece en el catálogo público. → `CourseService`/repos
4. **El precio final proviene del backend y se congela en la compra**
   (`Purchase.amount`); cambios posteriores del curso no alteran compras históricas.
5. El frontend **no** determina si un pago fue exitoso.
6. El webhook del proveedor se verifica (firma) antes de procesarse.
7. Un webhook repetido no duplica compras, inscripciones ni correos (idempotencia).
8. Una compra pagada genera exactamente una inscripción.
9. Una inscripción activa permite obtener los enlaces privados (WhatsApp/Meet).
10. El envío del correo **no** determina el estado del pago (procesos independientes).

### Flujo de compra (transaccional e idempotente)
```
Purchase=PENDING → crear pago (proveedor) → usuario paga → webhook verificado
  → [transacción + SELECT ... FOR UPDATE sobre la compra]
       Purchase=PAID → crear Enrollment=ACTIVE
  → agendar correo (background, con reintentos y EmailLog)
```
Si el proveedor de correo falla: la compra e inscripción siguen válidas; el
`EmailLog` queda en FAILED/PENDING para reintento. Ver `app/services/payment_service.py`.

## 9. Seguridad

- Contraseñas con **Argon2id**; nunca en texto plano ni en logs.
- **JWT** access (corto) + refresh (largo). Los refresh se registran en DB y se
  revocan en logout y al cambiar contraseña; el refresh **rota** en cada uso.
- Identidad **siempre desde el token** (`/users/me/...`), nunca un `user_id` del
  cliente.
- **CORS** restringido a orígenes del frontend por variable de entorno (nunca `*`
  con credenciales).
- **Rate limiting** por dependencia en `login`, `register`, `forgot-password`,
  `payments/create` y `payments/webhook`.
- **Anti-enumeración** en `forgot-password` (respuesta genérica).
- Webhooks: validación de firma antes de procesar.
- Sin fugas: manejador global de errores devuelve mensajes seguros; logging
  estructurado sin secretos ni tokens completos.

## 10. Integraciones (cómo cambiar/añadir un proveedor)

Cada integración define una **interfaz abstracta** + implementaciones + un
**factory** que elige según configuración. El código de negocio depende solo de
la interfaz.

- **Pagos** (`app/integrations/payments/`): `PaymentProvider` con
  `create_payment`, `verify_and_parse_webhook`, `verify_payment`,
  `refund_payment`. Implementaciones: `wompi` (real, Colombia/COP) y `fake`
  (tests/desarrollo). Seleccionado por `PAYMENT_PROVIDER`.
- **Correo** (`app/integrations/email/`): `EmailProvider.send`. Implementaciones:
  `smtp` y `console`. Seleccionado por `EMAIL_PROVIDER`.
- **Almacenamiento** (`app/integrations/storage/`): `StorageProvider` con
  `upload`/`delete`/`get_url`. Implementación: `local`. Las imágenes se guardan
  como URL/referencia, **no** como binario en PostgreSQL.

Para añadir un proveedor: implementa la interfaz, regístralo en el `factory`,
y agrega su valor al enum de configuración. **No** toques la lógica de negocio.

## 11. Configuración

Toda la configuración proviene de variables de entorno vía `pydantic-settings`
(`app/core/config.py`). Los secretos nunca se hardcodean. Documentadas en
`.env.example`. Ambientes: development / testing / staging / production. En
producción `ENABLE_DOCS=false` oculta `/docs`, `/redoc`, `/openapi.json`.

## 12. Observabilidad

- Logging JSON estructurado (`app/core/logging.py`).
- `X-Request-ID` por petición (entrante o generado) para correlación
  frontend/backend, presente en logs y respuestas de error.
- Health checks: `/api/v1/health`, `/health/live`, `/health/ready` (verifica DB).
- `AuditLog` y `EmailLog` como registros persistentes de eventos relevantes.

## 13. Testing

- Suite en `tests/`, corre contra **SQLite en memoria** (async) con proveedores
  `fake`/`console` → sin servicios externos.
- Incluye el **flujo completo de integración** (registro → curso → compra → pago
  → webhook → inscripción → mis cursos → acceso) + idempotencia y firma inválida.
- Ejecutar: `pytest`. Lint: `ruff check .`

## 14. Despliegue

- `Dockerfile` (usuario no-root; aplica `alembic upgrade head` al iniciar) y
  `docker-compose.yml` (API + PostgreSQL, Redis opcional comentado).
- Preparado para escalado horizontal: sin estado crítico en memoria, sin
  variables globales de sesión. **Nota:** el rate limiting actual es en memoria
  por instancia; para multi-instancia migrar a Redis (ver `docs/CONSIDERACIONES.md`).

## 15. Convenciones de código

- Type hints en todo; validación estricta con Pydantic antes de la lógica.
- SQLAlchemy 2.0 con `Mapped`/`mapped_column`.
- Un router por dominio; servicios especializados por dominio.
- Nombres de dominio estables en la API; nunca exponer nombres internos de tablas.
- Ruff como linter/formatter (config en `pyproject.toml`).
- Toda modificación de esquema se hace con **una migración Alembic**, nunca a mano.

## 16. Evolución prevista (sin reconstruir el backend)

La base está diseñada para crecer hacia: módulos/lecciones de curso, materiales
educativos, certificados, progreso, evaluaciones, notificaciones, y roles
adicionales (TEACHER/MANAGER/SUPPORT ya reservados). Ver el detalle y el estado
pendiente en `docs/CONSIDERACIONES.md`.
