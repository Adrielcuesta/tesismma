# scripts/main.py
import os
import sys
import time
import traceback
import logging
from pydantic import ValidationError
from typing import Optional

from . import config, document_utils, vector_db_manager, rag_components, report_utils, dashboard_generator
from .schemas import RiskReport, SourceChunk
from .pdf_utils import generate_pdf_from_html_file

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(module)s.%(funcName)s - %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.propagate = False

def run_analysis(
    selected_llm_model_id: str,
    force_recreate_db: bool = False,
    is_evaluation_mode: bool = False,
    eval_question: Optional[str] = None,
    eval_ground_truth: Optional[str] = None,
    generate_pdf_flag: bool = False # Nuevo parámetro
):
    start_time_total = time.time()
    if not is_evaluation_mode:
        logger.info(f"--- INICIANDO ANÁLISIS (Modelo: {selected_llm_model_id}, PDF: {generate_pdf_flag}) ---")

    try:
        # --- ETAPAS ANTERIORES (sin cambios) ---
        config.inicializar_directorios_datos()
        if not is_evaluation_mode:
            pdf_path_analizar_abs = document_utils.obtener_ruta_pdf_proyecto(config.DIRECTORIO_PROYECTO_ANALIZAR)
            if not pdf_path_analizar_abs: return None
            nombre_pdf_proyecto_detectado = os.path.basename(pdf_path_analizar_abs)
        else:
            nombre_pdf_proyecto_detectado = "Modo de Evaluación"
        embedding_function = vector_db_manager.get_embedding_function(config.EMBEDDING_MODEL_NAME_OR_PATH)
        if not embedding_function: return None
        vector_db = vector_db_manager.crear_o_cargar_chroma_db(recrear_db_flag=force_recreate_db, embedding_function=embedding_function)
        if not vector_db: return None
        llm = rag_components.get_llm_instance(selected_llm_model_id)
        if not llm: return None
        qa_chain = rag_components.crear_cadena_rag(llm, vector_db)
        if not qa_chain: return None
        if is_evaluation_mode:
            descripcion_nuevo_proyecto = eval_question
        else:
            descripcion_nuevo_proyecto = document_utils.procesar_pdf_proyecto_para_analisis(pdf_path_analizar_abs)
        if not descripcion_nuevo_proyecto: return None

        # --- Ejecución del Análisis RAG ---
        respuesta_rag_dict = qa_chain.invoke({"query": descripcion_nuevo_proyecto})
        risk_report_from_llm = respuesta_rag_dict.get("result")
        if not isinstance(risk_report_from_llm, RiskReport):
             raise TypeError("La cadena RAG no devolvió el objeto Pydantic esperado.")
        
        if is_evaluation_mode:
             # Devolvemos los datos para Ragas
             return {"question": eval_question, "answer": risk_report_from_llm.model_dump_json(), "contexts": [doc.page_content for doc in respuesta_rag_dict.get("source_documents", [])], "ground_truth": eval_ground_truth}

        # --- Generación de Reportes en modo normal ---
        # ... (código para llenar el risk_report_from_llm se mantiene igual y se omite por brevedad) ...
        fuentes_docs = respuesta_rag_dict.get("source_documents", [])
        fuentes_serializables = [SourceChunk(contenido=doc.page_content, nombre_documento_fuente=doc.metadata.get('source_document', 'N/A'), numero_pagina=doc.metadata.get('page_number', -1), score_relevancia=doc.metadata.get('relevance_score')).model_dump() for doc in fuentes_docs]
        risk_report_from_llm.fragmentos_fuente = [SourceChunk(**f) for f in fuentes_serializables]

        nombre_base_proyecto_analizado = "".join(c if c.isalnum() else "_" for c in os.path.splitext(nombre_pdf_proyecto_detectado)[0])
        output_dir_especifico_proyecto = os.path.join(config.DIRECTORIO_RESULTADOS, nombre_base_proyecto_analizado)
        os.makedirs(output_dir_especifico_proyecto, exist_ok=True)
        
        ruta_json_guardado = report_utils.formatear_y_guardar_reporte(risk_report_obj=risk_report_from_llm, fuentes_recuperadas_serializables=fuentes_serializables, nombre_original_pdf=nombre_pdf_proyecto_detectado, output_path_dir=output_dir_especifico_proyecto)
        if not ruta_json_guardado: return None

        # Generar Dashboard HTML
        dashboard_html_filename = f"dashboard_{nombre_base_proyecto_analizado}.html"
        ruta_output_dashboard_html_absoluta = os.path.join(output_dir_especifico_proyecto, dashboard_html_filename)
        dashboard_generator.generar_dashboard_html(
            ruta_json_resultados=ruta_json_guardado,
            ruta_output_dashboard_html=ruta_output_dashboard_html_absoluta,
            lista_pdfs_base_conocimiento=document_utils.listar_documentos_kb(config.DIRECTORIO_BASE_CONOCIMIENTO),
            info_tesis_config=config.INFO_TESIS,
            generate_pdf_flag=generate_pdf_flag # Pasamos el flag
        )

        # Generar PDF si fue solicitado
        if generate_pdf_flag and os.path.exists(ruta_output_dashboard_html_absoluta):
            pdf_path = ruta_output_dashboard_html_absoluta.replace('.html', '.pdf')
            logger.info(f"Generando reporte PDF en: {pdf_path}")
            generate_pdf_from_html_file(ruta_output_dashboard_html_absoluta, pdf_path)
        
        if os.path.exists(ruta_output_dashboard_html_absoluta):
            ruta_relativa = os.path.normpath(os.path.relpath(ruta_output_dashboard_html_absoluta, config.PROJECT_ROOT)).replace("\\", "/")
            return ruta_relativa
        else:
            return None

    except (ValidationError, TypeError) as e:
        logger.error(f"Error de validación/tipo: {e}", exc_info=True)
        if is_evaluation_mode: return {"error": str(e)}
        raise
    except Exception as e_main_flow:
        logger.error(f"Error catastrófico en el flujo principal: {e_main_flow}", exc_info=True)
        return None

if __name__ == '__main__':
    pass

