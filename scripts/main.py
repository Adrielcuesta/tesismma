# scripts/main.py
import os
import sys
import time 
import traceback
import logging

# --- Importación de Módulos del Paquete 'scripts' usando Imports Relativos ---
from . import config
from . import document_utils
from . import vector_db_manager
from . import rag_components
from . import report_utils
from . import dashboard_generator

# --- Configuración del Logging ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) 
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.propagate = False

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - ROOT - %(module)s.%(funcName)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
# --- Fin Configuración del Logging ---

def run_analysis():
    start_time_total = time.time()
    ruta_output_dashboard_html_relativa = None
    CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(CURRENT_SCRIPT_DIR)

    logger.info("######################################################################")
    logger.info("# INICIANDO PROCESO DE ANÁLISIS DE RIESGOS RAG (desde run_analysis)  #")
    logger.info("######################################################################")

    try:
        logger.info("--- ETAPA 0: Cargando Configuración e Inicializando Directorios ---")
        if not config.inicializar_directorios_datos():
            logger.error("Error fatal: No se pudieron inicializar los directorios de datos.")
            return None
        if not config.configure_google_api():
            logger.warning("Advertencia: API de Google no configurada. El LLM podría no funcionar.")

        logger.info("--- ETAPA 1: Detectando PDF del Proyecto a Analizar ---")
        pdf_path_analizar_abs = document_utils.obtener_ruta_pdf_proyecto(config.DIRECTORIO_PROYECTO_ANALIZAR)
        if not pdf_path_analizar_abs:
            return None 
        
        nombre_pdf_proyecto_detectado = os.path.basename(pdf_path_analizar_abs)
        nombre_base_proyecto_analizado = os.path.splitext(nombre_pdf_proyecto_detectado)[0]
        logger.info(f"PDF detectado para análisis: {nombre_pdf_proyecto_detectado}")

        output_dir_especifico_proyecto = os.path.join(config.DIRECTORIO_RESULTADOS, nombre_base_proyecto_analizado)
        os.makedirs(output_dir_especifico_proyecto, exist_ok=True)
        logger.info(f"Directorio de resultados para este proyecto: {output_dir_especifico_proyecto}")

        lista_pdfs_base_conocimiento = document_utils.listar_documentos_kb(config.DIRECTORIO_BASE_CONOCIMIENTO)

        logger.info("--- ETAPA 2: Inicializando Modelo de Embeddings ---")
        start_time_embed = time.time()
        embedding_function = vector_db_manager.get_embedding_function(config.EMBEDDING_MODEL_NAME_OR_PATH)
        if not embedding_function:
            logger.error("Error fatal: No se pudo inicializar el modelo de embeddings (main.py).")
            return None
        logger.info(f"Tiempo para inicializar embeddings: {time.time() - start_time_embed:.2f} segundos.")

        logger.info("--- ETAPA 3: Gestionando Base de Datos Vectorial (ChromaDB) ---")
        start_time_db = time.time()
        vector_db = vector_db_manager.crear_o_cargar_chroma_db(
            chroma_db_path=config.CHROMA_DB_PATH,
            docs_base_conocimiento_path=config.DIRECTORIO_BASE_CONOCIMIENTO,
            embedding_function=embedding_function,
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            recrear_db_flag=config.RECREAR_DB
        )
        if not vector_db:
            logger.error("Error fatal: No se pudo crear o cargar la base de datos vectorial (main.py).")
            return None
        logger.info(f"Tiempo para gestión de DB: {time.time() - start_time_db:.2f} segundos.")

        logger.info("--- ETAPA 4: Configurando LLM y Cadena RAG ---")
        start_time_rag_setup = time.time()
        if not config.GEMINI_API_KEY: 
            logger.error("Error fatal: GEMINI_API_KEY no está disponible.")
            return None
        # Usar GEMINI_MODEL_NAME de config.py
        llm = rag_components.get_llm_instance(config.GEMINI_MODEL_NAME, config.GEMINI_API_KEY)
        if not llm:
            logger.error("Error fatal: No se pudo inicializar el LLM (main.py).")
            return None
            
        qa_chain = rag_components.crear_cadena_rag(llm, vector_db, config.K_RETRIEVED_DOCS)
        if not qa_chain:
            logger.error("Error fatal: No se pudo crear la cadena RAG (main.py).")
            return None
        logger.info(f"Tiempo para configurar LLM y cadena RAG: {time.time() - start_time_rag_setup:.2f} segundos.")

        logger.info("--- ETAPA 5: Procesando Documento del Proyecto a Analizar ---")
        start_time_proc_pdf = time.time()
        # Llamar a la función que tienes en tu document_utils.py
        descripcion_nuevo_proyecto = document_utils.procesar_pdf_proyecto_para_analisis(
            pdf_path_analizar_abs,
            config.CHUNK_SIZE,
            config.CHUNK_OVERLAP,
            config.MAX_CHARS_PROYECTO
        )
        if not descripcion_nuevo_proyecto: 
            logger.error("Error fatal: No se pudo procesar el PDF del proyecto a analizar (main.py).")
            return None
        logger.info(f"Texto extraído y preparado del proyecto '{nombre_base_proyecto_analizado}'.")
        logger.info(f"Tiempo para procesar PDF del proyecto: {time.time() - start_time_proc_pdf:.2f} segundos.")

        logger.info(f"--- ETAPA 6: Ejecutando Análisis de Riesgos para el proyecto: {nombre_base_proyecto_analizado} ---")
        start_time_query = time.time()
        resultado_analisis_llm_str = "Error: Análisis no ejecutado o LLM no devolvió respuesta."
        fuentes_recuperadas_serializables = []
        
        try:
            logger.info("Enviando consulta a la cadena RAG (esto puede tardar)...")
            respuesta_rag = qa_chain.invoke({"query": descripcion_nuevo_proyecto})
            
            if isinstance(respuesta_rag, dict):
                resultado_analisis_llm_str = respuesta_rag.get("result", "No se encontró 'result' en la respuesta del LLM.")
                fuentes_recuperadas_docs = respuesta_rag.get("source_documents", [])
            else:
                resultado_analisis_llm_str = str(respuesta_rag)
                fuentes_recuperadas_docs = []
                logger.warning("La respuesta de la cadena RAG no fue un diccionario como se esperaba.")

            if resultado_analisis_llm_str:
                logger.info("Respuesta del LLM recibida.")
            else:
                logger.warning("Advertencia: El LLM no devolvió un resultado ('result' es None o vacío).")
                resultado_analisis_llm_str = "El LLM no devolvió un resultado interpretable."

            if fuentes_recuperadas_docs:
                logger.info("--- FUENTES RECUPERADAS POR EL RETRIEVER ---")
                for i, doc_fuente in enumerate(fuentes_recuperadas_docs):
                    fuente_info = {
                        "documento_fuente": doc_fuente.metadata.get('source_document', 'N/A'),
                        "pagina": doc_fuente.metadata.get('page_number', 'N/A'),
                        "contenido_fragmento": doc_fuente.page_content[:250] + "..."
                    }
                    fuentes_recuperadas_serializables.append(fuente_info)
                    logger.info(f"  Fuente {i+1}: {fuente_info['documento_fuente']} (Pág: {fuente_info['pagina']})")
            else:
                logger.info("No se recuperaron documentos fuente específicos para este análisis.")
                
        except Exception as e_invoke:
            logger.error(f"Error crítico durante la invocación de la cadena RAG (LLM): {e_invoke}")
            logger.error(traceback.format_exc())
            resultado_analisis_llm_str = f"Error en análisis durante la invocación de la cadena RAG: {str(e_invoke)}"
        
        logger.info(f"Tiempo para ejecutar consulta RAG: {time.time() - start_time_query:.2f} segundos.")

        logger.info("--- ETAPA 7: Formateando y Guardando Reporte JSON ---")
        start_time_report = time.time()
        # Usar el output_dir_especifico_proyecto que ya calculamos
        ruta_json_guardado = report_utils.formatear_y_guardar_reporte(
            resultado_analisis_llm=resultado_analisis_llm_str,
            fuentes_recuperadas=fuentes_recuperadas_serializables,
            nombre_pdf_proyecto=nombre_pdf_proyecto_detectado, 
            modelo_llm_usado=config.GEMINI_MODEL_NAME, # Usar GEMINI_MODEL_NAME
            output_path_dir=output_dir_especifico_proyecto
        )
        if not ruta_json_guardado:
            logger.error("No se pudo guardar el reporte JSON.")
        else:
            logger.info(f"Reporte JSON guardado en: {ruta_json_guardado}")
        logger.info(f"Tiempo para formatear y guardar reporte JSON: {time.time() - start_time_report:.2f} segundos.")

        if ruta_json_guardado and os.path.exists(ruta_json_guardado):
            logger.info("--- ETAPA 8: Generando Dashboard de Visualización ---")
            start_time_dashboard = time.time()
            
            base_name_json = os.path.splitext(os.path.basename(ruta_json_guardado))[0]
            # Construir el nombre del dashboard consistentemente
            dashboard_html_filename = base_name_json.replace("analisis_riesgos_", "dashboard_") + config.DASHBOARD_HTML_SUFFIX
            ruta_output_dashboard_html_absoluta = os.path.join(output_dir_especifico_proyecto, dashboard_html_filename)

            dashboard_generator.generar_dashboard_html(
                ruta_json_resultados=ruta_json_guardado,
                ruta_output_dashboard_html=ruta_output_dashboard_html_absoluta,
                lista_pdfs_base_conocimiento=lista_pdfs_base_conocimiento
            )
            
            if os.path.exists(ruta_output_dashboard_html_absoluta):
                logger.info(f"Dashboard HTML generado exitosamente en: {ruta_output_dashboard_html_absoluta}")
                ruta_output_dashboard_html_relativa = os.path.normpath(os.path.relpath(ruta_output_dashboard_html_absoluta, PROJECT_ROOT))
            else:
                logger.error(f"El dashboard HTML no se encontró en {ruta_output_dashboard_html_absoluta} después de intentar generarlo.")
            logger.info(f"Tiempo para generar dashboard HTML: {time.time() - start_time_dashboard:.2f} segundos.")
        else:
            logger.warning("El archivo JSON de resultados no se generó o no se encontró. No se puede crear el dashboard.")

        logger.info("######################################################################")
        logger.info("# PROCESO DE ANÁLISIS DE RIESGOS RAG FINALIZADO                    #")
        logger.info(f"# Tiempo total de ejecución: {time.time() - start_time_total:.2f} segundos.")
        logger.info("######################################################################")
        
        if ruta_output_dashboard_html_relativa:
            logger.info(f"Resultados generados en la subcarpeta '{nombre_base_proyecto_analizado}' dentro de: {os.path.relpath(config.DIRECTORIO_RESULTADOS, PROJECT_ROOT)}")
            logger.info(f"Dashboard relativo para Flask: {ruta_output_dashboard_html_relativa}")
        else:
            logger.error("El dashboard no pudo ser generado o su ruta no pudo ser determinada.")
        return ruta_output_dashboard_html_relativa

    except Exception as e_main_flow:
        logger.error(f"Error catastrófico e inesperado en el flujo principal de run_analysis: {e_main_flow}")
        logger.error(traceback.format_exc())
        return None

if __name__ == '__main__':
    logger.info("Ejecutando main.py como script independiente...")
    dashboard_file_path_relative = run_analysis()

    if dashboard_file_path_relative:
        logger.info("Proceso de análisis independiente completado.")
        abs_dashboard_path = os.path.abspath(os.path.join(PROJECT_ROOT, dashboard_file_path_relative))
        logger.info(f"Ruta absoluta del dashboard: {abs_dashboard_path}")
        file_url_path = abs_dashboard_path.replace(os.sep, '/')
        if sys.platform == "win32" and file_url_path.startswith('/'):
             file_url_path = file_url_path[1:]
        print(f"\nPara ver el dashboard, copia y pega esta URL en tu navegador:\nfile:///{file_url_path}")
    else:
        logger.error("El proceso de análisis independiente falló o no generó el dashboard. Revisa los logs.")