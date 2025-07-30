# scripts/rag_components.py
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
import logging
import os

from .schemas import LLMResponse
from . import config

logger = logging.getLogger(__name__)

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
4.  Cada objeto de la lista representa un riesgo y debe contener EXACTAMENTE los siguientes 7 campos:
    a. "descripcion_riesgo": Una descripción clara y concisa del riesgo.
    b. "tipo_de_riesgo": Clasificación del riesgo. Opciones válidas: "Explícito" (si el contexto lo menciona directamente) o "Implícito" (si se deduce lógicamente del contexto).
    c. "explicacion_riesgo": Una breve explicación de por qué es un riesgo, citando evidencia específica del "CONTEXTO PROPORCIONADO".
    d. "impacto_estimado": Opciones válidas: "Bajo", "Medio", "Alto".
    e. "probabilidad_estimada": Opciones válidas: "Baja", "Media", "Alta".
    f. "responsabilidad_mitigacion": El rol o departamento responsable de las tareas de mitigación preventivas (ej. "Ingeniería de Planta").
    g. "responsable_accidente": El rol o departamento que asumiría la responsabilidad si el riesgo se materializa (ej. "Jefe de Producción").
5.  Si, basándote estrictamente en el contexto, no se detecta ningún riesgo relevante, debes devolver una lista vacía para el campo `riesgos_identificados`. No inventes riesgos.

LA RESPUESTA DEBE SER UN OBJETO JSON VÁLIDO, SIGUIENDO ESTRICTAMENTE EL FORMATO DESCRITO.
EJEMPLO DE RESPUESTA JSON IDEAL:
{{
  "riesgos_identificados": [
    {{
      "descripcion_riesgo": "Vibraciones excesivas de la nueva prensa hidráulica podrían afectar la estructura del edificio.",
      "tipo_de_riesgo": "Implícito",
      "explicacion_riesgo": "El Contexto 2 menciona que equipos con más de 50 toneladas de fuerza de prensado, como el del proyecto, requieren un estudio de suelo y cimentación reforzada, lo cual no se especifica en la descripción del proyecto.",
      "impacto_estimado": "Alto",
      "probabilidad_estimada": "Media",
      "responsabilidad_mitigacion": "Ingeniería Civil y de Planta",
      "responsable_accidente": "Gerencia de Operaciones"
    }}
  ]
}}

Comienza tu respuesta JSON AHORA:
"""

def get_llm_instance(model_id: str):
    if model_id not in config.LLM_MODELS:
        logger.error(f"Modelo '{model_id}' no encontrado en config.LLM_MODELS.")
        raise ValueError(f"Modelo no soportado: {model_id}")

    model_config = config.LLM_MODELS[model_id]
    provider = model_config["provider"]
    api_key_env = model_config.get("api_key_env")
    api_key = os.getenv(api_key_env) if api_key_env else None

    logger.info(f"Intentando inicializar el modelo: '{model_id}' del proveedor: '{provider}'")

    if api_key_env and not api_key:
        logger.error(f"Clave API no encontrada. Asegúrese de que la variable de entorno '{api_key_env}' esté definida en su archivo .env.")
        raise ValueError(f"Clave API no encontrada para el modelo {model_id}")

    try:
        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model_id,
                google_api_key=api_key,
                temperature=0.2,
                convert_system_message_to_human=True
            )

        elif provider in ["openai", "openai_compatible"]:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model_id,
                api_key=api_key,
                base_url=model_config.get("base_url"),
                temperature=0.2
            )

        elif provider == "mistral":
            from langchain_mistralai import ChatMistralAI
            return ChatMistralAI(
                model=model_id,
                api_key=api_key,
                temperature=0.2
            )

        elif provider == "cohere":
            from langchain_cohere import ChatCohere
            return ChatCohere(
                model=model_id,
                cohere_api_key=api_key,
                temperature=0.2
            )

        else:
            logger.error(f"Proveedor '{provider}' no implementado.")
            return None

    except ImportError as e:
        logger.error(f"Error de importación para el proveedor '{provider}'. ¿Instalaste la librería requerida (ej. 'pip install langchain-mistralai')? Error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error al inicializar el modelo '{model_id}': {e}", exc_info=True)
        return None

def crear_cadena_rag(llm, vector_db_instance):
    if not llm or not vector_db_instance:
        logger.error("Instancia de LLM o Vector DB no proporcionada.")
        return None
    try:
        base_retriever = vector_db_instance.as_retriever(search_kwargs={"k": config.K_RETRIEVED_DOCS_BEFORE_RERANK})
        final_retriever = base_retriever

        if config.USE_RERANKER:
            logger.info("--- Habilitando Re-ranker (CrossEncoder) ---")
            try:
                model = HuggingFaceCrossEncoder(model_name='BAAI/bge-reranker-base')
                compressor = CrossEncoderReranker(model=model, top_n=config.RERANKER_TOP_N)
                final_retriever = ContextualCompressionRetriever(base_compressor=compressor, base_retriever=base_retriever)
                logger.info(f"--- Re-ranker configurado para devolver los mejores {config.RERANKER_TOP_N} fragmentos ---")
            except Exception as e_reranker:
                logger.error(f"No se pudo inicializar el Re-ranker. Se usará el retriever base. Error: {e_reranker}")

        prompt = PromptTemplate(template=PROMPT_TEMPLATE_STR, input_variables=["context", "question"])

  
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=final_retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt}
        )
        logger.info("--- Cadena RetrievalQA creada exitosamente ---")
        return qa_chain
    except Exception as e:
        logger.error(f"Error al crear la cadena RetrievalQA: {e}", exc_info=True)
        return None