# Flujo de Git — Sevanna Backend

> Toda sesión de trabajo futura debe seguir este flujo para mantener un
> historial limpio y un versionado predecible.

## Ramas

| Rama | Propósito | ¿Se hace push? | ¿Deploy? |
|---|---|---|---|
| `main` | Código **estable / producción**. Siempre desplegable. | Sí | Producción |
| `develop` | Rama de **integración**. Reúne features terminadas. | Sí | Staging |
| `feature/<nombre>` | Trabajo de una funcionalidad concreta. | Opcional | No |
| `fix/<nombre>` | Corrección de un bug. | Opcional | No |
| `release/<version>` | Estabilización previa a un release. | Sí | Staging |
| `hotfix/<nombre>` | Corrección urgente sobre `main`. | Sí | Producción |

Regla: **nunca se commitea directamente a `main`**. `main` solo recibe merges
desde `release/*`, `hotfix/*` o `develop` (en releases).

## Ciclo de trabajo estándar

```
1. Partir de develop actualizado:
   git checkout develop && git pull

2. Crear rama de trabajo:
   git checkout -b feature/catalogo-filtros-avanzados

3. Commits pequeños y coherentes (ver convención abajo).

4. Antes de integrar, verificar en local:
   ruff check .     &&     pytest

5. Merge a develop (o Pull Request si hay revisión):
   git checkout develop && git merge --no-ff feature/catalogo-filtros-avanzados

6. Push:
   git push origin develop

7. Borrar la rama de feature ya integrada:
   git branch -d feature/catalogo-filtros-avanzados
```

## Release a producción

```
git checkout -b release/0.2.0 develop
# ajustes finales, bump de versión, pruebas
git checkout main && git merge --no-ff release/0.2.0
git tag -a v0.2.0 -m "Release 0.2.0"
git checkout develop && git merge --no-ff release/0.2.0
git push origin main develop --tags
```

## Convención de mensajes de commit (Conventional Commits)

```
<tipo>(<área opcional>): <resumen en imperativo, minúscula>

[cuerpo opcional: qué y por qué]
```

Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `build`, `ci`.

Ejemplos:
- `feat(payments): validar firma del webhook de Wompi`
- `fix(auth): rotar refresh token al renovar sesión`
- `docs: actualizar documento de arquitectura`
- `test(purchases): cubrir precio congelado`

## Requisitos de calidad antes de integrar

- `ruff check .` sin errores.
- `pytest` en verde.
- Todo cambio de esquema acompañado de su migración Alembic.
- Actualizar `docs/ARCHITECTURE.md` si la arquitectura cambia, y
  `docs/CONSIDERACIONES.md` si se resuelve/agrega un pendiente.

## Qué NO se commitea

Ver `.gitignore`. En particular: `.env` (secretos), entornos virtuales,
`media/`, archivos `*.sqlite3`/`*.db`, cachés. **Nunca** subir secretos.

## Estado inicial del repositorio

- `main`: línea base 0.1.0 (backend funcional, tests en verde, docs).
- `develop`: creada desde `main` para el trabajo futuro.
