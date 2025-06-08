# scripts/main.py
import os
import sys
import logging
from pydantic import ValidationError
from typing import Optional

# Importaciones locales
from . import config, document_utils, vector_db_manager, rag_components, report_utils, dashboard_generator
from .schemas import RiskReport, SourceChunk, LLMResponse, RiskItem
from .report_utils import get_risk_severity_score

logger = logging.getLogger(__name__)
if not logger.handlers:
    # Configuración del logger si no está configurado
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
    eval_ground_truth: Optional[str] = None
):
    if not is_evaluation_mode:
        logger.info(f"--- INICIANDO ANÁLISIS (Modelo: {selected_llm_model_id}) ---")

    try:
        config.inicializar_directorios_datos()
        
        # 1. Cargar embeddings y base de datos vectorial
        embedding_function = vector_db_manager.get_embedding_function(config.EMBEDDING_MODEL_NAME_OR_PATH)
        if not embedding_function: return None
        
        vector_db = vector_db_manager.crear_o_cargar_chroma_db(
            chroma_db_path=config.CHROMA_DB_PATH,
            docs_base_conocimiento_path=config.DIRECTORIO_BASE_CONOCIMIENTO,
            embedding_function=embedding_function,
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            recrear_db_flag=force_recreate_db or config.RECREAR_DB # Usar flag de la UI o de config
        )
        if not vector_db: return None

        # 2. Cargar LLM y descripción del proyecto
        llm = rag_components.get_llm_instance(selected_llm_model_id)
        if not llm: return None

        if not is_evaluation_mode:
            pdf_path_analizar_abs = document_utils.obtener_ruta_pdf_proyecto(config.DIRECTORIO_PROYECTO_ANALIZAR)
            if not pdf_path_analizar_abs:
                logger.error("No se encontró ningún PDF en la carpeta del proyecto a analizar.")
                return None
            nombre_pdf_proyecto_detectado = os.path.basename(pdf_path_analizar_abs)
            
            descripcion_nuevo_proyecto = document_utils.procesar_pdf_proyecto_para_analisis(
                pdf_path_analizar_abs, config.MAX_CHARS_PROYECTO
            )
        else: # Modo evaluación
            nombre_pdf_proyecto_detectado = "Modo de Evaluación"
            descripcion_nuevo_proyecto = eval_question

        if not descripcion_nuevo_proyecto:
            logger.error("La descripción del proyecto está vacía. No se puede continuar.")
            return None

        # 3. Crear y ejecutar la cadena RAG
        qa_chain = rag_components.crear_cadena_rag(llm, vector_db)
        if not qa_chain: return None

        logger.info("Invocando la cadena RAG principal...")
        respuesta_rag_dict = qa_chain.invoke({"query": descripcion_nuevo_proyecto})
        
        llm_response_obj = respuesta_rag_dict.get("result")
        if not isinstance(llm_response_obj, LLMResponse):
             raise TypeError("La cadena RAG no devolvió el objeto LLMResponse Pydantic esperado.")

        fuentes_docs = respuesta_rag_dict.get("source_documents", [])
        
        # --- INICIO: Lógica de Cálculo de Score de Confianza Compuesto ---
        logger.info("Calculando score de confianza compuesto para cada riesgo...")
        
        # Obtenemos el mejor score de la evidencia recuperada
        scores = [doc.metadata.get('relevance_score', 0.0) for doc in fuentes_docs if doc.metadata.get('relevance_score') is not None]
        # Si el re-ranker está desactivado, no habrá scores. Usamos un valor neutral.
        max_relevance_score = max(scores) if scores else 0.5 
        
        # Iteramos sobre cada riesgo para asignarle su score compuesto
        for riesgo in llm_response_obj.riesgos_identificados:
            severity_score = get_risk_severity_score(riesgo.impacto_estimado, riesgo.probabilidad_estimada)
            
            # Promedio ponderado: 60% relevancia de evidencia, 40% severidad del riesgo
            composite_score = (max_relevance_score * 0.6) + (severity_score * 0.4)
            riesgo.score_confianza_compuesto = min(composite_score, 1.0) # Aseguramos que no pase de 1.0

        # --- FIN: Lógica de Cálculo de Score ---

        # 4. Procesar para evaluación o para reporte final
        if is_evaluation_mode:
            # Para Ragas, la "respuesta" es el JSON de la lista de riesgos
            answer_for_eval = llm_response_obj.model_dump_json()
            return {
                "question": eval_question,
                "answer": answer_for_eval,
                "contexts": [doc.page_content for doc in fuentes_docs],
                "ground_truth": eval_ground_truth
            }

        # 5. Ensamblar y guardar reportes
        logger.info("Ensamblando el reporte final...")
        
        # Crear los objetos SourceChunk para el reporte
        fuentes_serializables = [
            SourceChunk(
                contenido=doc.page_content,
                nombre_documento_fuente=doc.metadata.get('source_document', 'Desconocida'),
                numero_pagina=doc.metadata.get('page_number', -1),
                score_relevancia=doc.metadata.get('relevance_score')
            ) for doc in fuentes_docs
        ]
        
        # Crear el objeto RiskReport completo
        reporte_final = RiskReport(
            riesgos_identificados=llm_response_obj.riesgos_identificados,
            fragmentos_fuente=fuentes_serializables,
            respuesta_cruda_llm=llm_response_obj.model_dump_json(indent=2),
            configuracion_analisis={
                "modelo_llm_usado": selected_llm_model_id,
                "display_name_modelo": config.LLM_MODELS.get(selected_llm_model_id, {}).get("display_name", "N/A"),
                "k_docs_antes_rerank": config.K_RETRIEVED_DOCS_BEFORE_RERANK,
                "reranker_top_n": config.RERANKER_TOP_N if config.USE_RERANKER else "N/A"
            }
        )

        nombre_base_proyecto = "".join(c if c.isalnum() else "_" for c in os.path.splitext(nombre_pdf_proyecto_detectado)[0])
        output_dir_especifico = os.path.join(config.DIRECTORIO_RESULTADOS, nombre_base_proyecto)
        os.makedirs(output_dir_especifico, exist_ok=True)

        ruta_json_guardado = report_utils.formatear_y_guardar_reporte(
            risk_report_obj=reporte_final, 
            nombre_original_pdf=nombre_pdf_proyecto_detectado, 
            output_path_dir=output_dir_especifico
        )
        if not ruta_json_guardado: return None

        dashboard_html_filename = f"dashboard_{nombre_base_proyecto}.html"
        ruta_output_dashboard_html = os.path.join(output_dir_especifico, dashboard_html_filename)

        dashboard_generator.generar_dashboard_html(
            ruta_json_resultados=ruta_json_guardado,
            ruta_output_dashboard_html=ruta_output_dashboard_html,
            lista_pdfs_base_conocimiento=document_utils.listar_documentos_kb(config.DIRECTORIO_BASE_CONOCIMIENTO),
            info_tesis_config=config.INFO_TESIS
        )

        if os.path.exists(ruta_output_dashboard_html):
            return os.path.normpath(os.path.relpath(ruta_output_dashboard_html, config.PROJECT_ROOT)).replace("\\", "/")
        
        logger.error("El dashboard HTML no fue generado.")
        return None

    except (ValidationError, TypeError) as e:
        logger.error(f"Error de validación o tipo en la respuesta del LLM: {e}", exc_info=True)
        raise
    except Exception as e_main_flow:
        logger.error(f"Error catastrófico en el flujo principal: {e_main_flow}", exc_info=True)
        return None