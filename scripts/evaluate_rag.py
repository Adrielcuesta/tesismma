# scripts/evaluate_rag.py
import os
import sys
import logging
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)
import json
import shutil
import datetime
import time

# --- Configuración de Rutas y Módulos ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from scripts.main import run_analysis
    from scripts import config
    from scripts import vector_db_manager
except ImportError as e:
    logging.basicConfig(level=logging.CRITICAL)
    logging.critical(f"Error de importación crítico. Asegúrate de ejecutar desde la raíz del proyecto. Error: {e}")
    sys.exit(1)

# --- Configuración del Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - EVAL - %(message)s',
    datefmt='%H:%M:%S'
)
# Silenciar logs muy verbosos de otras librerías
logging.getLogger("ragas").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)

# --- Métricas a Evaluar ---
METRICS_TO_EVALUATE = [
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
]

def load_evaluation_dataset(path: str) -> Dataset:
    """Carga el dataset de evaluación desde un archivo .jsonl."""
    try:
        return Dataset.from_json(path)
    except Exception as e:
        logging.error(f"Error al cargar el dataset de evaluación desde '{path}': {e}")
        return None

def run_evaluation_for_model(model_id: str, eval_dataset: Dataset, db_connection: object):
    """Ejecuta el pipeline de análisis para un modelo y un dataset dados."""
    results = []
    total_questions = len(eval_dataset)
    logging.info(f"--- Iniciando evaluación para el modelo: {model_id} ({total_questions} preguntas) ---")

    for i, row in enumerate(eval_dataset):
        logging.info(f"Procesando pregunta {i+1}/{total_questions}: \"{row['question'][:50]}...\"")
        try:
            # Reutilizamos la función 'run_analysis' del proyecto
            result = run_analysis(
                selected_llm_model_id=model_id,
                is_evaluation_mode=True,
                eval_question=row["question"],
                eval_ground_truth=row["ground_truth"],
                db_connection=db_connection 
            )
            if result:
                results.append(result)
        except Exception as e:
            logging.error(f"Excepción inesperada al evaluar la pregunta {i+1}: {e}", exc_info=True)
        
        # Pausa para no saturar las APIs
        logging.info("Esperando 10 segundos...")
        time.sleep(10)

    return results

def main():
    """Función principal que orquesta todo el proceso de evaluación."""
    logging.info("======================================================")
    logging.info("=            INICIO EVALUACIÓN PIPELINE RAG            =")
    logging.info("======================================================")

    # 1. Cargar el dataset de evaluación
    eval_dataset_path = os.path.join(config.DATA_DIR, "eval_dataset.jsonl")
    eval_dataset = load_evaluation_dataset(eval_dataset_path)
    if not eval_dataset or len(eval_dataset) == 0:
        logging.error("El dataset de evaluación está vacío o no se pudo cargar. Abortando.")
        return

    # 2. Crear la base de datos vectorial UNA SOLA VEZ
    logging.info("Preparando la base de datos vectorial...")
    embedding_function = vector_db_manager.get_embedding_function(config.EMBEDDING_MODEL_NAME_OR_PATH)
    if not embedding_function: logging.error("No se pudo crear la función de embeddings."); return
        
    db_connection = vector_db_manager.crear_o_cargar_chroma_db(
        chroma_db_path=config.CHROMA_DB_PATH, 
        docs_base_conocimiento_path=config.DIRECTORIO_BASE_CONOCIMIENTO,
        embedding_function=embedding_function, 
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP, 
        recrear_db_flag=True # Forzar recreación al inicio de la evaluación
    )
    if not db_connection: logging.error("No se pudo crear la base de datos vectorial."); return
    logging.info("✅ Base de datos lista para ser reutilizada en toda la evaluación.")
    
    # 3. Ejecutar la evaluación para el modelo deseado
    model_to_evaluate = "gemini-1.5-flash"
    
    # Verificar que el modelo a evaluar tiene su API key
    if not os.getenv(config.LLM_MODELS[model_to_evaluate].get("api_key_env")):
        logging.error(f"No se encontró la API Key para el modelo a evaluar '{model_to_evaluate}'. Revisa tu archivo .env. Abortando.")
        return
        
    model_results_list = run_evaluation_for_model(model_to_evaluate, eval_dataset, db_connection)
    
    if not model_results_list:
        logging.error(f"No se obtuvieron resultados para el modelo {model_to_evaluate}. No se puede continuar."); return

    # 4. Calcular métricas con Ragas
    ragas_dataset = Dataset.from_list(model_results_list)
    logging.info(f"Calculando métricas con Ragas para el modelo: {model_to_evaluate}...")
    try:
        # Ragas usará automáticamente la variable de entorno OPENAI_API_KEY para calificar
        score = evaluate(ragas_dataset, metrics=METRICS_TO_EVALUATE)
        score_df = score.to_pandas()
        score_df["model_id"] = model_to_evaluate
        logging.info("✅ Evaluación con Ragas completada.")
    except Exception as e:
        logging.error(f"Error crítico durante la evaluación de Ragas: {e}", exc_info=True)
        logging.error("Asegúrate de tener una OPENAI_API_KEY válida en tu archivo .env para que Ragas pueda funcionar.")
        return

    # 5. Guardar y mostrar los resultados
    results_dir = os.path.join(config.DIRECTORIO_RESULTADOS, "evaluaciones_rag")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(results_dir, f"ragas_eval_{model_to_evaluate}_{timestamp}.csv")
    score_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    logging.info(f"Resultados de evaluación guardados en: {csv_path}")
    
    summary_df = score_df[['faithfulness', 'answer_relevancy', 'context_recall', 'context_precision']].mean().to_frame().T
    summary_df.insert(0, "model_id", model_to_evaluate)
    
    print("\n\n--- RESUMEN DE MÉTRICAS PROMEDIO PARA EL MODELO ---")
    print(summary_df.to_string(index=False))
    print("---------------------------------------------------")
    logging.info("======================================================")
    logging.info("=             FIN EVALUACIÓN PIPELINE RAG              =")
    logging.info("======================================================")

if __name__ == "__main__":
    main()