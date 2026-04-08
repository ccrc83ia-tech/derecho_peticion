# FuturoTech AI — Motor Jurídico Universal
## Documento Funcional del Producto

---

## 1. ¿Qué es FuturoTech AI?

FuturoTech AI es una plataforma de generación automatizada de documentos jurídicos impulsada por inteligencia artificial. Permite a firmas de abogados, consultorios jurídicos y profesionales del derecho crear documentos legales formales (derechos de petición, tutelas, demandas, contratos, etc.) en minutos, con calidad profesional, membrete corporativo y fundamentación jurídica precisa.

El sistema combina un motor de IA generativa (Google Gemini) con una base de conocimiento legal propia (RAG), lo que garantiza que los documentos generados citen normas reales y actualizadas, no información inventada.

---

## 2. ¿Qué problema resuelve?

| Problema actual | Cómo lo resuelve FuturoTech AI |
|---|---|
| Redactar un derecho de petición toma entre 30 minutos y 2 horas | Lo genera en menos de 1 minuto |
| Cada abogado redacta con estilo diferente, sin estándar | Plantillas con instrucciones de IA estandarizan el tono y estructura |
| Se olvidan artículos o se citan normas incorrectas | El sistema RAG inyecta el texto literal de las leyes aplicables |
| Copiar/pegar de modelos anteriores introduce errores | Cada documento se genera desde cero con los datos específicos del caso |
| No hay membrete ni formato profesional consistente | Branding automático: encabezado, pie de página, color corporativo, datos de contacto |
| Depender de ChatGPT requiere escribir el prompt correcto cada vez | El prompt está pre-configurado por plantilla, el usuario solo llena los datos del caso |

---

## 3. Módulos funcionales

### 3.1 Gestión de Empresas (Multi-tenant)

Permite registrar múltiples firmas de abogados o consultorios. Cada empresa tiene:

- **Datos corporativos**: nombre, NIT, dirección, teléfono, email, sitio web
- **Membrete del documento**: texto de encabezado, pie de página, logo (URL), color corporativo
- **Estado activo/inactivo**: solo una empresa puede estar activa a la vez; al activar una, las demás se desactivan automáticamente
- **Vista previa del membrete**: se muestra en tiempo real cómo se verá el encabezado del documento

**Caso de uso**: Un abogado que trabaja para dos firmas puede cambiar entre ellas y generar documentos con el membrete correcto de cada una.

### 3.2 Gestión de Plantillas

Cada tipo de documento jurídico se configura como una plantilla independiente con:

- **Información general**: ID único, nombre, descripción
- **Instrucciones para la IA (System Prompt)**: define cómo debe redactar la IA. Ejemplo: *"Eres un abogado experto en derecho administrativo colombiano. Genera derechos de petición formales con lenguaje respetuoso y preciso, citando las normas aplicables."*
- **Reglas jurídicas**: lista de leyes y normas que la IA debe aplicar. Ejemplo:
  - Artículo 23 de la Constitución Política de Colombia
  - Ley 1755 de 2015 — Derecho fundamental de petición
  - CPACA — Código de Procedimiento Administrativo
- **Campos dinámicos del formulario**: cada plantilla define qué datos necesita del usuario (nombre del cliente, cédula, entidad demandada, hechos del caso, etc.), con etiquetas personalizadas y marcación de campos obligatorios
- **Documentos de referencia (RAG)**: archivos PDF, TXT o DOCX con el texto completo de las leyes aplicables. El sistema los procesa, los fragmenta y los indexa para que la IA los use como fuente literal

**Caso de uso**: Se crea la plantilla "Derecho de Petición" con su prompt especializado, se le suben los PDFs de la Ley 1755 y el CPACA, y se definen los campos: nombre del cliente, cédula, entidad demandada, hechos del caso. Cualquier usuario de la firma puede generar derechos de petición sin conocer el prompt ni las normas.

### 3.3 Generación de Documentos

El flujo de generación es:

1. **Seleccionar empresa** (se pre-selecciona la activa)
2. **Seleccionar plantilla** (ej: "Derecho de Petición")
3. **Activar/desactivar reglas jurídicas** (checkboxes con las normas de la plantilla)
4. **Llenar los datos del caso** en un formulario dinámico generado a partir de los campos de la plantilla
5. **Generar** — el sistema:
   - Busca en la base de conocimiento (RAG) los fragmentos de ley más relevantes para este caso
   - Compone un prompt con: instrucciones de la IA + reglas jurídicas + texto literal de las normas + datos del caso
   - Envía todo a Google Gemini
   - Recibe el texto generado
   - Lo convierte en un documento DOCX con membrete corporativo
6. **Editar el documento** — el texto generado se muestra en un editor donde el abogado puede modificarlo antes de descargar. Soporta formato: **negrilla** y *cursiva*
7. **Descargar DOCX** — el documento final incluye encabezado con logo y datos de contacto, cuerpo con formato, y pie de página

