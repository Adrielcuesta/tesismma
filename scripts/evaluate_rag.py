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
    context_precision,
    context_recall,
)
import json

# Añadir el directorio raíz del proyecto al sys.path para poder importar los módulos
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from scripts.main import run_analysis
from scripts import config

# --- Configuración del Logging para este script ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - EVAL - %(message)s',
    datefmt='%H:%M:%S'
)
# Silenciar logs muy verbosos de otras librerías durante la evaluación
logging.getLogger("ragas").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# --- Métricas a evaluar ---
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

def run_evaluation_for_model(model_id: str, eval_dataset: Dataset):
    """Ejecuta el pipeline de análisis para un modelo y un dataset dados."""
    results = []
    total_questions = len(eval_dataset)
    logging.info(f"--- Iniciando evaluación para el modelo: {model_id} ({total_questions} preguntas) ---")

    for i, row in enumerate(eval_dataset):
        logging.info(f"Procesando pregunta {i+1}/{total_questions}: \"{row['question'][:50]}...\"")
        try:
            # Llamamos a nuestra función principal en modo evaluación
            result = run_analysis(
                selected_llm_model_id=model_id,
                force_recreate_db=False, # No recreamos la DB para cada pregunta
                is_evaluation_mode=True,
                eval_question=row["question"],
                eval_ground_truth=row["ground_truth"]
            )
            if result and "error" not in result:
                results.append(result)
            else:
                logging.error(f"El análisis para la pregunta {i+1} falló o devolvió un error: {result.get('error', 'Error desconocido')}")

        except Exception as e:
            logging.error(f"Excepción inesperada al evaluar la pregunta {i+1}: {e}", exc_info=True)

    return results

def main():
    """Función principal para orquestar la evaluación."""
    logging.info("======================================================")
    logging.info("=            INICIO EVALUACIÓN PIPELINE RAG            =")
    logging.info("======================================================")

    # 1. Cargar el dataset de evaluación
    eval_dataset_path = os.path.join(config.DATA_DIR, "eval_dataset.jsonl")
    eval_dataset = load_evaluation_dataset(eval_dataset_path)
    if not eval_dataset:
        return

    # 2. Iterar sobre todos los modelos configurados y evaluarlos
    all_results = []
    models_to_evaluate = list(config.LLM_MODELS.keys())

    for model_id in models_to_evaluate:
        # Primero, reconstruimos la base de datos una vez antes de evaluar el modelo
        # para asegurar que está limpia y actualizada.
        logging.info(f"Preparando la base de datos para la evaluación del modelo {model_id}...")
        run_analysis(
            selected_llm_model_id=model_id,
            force_recreate_db=True,
            is_evaluation_mode=True,
            eval_question="preparacion", # Pregunta dummy para forzar la recreación de la DB
            eval_ground_truth="preparacion"
        )

        # Ahora, ejecutamos la evaluación real
        model_results_list = run_evaluation_for_model(model_id, eval_dataset)
        
        if not model_results_list:
            logging.warning(f"No se obtuvieron resultados para el modelo {model_id}. Saltando evaluación de Ragas.")
            continue

        # Convertimos la lista de resultados a un Dataset de Hugging Face
        ragas_dataset = Dataset.from_list(model_results_list)

        # 3. Ejecutar Ragas para calcular métricas
        logging.info(f"Calculando métricas con Ragas para el modelo: {model_id}...")
        try:
            score = evaluate(ragas_dataset, metrics=METRICS_TO_EVALUATE)
            score_df = score.to_pandas()
            score_df["model_id"] = model_id # Añadimos el nombre del modelo a los resultados
            all_results.append(score_df)
            logging.info(f"Evaluación para {model_id} completada.")
            print(f"\nResultados para {model_id}:\n", score_df.head())
        except Exception as e:
            logging.error(f"Error durante la evaluación de Ragas para el modelo {model_id}: {e}", exc_info=True)


    if not all_results:
        logging.error("No se pudieron completar las evaluaciones para ningún modelo.")
        return

    # 4. Consolidar y guardar resultados
    final_df = pd.concat(all_results, ignore_index=True)
    
    # Organizar columnas para mayor claridad
    cols = ['model_id', 'question', 'faithfulness', 'answer_relevancy', 'context_recall', 'context_precision', 'ground_truth', 'answer', 'contexts']
    final_df = final_df[[c for c in cols if c in final_df.columns]]

    # Guardar en JSON y CSV
    results_dir = os.path.join(config.DIRECTORIO_RESULTADOS, "evaluaciones_rag")
    os.makedirs(results_dir, exist_ok=True)
    
    json_path = os.path.join(results_dir, "ragas_evaluation_results.json")
    csv_path = os.path.join(results_dir, "ragas_evaluation_results.csv")

    final_df.to_json(json_path, orient='records', indent=4)
    final_df.to_csv(csv_path, index=False)
    
    logging.info(f"Resultados de evaluación guardados en: {results_dir}")
    logging.info(f"Resultados finales (promedio por modelo):\n{final_df.groupby('model_id').mean(numeric_only=True)}")
    logging.info("======================================================")
    logging.info("=            FIN EVALUACIÓN PIPELINE RAG             =")
    logging.info("======================================================")


if __name__ == "__main__":
    main()
