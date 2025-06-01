# scripts/rag_components.py
from langchain.chains import RetrievalQA
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
import logging
import traceback

logger = logging.getLogger(__name__)

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
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY no proporcionada para inicializar el LLM.")
        return None
    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=gemini_api_key,
            temperature=0.3,
        )
        logger.info(f"--- LLM ({model_name}) configurado exitosamente ---")
        return llm
    except Exception as e:
        logger.error(f"Error al configurar el LLM ({model_name}): {e}")
        logger.debug(traceback.format_exc())
        return None

def crear_cadena_rag(llm, vector_db_instance, k_retrieved_docs):
    if not llm:
        logger.error("Instancia LLM no proporcionada para crear la cadena RAG.")
        return None
    if not vector_db_instance:
        logger.error("Instancia de Vector DB no proporcionada para crear la cadena RAG.")
        return None
    
    try:
        retriever = vector_db_instance.as_retriever(search_kwargs={"k": k_retrieved_docs})
        logger.info(f"--- Retriever configurado para obtener {k_retrieved_docs} fragmentos ---")

        prompt = PromptTemplate(
            template=PROMPT_TEMPLATE_STR,
            input_variables=["context", "question"]
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt}
        )
        logger.info("--- Cadena RetrievalQA creada exitosamente ---")
        return qa_chain
    except Exception as e:
        logger.error(f"Error al crear la cadena RetrievalQA: {e}")
        logger.debug(traceback.format_exc())
        return None

if __name__ == '__main__':
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger.info("Módulo rag_components.py cargado.")