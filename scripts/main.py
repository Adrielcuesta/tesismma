# scripts/main.py
import os
import time 

# Importar módulos del proyecto
import config
import document_utils
import vector_db_manager
import rag_components
import report_utils
import dashboard_generator

def ejecutar_flujo_completo_analisis():
    """
    Orquesta el flujo completo del análisis de riesgos.
    """
    start_time_total = time.time()

    print("######################################################################")
    print("# INICIANDO PROCESO DE ANÁLISIS DE RIESGOS RAG (Versión Local)     #")
    print("######################################################################")

    # --- ETAPA 0: Cargar Configuración e Inicializar Directorios ---
    print("\n--- ETAPA 0: Cargando Configuración e Inicializando Directorios ---")
    if not config.inicializar_directorios_datos():
        print("Error fatal: No se pudieron inicializar los directorios de datos. Terminando.")
        return
    if not config.configure_google_api():
        print("Advertencia: API de Google no configurada. El LLM podría no funcionar.")
        # Considerar si terminar aquí si la API es crucial para todas las etapas.

    # --- ETAPA 1: Detectar PDF del Proyecto a Analizar ---
    print("\n--- ETAPA 1: Detectando PDF del Proyecto a Analizar ---")
    pdfs_en_proyecto_analizar = []
    if os.path.exists(config.PROYECTO_A_ANALIZAR_PATH):
        pdfs_en_proyecto_analizar = [f for f in os.listdir(config.PROYECTO_A_ANALIZAR_PATH) if f.lower().endswith(".pdf")]
    
    if not pdfs_en_proyecto_analizar:
        print(f"Error fatal: No se encontraron archivos PDF en la carpeta '{config.PROYECTO_A_ANALIZAR_PATH}'.")
        print("Por favor, añade un (y solo un) PDF para analizar en esa carpeta. Terminando.")
        return
    if len(pdfs_en_proyecto_analizar) > 1:
        print(f"Error fatal: Se encontraron múltiples archivos PDF en '{config.PROYECTO_A_ANALIZAR_PATH}'.")
        print("Por favor, deja solo un PDF en esa carpeta para el análisis. Terminando.")
        print(f"Archivos encontrados: {pdfs_en_proyecto_analizar}")
        return
    
    nombre_pdf_proyecto_detectado = pdfs_en_proyecto_analizar[0]
    print(f"PDF detectado para análisis: {nombre_pdf_proyecto_detectado}")

    # Crear directorio de salida específico para este proyecto dentro de OUTPUT_PATH
    nombre_base_proyecto_analizado = os.path.splitext(nombre_pdf_proyecto_detectado)[0]
    output_dir_especifico_proyecto = os.path.join(config.OUTPUT_PATH, nombre_base_proyecto_analizado)
    try:
        os.makedirs(output_dir_especifico_proyecto, exist_ok=True)
        print(f"Directorio de resultados para este proyecto: {output_dir_especifico_proyecto}")
    except OSError as e:
        print(f"Error fatal: No se pudo crear el directorio de salida específico '{output_dir_especifico_proyecto}': {e}. Terminando.")
        return

    # Obtener lista de PDFs de la base de conocimiento para el dashboard
    lista_pdfs_base_conocimiento = []
    try:
        if os.path.exists(config.DOCS_BASE_CONOCIMIENTO_PATH):
            lista_pdfs_base_conocimiento = [f for f in os.listdir(config.DOCS_BASE_CONOCIMIENTO_PATH) if f.lower().endswith(".pdf")]
        if not lista_pdfs_base_conocimiento:
            print(f"Advertencia: No se encontraron PDFs en la carpeta de base de conocimiento: {config.DOCS_BASE_CONOCIMIENTO_PATH}")
    except Exception as e:
        print(f"Error al listar PDFs de la base de conocimiento: {e}")

    # --- ETAPA 2: Inicializando Modelo de Embeddings ---
    print("\n--- ETAPA 2: Inicializando Modelo de Embeddings ---")
    start_time_embed = time.time()
    embedding_function = vector_db_manager.get_embedding_function(config.EMBEDDING_MODEL_NAME)
    if not embedding_function:
        print("Error fatal: No se pudo inicializar el modelo de embeddings. Terminando.")
        return
    print(f"Tiempo para inicializar embeddings: {time.time() - start_time_embed:.2f} segundos.")

    # --- ETAPA 3: Gestionando Base de Datos Vectorial (ChromaDB) ---
    print("\n--- ETAPA 3: Gestionando Base de Datos Vectorial (ChromaDB) ---")
    start_time_db = time.time()
    vector_db = vector_db_manager.crear_o_cargar_chroma_db(
        chroma_db_path=config.CHROMA_DB_PATH,
        docs_base_conocimiento_path=config.DOCS_BASE_CONOCIMIENTO_PATH,
        embedding_function=embedding_function,
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        recrear_db_flag=config.RECREAR_DB
    )
    if not vector_db:
        print("Error fatal: No se pudo crear o cargar la base de datos vectorial. Terminando.")
        return
    print(f"Tiempo para gestión de DB: {time.time() - start_time_db:.2f} segundos.")

    # --- ETAPA 4: Configurando LLM y Cadena RAG ---
    print("\n--- ETAPA 4: Configurando LLM y Cadena RAG ---")
    start_time_rag_setup = time.time()
    if not config.GEMINI_API_KEY: # Chequeo adicional por si configure_google_api() no detuvo el flujo
        print("Error fatal: GEMINI_API_KEY no está disponible. Terminando.")
        return
    llm = rag_components.get_llm_instance(config.LLM_MODEL_NAME, config.GEMINI_API_KEY)
    if not llm:
        print("Error fatal: No se pudo inicializar el LLM. Terminando.")
        return
        
    qa_chain = rag_components.crear_cadena_rag(llm, vector_db, config.K_RETRIEVED_DOCS)
    if not qa_chain:
        print("Error fatal: No se pudo crear la cadena RAG. Terminando.")
        return
    print(f"Tiempo para configurar LLM y cadena RAG: {time.time() - start_time_rag_setup:.2f} segundos.")

    # --- ETAPA 5: Procesando Documento del Proyecto a Analizar ---
    print("\n--- ETAPA 5: Procesando Documento del Proyecto a Analizar ---")
    start_time_proc_pdf = time.time()
    ruta_pdf_proyecto = os.path.join(config.PROYECTO_A_ANALIZAR_PATH, nombre_pdf_proyecto_detectado)
    descripcion_nuevo_proyecto = document_utils.procesar_pdf_proyecto_para_analisis(
        ruta_pdf_proyecto,
        config.CHUNK_SIZE,
        config.CHUNK_OVERLAP,
        config.MAX_CHARS_PROYECTO
    )
    if not descripcion_nuevo_proyecto:
        print("Error fatal: No se pudo procesar el PDF del proyecto a analizar. Terminando.")
        return
    print(f"Tiempo para procesar PDF del proyecto: {time.time() - start_time_proc_pdf:.2f} segundos.")

    # --- ETAPA 6: Ejecutando Análisis de Riesgos con la Cadena RAG ---
    print("\n--- ETAPA 6: Ejecutando Análisis de Riesgos con la Cadena RAG ---")
    start_time_query = time.time()
    resultado_analisis_llm = None
    fuentes_recuperadas_serializables = []
    ruta_json_resultados_generado = None 

    try:
        respuesta_rag = qa_chain.invoke({"query": descripcion_nuevo_proyecto})
        resultado_analisis_llm = respuesta_rag.get("result")
        fuentes_recuperadas_docs = respuesta_rag.get("source_documents", [])

        if resultado_analisis_llm:
            print("\n--- ANÁLISIS DE RIESGOS GENERADO (RESPUESTA CRUDA DEL LLM) ---")
            # Imprime solo una parte si es muy largo para la consola
            print(resultado_analisis_llm[:1000] + "..." if isinstance(resultado_analisis_llm, str) and len(resultado_analisis_llm) > 1000 else resultado_analisis_llm)
        else:
            print("Advertencia: El LLM no devolvió un resultado ('result' es None o vacío).")
            resultado_analisis_llm = "El LLM no devolvió un resultado." # Para que el reporte no esté vacío

        print("\n--- FUENTES RECUPERADAS POR EL RETRIEVER ---")
        if fuentes_recuperadas_docs:
            for i, doc_fuente in enumerate(fuentes_recuperadas_docs):
                fuentes_recuperadas_serializables.append({
                    "metadata": doc_fuente.metadata,
                    "page_content_snippet": doc_fuente.page_content[:200] + "..."
                })
                print(f"  Fuente {i+1}: {doc_fuente.metadata.get('source_document', 'N/A')} (Pág: {doc_fuente.metadata.get('page_number', 'N/A')}, Inicio Chunk: {doc_fuente.metadata.get('start_index','N/A')})")
        else:
            print("  No se recuperaron fuentes específicas para este análisis.")
            
    except Exception as e_invoke:
        print(f"Error crítico durante la invocación de la cadena RAG: {e_invoke}")
        resultado_analisis_llm = f"Error en análisis durante la invocación de la cadena RAG: {str(e_invoke)}"
    
    print(f"Tiempo para ejecutar consulta RAG: {time.time() - start_time_query:.2f} segundos.")

    # --- ETAPA 7: Formateando y Guardando Reporte JSON ---
    if resultado_analisis_llm is not None: 
        print("\n--- ETAPA 7: Formateando y Guardando Reporte JSON ---")
        start_time_report = time.time()
        ruta_json_resultados_generado = report_utils.formatear_y_guardar_reporte(
            resultado_analisis_llm=resultado_analisis_llm,
            fuentes_recuperadas=fuentes_recuperadas_serializables,
            nombre_pdf_proyecto=nombre_pdf_proyecto_detectado, # Usar el nombre detectado
            modelo_llm_usado=config.LLM_MODEL_NAME,
            output_path_dir=output_dir_especifico_proyecto # Guardar en la subcarpeta específica
        )
        print(f"Tiempo para formatear y guardar reporte JSON: {time.time() - start_time_report:.2f} segundos.")
    else:
        print("\nNo se generó resultado del LLM o hubo un error crítico previo, no se guardará reporte JSON ni se generará dashboard.")

    # --- ETAPA 8: Generando Dashboard de Visualización ---
    if ruta_json_resultados_generado and os.path.exists(ruta_json_resultados_generado):
        print("\n--- ETAPA 8: Generando Dashboard de Visualización ---")
        start_time_dashboard = time.time()
        
        # El nombre del dashboard HTML se basará en el nombre del JSON pero con sufijo _dashboard.html
        # El JSON ya se guarda con timestamp, así que el HTML también lo tendrá indirectamente.
        # El nombre base del JSON es algo como "analisis_riesgos_ProyectoEjemplo_20250529_203000"
        base_name_json = os.path.splitext(os.path.basename(ruta_json_resultados_generado))[0]
        dashboard_html_filename = base_name_json + config.DASHBOARD_HTML_SUFFIX
        ruta_output_dashboard_html = os.path.join(output_dir_especifico_proyecto, dashboard_html_filename)

        dashboard_generator.generar_dashboard_html(
            ruta_json_resultados=ruta_json_resultados_generado,
            ruta_output_dashboard_html=ruta_output_dashboard_html,
            lista_pdfs_base_conocimiento=lista_pdfs_base_conocimiento
        )
        print(f"Tiempo para generar dashboard HTML: {time.time() - start_time_dashboard:.2f} segundos.")
    elif resultado_analisis_llm is not None:
        print("Advertencia: El archivo JSON de resultados no se generó o no se encontró. No se puede crear el dashboard.")


    print("\n######################################################################")
    print("# PROCESO DE ANÁLISIS DE RIESGOS RAG FINALIZADO                    #")
    print(f"# Tiempo total de ejecución: {time.time() - start_time_total:.2f} segundos.")
    print("######################################################################")
    print(f"\nRevisa los resultados en la subcarpeta '{nombre_base_proyecto_analizado}' dentro de: {config.OUTPUT_PATH}")
    print(f"Para re-crear la base de conocimiento, edita 'RECREAR_DB' en '{os.path.join(config.PROJECT_ROOT, 'scripts', 'config.py')}' y vuelve a ejecutar.")

if __name__ == '__main__':
    ejecutar_flujo_completo_analisis()