**Caso de uso**: Un asistente jurídico llena nombre, cédula, entidad y hechos. En 30 segundos tiene un derecho de petición completo, con citas textuales de la Ley 1755, listo para revisar y firmar.

### 3.4 Base de Conocimiento Legal (RAG)

Este es el diferenciador técnico más importante del sistema:

- **Qué es**: una base de datos vectorial (ChromaDB) donde se almacenan los textos completos de leyes, normas, decretos y cualquier documento legal relevante
- **Cómo funciona**:
  1. El usuario sube un PDF (ej: Ley 1755 de 2015 completa)
  2. El sistema extrae el texto del PDF
  3. Lo divide en fragmentos de ~1500 caracteres con solapamiento
  4. Genera embeddings (representaciones numéricas) de cada fragmento usando Google Gemini
  5. Los almacena en ChromaDB, asociados a la plantilla
  6. Al generar un documento, busca los fragmentos más relevantes según los datos del caso
  7. Los inyecta en el prompt para que la IA cite textualmente
- **Cada plantilla tiene su propia colección**: los documentos de "Derecho de Petición" no se mezclan con los de "Tutela"
- **Se pueden agregar y eliminar documentos** desde la interfaz

**Caso de uso**: Se sube el PDF completo del CPACA (400+ páginas). Cuando un usuario genera un derecho de petición sobre pensiones, el sistema automáticamente encuentra y le pasa a la IA los artículos relevantes sobre términos de respuesta y silencio administrativo, no todo el código.

### 3.5 API REST

El sistema expone una API REST (FastAPI) que permite integración con otros sistemas:

- **POST /api/v1/documents/generate** — genera un documento enviando tenant_id, template_id, metadata y reglas seleccionadas
- **GET /files/{filename}** — descarga el DOCX generado
- **Documentación automática** en /docs (Swagger UI)

**Caso de uso**: Un sistema de gestión de casos (CRM jurídico) puede llamar a la API para generar documentos automáticamente cuando se crea un nuevo caso.

### 3.6 Sistema de Logging

Registro completo de toda la actividad:

- Cada generación tiene un transaction_id único para trazabilidad
- Se registra: tenant, plantilla, campos enviados, longitud del prompt, resultado de la IA, ruta del archivo generado
- Logs rotativos (5MB máximo, 3 backups) en `logs/app.log`
- Nivel configurable por variable de entorno

---

## 4. ¿Por qué usar FuturoTech AI en vez de ChatGPT u otra IA genérica?

| Aspecto | ChatGPT / IA genérica | FuturoTech AI |
|---|---|---|
| **Conocimiento legal** | Recuerda normas de su entrenamiento, puede inventar artículos o citar versiones desactualizadas | Usa el texto literal de las leyes que usted sube (RAG). No inventa, cita textualmente |
| **Consistencia** | Cada vez hay que escribir el prompt desde cero. Dos personas obtienen resultados diferentes | El prompt está pre-configurado por plantilla. Todos los usuarios generan con el mismo estándar |
| **Membrete profesional** | Genera texto plano. Hay que copiar/pegar en Word y formatear manualmente | Genera DOCX con encabezado, logo, datos de contacto, color corporativo y pie de página automáticamente |
| **Datos del caso** | Hay que explicarle a la IA qué datos necesita cada vez | Formulario dinámico con campos obligatorios. El usuario solo llena y genera |
| **Seguridad de datos** | Los datos del cliente se envían a servidores de OpenAI/terceros sin control | La aplicación corre en su propia infraestructura. Los datos no salen de su servidor (excepto la llamada a Gemini para generar) |
| **Reglas jurídicas** | Hay que recordar qué leyes aplican y mencionarlas en el prompt | Las reglas están configuradas por plantilla. Se activan con un checkbox |
| **Edición post-generación** | Hay que copiar el texto, pegarlo en Word, formatear | Editor integrado con vista previa. Edita y descarga sin salir de la aplicación |
| **Multi-empresa** | No aplica | Cambie entre firmas de abogados con un clic. Cada una con su membrete |
| **Escalabilidad** | Un chat a la vez | API REST permite integración con CRMs, generación masiva, automatización |
| **Costo** | ChatGPT Plus: $20 USD/mes por usuario | Una sola API key de Gemini sirve para toda la firma |
| **Actualización de normas** | Depende de cuándo se re-entrenó el modelo | Usted sube el PDF actualizado y el sistema lo usa inmediatamente |

---

## 5. ¿Por qué usar FuturoTech AI en vez de hacerlo manualmente?

