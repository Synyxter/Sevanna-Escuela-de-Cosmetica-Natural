# Puesta en marcha — Guía paso a paso (local → producción)

Guía para reunir la configuración que falta y dejar el backend listo para tu
frontend y para producción. Cada punto dice **qué hacer** y **qué enviarme**.

> **Actualización de alcance (2026-08-16):** Sevanna es un **catálogo de cursos**;
> inscripción y pago se gestionan por WhatsApp. Por eso los pasos **§3 (Wompi)** y
> **§4 (SMTP)** son **opcionales / a futuro**: solo aplican si algún día reactivas
> `ENABLE_COMMERCE` (pagos) o `ENABLE_ACCOUNTS` (cuentas/correo). Lo imprescindible
> hoy es **§1 (frontend/CORS)** y **§2 (PostgreSQL)**.

> **Seguridad de secretos (importante):** los valores sensibles (llaves de
> Wompi, contraseña SMTP, URL de la base de datos) **los pones tú** en el
> archivo `.env` local — **no los pegues en el chat**. `.env` está en
> `.gitignore` y no se sube. Yo me encargo del código, la configuración y las
> pruebas. En producción usa las variables de entorno del hosting, no un `.env`
> versionado.

## Orden recomendado
1. PostgreSQL → 2. Dominio del frontend → 3. Wompi (sandbox) →
4. SMTP → 5. Contrato con el frontend → 6. Alcance v1/v2.

---

## 1. Dominio(s) del frontend

**Objetivo:** fijar CORS y las URLs de enlaces de correo (verificación/reset) y
el `redirect` de pago.

**Pasos**
1. Identifica los dominios que usará el frontend: desarrollo (p. ej.
   `http://localhost:5173`), staging y producción (p. ej. `https://sevanna.co`).
2. En tu `.env` define:
   - `CORS_ORIGINS=https://sevanna.co,https://www.sevanna.co` (coma-separado)
   - `FRONTEND_URL=https://sevanna.co`
   - `PAYMENT_REDIRECT_URL=https://sevanna.co/checkout/result`

**Qué enviarme:** la lista de dominios (dev/staging/prod). Los pongo en la
configuración y ajusto los enlaces.

---

## 2. PostgreSQL

Elige **una** opción.

### Opción A — Local con Docker (más rápido para empezar)
```bash
docker compose up -d db          # levanta solo PostgreSQL
# En .env:
# DATABASE_URL=postgresql+asyncpg://sevanna:sevanna@localhost:5432/sevanna
alembic upgrade head
python -m scripts.seed
```

### Opción B — Gestionado (Neon, Supabase, Railway, Render, RDS…)
1. Crea una base PostgreSQL en el proveedor.
2. Copia la *connection string* y conviértela al driver async:
   `postgresql+asyncpg://USUARIO:PASSWORD@HOST:5432/BASE`
   (si exige SSL, normalmente funciona igual; si no, se ajusta un parámetro).
3. Pon esa URL en `DATABASE_URL` del `.env` y ejecuta:
   `alembic upgrade head` y `python -m scripts.seed`.

**Qué enviarme:** qué opción elegiste. Si es gestionada, dime el proveedor
(la URL la pones tú en `.env`). Con eso valido migraciones y seed.

---

## 3. Wompi (empezar en sandbox)

**Objetivo:** activar el proveedor de pagos real (hoy los tests usan `fake`).

**Pasos**
1. Crea tu cuenta de comercio en Wompi (**comercios.wompi.co**) y entra al panel.
2. Ve a la sección de **Desarrolladores / Llaves de API** y selecciona el
   entorno **Sandbox / Pruebas**. Ahí encontrarás:
   - **Llave pública** `pub_test_...`
   - **Llave privada** `prv_test_...`
   - **Secreto de integridad** (firma del *checkout*)
   - **Secreto de eventos** (firma del *webhook*)
3. Configura la **URL del webhook de eventos** apuntando a:
   `https://<tu-dominio-o-túnel>/api/v1/payments/webhook`
   - En producción: el dominio donde despliegues el backend.
   - En local: necesitas un túnel público. Instala **ngrok** y ejecuta
     `ngrok http 8000`; usa la URL `https://xxxx.ngrok.io` en el panel de Wompi.
