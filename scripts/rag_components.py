# scripts/rag_components.py
from langchain.chains import RetrievalQA
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
# No es necesario importar config si los parámetros se pasan a las funciones
# vector_db se pasará como argumento, no se carga aquí directamente.

# Plantilla de Prompt (puede ser extensa, mantenerla aquí o en un archivo de texto separado)
PROMPT_TEMPLATE_STR = """
Eres un asistente de IA altamente especializado en la identificación y evaluación de riesgos para proyectos de instalación de maquinaria industrial, basándote en el Project Management Body of Knowledge (PMBOK) y documentación técnica.
Tu tarea es analizar la descripción del "NUEVO PROYECTO" que se proporciona a continuación. Debes utilizar ÚNICAMENTE la información contenida en el "CONTEXTO PROPORCIONADO" (extractos del PMBOK, manuales técnicos, y lecciones de proyectos anteriores) para realizar tu análisis.

CONTEXTO PROPORCIONADO:
{context}

NUEVO PROYECTO (PREGUNTA DEL USUARIO):
{question}

INSTRUCCIONES PARA LA RESPUESTA:
1. Identifica una lista de posibles riesgos específicos para el "NUEVO PROYECTO".
2. Para cada riesgo identificado, proporciona:
    a. "descripcion_riesgo": Una descripción clara y concisa del riesgo.
    b. "explicacion_riesgo": Una breve explicación de por qué es un riesgo, citando específicamente la(s) parte(s) del "CONTEXTO PROPORCIONADO" que lo sustentan (ej., "Basado en la sección X del Contexto Y..."). Si el contexto no sustenta directamente un riesgo pero la descripción del proyecto lo sugiere, indícalo.
    c. "impacto_estimado": Una estimación del impacto potencial del riesgo (opciones: "Bajo", "Medio", "Alto").
    d. "probabilidad_estimada": Una estimación de la probabilidad de ocurrencia del riesgo (opciones: "Baja", "Media", "Alta").
3. Si no encuentras información relevante en el "CONTEXTO PROPORCIONADO" para identificar riesgos o responder sobre un aspecto específico del "NUEVO PROYECTO", debes indicarlo claramente diciendo: "No se encontró información suficiente en el contexto proporcionado para evaluar [aspecto específico]". No inventes información.
4. Formatea TODA tu respuesta como un ÚNICO objeto JSON. El objeto JSON debe tener una clave principal llamada "riesgos_identificados", que contenga una lista de objetos, donde cada objeto representa un riesgo individual con las claves "descripcion_riesgo", "explicacion_riesgo", "impacto_estimado", y "probabilidad_estimada".

Ejemplo de formato de un riesgo dentro de la lista:
{{
  "descripcion_riesgo": "Falla en la integración del nuevo sistema de control con la infraestructura existente.",
  "explicacion_riesgo": "El Contexto 3 menciona problemas de compatibilidad con sistemas heredados similares. El Nuevo Proyecto implica una integración con un sistema antiguo.",
  "impacto_estimado": "Alto",
  "probabilidad_estimada": "Media"
}}

Comienza tu respuesta JSON:
"""

def get_llm_instance(model_name, gemini_api_key):
    """Inicializa y retorna la instancia del LLM (Gemini)."""
    if not gemini_api_key:
        print("Error: GEMINI_API_KEY no proporcionada para inicializar el LLM.")
        return None
    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=gemini_api_key,
            temperature=0.3, # Para respuestas más factuales
            # convert_system_message_to_human=True # Chequear si aún es necesario o causa warnings
        )
        print(f"--- LLM ({model_name}) configurado exitosamente ---")
        return llm
    except Exception as e:
        print(f"Error al configurar el LLM ({model_name}): {e}")
        return None

def crear_cadena_rag(llm, vector_db_instance, k_retrieved_docs):
    """
    Crea y retorna la cadena RetrievalQA.
    """
    if not llm:
        print("Error: Instancia LLM no proporcionada para crear la cadena RAG.")
        return None
    if not vector_db_instance:
        print("Error: Instancia de Vector DB no proporcionada para crear la cadena RAG.")
        return None
    
    try:
        retriever = vector_db_instance.as_retriever(search_kwargs={"k": k_retrieved_docs})
        print(f"--- Retriever configurado para obtener {k_retrieved_docs} fragmentos ---")

        prompt = PromptTemplate(
            template=PROMPT_TEMPLATE_STR,
            input_variables=["context", "question"]
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff", # "stuff" es simple y efectivo para contextos no demasiado largos
            retriever=retriever,
            return_source_documents=True, # Para obtener los documentos fuente
            chain_type_kwargs={"prompt": prompt}
        )
        print("--- Cadena RetrievalQA creada exitosamente ---")
        return qa_chain
    except Exception as e:
        print(f"Error al crear la cadena RetrievalQA: {e}")
        return None

if __name__ == '__main__':
    # Esta sección es solo para probar el módulo, no se usa en el flujo principal.
    # Para probarlo necesitarías una instancia de vector_db y la API key.
    # from config import LLM_MODEL_NAME, GEMINI_API_KEY, K_RETRIEVED_DOCS, configure_google_api
    # from vector_db_manager import get_embedding_function, crear_o_cargar_chroma_db
    # from config import CHROMA_DB_PATH, DOCS_BASE_CONOCIMIENTO_PATH, CHUNK_SIZE, CHUNK_OVERLAP, RECREAR_DB_FLAG_DUMMY # Necesitarías una config dummy
    
    # print("Probando componentes RAG...")
    # if configure_google_api(): # Asumiendo que config.py tiene GEMINI_API_KEY
    #     test_llm = get_llm_instance(LLM_MODEL_NAME, GEMINI_API_KEY)
    #     # Necesitarías cargar una dummy DB para probar la cadena completa
    #     # embedding_func = get_embedding_function("all-MiniLM-L6-v2")
    #     # dummy_db = crear_o_cargar_chroma_db(CHROMA_DB_PATH, DOCS_BASE_CONOCIMIENTO_PATH, embedding_func, CHUNK_SIZE, CHUNK_OVERLAP, False)
    #     if test_llm: # and dummy_db:
    #         # test_chain = crear_cadena_rag(test_llm, dummy_db, K_RETRIEVED_DOCS)
    #         # if test_chain:
    #         #     print("Prueba de creación de cadena RAG exitosa.")
    #         # else:
    #         #     print("Prueba de creación de cadena RAG fallida.")
    #         print("Prueba de instanciación de LLM exitosa (cadena RAG no probada sin DB).")
    #     else:
    #         print("Prueba de componentes RAG fallida (LLM o DB).")
    print("Módulo rag_components.py cargado. Contiene funciones para LLM y cadena RAG.")

