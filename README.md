# ⚖️ FuturoTech AI — Universal Legal Engine

Motor universal para generación automatizada de documentos jurídicos con inteligencia artificial.

Combina **Google Gemini** + **RAG (ChromaDB)** + **arquitectura hexagonal** para que firmas de abogados generen documentos legales formales en segundos, con citas textuales de normas reales y membrete corporativo.

---

## Funcionalidades

| Módulo | Descripción |
|---|---|
| **Generación con IA** | Documentos jurídicos completos vía Google Gemini 2.5 Flash |
| **RAG Legal** | Base de conocimiento vectorial (ChromaDB) con embeddings Gemini. Cita textualmente las normas subidas |
| **Multi-tenant** | Múltiples firmas con branding independiente (logo, encabezado, pie, color corporativo) |
| **Plantillas dinámicas** | Cada tipo de documento tiene su prompt, reglas jurídicas y campos configurables |
| **Versionado de plantillas** | Historial inmutable de cada cambio en una plantilla (`template_versions`) |
| **Entidades destinatarias** | Directorio de 27 tipos de entidades colombianas (EPS, bancos, juzgados, etc.) |
| **Exportación DOCX + PDF** | Documentos con membrete profesional. Editor post-generación con soporte markdown |
| **RBAC** | 4 roles (admin, abogado, pasante, consulta) con 8 permisos granulares |
| **API REST** | FastAPI con CORS, rate limiting por usuario/IP, security headers, health check profundo |
| **Resiliencia** | Circuit breaker + reintentos exponenciales para el servicio de IA (Gemini) |

---

## Arquitectura

```
src/
├── domain/                        # Núcleo — sin dependencias externas
│   ├── models.py                  # Pydantic: TenantConfig, Entity, User, LegalContext
│   ├── exceptions.py              # DomainException, AuthenticationException, etc.
│   └── ports/
│       ├── in_ports.py            # GenerateDocumentPort (driving)
│       └── out_ports.py           # AI, Tenant, Template, Entity, User, FileExporter, KnowledgeBase
│
├── application/                   # Casos de uso y servicios
│   ├── use_cases/
│   │   └── generate_document.py   # Orquesta: tenant → prompt + RAG → Gemini → DOCX
│   └── services/
│       └── auth_service.py        # bcrypt, contraseñas seguras, ensure_default_admin
│
└── infrastructure/                # Adaptadores concretos
    ├── container.py               # Composition Root (inyección de dependencias)
    ├── logging_config.py          # Structured JSON logging + correlation IDs
    ├── ingestion/
    │   └── ingest_service.py      # Extracción PDF/TXT/DOCX + validación de tamaño
    └── adapters/
        ├── input/
        │   ├── api/
        │   │   ├── routes.py      # FastAPI controller (usa DTOs, no modelos de dominio)
        │   │   └── dtos.py        # DTOs de transporte HTTP separados del dominio
        │   └── ui/                # Streamlit frontend
        │       ├── pages/         # login, generate, templates, entities, company, users
        │       ├── components.py  # Componentes reutilizables
        │       ├── constants.py   # Configuración centralizada
        │       └── state.py       # CRUD wrappers + auth helpers
        └── output/
            ├── ai_gemini.py       # Gemini adapter (circuit breaker + retry exponencial)
            ├── db_sqlite.py       # SQLite repository — desarrollo local (caché TTL plantillas)
            ├── db_postgres.py     # PostgreSQL repository — producción (SQLAlchemy async)
            ├── db_models.py       # Modelos SQLAlchemy ORM (fuente de verdad del esquema)
            ├── doc_generator.py   # DOCX + PDF engine
            └── knowledge_base.py  # ChromaDB + Gemini Embeddings (caché LRU embeddings)

alembic/                           # Migraciones de base de datos
├── env.py
└── versions/
    ├── 1b6de2a32c03_initial_schema.py
    └── 42a5167fc39a_add_template_versioning.py

scripts/
└── migrate_sqlite_to_postgres.py  # Migración one-shot de datos SQLite → PostgreSQL

tests/
├── conftest.py                    # Fixtures compartidos
├── unit/
│   ├── test_auth_service.py
│   ├── test_generate_use_case.py
│   ├── test_ingest_service.py
│   └── test_sqlite_repository.py
└── integration/
    └── test_api.py
```

