# FuturoTech AI — Universal Legal Engine

## 📋 Descripción del Proyecto

**FuturoTech AI** es un motor universal para la generación automatizada de documentos jurídicos que utiliza inteligencia artificial (Google Gemini) para crear documentos legales personalizados basados en plantillas y metadatos específicos.

## 🎯 Funcionalidad Principal

El sistema permite a firmas de abogados y profesionales del derecho generar automáticamente documentos jurídicos formales (como derechos de petición) mediante:

- **Configuración multi-tenant**: Cada firma puede tener su propia configuración, branding y reglas jurídicas
- **Generación con IA**: Utiliza Google Gemini para crear contenido jurídico contextualizado
- **Exportación a DOCX**: Genera documentos Word con formato profesional y branding personalizado
- **API REST**: Interfaz HTTP para integración con otros sistemas

## 🏗️ Arquitectura

El proyecto sigue una **arquitectura hexagonal (Clean Architecture)** con separación clara de responsabilidades:

```
src/
├── domain/           # Lógica de negocio y modelos
├── application/      # Casos de uso
└── infrastructure/   # Adaptadores externos
    ├── input/        # API REST (FastAPI)
    └── output/       # IA (Gemini), Base de datos, Generador DOCX
```

### Componentes Principales

- **Domain**: Modelos de datos, excepciones y puertos (interfaces)
- **Application**: Caso de uso principal `GenerateDocumentUseCase`
- **Infrastructure**: 
  - API REST con FastAPI
  - Adaptador para Google Gemini AI
  - Generador de documentos DOCX
  - Repositorio de configuración de tenants

## 🚀 Funcionalidades

### 1. Gestión Multi-Tenant
- Configuración independiente por firma legal
- Branding personalizado (logos, colores, encabezados)
- Reglas jurídicas específicas por tenant
- Campos obligatorios configurables

### 2. Generación de Documentos
- Plantillas parametrizables
- Contexto jurídico inteligente
- Integración con Google Gemini AI
- Validación de metadatos requeridos

### 3. Exportación Profesional
- Documentos DOCX con formato
- Branding corporativo aplicado
- Descarga directa vía URL

## 📡 API Endpoints

### `POST /api/v1/documents/generate`

Genera un documento jurídico basado en plantilla y metadatos.

**Headers:**
- `X-Tenant-ID`: Identificador del tenant (firma legal)

**Request Body:**
```json
{
  "template_id": "REQ-PENSIONAL-V1",
  "metadata": {
    "cliente_nombre": "Juan Pérez",
    "cedula": "12345678",
    "entidad_demandada": "Ministerio de Salud",
    "hechos_crudos": "Descripción de los hechos..."
  }
}
```

**Response:**
```json
{
  "transaction_id": "uuid-generado",
  "status": "COMPLETED",
  "download_url": "/files/documento.docx"
}
```

## 🔧 Configuración de Tenants

Cada tenant se configura en `tenants.json`:

```json
{
  "tenant_id": "firma-abc",
  "name": "Firma ABC Abogados",
  "system_prompt": "Eres un abogado experto en derecho administrativo...",
  "legal_rules": [
    "Artículo 23 de la Constitución Política de Colombia",
    "Ley 1755 de 2015 — Derecho fundamental de petición"
  ],
  "branding": {
    "header_text": "FIRMA ABC ABOGADOS ASOCIADOS",
    "footer_text": "NIT 900.123.456-7 | Bogotá D.C.",
    "primary_color": "#1a237e"
  },
  "required_fields": ["cliente_nombre", "cedula", "entidad_demandada"]
}
```

## 🛠️ Tecnologías Utilizadas

- **FastAPI**: Framework web para la API REST
- **Google Gemini AI**: Modelo de IA para generación de contenido jurídico
- **python-docx**: Generación de documentos Word
- **Pydantic**: Validación de datos y modelos
- **Uvicorn**: Servidor ASGI

## 📦 Instalación y Ejecución

1. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

2. **Configurar variables de entorno:**
```bash
# .env
GEMINI_API_KEY=tu_api_key_de_gemini
```

3. **Ejecutar el servidor:**
```bash
python src/main.py
```

El servidor estará disponible en `http://localhost:8000`

## 📁 Estructura de Archivos Generados

Los documentos se almacenan en `generated_docs/` con el formato:
```
{transaction_id}_{template_id}.docx
```

## 🎯 Casos de Uso Principales

1. **Derecho de Petición**: Generación automática de solicitudes formales ante entidades públicas
2. **Documentos Corporativos**: Contratos, cartas legales, etc.
3. **Multi-jurisdicción**: Soporte para diferentes marcos legales (Colombia, Estados Unidos, etc.)

## 🔒 Características de Seguridad

- Validación estricta de metadatos requeridos
- Manejo de excepciones específicas del dominio
- Configuración segura de API keys
- Separación de responsabilidades por tenant

## 📈 Escalabilidad

- Arquitectura modular y extensible
- Fácil adición de nuevos proveedores de IA
- Soporte para múltiples formatos de exportación
- Configuración flexible por tenant

---

**Versión**: 1.0.0  
**Título**: FuturoTech AI — Universal Legal Engine