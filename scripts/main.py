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
logger = logging.getLogger(__name__) # Obtener logger específico para este módulo
# Establecer nivel y handlers solo si no están ya configurados (evita duplicados si se importa)
if not logger.handlers:
    logger.setLevel(logging.INFO) 
    console_handler = logging.StreamHandler(sys.stdout) # Usar sys.stdout para Cloud Run logging
    # Usar un formato más simple para Cloud Run, o uno más detallado para local
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(module)s.%(funcName)s - %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.propagate = False # Evita que los logs se pasen al root logger si este también tiene handlers

# Configuración de fallback para el root logger si es necesario (ej. si otros módulos no configuran bien)
# Esto es más una salvaguarda, idealmente cada módulo configura su logger o usa el root logger con cuidado.
if not logging.getLogger().handlers: # Solo si el root logger no tiene handlers
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - ROOT - %(module)s.%(funcName)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)] # Asegurar salida a consola para Cloud Run
    )
# --- Fin Configuración del Logging ---

def run_analysis(force_recreate_db=None): # Aceptar el parámetro aquí
    start_time_total = time.time()
    ruta_output_dashboard_html_relativa = None
    
    # Determinar PROJECT_ROOT de forma consistente
    # Si main.py está en scripts/, y app.py está en la raíz del proyecto,
    # config.PROJECT_ROOT ya debería estar definido correctamente respecto a la raíz del proyecto.
    # Usaremos config.PROJECT_ROOT para consistencia.
    PROJECT_ROOT_FROM_CONFIG = config.PROJECT_ROOT 
    
    logger.info("######################################################################")
    logger.info("# INICIANDO PROCESO DE ANÁLISIS DE RIESGOS RAG (desde run_analysis)  #")
    logger.info("######################################################################")

    try:
        logger.info("--- ETAPA 0: Cargando Configuración e Inicializando Directorios ---")
        if not config.inicializar_directorios_datos():
            logger.error("Error fatal: No se pudieron inicializar los directorios de datos.")
            return None # Devolver None si hay error para que app.py lo maneje
        if not config.configure_google_api():
            logger.warning("Advertencia: API de Google no configurada. El LLM podría no funcionar.")
            # Continuar de todas formas, podría ser un análisis solo con retriever o para probar otras partes

        logger.info("--- ETAPA 1: Detectando PDF del Proyecto a Analizar ---")
        # document_utils.obtener_ruta_pdf_proyecto ya loguea errores si no encuentra el PDF
        pdf_path_analizar_abs = document_utils.obtener_ruta_pdf_proyecto(config.DIRECTORIO_PROYECTO_ANALIZAR)
        if not pdf_path_analizar_abs:
            logger.error("Error fatal: No se encontró un PDF válido en la carpeta del proyecto a analizar.")
            return None 
        
        nombre_pdf_proyecto_detectado = os.path.basename(pdf_path_analizar_abs)
        nombre_base_proyecto_analizado = os.path.splitext(nombre_pdf_proyecto_detectado)[0]
        logger.info(f"PDF detectado para análisis: {nombre_pdf_proyecto_detectado}")

        # Crear directorio de salida específico para este proyecto
        output_dir_especifico_proyecto = os.path.join(config.DIRECTORIO_RESULTADOS, nombre_base_proyecto_analizado)
        try:
            os.makedirs(output_dir_especifico_proyecto, exist_ok=True)
            logger.info(f"Directorio de resultados para este proyecto: {output_dir_especifico_proyecto}")
        except OSError as e:
            logger.error(f"Error fatal al crear directorio de salida '{output_dir_especifico_proyecto}': {e}")
            return None

        lista_pdfs_base_conocimiento = document_utils.listar_documentos_kb(config.DIRECTORIO_BASE_CONOCIMIENTO)
        if not lista_pdfs_base_conocimiento:
             logger.warning(f"No se encontraron PDFs en la carpeta de base de conocimiento: {config.DIRECTORIO_BASE_CONOCIMIENTO}. La base vectorial podría estar vacía si se recrea.")


        logger.info("--- ETAPA 2: Inicializando Modelo de Embeddings ---")
        start_time_embed = time.time()
        embedding_function = vector_db_manager.get_embedding_function(config.EMBEDDING_MODEL_NAME_OR_PATH)
        if not embedding_function:
            logger.error("Error fatal: No se pudo inicializar el modelo de embeddings (main.py).")
            return None
        logger.info(f"Tiempo para inicializar embeddings: {time.time() - start_time_embed:.2f} segundos.")

        logger.info("--- ETAPA 3: Gestionando Base de Datos Vectorial (ChromaDB) ---")
        start_time_db = time.time()
        
        # Decidir si se recrea la DB basado en el parámetro o en config.py
        recrear_db_final_decision = config.RECREAR_DB # Valor por defecto desde config.py
        if force_recreate_db is not None:
            logger.info(f"Opción de recrear DB desde Flask: {force_recreate_db}. Anulando valor de config.py ({config.RECREAR_DB}) para esta ejecución.")
            recrear_db_final_decision = force_recreate_db
        else:
            logger.info(f"Usando valor de RECREAR_DB de config.py: {config.RECREAR_DB}")

        vector_db = vector_db_manager.crear_o_cargar_chroma_db(
            chroma_db_path=config.CHROMA_DB_PATH,
            docs_base_conocimiento_path=config.DIRECTORIO_BASE_CONOCIMIENTO,
            embedding_function=embedding_function,
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            recrear_db_flag=recrear_db_final_decision # Usar la decisión final
        )
        if not vector_db:
            logger.error("Error fatal: No se pudo crear o cargar la base de datos vectorial (main.py).")
            return None
        logger.info(f"Tiempo para gestión de DB: {time.time() - start_time_db:.2f} segundos.")

        logger.info("--- ETAPA 4: Configurando LLM y Cadena RAG ---")
        start_time_rag_setup = time.time()
        if not config.GEMINI_API_KEY: 
            logger.error("Error fatal: GEMINI_API_KEY no está disponible. El análisis RAG no funcionará.")
            # Podríamos optar por no devolver None aquí si queremos que el sistema genere un reporte "vacío"
            # o un dashboard indicando el problema, pero por ahora, es un error que impide el análisis.
            return None 
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
        # pdf_path_analizar_abs ya está definido y validado
        descripcion_nuevo_proyecto = document_utils.procesar_pdf_proyecto_para_analisis(
            pdf_path_analizar_abs,
            config.CHUNK_SIZE,
            config.CHUNK_OVERLAP,
            config.MAX_CHARS_PROYECTO
        )
        if not descripcion_nuevo_proyecto: 
            logger.error("Error fatal: No se pudo procesar el PDF del proyecto a analizar (main.py).")
            return None
        logger.info(f"Texto extraído y preparado del proyecto '{nombre_base_proyecto_analizado}'. Longitud: {len(descripcion_nuevo_proyecto)} caracteres.")
        logger.info(f"Tiempo para procesar PDF del proyecto: {time.time() - start_time_proc_pdf:.2f} segundos.")

        logger.info(f"--- ETAPA 6: Ejecutando Análisis de Riesgos para el proyecto: {nombre_base_proyecto_analizado} ---")
        start_time_query = time.time()
        resultado_analisis_llm_str = "Error: Análisis no ejecutado o LLM no devolvió respuesta."
        fuentes_recuperadas_serializables = []
        
        try:
            logger.info("Enviando consulta a la cadena RAG (esto puede tardar)...")
            # La plantilla de prompt espera la descripción del proyecto en la variable "query" o "question"
            # En rag_components.py, el PromptTemplate usa "question"
            respuesta_rag = qa_chain.invoke({"query": descripcion_nuevo_proyecto}) 
            
            if isinstance(respuesta_rag, dict):
                resultado_analisis_llm_str = respuesta_rag.get("result", "No se encontró 'result' en la respuesta del LLM.")
                fuentes_recuperadas_docs = respuesta_rag.get("source_documents", [])
            else: # Si la cadena no devuelve un dict (inesperado para RetrievalQA con return_source_documents=True)
                resultado_analisis_llm_str = str(respuesta_rag) # Intentar convertir a string
                fuentes_recuperadas_docs = []
                logger.warning(f"La respuesta de la cadena RAG no fue un diccionario como se esperaba. Tipo recibido: {type(respuesta_rag)}")

            if resultado_analisis_llm_str and isinstance(resultado_analisis_llm_str, str) and resultado_analisis_llm_str.strip():
                logger.info("Respuesta del LLM recibida.")
                logger.debug(f"Respuesta LLM (raw - primeros 500 chars): {resultado_analisis_llm_str[:500]}...")
            else:
                logger.warning("Advertencia: El LLM no devolvió un resultado ('result' es None, vacío, o no es string).")
                resultado_analisis_llm_str = "El LLM no devolvió un resultado interpretable o la respuesta estaba vacía."


            if fuentes_recuperadas_docs:
                logger.info("--- FUENTES RECUPERADAS POR EL RETRIEVER ---")
                for i, doc_fuente in enumerate(fuentes_recuperadas_docs):
                    fuente_info = {
                        "documento_fuente": doc_fuente.metadata.get('source_document', 'N/A'),
                        "pagina": doc_fuente.metadata.get('page_number', 'N/A'),
                        "contenido_fragmento": doc_fuente.page_content[:250] + "..." # Snippet
                    }
                    fuentes_recuperadas_serializables.append(fuente_info)
                    logger.info(f"  Fuente {i+1}: {fuente_info['documento_fuente']} (Pág: {fuente_info['pagina']})")
            else:
                logger.info("No se recuperaron documentos fuente específicos para este análisis.")
                
        except Exception as e_invoke:
            logger.error(f"Error crítico durante la invocación de la cadena RAG (LLM): {e_invoke}")
            logger.error(traceback.format_exc())
            resultado_analisis_llm_str = f"Error en análisis durante la invocación de la cadena RAG: {str(e_invoke)}"
            # No devolvemos None aquí todavía, para que se intente generar un reporte con el error.
        
        logger.info(f"Tiempo para ejecutar consulta RAG: {time.time() - start_time_query:.2f} segundos.")

        logger.info("--- ETAPA 7: Formateando y Guardando Reporte JSON ---")
        start_time_report = time.time()
        ruta_json_guardado = report_utils.formatear_y_guardar_reporte(
            resultado_analisis_llm=resultado_analisis_llm_str, # Siempre pasar el string
            fuentes_recuperadas=fuentes_recuperadas_serializables,
            nombre_pdf_proyecto=nombre_pdf_proyecto_detectado, 
            modelo_llm_usado=config.GEMINI_MODEL_NAME, # Usar el nombre del modelo de config.py
            output_path_dir=output_dir_especifico_proyecto
        )
        if not ruta_json_guardado:
            logger.error("No se pudo guardar el reporte JSON (formatear_y_guardar_reporte devolvió None).")
        else:
            logger.info(f"Reporte JSON guardado en: {ruta_json_guardado}")
        logger.info(f"Tiempo para formatear y guardar reporte JSON: {time.time() - start_time_report:.2f} segundos.")

        # Generar dashboard solo si el JSON se guardó exitosamente
        if ruta_json_guardado and os.path.exists(ruta_json_guardado):
            logger.info("--- ETAPA 8: Generando Dashboard de Visualización ---")
            start_time_dashboard = time.time()
            
            dashboard_html_filename = f"dashboard_{nombre_base_proyecto_analizado}.html" # Nombre consistente
            ruta_output_dashboard_html_absoluta = os.path.join(output_dir_especifico_proyecto, dashboard_html_filename)

            dashboard_generator.generar_dashboard_html(
                ruta_json_resultados=ruta_json_guardado,
                ruta_output_dashboard_html=ruta_output_dashboard_html_absoluta,
                lista_pdfs_base_conocimiento=lista_pdfs_base_conocimiento
            )
            
            if os.path.exists(ruta_output_dashboard_html_absoluta):
                logger.info(f"Dashboard HTML generado exitosamente en: {ruta_output_dashboard_html_absoluta}")
                # Calcular ruta relativa desde PROJECT_ROOT_FROM_CONFIG para Flask
                ruta_output_dashboard_html_relativa = os.path.normpath(os.path.relpath(ruta_output_dashboard_html_absoluta, PROJECT_ROOT_FROM_CONFIG)).replace("\\", "/")
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
            logger.info(f"Resultados generados en la subcarpeta '{nombre_base_proyecto_analizado}' dentro de: {os.path.relpath(config.DIRECTORIO_RESULTADOS, PROJECT_ROOT_FROM_CONFIG)}")
            logger.info(f"Dashboard relativo para Flask: {ruta_output_dashboard_html_relativa}")
        else:
            logger.error("El dashboard no pudo ser generado o su ruta no pudo ser determinada.")
        
        return ruta_output_dashboard_html_relativa # Devolver la ruta relativa

    except Exception as e_main_flow: # Captura general para errores no esperados en el flujo
        logger.error(f"Error catastrófico e inesperado en el flujo principal de run_analysis: {e_main_flow}")
        logger.error(traceback.format_exc())
        return None # Asegurar que se devuelve None en caso de error mayor

