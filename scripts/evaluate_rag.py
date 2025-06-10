# scripts/evaluate_rag.py
import os
import sys
import logging
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_recall, context_precision
import json
import shutil
import datetime
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from scripts.main import run_analysis
from scripts import config, vector_db_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - EVAL - %(message)s', datefmt='%H:%M:%S')
logging.getLogger("ragas").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

METRICS_TO_EVALUATE = [faithfulness, answer_relevancy, context_recall, context_precision]

def load_evaluation_dataset(path: str) -> Dataset:
    try:
        return Dataset.from_json(path)
    except Exception as e:
        logging.error(f"Error al cargar el dataset de evaluación desde '{path}': {e}")
        return None

def run_evaluation_for_model(model_id: str, eval_dataset: Dataset, db_connection: object):
    results = []
    logging.info(f"--- Iniciando evaluación para el modelo: {model_id} ({len(eval_dataset)} preguntas) ---")
    for i, row in enumerate(eval_dataset):
        logging.info(f"Procesando pregunta {i+1}/{len(eval_dataset)}: \"{row['question'][:50]}...\"")
        try:
            result = run_analysis(
                selected_llm_model_id=model_id, is_evaluation_mode=True,
                eval_question=row["question"], eval_ground_truth=row["ground_truth"],
                db_connection=db_connection
            )
            if result: results.append(result)
        except Exception as e:
            logging.error(f"Excepción inesperada al evaluar la pregunta {i+1}: {e}", exc_info=True)
        logging.info("Esperando 10 segundos...")
        time.sleep(10)
    return results

def main():
    logging.info("================ INICIO EVALUACIÓN PIPELINE RAG ================")
    eval_dataset_path = os.path.join(config.DATA_DIR, "eval_dataset.jsonl")
    eval_dataset = load_evaluation_dataset(eval_dataset_path)
    if not eval_dataset or len(eval_dataset) == 0:
        logging.error("El dataset de evaluación está vacío o no se pudo cargar."); return

    logging.info("Preparando la base de datos vectorial...")
    embedding_function = vector_db_manager.get_embedding_function(config.EMBEDDING_MODEL_NAME_OR_PATH)
    if not embedding_function: logging.error("No se pudo crear la función de embeddings."); return
    db_connection = vector_db_manager.crear_o_cargar_chroma_db(
        chroma_db_path=config.CHROMA_DB_PATH, docs_base_conocimiento_path=config.DIRECTORIO_BASE_CONOCIMIENTO,
        embedding_function=embedding_function, chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP, recrear_db_flag=True
    )
    if not db_connection: logging.error("No se pudo crear la base de datos vectorial."); return
    logging.info("✅ Base de datos lista para ser reutilizada.")

    if not os.getenv("OPENAI_API_KEY"):
        logging.error("No se encontró OPENAI_API_KEY. Ragas la necesita para funcionar. Abortando."); return
    logging.info("✅ Ragas utilizará OpenAI como modelo de evaluación (requiere OPENAI_API_KEY).")

    all_results = []
    models_to_evaluate = list(config.LLM_MODELS.keys())
    
    for model_id in models_to_evaluate:
        if not os.getenv(config.LLM_MODELS[model_id].get("api_key_env")):
            logging.warning(f"No se encontró API Key para '{model_id}'. Saltando su evaluación."); continue
        
        model_results_list = run_evaluation_for_model(model_id, eval_dataset, db_connection)
        if not model_results_list:
            logging.warning(f"No se obtuvieron resultados para {model_id}. Saltando Ragas."); continue

        ragas_dataset = Dataset.from_list(model_results_list)
        logging.info(f"Calculando métricas con Ragas para el modelo: {model_id}...")
        try:
            score = evaluate(ragas_dataset, metrics=METRICS_TO_EVALUATE)
            score_df = score.to_pandas()
            score_df["model_id"] = model_id
            all_results.append(score_df)
            logging.info(f"Evaluación para {model_id} completada.")
        except Exception as e:
            logging.error(f"Error durante la evaluación de Ragas para {model_id}: {e}", exc_info=True)

    if not all_results: logging.error("No se pudieron completar las evaluaciones."); return

    final_df = pd.concat(all_results, ignore_index=True)
    cols = ['model_id', 'question', 'answer', 'contexts', 'ground_truth', 'faithfulness', 'answer_relevancy', 'context_recall', 'context_precision']
    final_df = final_df[[c for c in cols if c in final_df.columns]]
    results_dir = os.path.join(config.DIRECTORIO_RESULTADOS, "evaluaciones_rag")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(results_dir, f"ragas_eval_TODOS_{timestamp}.csv")
    final_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    logging.info(f"Resultados de evaluación guardados en: {csv_path}")
    
    summary_df = final_df.groupby('model_id')[['faithfulness', 'answer_relevancy', 'context_recall', 'context_precision']].mean(numeric_only=True).reset_index()
    print("\n\n--- RESUMEN DE MÉTRICAS PROMEDIO POR MODELO ---")
    print(summary_df.to_string(index=False))
    print("-------------------------------------------------")
    logging.info("================ FIN EVALUACIÓN PIPELINE RAG ================")

if __name__ == "__main__":
    main()