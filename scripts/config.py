# scripts/config.py
import os
import shutil # Aunque no se use directamente aquí, puede ser útil mantenerlo por si se añade lógica futura.
from datetime import datetime # Aunque no se use directamente aquí.
import google.generativeai as genai
from dotenv import load_dotenv

# Cargar variables de entorno desde .env que debe estar en la raíz del proyecto
# Esto se ejecuta siempre que se importa el módulo config.
dotenv_path = os.path.join(os.path.dirname(__file__), os.pardir, '.env')
load_dotenv(dotenv_path)

# --- API Key ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- Rutas Base ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA_DIR = os.path.join(PROJECT_ROOT, "datos")

# --- Rutas Específicas de Datos ---
DOCS_BASE_CONOCIMIENTO_PATH = os.path.join(DATA_DIR, "BaseConocimiento")
PROYECTO_A_ANALIZAR_PATH = os.path.join(DATA_DIR, "ProyectoAnalizar")
CHROMA_DB_PATH = os.path.join(DATA_DIR, "ChromaDB_V1")
OUTPUT_PATH = os.path.join(DATA_DIR, "Resultados")
MODELOS_LOCALES_PATH = os.path.join(PROJECT_ROOT, "modelos_locales") # Ruta base para modelos locales

# --- Modelo de Embeddings ---
DEFAULT_EMBEDDING_MODEL_HF_REPO_ID = 'sentence-transformers/all-MiniLM-L6-v2'
# Inicializar con el valor por defecto. Se intentará sobrescribir con la variable de entorno.
EMBEDDING_MODEL_NAME_OR_PATH = DEFAULT_EMBEDDING_MODEL_HF_REPO_ID

env_model_path_str = os.environ.get('EMBEDDING_MODEL_PATH', '').strip()

if env_model_path_str:
    # Si se proporciona una ruta en .env, se intenta usarla.
    # Normalizar la ruta (ej. D:/folder//file -> D:/folder/file)
    # y reemplazar barras invertidas ("\") con barras inclinadas ("/") para mayor compatibilidad.
    candidate_path = os.path.normpath(env_model_path_str).replace("\\", "/")
    
    if os.path.isdir(candidate_path):
        EMBEDDING_MODEL_NAME_OR_PATH = candidate_path
        # Este print se ejecutará cuando se importe config.py y se defina la variable
        print(f"INFO (config.py): Usando modelo de embeddings local especificado en .env: {EMBEDDING_MODEL_NAME_OR_PATH}")
    else:
        print(f"ADVERTENCIA (config.py): La ruta local para el modelo de embeddings especificada en .env ('{env_model_path_str}') NO es un directorio válido o no existe.")
        print(f"Revirtiendo al modelo por defecto de Hugging Face: '{DEFAULT_EMBEDDING_MODEL_HF_REPO_ID}'")
        EMBEDDING_MODEL_NAME_OR_PATH = DEFAULT_EMBEDDING_MODEL_HF_REPO_ID # Asegurar que revierte
else:
    # Este print se ejecutará si EMBEDDING_MODEL_PATH no está en .env o está vacío
    print(f"INFO (config.py): No se especificó EMBEDDING_MODEL_PATH en .env o está vacío. Usando por defecto: {EMBEDDING_MODEL_NAME_OR_PATH}")

# --- Parámetros de Procesamiento ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
LLM_MODEL_NAME = 'gemini-1.5-flash-latest'
K_RETRIEVED_DOCS = 3
MAX_CHARS_PROYECTO = 32000

# --- Nombres de Archivos de Salida ---
DASHBOARD_HTML_SUFFIX = "_dashboard.html"

# --- Control de Base de Datos ---
# Si RECREAR_DB = False No recrea la base de datos
# Si RECREAR_DB = True Borra la base de datos y la vuelve a crear
RECREAR_DB = True # Mantener en True para esta prueba para asegurar que usa el modelo correcto

# --- Flags para evitar re-ejecución de inicializaciones ---
_api_configured_flag = False
_dirs_initialized_flag = False

def configure_google_api():
    """Configura la API de Google Generative AI. Se ejecuta solo una vez."""
    global _api_configured_flag
    if _api_configured_flag:
        return True # Ya configurada

    if not GEMINI_API_KEY:
        print("ADVERTENCIA (config.py): GEMINI_API_KEY no encontrada en .env. El LLM no funcionará.")
        return False
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("--- API Key de Gemini configurada exitosamente (desde config.py) ---")
        _api_configured_flag = True
        return True
    except Exception as e:
        print(f"Error al configurar la API Key de Gemini (desde config.py): {e}")
        return False

def inicializar_directorios_datos():
    """Crea los directorios de datos necesarios si no existen. Se ejecuta solo una vez."""
    global _dirs_initialized_flag
    if _dirs_initialized_flag:
        return True # Ya inicializados

    try:
        os.makedirs(DOCS_BASE_CONOCIMIENTO_PATH, exist_ok=True)
        os.makedirs(PROYECTO_A_ANALIZAR_PATH, exist_ok=True)
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        os.makedirs(OUTPUT_PATH, exist_ok=True)
        # Asegurar que la carpeta base para modelos locales exista (útil para la guía del usuario)
        os.makedirs(MODELOS_LOCALES_PATH, exist_ok=True) 
        
        print("--- Directorios de datos inicializados/verificados (desde config.py) ---")
        print(f"Directorio Raíz del Proyecto: {PROJECT_ROOT}")
        # Puedes añadir más prints de las rutas si lo deseas para depuración, pero main.py ya lo hace.
        _dirs_initialized_flag = True
        return True
    except OSError as e:
        print(f"Error al crear directorios (desde config.py): {e}")
        return False

# Este bloque solo se ejecuta si corres 'python config.py' directamente.
# No se ejecutará cuando config.py sea importado por main.py.
if __name__ == '__main__':
    print("--- [INICIO] Ejecutando config.py directamente para verificación ---")
    
    # Llamar a las funciones aquí para probar su lógica de ejecución única
    print("\nLlamando a configure_google_api():")
    configure_google_api()
    print("Segunda llamada a configure_google_api() (no debería reimprimir 'exitosa'):")
    configure_google_api() # Para probar el flag

    print("\nLlamando a inicializar_directorios_datos():")
    inicializar_directorios_datos()
    print("Segunda llamada a inicializar_directorios_datos() (no debería reimprimir todo):")
    inicializar_directorios_datos() # Para probar el flag
    
    print(f"\nValor final de EMBEDDING_MODEL_NAME_OR_PATH que se usará: '{EMBEDDING_MODEL_NAME_OR_PATH}'")
    if os.path.isdir(EMBEDDING_MODEL_NAME_OR_PATH):
         print(f"  -> La ruta del modelo local es un directorio válido.")
    elif EMBEDDING_MODEL_NAME_OR_PATH == DEFAULT_EMBEDDING_MODEL_HF_REPO_ID:
         print(f"  -> Se usará el modelo de Hugging Face Hub: '{EMBEDDING_MODEL_NAME_OR_PATH}'.")
    else:
         print(f"  -> ADVERTENCIA: La ruta/nombre del modelo '{EMBEDDING_MODEL_NAME_OR_PATH}' podría no ser válida o no existir.")
    print("--- [FIN] Verificación de config.py ---")

