# Colección Postman — Sevanna API

Colección lista para probar toda la API localmente.

## Importar

En Postman: **Import** → arrastra `Sevanna.postman_collection.json`.
(La colección ya está también en el workspace personal de Postman como **Sevanna API**.)

## Variables de colección (ya incluidas)

| Variable | Valor por defecto | Uso |
|---|---|---|
| `base_url` | `http://localhost:8000/api/v1` | Base de la API |
| `access_token` / `refresh_token` | (vacío) | Se rellenan solos al hac**Login** |
| `admin_email` / `admin_password` | `admin@sevanna.co` / `Admin12345` | Admin sembrado |
| `webhook_secret` | `fake-secret` | Firma del webhook en modo `fake` |
| `course_id`, `course_slug`, `purchase_id`, `payment_id`, `payment_reference`, `enrollment_id` | (se rellenan solos) | Encadenan el flujo |

## Flujo recomendado (los IDs se guardan automáticamente)

1. **Auth → Login** (con el admin) → guarda `access_token`.
2. **Admin → Create Course** → guarda `course_id` y `course_slug`.
3. **Purchases → Create Purchase** → guarda `purchase_id`.
4. **Payments → Create Payment** → guarda `payment_reference`.
5. **Payments → Payment Webhook (fake)** → marca la compra como PAID y crea la inscripción.
6. **Users → My Courses** → guarda `enrollment_id`.
7. **Enrollments → Enrollment Access** → obtiene los enlaces privados (WhatsApp/Meet).

> Requiere el backend corriendo (`uvicorn app.main:app --reload`) y datos
> sembrados (`python -m scripts.seed`). Ver el README principal.