if __name__ == '__main__':
    logger.info("Ejecutando main.py como script independiente...")
    # Simular la determinación de PROJECT_ROOT como lo haría app.py o config.py
    # Esto es solo para la ejecución directa de main.py
    PROJECT_ROOT_MAIN_EXEC = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

    dashboard_file_path_relative = run_analysis() # Llamar sin argumento para usar config.RECREAR_DB

    if dashboard_file_path_relative:
        logger.info("Proceso de análisis independiente completado.")
        # La ruta devuelta ya es relativa a PROJECT_ROOT_FROM_CONFIG (que es config.PROJECT_ROOT)
        # Para la URL `file:///`, necesitamos una ruta absoluta.
        abs_dashboard_path = os.path.abspath(os.path.join(PROJECT_ROOT_MAIN_EXEC, dashboard_file_path_relative))
        logger.info(f"Ruta absoluta del dashboard: {abs_dashboard_path}")
        
        # Crear URL de archivo correcta para diferentes OS
        file_url_path = abs_dashboard_path.replace(os.sep, '/')
        if sys.platform == "win32":
            if not file_url_path.startswith('/'): # Para rutas como C:/...
                file_url_path_for_url = "/" + file_url_path
            else: # Para rutas de red //server/share que se vuelven /server/share
                 file_url_path_for_url = file_url_path
        else: # macOS, Linux
            file_url_path_for_url = file_url_path
            if not file_url_path_for_url.startswith('/'):
                 file_url_path_for_url = "/" + file_url_path_for_url
        
        # Reemplazar espacios para la URL
        final_url = f"file://{file_url_path_for_url.replace(' ', '%20')}"
        print(f"\nPara ver el dashboard, copia y pega esta URL en tu navegador:\n{final_url}")
    else:
        logger.error("El proceso de análisis independiente falló o no generó el dashboard. Revisa los logs.")