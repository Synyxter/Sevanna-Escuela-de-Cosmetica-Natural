# Consideraciones y pendientes — Sevanna Backend

> Registro vivo de lo que falta, deuda técnica consciente y decisiones a
> revisar. Actualízalo cuando resuelvas o agregues un pendiente.

Última actualización: 2026-08-15 · Backend 0.1.0

Leyenda de prioridad: 🔴 bloqueante para producción · 🟠 importante · 🟢 mejora / futuro

---

## 1. Configuración requerida antes de producción

- 🔴 **Secreto JWT fuerte**: generar `JWT_SECRET_KEY` aleatorio y largo
  (`python -c "import secrets; print(secrets.token_urlsafe(64))"`).
- 🔴 **PostgreSQL real**: definir `DATABASE_URL` y ejecutar `alembic upgrade head`.
- 🔴 **Credenciales de Wompi** (empezar en sandbox): `PAYMENT_API_KEY` (privada),
  `PAYMENT_PUBLIC_KEY`, `PAYMENT_INTEGRITY_SECRET` (firma de checkout),
  `PAYMENT_WEBHOOK_SECRET` (firma de eventos), y registrar la URL pública del
  webhook `POST /api/v1/payments/webhook` en el panel de Wompi.
- 🔴 **Dominios del frontend**: `CORS_ORIGINS` y `FRONTEND_URL`
  (usado en enlaces de verificación/reset) y `PAYMENT_REDIRECT_URL`.
- 🟠 **SMTP real** cuando se salga de `console`: `SMTP_HOST/PORT/USERNAME/PASSWORD`
  y `EMAIL_FROM`.
- 🟠 **Almacenamiento**: definir proveedor real (S3/Cloudinary) — ver §3.
- 🟠 `ENABLE_DOCS=false` en producción si se decide ocultar `/docs`.

## 2. Deuda técnica consciente (revisar)

- 🟠 **Rate limiting en memoria**: `app/core/rate_limit.py` usa un store en
  proceso. Con múltiples instancias detrás de un balanceador, los contadores no
  se comparten. **Acción:** migrar a Redis manteniendo la misma interfaz de
  dependencia. (El diseño ya lo contempla.)
- 🟠 **Correos vía `BackgroundTasks`**: hoy el envío corre en background dentro
  del proceso, con reintentos en `EmailService` y estado en `EmailLog`. Para
  mayor escala/robustez, mover a una cola (Redis + Arq/Celery/RQ) con reintentos
  persistentes y reprocesamiento de `EmailLog` en estado FAILED.
- 🟠 **`AuditLog` no está poblado**: el modelo existe pero los servicios aún no
  escriben eventos de auditoría. **Acción:** registrar eventos clave (login,
  cambios admin, transiciones de pago) desde la capa de servicios.
- 🟠 **Refunds no implementados**: `PaymentProvider.refund_payment` es parte de
  la interfaz pero Wompi no lo implementa aún; `PurchaseStatus.REFUNDED` y
  `PaymentStatus.REFUNDED` existen para cuando se implemente.
- 🟢 **JSON vs JSONB**: se usa `JSON` genérico (portable a SQLite en tests). En
  PostgreSQL podría convenir `JSONB` para indexar `materials`/`learning_outcomes`
  si se necesitan consultas sobre su contenido.
- 🟢 **Paginación por offset**: suficiente hoy; considerar cursor si crecen mucho
  los catálogos/listados admin.

## 3. Funcionalidad incompleta (por implementar)

- 🟠 **Carga de imágenes de curso**: hoy el admin envía `image_url` directamente.
  Falta un endpoint de subida (`multipart`) que use `StorageProvider.upload` y
  un proveedor S3/Cloudinary. La abstracción (`app/integrations/storage`) ya está.
- 🟢 **Reenvío de verificación de correo**: existe `verify-email`, pero no un
  endpoint para reenviar el enlace si expira.
- 🟢 **Gestión admin de categorías**: se puede crear categoría; falta
  editar/eliminar/listar-admin si se requiere.
- 🟢 **Endpoints admin adicionales**: cambiar rol/activar-desactivar usuarios,
  detalle admin de compra con su pago, filtros en listados admin.

## 4. Decisiones a confirmar

- 🟠 **Registro y enumeración de usuarios**: `register` devuelve `409` con mensaje
  genérico si el correo existe. Cumple "no revelar detalle", pero un 409 permite
  inferir existencia. Alternativa más estricta: responder `201` siempre y enviar
  un correo de "esta cuenta ya existe". Decidir con el equipo.
- 🟠 **Login sin verificación de correo**: hoy se permite iniciar sesión aunque
  `email_verified = false`. Definir si se debe **bloquear** el login (o ciertas
  acciones, p.ej. comprar) hasta verificar el correo.
- 🟢 **Enlaces de correo**: `FRONTEND_URL/verify-email?token=...` y
  `/reset-password?token=...`. Confirmar las rutas exactas con el frontend.
- 🟢 **Firma del webhook de Wompi**: la validación reconstruye el checksum con las
  `signature.properties` + `timestamp` + secreto de eventos. **Verificar contra
  el sandbox real de Wompi** que las propiedades y el formato coinciden.

## 5. Operación / DevOps pendiente

- 🟠 **CI/CD**: no hay pipeline. Agregar workflow (p.ej. GitHub Actions) que
  ejecute `ruff check .` y `pytest` en cada push/PR, y build de imagen.
- 🟢 **Pre-commit** (opcional): hooks de ruff/format antes de commitear.
- 🟢 **MyPy** (opcional): chequeo estático de tipos.
- 🟢 **Observabilidad avanzada**: métricas (Prometheus) y trazas (OpenTelemetry)
  si se requiere en producción.
- 🟢 **Cache (Redis)**: previsto para cursos populares/consultas frecuentes; no
  introducir hasta que la escala lo justifique.

## 6. Cobertura de pruebas

- ✅ Cubierto: registro, login, refresh (rotación), catálogo (filtros, borrador
  oculto, enlaces privados no expuestos), flujo completo de compra, idempotencia
  de webhook, rechazo de firma inválida, acceso no autenticado.
- 🟢 Por ampliar: pruebas unitarias de servicios (casos límite de precios,
  concurrencia de webhooks, reintentos de correo, expiración de tokens de
  reset/verificación), y pruebas de integración contra PostgreSQL real (además
  de SQLite) para validar el índice único parcial y `SELECT ... FOR UPDATE`.

## 7. Evolución de producto prevista (futuro, sin reconstruir)

Módulos y lecciones de curso · materiales/recursos descargables · certificados ·
progreso del estudiante · evaluaciones · talleres · notificaciones · roles
adicionales (TEACHER/MANAGER/SUPPORT ya reservados en el enum) · reportes admin.

---

### Cómo usar este documento
Al iniciar una tarea, revisa las secciones 🔴/🟠 relevantes. Al cerrar una tarea
que resuelve un pendiente, muévelo a "resuelto" o elimínalo y, si aplica,
actualiza `docs/ARCHITECTURE.md`.
