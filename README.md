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
| **Entidades destinatarias** | Directorio de 27 tipos de entidades colombianas (EPS, bancos, juzgados, etc.) |
| **Exportación DOCX + PDF** | Documentos con membrete profesional. Editor post-generación con soporte markdown |
| **RBAC** | 4 roles (admin, abogado, pasante, consulta) con 8 permisos granulares |
| **API REST** | FastAPI con CORS, rate limiting, security headers, health check |

---

## Arquitectura

```
src/
├── domain/                  # Modelos, excepciones, ports (interfaces)
│   ├── models.py            # Pydantic: TenantConfig, Entity, User, Permission, Role
│   ├── exceptions.py        # DomainException, AuthenticationException, etc.
│   └── ports/
│       ├── in_ports.py      # GenerateDocumentPort (driving)
│       └── out_ports.py     # AI, Tenant, Template, Entity, User, FileExporter, KnowledgeBase
│
├── application/             # Casos de uso y servicios
│   ├── use_cases/
│   │   └── generate_document.py   # Orquesta: tenant → prompt + RAG → Gemini → DOCX
│   └── services/
│       └── auth_service.py        # bcrypt, authenticate, ensure_default_admin
│
└── infrastructure/          # Adaptadores concretos
    ├── container.py         # Composition Root (inyección de dependencias)
    ├── logging_config.py    # Logging rotativo centralizado
    ├── ingestion/
    │   └── ingest_service.py      # Extracción de texto PDF/TXT/DOCX para RAG
    └── adapters/
        ├── input/
        │   ├── api/routes.py      # FastAPI controller
        │   └── ui/                # Streamlit frontend
        │       ├── pages/         # login, generate, templates, entities, company, users
        │       ├── components.py  # Componentes reutilizables
        │       ├── constants.py   # Configuración centralizada
        │       └── state.py       # CRUD wrappers + auth helpers
        └── output/
            ├── ai_gemini.py       # Gemini adapter (retry + timeout)
            ├── db_sqlite.py       # SQLite repository (4 ports)
            ├── doc_generator.py   # DOCX + PDF engine
            └── knowledge_base.py  # ChromaDB + Gemini Embeddings
```

---

## Requisitos previos

- **Python** 3.12+
- **API Key** de [Google AI Studio](https://aistudio.google.com/apikey) (Gemini)

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd derecho_peticion

# 2. Crear entorno virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/macOS
# Editar .env y agregar tu GEMINI_API_KEY
```

---

## Variables de entorno

| Variable | Descripción | Default |
|---|---|---|
| `GEMINI_API_KEY` | API key de Google Gemini | — (requerida) |
| `GEMINI_MODEL` | Modelo de IA | `gemini-2.5-flash` |
| `DB_PATH` | Ruta de la base de datos SQLite | `legal_engine.db` |
| `CHROMA_DIR` | Directorio de ChromaDB | `chroma_db` |
| `RAG_CHUNK_SIZE` | Tamaño de fragmento para RAG | `1500` |
| `RAG_CHUNK_OVERLAP` | Solapamiento entre fragmentos | `200` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |
| `LOG_FILE` | Ruta del archivo de log | `logs/app.log` |
| `API_HOST` | Host de la API | `localhost` |
| `API_PORT` | Puerto de la API | `8000` |
| `CORS_ORIGINS` | Orígenes permitidos (separados por coma) | `http://localhost:8501` |
| `RATE_LIMIT_RPM` | Requests por minuto por IP | `30` |
| `ENABLE_DOCS` | Habilitar Swagger UI en `/docs` | `true` |
| `API_TIMEOUT_GENERATE` | Timeout de generación (segundos) | `120` |

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

### Credenciales por defecto

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `admin123` | Administrador (todos los permisos) |
| `abogado` | `abogado123` | Abogado (genera, ve plantillas/entidades/empresa, gestiona entidades) |
| `pasante` | `pasante123` | Pasante (genera, ve plantillas y entidades) |
| `consulta` | `consulta123` | Solo consulta (ve plantillas, entidades y empresa) |

> Se crean automáticamente al primer arranque si no existen usuarios.

---

## API Endpoints

### `POST /api/v1/documents/generate`

Genera un documento jurídico.

**Headers:**
```
X-Tenant-ID: <tenant_id>
Content-Type: application/json
```

**Body:**
```json
{
  "template_id": "derecho-peticion-v1",
  "metadata": {
    "cliente_nombre": "<name>",
    "cedula": "<document_id>",
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

Health check del servicio.

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
| Embeddings | Gemini Embedding 001 |
| Base de conocimiento | ChromaDB (vectorial) |
| Base de datos | SQLite (WAL mode) |
| Exportación DOCX | python-docx |
| Exportación PDF | fpdf2 |
| Autenticación | bcrypt |
| Arquitectura | Hexagonal (Ports & Adapters) |

---

## Estructura de la base de datos

```
tenants            — Empresas / firmas (multi-tenant)
templates          — Plantillas de documentos
template_documents — Documentos RAG indexados por plantilla
entities           — Entidades destinatarias
users              — Usuarios con roles RBAC
```

---

## Licencia

Proyecto privado — FuturoTech AI.