4. En tu `.env`:
   ```env
   PAYMENT_PROVIDER=wompi
   PAYMENT_PUBLIC_KEY=pub_test_...
   PAYMENT_API_KEY=prv_test_...
   PAYMENT_INTEGRITY_SECRET=...
   PAYMENT_WEBHOOK_SECRET=...
   PAYMENT_BASE_URL=https://sandbox.wompi.co/v1
   PAYMENT_REDIRECT_URL=https://<tu-frontend>/checkout/result
   ```

**Qué enviarme:** confirmación de que ya cargaste las llaves en `.env` y la URL
pública del webhook que registraste. Luego hacemos **una transacción de prueba**
juntos para validar que la firma del webhook (properties/checksum) coincide con
lo implementado y ajustar si hiciera falta.

---

## 4. SMTP (correo real)

**Objetivo:** salir del modo `console` (que solo imprime en logs).

**Opción simple — Gmail con contraseña de aplicación**
1. Activa la **Verificación en 2 pasos** en tu cuenta de Google.
2. Google → **Seguridad** → **Contraseñas de aplicaciones** → genera una.
3. En `.env`:
   ```env
   EMAIL_PROVIDER=smtp
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=tucorreo@gmail.com
   SMTP_PASSWORD=la-contraseña-de-aplicación
   SMTP_USE_TLS=true
   EMAIL_FROM=no-reply@sevanna.co
   EMAIL_FROM_NAME=Sevanna
   ```

**Alternativas transaccionales:** Brevo, Zoho, Mailgun, Amazon SES (para
volumen/entregabilidad). Todas dan credenciales SMTP equivalentes.

**Qué enviarme:** el proveedor elegido (los valores los pones tú en `.env`).
Cuando esté, probamos verificación de correo y recuperación de contraseña.

---

## 5. Contrato con el frontend

**Objetivo:** que las respuestas encajen exactamente con lo que tu UI espera.

**Qué necesito de ti (envíame lo que tengas):**
- Stack del frontend (React/Next, Vue, etc.) y si usan **TypeScript**.
- Los **tipos/interfaces** que el frontend espera para: curso (lista y detalle),
  usuario, compra, inscripción, y el *envelope* de respuesta.
- Las pantallas y qué campos muestran (para confirmar nombres/estructura, p. ej.
  la forma de `materials`).
- Si ya hay un cliente de API o llamadas definidas, compárteme ese archivo.

**Si aún no está definido:** dime "que el frontend se adapte al contrato actual"
y te entrego la referencia de tipos a partir del OpenAPI.

---

## 6. Alcance: qué entra en v1 y qué queda para v2

**Candidatos a cerrar en v1 (dime cuáles quieres):**
- Endpoint admin **dedicado** para editar enlaces WhatsApp/Meet por curso
  (hoy ya se pueden cambiar vía `PATCH /admin/courses/{id}`).
- **Carga de imágenes** real (subida a S3/Cloudinary) en vez de `image_url`.
- **Bloquear login o compra** si el correo no está verificado.
- **CI** (GitHub Actions: `ruff` + `pytest` en cada push/PR).

**Previsto para v2 (futuro):** módulos/lecciones, materiales descargables,
certificados, progreso, evaluaciones, talleres, notificaciones, roles extra.

**Qué enviarme:** marca qué entra en v1 y qué dejamos para v2.

---

## Checklist final antes de producción
- [ ] `JWT_SECRET_KEY` fuerte y aleatorio.
- [ ] `DATABASE_URL` de producción + `alembic upgrade head`.
- [ ] Wompi **producción** (`pub_prod`/`prv_prod`, secretos, webhook público).
- [ ] `CORS_ORIGINS` con el dominio real del frontend.
- [ ] SMTP real y probado.
- [ ] `ENABLE_DOCS=false` si decides ocultar `/docs`.
- [ ] Secretos en variables de entorno del hosting (no en un `.env` versionado).

Ver también `docs/CONSIDERACIONES.md` (pendientes) y `docs/ARCHITECTURE.md`.
