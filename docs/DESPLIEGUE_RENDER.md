# Despliegue en Render — Sevanna Backend

Guía para publicar la API (FastAPI + PostgreSQL) en **Render** y que el frontend
la consuma por HTTPS. El repositorio ya incluye `Dockerfile` y `render.yaml`.

> Yo no puedo crear tu cuenta ni ingresar tus credenciales. Tú haces los pasos
> marcados con 👤; el proyecto ya quedó preparado para que sean mínimos.

## 0. Requisitos
- 👤 Cuenta en **https://render.com** (puedes entrar con tu GitHub).
- Repo en GitHub: `Synyxter/Sevanna-Escuela-de-Cosmetica-Natural` (ya está).
- El despliegue usa la rama **`main`** (ya tiene todo lo último).

## 1. Crear los servicios con el Blueprint (recomendado)
1. 👤 En Render: **New +** → **Blueprint**.
2. 👤 Conecta y selecciona el repositorio de Sevanna.
3. Render detecta `render.yaml` y propone crear:
   - **sevanna-db** (PostgreSQL)
   - **sevanna-api** (servicio web Docker)
4. 👤 Pulsa **Apply**. Render construye la imagen y crea la base.

Al primer arranque, el contenedor ejecuta `alembic upgrade head` automáticamente
(crea las tablas). La app también normaliza la `DATABASE_URL` que inyecta Render.

## 2. Definir las variables manuales (secretas / propias)
En **sevanna-api → Environment**, define (quedaron como "sync: false"):

| Variable | Valor |
|---|---|
| `FIRST_ADMIN_PASSWORD` | una contraseña fuerte para el admin |
| `CORS_ORIGINS` | dominio(s) del frontend, ej. `https://sevanna.co,https://www.sevanna.co` |
| `FRONTEND_URL` | `https://sevanna.co` |

> Si aún no tienes el dominio del frontend, pon temporalmente la URL que te dé
> Render para el frontend, o `*` **solo para pruebas** (no en producción con datos).
> Guarda cambios → Render redepliega.

## 3. Sembrar los datos (una sola vez)
La base de producción arranca vacía. En **sevanna-api → Shell** (en el dashboard):

```bash
python -m scripts.seed          # crea el administrador inicial
python -m scripts.seed_catalog  # crea las 9 categorías + 32 cursos/talleres
```

Ambos son idempotentes (no duplican si se corren de nuevo).

## 4. Verificar
La API queda en `https://sevanna-api.onrender.com` (o el nombre que asigne Render):
- Health: `GET /api/v1/health` → `{"status":"ok"}`
- Docs: `/docs`
- Catálogo: `GET /api/v1/courses` → 32 cursos

## 5. Conectar el frontend
- **Base URL del API:** `https://<tu-servicio>.onrender.com/api/v1`
- Asegúrate de que el dominio del frontend esté en `CORS_ORIGINS`.
- Endpoints públicos que usará el catálogo:
  `GET /courses`, `GET /courses/{slug}`, `GET /courses/featured`, `GET /categories`.
- Login de administrador: `POST /auth/login`.

## 6. Notas importantes
- **Plan gratis:** el servicio web se **duerme** tras inactividad (primer request
  lento) y la **base gratuita expira en ~30 días**. Para producción del cliente,
  sube ambos a un plan de pago (web ~$7/mes, DB ~$7/mes) para persistencia y sin
  cold starts.
- **Despliegue continuo:** con `autoDeploy: true`, cada push a `main` redepliega.
- **Migraciones:** se aplican solas en cada arranque (`alembic upgrade head`).
- **Módulos:** cuentas y comercio están desactivados (`ENABLE_ACCOUNTS=false`,
  `ENABLE_COMMERCE=false`); reactivar en el futuro es cambiar la variable.
- **Dominio propio (opcional):** en **sevanna-api → Settings → Custom Domains**.

## Alternativa sin Blueprint (manual)
Si prefieres no usar `render.yaml`: crea primero un **PostgreSQL**, luego un
**Web Service** desde el repo (runtime Docker, health check `/api/v1/health`) y
copia la *Internal Database URL* en la variable `DATABASE_URL`, más las variables
de la sección 2. El resto es igual.
