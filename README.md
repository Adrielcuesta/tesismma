<p align="center">
  <img src="static/images/logo_itba_rag.png" alt="Logo Proyecto RAG ITBA" width="250"/>
</p>
<h1 align="center">TESIS FIN DE MAESTRÍA</h1>
<h2 align="center">Innovación en entornos empresariales</h2>
<h3 align="center">Sistemas RAG para la Optimización de la Gestión de Proyectos y Análisis Estratégico</h3>
<h4 align="center" class="app-subtitle">ANALIZADOR DE RIESGOS CON IA</h4>
<p align="center">
  <strong>ITBA - Instituto Tecnológico Buenos Aires</strong><br>
  <strong>Maestría en Management & Analytics</strong><br>
  <strong>Alumno: Adriel J. Cuesta</strong>
</p>

Repositorio: [https://github.com/Adrielcuesta/tesismma.git](https://github.com/Adrielcuesta/tesismma.git)

## Descripción del Proyecto

Este proyecto implementa un sistema avanzado de **Generación Aumentada por Recuperación (RAG)** enfocado en el análisis de riesgos para la instalación de maquinaria industrial. El sistema utiliza una base de conocimiento documental y un Modelo de Lenguaje Grande (LLM) de Google (Gemini) para identificar, evaluar y detallar riesgos potenciales asociados a un nuevo proyecto descrito por el usuario.

La interacción principal con el sistema se realiza a través de una **aplicación web intuitiva desarrollada con Flask**, que permite la carga de documentos, la configuración del análisis y la visualización de resultados. Al finalizar, el sistema genera:

* Un **reporte JSON** estructurado con los hallazgos.
* Un **dashboard HTML dinámico y visualmente armonizado** con la interfaz principal.
* Opcionalmente, un **reporte en formato PDF** para facilitar su distribución y archivo.

Además, el proyecto está **preparado para ser empaquetado con Docker**, facilitando su despliegue en diferentes entornos, incluyendo la nube.

## Características Principales

* **Interfaz Web Moderna con Flask:** Permite una gestión sencilla de los documentos (base de conocimiento y proyecto a analizar) y la ejecución del análisis.
* **Salida Multiformato:** Generación de resultados en JSON, HTML interactivo y PDF (opcional).
* **Configuración Flexible del Análisis:**
    * Opción para utilizar una base de conocimiento vectorial existente o reconstruirla con nuevos PDFs.
    * Opción para analizar un PDF de proyecto previamente cargado o subir uno nuevo para cada análisis.
* **Análisis Basado en RAG:** Utiliza el poder de los LLMs (Gemini) aumentado con información específica de una base de conocimiento para un análisis de riesgos contextualizado.
* **Componentes Modulares:** El backend está organizado en módulos de Python para una mejor mantenibilidad y escalabilidad.
* **Persistencia de Datos:** La base de datos vectorial (ChromaDB) se almacena localmente, permitiendo su reutilización.
* **Dockerizable:** Incluye `Dockerfile` y `.dockerignore` para una fácil creación de imágenes Docker.
* **Documentación de Soporte:** Notebooks de Jupyter en `notebooks_documentacion/` ofrecen explicaciones detalladas sobre los componentes y la lógica original del sistema RAG.

## Requisitos Previos

* **Python:** Versión 3.10, 3.11 o 3.12 (Python 3.12 es la recomendada y usada para el desarrollo).
* **Git:** Para clonar el repositorio.
* **Docker:** Docker Desktop (Windows/macOS) o Docker Engine (Linux) es necesario si se desea ejecutar la versión dockerizada.
* **API Key de Google Gemini:** Una clave válida para acceder al LLM de Gemini.
* **Microsoft C++ Build Tools (Windows):** Altamente recomendado tenerlas instaladas (o el Visual C++ Redistributable como mínimo) para la correcta instalación de algunas dependencias de Python que requieren compilación (ej. `numpy`, `onnxruntime`). Se pueden obtener desde la [página de descargas de Visual Studio](https://visualstudio.microsoft.com/es/downloads/) (buscar "Herramientas de compilación para Visual Studio" e instalar la carga de trabajo "Desarrollo para el escritorio con C++").

## Estructura del Proyecto Detallada

```plaintext
tesismma/
├── app.py                      # Aplicación principal Flask (interfaz de usuario)
├── Dockerfile                  # Instrucciones para construir la imagen Docker
├── .dockerignore               # Archivos y carpetas a ignorar por Docker
├── datos/
│   ├── BaseConocimiento/       # PDFs para la base de conocimiento (subidos vía app.py)
│   ├── ProyectoAnalizar/       # PDF del proyecto a analizar (subido vía app.py)
│   ├── ChromaDB_V1/            # Base de datos vectorial (generada, ignorada por Git)
│   └── Resultados/             # Reportes (JSON, HTML, PDF) (generados, ignorados por Git)
├── modelos_locales/            # Opcional: para modelos de embedding descargados localmente
│   └── all-MiniLM-L6-v2/       # Ejemplo de un modelo de embedding local
├── notebooks_documentacion/    # Notebooks Jupyter con explicaciones de componentes
├── scripts/                    # Módulos de Python con la lógica del sistema
│   ├── init.py
│   ├── config.py               # Configuración central (rutas, API keys, parámetros)
│   ├── document_utils.py       # Utilidades para cargar y procesar PDFs
│   ├── vector_db_manager.py    # Gestión de la base de datos vectorial ChromaDB
│   ├── rag_components.py       # Componentes RAG (LLM, prompt, cadena de consulta)
│   ├── report_utils.py         # Generación y formateo del reporte JSON
│   ├── dashboard_generator.py  # Generación del dashboard HTML dinámico
│   ├── pdf_utils.py            # Generación de reportes PDF desde HTML (usa WeasyPrint)
│   ├── main.py                 # Orquestador del flujo de análisis (invocado por app.py)
│   ├── descargar_modelo.py     # Script para descargar modelos de embedding
│   └── test_chroma_super_minimal.py # Script de diagnóstico para ChromaDB
├── static/                     # Archivos estáticos para la aplicación Flask
│   └── images/                 # Logos e imágenes para la interfaz y dashboards
│       ├── header_banner_abstract.png  # Banner principal
│       ├── logo-itba.png               # Logo circular para cabecera
│       ├── itba.png                    # Logo institucional ITBA para footer
│       └── logo_itba_rag.png           # Logo para este README
├── .env                        # Archivo para variables de entorno 
├── .env.example                # Plantilla para el archivo .env
├── requirements.txt            # Dependencias de Python del proyecto
├── .gitignore                  # Archivos y carpetas ignoradas por Git
└── README.md                   # Este archivo
```
## Configuración y Ejecución Local (Recomendado para Desarrollo y Pruebas)

Sigue estos pasos para configurar y ejecutar el proyecto en tu máquina local:

1.  **Clonar el Repositorio:**
    ```bash
    git clone https://github.com/Adrielcuesta/tesismma.git
    cd tesismma
    ```

2.  **Crear y Activar Entorno Virtual:**
    Se recomienda usar Python 3.12.
    ```bash
    # Ejemplo con Python 3.12 en Windows (ajusta según tu comando de Python)
    py -3.12 -m venv venv
    Set-ExecutionPolicy Unrestricted -Scope Proces
    .\venv\Scripts\Activate.ps1
    ```
    ```bash
    # Windows CMD:
    venv\Scripts\activate
    # Linux/macOS:
    source venv/bin/activate
    ```
    Sabrás que está activado porque verás `(venv)` al inicio de tu línea de comandos.

3.  **Instalar Dependencias:**
    Con el entorno virtual activado:
    ```bash
    pip install -r requirements.txt
    ```
    *Nota para usuarios de Linux:* Si la instalación de `WeasyPrint` (para los PDFs) falla, es probable que necesites instalar algunas dependencias de sistema adicionales. Consulta la sección "Requisitos Previos".

4.  **Configurar Variables de Entorno:**
    * Copia el archivo `.env.example` y renómbralo a `.env` en la raíz del proyecto (`tesismma/`).
    * Abre `.env` con un editor de texto y añade tu `GEMINI_API_KEY` real donde se indica.
      Si aún no tienes una API Key, puedes obtenerla de forma gratuita haciendo clic aquí: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
    
        ```
        GEMINI_API_KEY="TU_API_KEY_DE_GEMINI_AQUI"
        # FLASK_SECRET_KEY="UNA_CLAVE_SECRETA_ALEATORIA_Y_LARGA" # Opcional, se autogenera si no está.
        # EMBEDDING_MODEL_PATH="modelos_locales/all-MiniLM-L6-v2" # Opcional, para usar un modelo local
        ```
    * Si deseas usar un modelo de embedding local, descomenta y configura `EMBEDDING_MODEL_PATH` apuntando a la ruta relativa del modelo dentro del proyecto (ej. `modelos_locales/all-MiniLM-L6-v2`).

5.  **Ejecutar la Aplicación Web Flask:**
    Desde la raíz del proyecto (`tesismma/`) y con el entorno virtual activado:
    ```bash
    python app.py
    ```
    La consola te indicará que el servidor de desarrollo está corriendo, usualmente en `http://127.0.0.1:8080` o `http://localhost:8080`.

6.  **Usar la Aplicación:**
    * Abre la URL proporcionada por Flask en tu navegador web.
    * **Carga de Archivos:**
        * **Base de Conocimiento:** Sube los PDFs que formarán tu base de conocimiento.
            * Si desmarcas "Usar Base de Conocimiento por defecto", se creará una nueva base vectorial con los archivos que subas (o los existentes en la carpeta `datos/BaseConocimiento/` si no subes nuevos).
            * Si la dejas marcada, se intentará usar una base vectorial ya existente.
        * **Proyecto a Analizar:** Sube el PDF del proyecto que deseas analizar.
            * Si desmarcas "Utilizar documento previamente cargado", debes subir un archivo.
            * Si la dejas marcada, se usará el último archivo que esté en `datos/ProyectoAnalizar/`.
    * **Generación de PDF:** Marca la casilla "Generar también reporte en PDF" si deseas esta salida adicional.
    * Haz clic en "Iniciar Análisis".
    * El dashboard HTML con los resultados se mostrará en el navegador. Los archivos generados (JSON, HTML y opcionalmente PDF) se guardarán en una subcarpeta dentro de `datos/Resultados/`, nombrada según el archivo del proyecto analizado.

**Nota sobre `RECREAR_DB` en `config.py`:**
La variable `RECREAR_DB` en `scripts/config.py` establece el comportamiento por defecto para la creación de la base de datos vectorial si el script `main.py` se ejecutara directamente. Sin embargo, al usar la interfaz web (`app.py`), la decisión de recrear la base de conocimiento es controlada dinámicamente por la casilla "Usar Base de Conocimiento por defecto" en la interfaz.

## Ejecución con Docker (Opcional)

Para ejecutar la aplicación en un entorno aislado y portable usando Docker:

1.  **Asegúrate de que Docker Desktop (o Docker Engine) esté instalado y corriendo.**
2.  **Archivo `.env`:** Confirma que tu archivo `.env` con la `GEMINI_API_KEY` esté presente en la raíz del proyecto. El `Dockerfile` está configurado para copiarlo a la imagen. Para entornos de producción, considera métodos más seguros para la gestión de secretos.
3.  **Construir la Imagen Docker:**
    Navega a la raíz de tu proyecto (`tesismma/`) en la terminal y ejecuta:
    ```bash
    docker build -t mi-analizador-riesgos .
    ```
    (Puedes usar el nombre que prefieras en lugar de `mi-analizador-riesgos`).

4.  **Ejecutar el Contenedor Docker:**
    ```bash
    docker run -p 8080:8080 --rm mi-analizador-riesgos
    ```
    * `-p 8080:8080`: Mapea el puerto 8080 de tu máquina al puerto 8080 del contenedor.
    * `--rm`: Elimina el contenedor automáticamente cuando se detiene (conveniente para pruebas).
    * Si el archivo `.env` no se leyera correctamente dentro del contenedor o prefieres pasar la API key explícitamente:
        ```bash
        docker run -p 8080:8080 -e GEMINI_API_KEY="TU_API_KEY_AQUI" --rm mi-analizador-riesgos
        ```

5.  **Acceder a la Aplicación en Docker:**
    Abre tu navegador web y ve a `http://localhost:8080`. La aplicación debería funcionar igual que en la ejecución local.

## Descripción Actualizada de Módulos Clave

* **`app.py` (Raíz del Proyecto):** Aplicación web principal desarrollada con Flask. Proporciona la interfaz de usuario para la carga de archivos, inicio de análisis y visualización (sirve el dashboard HTML).
* **`scripts/config.py`**: Define configuraciones globales, rutas (incluyendo `INFO_TESIS` para datos de la tesis), parámetros y carga la API key.
* **`scripts/main.py`**: Orquestador del flujo completo de análisis RAG. Es invocado por `app.py` y coordina los demás módulos del backend.
* **`scripts/document_utils.py`**: Utilidades para cargar, parsear y fragmentar documentos PDF.
* **`scripts/vector_db_manager.py`**: Gestión de la base de datos vectorial ChromaDB y los embeddings.
* **`scripts/rag_components.py`**: Define la plantilla del prompt, inicializa el LLM (Gemini) y construye la cadena de RAG (RetrievalQA).
* **`scripts/report_utils.py`**: Parsea la respuesta JSON del LLM, asigna estados RAG y guarda el resultado en un archivo JSON estructurado.
* **`scripts/dashboard_generator.py`**: Genera un dashboard HTML dinámico y visualmente estilizado a partir del archivo JSON de resultados.
* **`scripts/pdf_utils.py`**: Utilidades para generar reportes PDF a partir del contenido HTML del dashboard, utilizando la biblioteca WeasyPrint.
* **`scripts/descargar_modelo.py`**: Script de utilidad para descargar modelos de embedding (ej. `all-MiniLM-L6-v2`) a la carpeta `modelos_locales/`.
* **`scripts/test_chroma_super_minimal.py`**: Script de diagnóstico para probar la funcionalidad básica de ChromaDB.

## Solución de Problemas Comunes

* **`GEMINI_API_KEY not found`**: Verifica que el archivo `.env` exista en la raíz, contenga tu API Key correctamente, y que sea accesible por la aplicación (especialmente en Docker).
* **Imágenes no se muestran en la aplicación web (`app.py`) o en el dashboard HTML:**
    * Asegúrate de que todos los archivos de imagen (`header_banner_abstract.png`, `logo-itba.png`, `itba.png`, `logo_itba_rag.png`) estén en la carpeta `tesismma/static/images/` con esos nombres y extensiones **.png** exactos.
    * Fuerza un refresco completo del navegador (Ctrl+Shift+R o Cmd+Shift+R) para evitar problemas de caché.
* **Errores con WeasyPrint al generar PDF (especialmente en Linux):**
    * Instala las dependencias de sistema requeridas por WeasyPrint (Pango, Cairo, GDK-PixBuf, etc.). Consulta la sección "Requisitos Previos".
* **Errores de `ImportError: DLL load failed` (Windows, durante `pip install`):**
    * Instala las **Microsoft C++ Build Tools** (con la carga de trabajo "Desarrollo para el escritorio con C++") y reinicia tu PC.
* **Errores de `CERTIFICATE_VERIFY_FAILED`:**
    * Verifica que `certifi` esté instalado.
    * Si estás detrás de un proxy corporativo, configura las variables de entorno `HTTP_PROXY` y `HTTPS_PROXY`.
* **Problemas con ChromaDB (crashes silenciosos o errores de compilación):**
    * Asegúrate de usar una versión de Python compatible (3.10-3.12).
    * Verifica la instalación de las Microsoft C++ Build Tools.
    * Asegúrate de que `numpy` (una versión compatible, `requirements.txt` debería manejar esto) y `onnxruntime` (si es una dependencia indirecta de tus modelos de embedding) estén instalados correctamente.
    * Prueba con el script `scripts/test_chroma_super_minimal.py`.