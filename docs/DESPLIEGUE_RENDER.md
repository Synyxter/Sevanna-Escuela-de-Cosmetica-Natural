# Despliegue en Render — Sevanna Backend

Guía para publicar la API (FastAPI) en **Render**, con la base PostgreSQL en
**Neon**, y que el frontend la consuma por HTTPS. El repositorio ya incluye
`Dockerfile` y `render.yaml`.

> Yo no puedo crear tu cuenta ni ingresar tus credenciales. Tú haces los pasos
> marcados con 👤; el proyecto ya quedó preparado para que sean mínimos.

> **¿Por qué Neon y no la PostgreSQL de Render?** La base gratuita de Render
> **expira a los ~30 días** y se borra. Neon en plan gratuito no expira: la base
> se suspende sin uso y despierta en menos de un segundo en la siguiente consulta.

## 0. Requisitos
- 👤 Cuenta en **https://render.com** (puedes entrar con tu GitHub).
- 👤 Cuenta en **https://neon.tech** (también con GitHub).
- Repo en GitHub: `Synyxter/Sevanna-Escuela-de-Cosmetica-Natural` (ya está).
- El despliegue usa la rama **`main`**.

## 1. Crear la base en Neon
1. 👤 En Neon: **New Project** → nombre `sevanna`, Postgres 16, región
   **AWS US East 1 (N. Virginia)** (la misma zona que el servicio de Render).
2. 👤 En **Connect**, desactiva **Connection pooling** y copia la cadena de
   conexión. Se ve así:
   `postgresql://neondb_owner:XXXX@ep-xxxx.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`

> **Usa la conexión directa (sin `-pooler` en el host).** El pooler de Neon
> (PgBouncer en modo transacción) no es compatible con las sentencias
> preparadas que usa `asyncpg`.
>
> La URL se pega **tal cual**: la app convierte `postgresql://` a
> `postgresql+asyncpg://`, `sslmode` a `ssl` y descarta `channel_binding`
> (ver `app/core/config.py`).

## 2. Crear el servicio web con el Blueprint
1. 👤 En Render: **New +** → **Blueprint**.
2. 👤 Conecta y selecciona el repositorio de Sevanna.
3. Render detecta `render.yaml` y propone crear **sevanna-api** (Docker).
4. 👤 Pulsa **Apply**.

Si el servicio ya existía, no hace falta recrearlo: basta con cambiar
`DATABASE_URL` (paso 3) y redesplegar.

## 3. Definir las variables manuales (secretas / propias)
En **sevanna-api → Environment**, define (quedaron como "sync: false"):

| Variable | Valor |
|---|---|
| `DATABASE_URL` | la cadena de Neon del paso 1 |
| `FIRST_ADMIN_PASSWORD` | una contraseña fuerte para el admin |
| `CORS_ORIGINS` | dominio(s) del frontend, ej. `https://sevanna.co,https://www.sevanna.co` |
| `FRONTEND_URL` | `https://sevanna.co` |

> Si `FIRST_ADMIN_PASSWORD` no está definida, el admin se crea con la
> contraseña por defecto de `app/core/config.py`. Defínela **antes** del primer
> arranque contra la base nueva.

Guarda cambios → Render redepliega.

## 4. Datos iniciales (automático)
Al arrancar, el contenedor ejecuta `alembic upgrade head` (crea las tablas) y la
app siembra el administrador y sincroniza el catálogo (`AUTO_SEED`, activo por
defecto; ver `app/core/bootstrap.py`). No hay que correr nada a mano.

Si quieres forzarlo, en **sevanna-api → Shell**:

```bash
python -m scripts.seed          # crea el administrador inicial
python -m scripts.seed_catalog  # crea categorías + cursos/talleres
```

Ambos son idempotentes (no duplican si se corren de nuevo).

## 5. Verificar
La API queda en `https://sevanna-api.onrender.com` (o el nombre que asigne Render):
- Health: `GET /api/v1/health/ready` → `{"status":"ready"}` (confirma la conexión a la base)
- Docs: `/docs`
- Catálogo: `GET /api/v1/courses`

## 6. Conectar el frontend
- **Base URL del API:** `https://<tu-servicio>.onrender.com/api/v1`
- Asegúrate de que el dominio del frontend esté en `CORS_ORIGINS`.
- Endpoints públicos que usará el catálogo:
  `GET /courses`, `GET /courses/{slug}`, `GET /courses/featured`, `GET /categories`.
- Login de administrador: `POST /auth/login`.

## 7. Disponibilidad 24/7
El servicio web **gratis** de Render se **duerme tras ~15 min sin tráfico**; la
siguiente petición tarda 30–60 s+ en despertarlo (el frontend corta a los 20 s).

- **Recomendado para producción:** plan **Starter** (~$7/mes) en
  **sevanna-api → Settings → Instance Type**. Siempre encendido.
- **Alternativa gratuita:** un monitor externo que llame a la API cada 5–10 min
  para que no se duerma. 👤 En **https://uptimerobot.com** → *Add New Monitor* →
  tipo **HTTP(s)**, URL `https://sevanna-api.onrender.com/api/v1/health/live`,
  intervalo **5 minutes**. Un único servicio encendido todo el mes cabe en las
  750 h gratuitas de Render. Usa `/health/live` (no toca la base, así Neon
  puede suspenderse y no consume horas de cómputo).

## 8. Notas importantes
- **Despliegue continuo:** con `autoDeploy: true`, cada push a `main` redepliega.
- **Migraciones:** se aplican solas en cada arranque (`alembic upgrade head`).
- **Módulos:** cuentas y comercio están desactivados (`ENABLE_ACCOUNTS=false`,
  `ENABLE_COMMERCE=false`); reactivar en el futuro es cambiar la variable.
- **Dominio propio (opcional):** en **sevanna-api → Settings → Custom Domains**.

## Alternativa sin Blueprint (manual)
Si prefieres no usar `render.yaml`: crea un **Web Service** desde el repo
(runtime Docker, health check `/api/v1/health`) y define las variables del
paso 3. El resto es igual.
