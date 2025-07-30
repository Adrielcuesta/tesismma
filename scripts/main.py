# scripts/main.py
import os
import sys
import logging
import json # <--- AÑADIDO
from pydantic import ValidationError
from typing import Optional

from . import config, document_utils, vector_db_manager, rag_components, report_utils, dashboard_generator
from .schemas import RiskReport, SourceChunk, LLMResponse, RiskItem
from .report_utils import get_risk_severity_score

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
    db_connection: Optional[object] = None
):
    if not is_evaluation_mode: logger.info(f"--- INICIANDO ANÁLISIS (Modelo: {selected_llm_model_id}) ---")
    try:
        config.inicializar_directorios_datos()
        
        if db_connection:
            vector_db = db_connection
        else:
            embedding_function = vector_db_manager.get_embedding_function(config.EMBEDDING_MODEL_NAME_OR_PATH)
            if not embedding_function: return None
            vector_db = vector_db_manager.crear_o_cargar_chroma_db(
                chroma_db_path=config.CHROMA_DB_PATH, docs_base_conocimiento_path=config.DIRECTORIO_BASE_CONOCIMIENTO,
                embedding_function=embedding_function, chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP,
                recrear_db_flag=force_recreate_db or config.RECREAR_DB
            )
        if not vector_db: return None

        llm = rag_components.get_llm_instance(selected_llm_model_id)
        if not llm: return None

        if not is_evaluation_mode:
            pdf_path_analizar_abs = document_utils.obtener_ruta_pdf_proyecto(config.DIRECTORIO_PROYECTO_ANALIZAR)
            if not pdf_path_analizar_abs: logger.error("No se encontró PDF en la carpeta a analizar."); return None
            nombre_pdf_proyecto_detectado = os.path.basename(pdf_path_analizar_abs)
            descripcion_nuevo_proyecto = document_utils.procesar_pdf_proyecto_para_analisis(pdf_path_analizar_abs, config.MAX_CHARS_PROYECTO)
        else:
            nombre_pdf_proyecto_detectado, descripcion_nuevo_proyecto = "Modo de Evaluación", eval_question
        
        if not descripcion_nuevo_proyecto: logger.error("La descripción del proyecto está vacía."); return None
        
        qa_chain = rag_components.crear_cadena_rag(llm, vector_db)
        if not qa_chain: return None
        
        logger.info("Invocando la cadena RAG principal...")
        respuesta_rag_dict = qa_chain.invoke({"query": descripcion_nuevo_proyecto})
        
        # --- INICIO DE LA CORRECCIÓN: Parseo manual de la respuesta del LLM ---
        raw_json_string = respuesta_rag_dict.get("result", "{}")
        
        # Limpiar el string en caso de que el LLM devuelva markdown
        if "```json" in raw_json_string:
            clean_json_string = raw_json_string.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_json_string:
            clean_json_string = raw_json_string.split("```")[1].split("```")[0].strip()
        else:
            clean_json_string = raw_json_string

        try:
            # Parsear el string a un diccionario y luego validar con Pydantic
            llm_response_data = json.loads(clean_json_string)
            llm_response_obj = LLMResponse.model_validate(llm_response_data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Error CRÍTICO al parsear o validar la respuesta JSON del LLM: {e}")
            logger.error(f"Respuesta recibida del LLM (string crudo):\n---INICIO---\n{raw_json_string}\n---FIN---")
            raise  # Re-lanzamos la excepción para que el error sea visible en la app
        # --- FIN DE LA CORRECCIÓN ---
            
        fuentes_docs = respuesta_rag_dict.get("source_documents", [])
        logger.info(f"Metadatos de la evidencia recuperada: {[doc.metadata for doc in fuentes_docs]}")
        
        logger.info("Calculando score de confianza compuesto...")
        scores = [doc.metadata.get('relevance_score', 0.0) for doc in fuentes_docs if doc.metadata.get('relevance_score') is not None]
        max_relevance_score = max(scores) if scores else 0.5
        for riesgo in llm_response_obj.riesgos_identificados:
            severity_score = get_risk_severity_score(riesgo.impacto_estimado, riesgo.probabilidad_estimada)
            riesgo.score_confianza_compuesto = min((max_relevance_score * 0.6) + (severity_score * 0.4), 1.0)
            
        if is_evaluation_mode:
            return {"question": eval_question, "answer": llm_response_obj.model_dump_json(), "contexts": [doc.page_content for doc in fuentes_docs], "ground_truth": eval_ground_truth}
        
        logger.info("Ensamblando el reporte final...")
        
        fragmentos_fuente_mapeados = [
            SourceChunk(
                contenido=doc.page_content,
                nombre_documento_fuente=doc.metadata.get('source_document', 'Desconocido'),
                numero_pagina=doc.metadata.get('page_number', -1),
                score_relevancia=doc.metadata.get('relevance_score')
            ) for doc in fuentes_docs
        ]

        reporte_final = RiskReport(
            riesgos_identificados=llm_response_obj.riesgos_identificados,
            fragmentos_fuente=fragmentos_fuente_mapeados,
            respuesta_cruda_llm=llm_response_obj.model_dump_json(indent=2),
            configuracion_analisis={
                "modelo_llm_usado": selected_llm_model_id, "display_name_modelo": config.LLM_MODELS.get(selected_llm_model_id, {}).get("display_name", "N/A"),
                "reranker_top_n": config.RERANKER_TOP_N if config.USE_RERANKER else "N/A"
            }
        )
        
        nombre_base_proyecto = "".join(c for c in os.path.splitext(nombre_pdf_proyecto_detectado)[0] if c.isalnum() or c in (' ', '_')).rstrip()
        output_dir_especifico = os.path.join(config.DIRECTORIO_RESULTADOS_BASE, nombre_base_proyecto)
        os.makedirs(output_dir_especifico, exist_ok=True)
        ruta_json_guardado = report_utils.formatear_y_guardar_reporte(reporte_final, nombre_pdf_proyecto_detectado, output_dir_especifico)
        if not ruta_json_guardado: return None
        
        dashboard_html_filename = f"dashboard_{nombre_base_proyecto}.html"
        ruta_output_dashboard_html = os.path.join(output_dir_especifico, dashboard_html_filename)
        dashboard_generator.generar_dashboard_html(
            ruta_json_resultados=ruta_json_guardado, ruta_output_dashboard_html=ruta_output_dashboard_html,
            info_tesis_config=config.INFO_TESIS
        )
        if os.path.exists(ruta_output_dashboard_html):
            return os.path.normpath(os.path.relpath(ruta_output_dashboard_html, config.PROJECT_ROOT)).replace("\\", "/")
        logger.error("El dashboard HTML no fue generado."); return None
    except (ValidationError, TypeError) as e:
        logger.error(f"Error de validación o tipo: {e}", exc_info=True); raise
    except Exception as e_main_flow:
        logger.error(f"Error catastrófico en el flujo principal: {e_main_flow}", exc_info=True); return None