# scripts/rag_components.py
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from pydantic import ValidationError
import logging
import traceback
import os

# Nuevas importaciones para los modelos de LLM adicionales
from langchain_mistralai import ChatMistralAI
from langchain_cohere import ChatCohere

from .schemas import LLMResponse
from . import config

logger = logging.getLogger(__name__)

# --- PROMPT DEFINITIVO: Inspirado en tu versión original, pero completado y perfeccionado ---
PROMPT_TEMPLATE_STR = """
Eres un asistente de IA experto en la identificación y evaluación de riesgos para proyectos de instalación de maquinaria industrial.
Tu tarea es analizar la descripción del "NUEVO PROYECTO" y, basándote ÚNICAMENTE en el "CONTEXTO PROPORCIONADO", identificar una lista de posibles riesgos.

CONTEXTO PROPORCIONADO:
{context}

NUEVO PROYECTO (PREGUNTA DEL USUARIO):
{question}

INSTRUCCIONES ESTRICTAS PARA LA RESPUESTA:
1.  Tu respuesta DEBE ser un único objeto JSON. NO incluyas ningún texto antes o después del objeto JSON.
2.  El objeto JSON debe tener UNA SOLA CLAVE PRINCIPAL: "riesgos_identificados".
3.  El valor de "riesgos_identificados" debe ser una lista de objetos.
4.  Cada objeto de la lista representa un riesgo y debe contener EXACTAMENTE los siguientes 6 campos:
    a. "descripcion_riesgo": Una descripción clara y concisa del riesgo.
    b. "explicacion_riesgo": Una breve explicación de por qué es un riesgo, citando evidencia específica del "CONTEXTO PROPORCIONADO".
    c. "impacto_estimado": Opciones válidas: "Bajo", "Medio", "Alto".
    d. "probabilidad_estimada": Opciones válidas: "Baja", "Media", "Alta".
    e. "responsabilidad_mitigacion": El rol o departamento responsable de las tareas de mitigación preventivas (ej. "Ingeniería de Planta").
    f. "responsable_accidente": El rol o departamento que asumiría la responsabilidad si el riesgo se materializa (ej. "Jefe de Producción").
5.  Si, basándote estrictamente en el contexto, no se detecta ningún riesgo relevante, debes devolver una lista vacía para el campo `riesgos_identificados`. No inventes riesgos.

EJEMPLO DE RESPUESTA JSON IDEAL:
```json
{{
  "riesgos_identificados": [
    {{
      "descripcion_riesgo": "Vibraciones excesivas de la nueva prensa hidráulica podrían afectar la estructura del edificio.",
      "impacto_estimado": "Alto",
      "probabilidad_estimada": "Media",
      "responsabilidad_mitigacion": "Ingeniería Civil y de Planta",
      "responsable_accidente": "Gerencia de Operaciones",
      "explicacion_riesgo": "El Contexto 2 menciona que equipos con más de 50 toneladas de fuerza de prensado, como el del proyecto, requieren un estudio de suelo y cimentación reforzada, lo cual no se especifica en la descripción del proyecto."
    }}
  ]
}}
```

Comienza tu respuesta JSON ahora:
"""

def get_llm_instance(model_id: str):
    """
    Fábrica de instancias de LLM basada en el ID del modelo configurado.
    Permite inicializar diferentes modelos de Google, OpenAI, Mistral y Cohere.
    """
    if model_id not in config.LLM_MODELS:
        logger.error(f"Modelo '{model_id}' no encontrado en la configuración LLM_MODELS.")
        raise ValueError(f"Modelo no soportado: {model_id}")

    model_config = config.LLM_MODELS[model_id]
    provider = model_config["provider"]
    api_key_env = model_config.get("api_key_env")

    logger.info(f"Intentando inicializar el modelo: '{model_id}' del proveedor: '{provider}'")
    try:
        api_key = os.getenv(api_key_env) if api_key_env else None
        if api_key_env and not api_key:
            logger.error(f"Variable de entorno '{api_key_env}' no encontrada para el modelo '{model_id}'.")
            return None

        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            config.configure_google_api() # Asegura que la API de Google esté configurada
            return ChatGoogleGenerativeAI(model=model_id, google_api_key=api_key, temperature=0.2, convert_system_message_to_human=True)
        elif provider == "openai" or provider == "openai_compatible":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=model_id, api_key=api_key, base_url=model_config.get("base_url"), temperature=0.2)
        elif provider == "mistralai":
            # Inicializa el modelo de Mistral AI
            return ChatMistralAI(model=model_id, api_key=api_key, temperature=0.2)
        elif provider == "cohere":
            # Inicializa el modelo de Cohere, usando el parámetro 'cohere_api_key'
            return ChatCohere(model=model_id, cohere_api_key=api_key, temperature=0.2)
        else:
            logger.error(f"Proveedor '{provider}' no implementado o reconocido.")
            return None
    except Exception as e:
        logger.error(f"Error inesperado al inicializar el modelo '{model_id}': {e}", exc_info=True)
        return None