---

## Requisitos previos

- **Python** 3.12+
- **API Key** de [Google AI Studio](https://aistudio.google.com/apikey) (Gemini)
- **PostgreSQL** 14+ (producción) — opcional, SQLite disponible para desarrollo local

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd derecho_peticion

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/macOS
# Editar .env con GEMINI_API_KEY y DATABASE_URL
```

---

## Variables de entorno

| Variable | Descripción | Default |
|---|---|---|
| `GEMINI_API_KEY` | API key de Google Gemini | — (requerida) |
| `GEMINI_MODEL` | Modelo de IA | `gemini-2.5-flash` |
| `DATABASE_URL` | URL PostgreSQL async — si se omite usa SQLite | — |
| `DB_PATH` | Ruta SQLite (solo si `DATABASE_URL` no está definida) | `legal_engine.db` |
| `CHROMA_DIR` | Directorio de ChromaDB | `chroma_db` |
| `RAG_CHUNK_SIZE` | Tamaño de fragmento para RAG | `1500` |
| `RAG_CHUNK_OVERLAP` | Solapamiento entre fragmentos | `200` |
| `RAG_MAX_FILE_MB` | Tamaño máximo de archivo para ingesta RAG | `20` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |
| `LOG_FILE` | Ruta del archivo de log | `logs/app.log` |
| `LOG_FORMAT` | Formato de log: `json` \| `text` | `json` |
| `API_HOST` | Host de la API | `localhost` |
| `API_PORT` | Puerto de la API | `8000` |
| `CORS_ORIGINS` | Orígenes permitidos (separados por coma) | `http://localhost:8501` |
| `RATE_LIMIT_RPM` | Requests por minuto por usuario/IP | `30` |
| `ENABLE_DOCS` | Habilitar Swagger UI en `/docs` | `true` |
| `API_TIMEOUT_GENERATE` | Timeout de generación (segundos) | `120` |

---

## Base de datos

### Desarrollo local — SQLite (sin configuración adicional)

El sistema usa SQLite automáticamente cuando `DATABASE_URL` no está definida. Las tablas se crean al primer arranque.

### Producción — PostgreSQL + Alembic

**1. Levantar PostgreSQL:**
```bash
docker run -d --name legal_pg \
  -e POSTGRES_DB=legal_engine \
  -e POSTGRES_USER=legal \
  -e POSTGRES_PASSWORD=secret \
  -p 5432:5432 postgres:16
```

**2. Configurar `.env`:**
```
DATABASE_URL=postgresql+asyncpg://legal:secret@localhost:5432/legal_engine
```

**3. Ejecutar migraciones:**
```bash
py -m alembic upgrade head
```

**4. Migrar datos existentes de SQLite (una sola vez):**
```bash
py scripts/migrate_sqlite_to_postgres.py
```

### Crear nueva migración tras cambios de esquema

```bash
py -m alembic revision --autogenerate -m "descripcion_del_cambio"
py -m alembic upgrade head
```

---

## Ejecución

### Backend (API)

```bash
cd src
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

La API estará en `http://localhost:8000`. Swagger UI en `http://localhost:8000/docs`.

### Frontend (Streamlit)

```bash
python -m streamlit run run_ui.py
```

La UI estará en `http://localhost:8501`.

### Credenciales en primer arranque

Al iniciar por primera vez sin usuarios en la base de datos, el sistema **genera contraseñas aleatorias seguras** (16 caracteres) y las muestra **una única vez** en consola:

```
============================================================
  PRIMER ARRANQUE — Credenciales iniciales generadas
  Guarde estas contraseñas en un lugar seguro.
  No se volverán a mostrar.
============================================================
  admin      → Xk9#mP2$vLqR8nYw
  abogado    → Tz4@jN7!cWsE3bQu
  pasante    → Rp6&hF1*dAoK5mVx
  consulta   → Yw8%gB3^eJiL9nCz
============================================================
```

> Las contraseñas nunca se almacenan en texto plano ni están hardcodeadas en el código.

---

## Tests

```bash
# Todos los tests
py -m pytest

# Solo unitarios
py -m pytest tests/unit -v

# Solo integración
py -m pytest tests/integration -v

# Con cobertura
py -m pytest --cov=src --cov-report=term-missing
```

**Cobertura actual:** 23 tests unitarios + 5 tests de integración, todos pasando.

---

## API Endpoints

### `POST /api/v1/documents/generate`

Genera un documento jurídico.

**Headers:**
```
X-Tenant-ID: <tenant_id>
X-User-ID: <user_id>          (opcional — mejora el rate limiting por usuario)
Content-Type: application/json
```

**Body:**
```json
{
  "template_id": "derecho-peticion-v1",
  "metadata": {
    "cliente_nombre": "<nombre>",
    "cedula": "<cedula>",
    "hechos_crudos": "Descripción de los hechos..."
  },
  "selected_rules": ["Ley 1755 de 2015"]
}
```

**Response:**
```json
{
  "transaction_id": "uuid",
  "status": "COMPLETED",
  "download_url": "/files/uuid_template.docx"
}
```

### `GET /files/{filename}`

Descarga el documento generado.

### `GET /health`

Health check profundo — verifica base de datos, ChromaDB y estado del circuit breaker de Gemini.

```json
{
  "status": "ok",
  "checks": {
    "database": "ok",
    "chromadb": "ok",
    "gemini_circuit": "closed"
  }
}
```

Retorna `200` si todo está operativo, `503` si algún componente está degradado.

---

## Roles y permisos (RBAC)

| Permiso | admin | abogado | pasante | consulta |
|---|:---:|:---:|:---:|:---:|
| Generar documentos | ✅ | ✅ | ✅ | ❌ |
| Ver plantillas | ✅ | ✅ | ✅ | ✅ |
| Gestionar plantillas | ✅ | ❌ | ❌ | ❌ |
| Ver entidades | ✅ | ✅ | ✅ | ✅ |
| Gestionar entidades | ✅ | ✅ | ❌ | ❌ |
| Ver empresa | ✅ | ✅ | ❌ | ✅ |
| Gestionar empresa | ✅ | ❌ | ❌ | ❌ |
| Gestionar usuarios | ✅ | ❌ | ❌ | ❌ |

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Backend API | Python 3.12 · FastAPI · Uvicorn |
| Frontend | Streamlit |
| IA Generativa | Google Gemini 2.5 Flash |
| Embeddings | Gemini Embedding 001 + caché LRU (256 entradas) |
| Base de conocimiento | ChromaDB (vectorial) |
| Base de datos (prod) | PostgreSQL 14+ · SQLAlchemy async · asyncpg |
| Base de datos (dev) | SQLite WAL mode · caché TTL plantillas |
| Migraciones | Alembic |
| Resiliencia IA | pybreaker (circuit breaker) · tenacity (retry exponencial) |
| Exportación DOCX | python-docx |
| Exportación PDF | fpdf2 |
| Autenticación | bcrypt · contraseñas aleatorias `secrets` |
| Logging | JSON estructurado · correlation IDs · RotatingFileHandler |
| Tests | pytest · pytest-asyncio · httpx |
| Arquitectura | Hexagonal (Ports & Adapters) · DTOs separados del dominio |

---

## Estructura de la base de datos

```
tenants            — Empresas / firmas (multi-tenant)
templates          — Plantillas de documentos (versión activa)
template_versions  — Historial inmutable de versiones por plantilla
template_documents — Documentos RAG indexados por plantilla
entities           — Entidades destinatarias
users              — Usuarios con roles RBAC
```

---

## Seguridad

- Contraseñas hasheadas con **bcrypt** (salt aleatorio por usuario)
- Contraseñas iniciales generadas con **`secrets`** — nunca hardcodeadas
- **Rate limiting** por usuario autenticado (`X-User-ID`) con fallback a IP
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
- **Correlation ID** en cada request para trazabilidad end-to-end
- **Circuit breaker** en Gemini: evita cascada de fallos ante caídas del proveedor de IA
- Validación de tamaño máximo en ingesta RAG (`RAG_MAX_FILE_MB`)

---

## Licencia

Proyecto privado — FuturoTech AI.