| Aspecto | Proceso manual | FuturoTech AI |
|---|---|---|
| **Tiempo por documento** | 30 min — 2 horas | Menos de 1 minuto |
| **Errores de transcripción** | Copiar/pegar de modelos anteriores introduce datos de otros clientes | Cada documento se genera desde cero con los datos correctos |
| **Citas legales** | Hay que buscar el artículo exacto, copiarlo, verificar vigencia | El sistema busca automáticamente en la base de conocimiento y cita textualmente |
| **Formato y presentación** | Depende de quién lo haga. Fuentes, márgenes y estilos inconsistentes | Formato profesional estandarizado con membrete corporativo |
| **Capacitación** | Un abogado junior necesita meses para redactar bien | Con la plantilla configurada, cualquier asistente genera documentos de calidad senior |
| **Volumen** | Un abogado puede hacer 5-10 documentos al día | Sin límite práctico. Se pueden generar cientos por día |
| **Trazabilidad** | No hay registro de quién generó qué, cuándo, con qué datos | Cada documento tiene transaction_id, timestamp y log completo |
| **Actualización de modelos** | Cuando cambia una ley, hay que actualizar todos los modelos Word manualmente | Se actualiza la plantilla y/o se sube el nuevo PDF. Todos los documentos futuros usan la versión actualizada |

---

## 6. Flujo operativo típico

```
┌─────────────────────────────────────────────────────────┐
│                   CONFIGURACIÓN INICIAL                  │
│                     (se hace una vez)                     │
├─────────────────────────────────────────────────────────┤
│  1. Registrar empresa (nombre, NIT, membrete, logo)     │
│  2. Crear plantilla (ej: "Derecho de Petición")         │
│     - Escribir instrucciones para la IA                 │
│     - Agregar reglas jurídicas                          │
│     - Definir campos del formulario                     │
│     - Subir PDFs de las leyes aplicables                │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    USO DIARIO                             │
│              (cada vez que se necesita un documento)      │
├─────────────────────────────────────────────────────────┤
│  1. Seleccionar plantilla                               │
│  2. Llenar datos del caso (nombre, cédula, hechos)      │
│  3. Clic en "Generar"                                   │
│  4. Revisar/editar el documento generado                │
│  5. Descargar DOCX                                      │
│  6. Imprimir, firmar y radicar                          │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Arquitectura técnica (resumen)

| Componente | Tecnología | Función |
|---|---|---|
| Backend API | Python + FastAPI | Orquesta la generación de documentos |
| Frontend | Python + Streamlit | Interfaz web para usuarios |
| IA Generativa | Google Gemini 2.5 Flash | Redacta el contenido del documento |
| Base de conocimiento | ChromaDB + Gemini Embeddings | Almacena y busca textos legales (RAG) |
| Base de datos | SQLite | Empresas, plantillas, documentos subidos |
| Exportación | python-docx | Genera archivos DOCX con formato profesional |
| Arquitectura | Hexagonal (Ports & Adapters) | Desacoplamiento, testabilidad, extensibilidad |

---

## 8. Configuración parametrizable

Todo el sistema es configurable sin tocar código:

| Parámetro | Variable de entorno | Valor por defecto |
|---|---|---|
| Modelo de IA | `GEMINI_MODEL` | gemini-2.5-flash |
| API Key de Gemini | `GEMINI_API_KEY` | — |
| Base de datos | `DB_PATH` | legal_engine.db |
| Directorio ChromaDB | `CHROMA_DIR` | chroma_db |
| Tamaño de fragmento RAG | `RAG_CHUNK_SIZE` | 1500 |
| Solapamiento de fragmentos | `RAG_CHUNK_OVERLAP` | 200 |
| Nivel de log | `LOG_LEVEL` | INFO |
| Puerto de la API | `API_PORT` | 8000 |
| Timeout de generación | `API_TIMEOUT_GENERATE` | 120 segundos |

---

## 9. Tipos de documentos soportados

El sistema es genérico — soporta cualquier tipo de documento jurídico mediante plantillas:

- Derechos de petición
- Acciones de tutela
- Demandas laborales
- Demandas administrativas
- Contratos
- Poderes
- Memoriales
- Recursos de reposición y apelación
- Cualquier otro documento que se pueda parametrizar con campos + instrucciones de IA + normas aplicables

---

## 10. Roadmap futuro

| Funcionalidad | Estado |
|---|---|
| Generación con IA (Gemini) | ✅ Implementado |
| Multi-empresa con membrete | ✅ Implementado |
| Plantillas dinámicas | ✅ Implementado |
| RAG con base de conocimiento legal | ✅ Implementado |
| Editor de documentos post-generación | ✅ Implementado |
| Exportación DOCX con formato | ✅ Implementado |
| Exportación PDF con membrete | ✅ Implementado |
| API REST para integración | ✅ Implementado |
| Logging y trazabilidad | ✅ Implementado |
| Autenticación de usuarios (RBAC) | ✅ Implementado |
| Entidades destinatarias (27 tipos) | ✅ Implementado |
| Seguridad (CORS, rate limiting, headers) | ✅ Implementado |
| Historial de documentos generados | 🔜 Próximamente |
| Tests unitarios e integración | 🔜 Próximamente |
| Firma digital integrada | 🔜 Próximamente |
| Despliegue en AWS (ECS/Lambda) | 🔜 Próximamente |