def crear_cadena_rag(llm, vector_db_instance):
    """
    Crea la cadena RAG (Retrieval-Augmented Generation) que combina el LLM
    con la base de datos vectorial y, opcionalmente, un re-ranker.
    """
    if not llm:
        logger.error("Instancia LLM no proporcionada para crear la cadena RAG.")
        return None
    if not vector_db_instance:
        logger.error("Instancia de Vector DB no proporcionada para crear la cadena RAG.")
        return None

    try:
        # Configura el retriever base para obtener documentos de la DB vectorial
        base_retriever = vector_db_instance.as_retriever(
            search_kwargs={"k": config.K_RETRIEVED_DOCS_BEFORE_RERANK}
        )
        final_retriever = base_retriever # Por defecto, usa el retriever base

        # Si el re-ranker está habilitado en la configuración, lo inicializa y lo aplica
        if config.USE_RERANKER:
            logger.info("--- Habilitando Re-ranker (CrossEncoder) ---")
            try:
                # Se inicializa el modelo CrossEncoder.
                # Nota: Se eliminó el parámetro 'cache_folder' ya que causaba un error
                # y HuggingFaceCrossEncoder maneja su caché internamente.
                model = HuggingFaceCrossEncoder(model_name='BAAI/bge-reranker-base')
                compressor = CrossEncoderReranker(model=model, top_n=config.RERANKER_TOP_N)
                
                # Combina el retriever base con el compresor (re-ranker)
                compression_retriever = ContextualCompressionRetriever(
                    base_compressor=compressor,
                    base_retriever=base_retriever
                )
                final_retriever = compression_retriever # El retriever final ahora incluye el re-ranker
                logger.info(f"--- Re-ranker configurado para devolver los mejores {config.RERANKER_TOP_N} fragmentos ---")
            except Exception as e_reranker:
                logger.error(f"No se pudo inicializar el Re-ranker. Se usará el retriever base. Error: {e_reranker}", exc_info=True)
                final_retriever = base_retriever # Si falla el re-ranker, se vuelve al retriever base
        else:
            logger.info("--- Re-ranker deshabilitado por configuración. Usando retriever base. ---")

        # Define la plantilla del prompt que se usará con el LLM
        prompt = PromptTemplate(
            template=PROMPT_TEMPLATE_STR,
            input_variables=["context", "question"]
        )
        
        # Configura el LLM para que su salida sea estructurada según el esquema LLMResponse
        structured_llm = llm.with_structured_output(LLMResponse)

        # Crea la cadena RetrievalQA, que orquesta la recuperación y la generación
        qa_chain = RetrievalQA.from_chain_type(
            llm=structured_llm,
            chain_type="stuff", # Método para combinar los documentos recuperados en el prompt
            retriever=final_retriever,
            return_source_documents=True, # Importante para obtener la evidencia
            chain_type_kwargs={"prompt": prompt} # Pasa el prompt personalizado
        )
        logger.info("--- Cadena RetrievalQA creada exitosamente ---")
        return qa_chain
    except Exception as e:
        logger.error(f"Error al crear la cadena RetrievalQA: {e}", exc_info=True)
        return None

if __name__ == '__main__':
    # Bloque para probar el módulo directamente
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger.info("Módulo rag_components.py cargado.")

