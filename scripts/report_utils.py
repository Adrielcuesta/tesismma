# scripts/report_utils.py
import json
import os
from datetime import datetime
import logging
import traceback

logger = logging.getLogger(__name__)

def intentar_parsear_json_riesgos(texto_llm_str):
    if not isinstance(texto_llm_str, str):
        logger.error("Error de parseo: la entrada para `intentar_parsear_json_riesgos` no es un string.")
        return None
    
    cleaned_text = texto_llm_str.strip()
    
    if cleaned_text.startswith("```json") and cleaned_text.endswith("```"):
        json_candidate_str = cleaned_text[len("```json"):-len("```")].strip()
    elif cleaned_text.startswith("```") and cleaned_text.endswith("```"):
        json_candidate_str = cleaned_text[len("```"):-len("```")].strip()
    else:
        json_candidate_str = cleaned_text

    if not (json_candidate_str.startswith("{") and json_candidate_str.endswith("}")):
        first_brace = json_candidate_str.find('{')
        last_brace = json_candidate_str.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_candidate_str = json_candidate_str[first_brace : last_brace + 1]
        else:
            logger.warning("Advertencia de parseo: No se encontró una estructura JSON clara ({...}) en la respuesta del LLM.")
            return None
            
    try:
        parsed_json = json.loads(json_candidate_str)
        return parsed_json
    except json.JSONDecodeError as e:
        logger.error(f"Error de parseo JSON: {e}")
        logger.debug(f"Texto que intentó parsearse (después de limpieza): '{json_candidate_str[:500]}...'")
        return None
    except Exception as e_gen:
        logger.error(f"Error de parseo inesperado: {e_gen}")
        logger.debug(traceback.format_exc())
        return None

def asignar_estado_rag(impacto_str, probabilidad_str):
    impacto = impacto_str.lower().strip() if isinstance(impacto_str, str) else "desconocido"
    probabilidad = probabilidad_str.lower().strip() if isinstance(probabilidad_str, str) else "desconocido"
    if impacto == "alto":
        if probabilidad in ["media", "alta"]: return "Rojo"
        else: return "Ámbar"
    elif impacto == "medio":
        if probabilidad == "alta": return "Rojo"
        elif probabilidad == "media": return "Ámbar"
        else: return "Verde"
    elif impacto == "bajo":
        if probabilidad == "alta": return "Ámbar"
        else: return "Verde"
    return "Gris (Indeterminado)"

def formatear_y_guardar_reporte(resultado_analisis_llm, fuentes_recuperadas, 
                                nombre_pdf_proyecto, modelo_llm_usado, output_path_dir):
    logger.info("Procesando salida del LLM para formato estructurado (JSON)...")
    
    reporte_final = {
        "timestamp_analisis": datetime.now().isoformat(),
        "nombre_proyecto_analizado": nombre_pdf_proyecto,
        "modelo_llm_usado": modelo_llm_usado,
        "respuesta_cruda_llm": resultado_analisis_llm if isinstance(resultado_analisis_llm, str) else str(resultado_analisis_llm),
        "riesgos_identificados_estructurados": [],
        "fuentes_contexto_recuperadas": fuentes_recuperadas if fuentes_recuperadas else []
    }

    if isinstance(resultado_analisis_llm, str):
        json_output_llm = intentar_parsear_json_riesgos(resultado_analisis_llm)
        if json_output_llm and "riesgos_identificados" in json_output_llm and \
           isinstance(json_output_llm["riesgos_identificados"], list):
            logger.info("JSON de riesgos parseado exitosamente desde la respuesta del LLM.")
            for riesgo_item_llm in json_output_llm["riesgos_identificados"]:
                if isinstance(riesgo_item_llm, dict):
                    descripcion = riesgo_item_llm.get("descripcion_riesgo", "Descripción no proporcionada")
                    explicacion = riesgo_item_llm.get("explicacion_riesgo", "Explicación no proporcionada")
                    impacto = riesgo_item_llm.get("impacto_estimado", "Desconocido")
                    probabilidad = riesgo_item_llm.get("probabilidad_estimada", "Desconocido")
                    estado_rag = asignar_estado_rag(impacto, probabilidad)
                    reporte_final["riesgos_identificados_estructurados"].append({
                        "descripcion_riesgo": descripcion,
                        "explicacion_riesgo_llm": explicacion,
                        "impacto_estimado_llm": impacto,
                        "probabilidad_estimada_llm": probabilidad,
                        "estado_RAG_sugerido": estado_rag
                    })
                else:
                    logger.warning(f"Item de riesgo no es un diccionario: {riesgo_item_llm}")
                    reporte_final["riesgos_identificados_estructurados"].append(
                         {"error_parseo_item_riesgo": "Item no es un diccionario válido", "contenido_item": str(riesgo_item_llm)}
                     )
            if not reporte_final["riesgos_identificados_estructurados"] and json_output_llm.get("riesgos_identificados"): # Check if key exists
                 logger.warning("La lista 'riesgos_identificados' del LLM contenía elementos, pero no se pudieron procesar como diccionarios válidos.")
            elif not json_output_llm.get("riesgos_identificados"): # Check if key exists
                 logger.info("La lista 'riesgos_identificados' del LLM estaba vacía.")
        else:
            logger.warning("No se pudo parsear un JSON estructurado de riesgos desde la respuesta del LLM.")
    else:
        logger.warning("El resultado del análisis no es un string, no se intentará parseo JSON.")

    timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_project_name = "".join(c if c.isalnum() else "_" for c in nombre_pdf_proyecto.replace('.pdf',''))
    # Usar el nombre base del proyecto para el JSON, consistente con dashboard
    output_filename_json = f"analisis_riesgos_{clean_project_name}.json" # Quitamos timestamp para sobreescribir si se re-analiza
    output_file_path_json = os.path.join(output_path_dir, output_filename_json)

    try:
        with open(output_file_path_json, 'w', encoding='utf-8') as f:
            json.dump(reporte_final, f, ensure_ascii=False, indent=4)
        logger.info(f"Reporte JSON guardado en: {output_file_path_json}")
        return output_file_path_json
    except Exception as e_save:
        logger.error(f"Error crítico al guardar el archivo JSON de resultados: {e_save}")
        logger.debug(traceback.format_exc())
        return None

if __name__ == '__main__':
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger.info("Módulo report_utils.py cargado.")