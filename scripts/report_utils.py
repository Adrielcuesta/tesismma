# scripts/report_utils.py
import json
import os
from datetime import datetime
import logging
import traceback
from typing import Optional

from .schemas import RiskReport

logger = logging.getLogger(__name__)

def asignar_estado_rag(impacto_str: str, probabilidad_str: str) -> str:
    """Asigna un estado RAG (Rojo, Ámbar, Verde) basado en el impacto y la probabilidad."""
    impacto = impacto_str.lower().strip()
    probabilidad = probabilidad_str.lower().strip()
    if impacto == "alto":
        return "Rojo" if probabilidad in ["media", "alta"] else "Ámbar"
    elif impacto == "medio":
        return "Rojo" if probabilidad == "alta" else ("Ámbar" if probabilidad == "media" else "Verde")
    elif impacto == "bajo":
        return "Ámbar" if probabilidad == "alta" else "Verde"
    return "Gris (Indeterminado)"

def formatear_y_guardar_reporte(
    risk_report_obj: RiskReport,
    fuentes_recuperadas_serializables: list,
    nombre_original_pdf: str,
    output_path_dir: str
) -> Optional[str]:
    """Toma el objeto RiskReport validado, le añade metadatos finales y lo guarda como JSON."""
    logger.info("Procesando objeto RiskReport para guardado final (JSON)...")

    # 1. Añadir los estados RAG a cada riesgo.
    riesgos_con_estado = []
    for riesgo_item in risk_report_obj.riesgos_identificados:
        estado_rag = asignar_estado_rag(riesgo_item.impacto_estimado, riesgo_item.probabilidad_estimada)
        riesgo_dict = riesgo_item.model_dump()
        riesgo_dict["estado_RAG_sugerido"] = estado_rag
        riesgos_con_estado.append(riesgo_dict)

    # 2. Convertimos el objeto a diccionario para poder modificarlo
    reporte_final_dict = risk_report_obj.model_dump()
    reporte_final_dict["riesgos_identificados_estructurados"] = riesgos_con_estado
    del reporte_final_dict["riesgos_identificados"]

    # 3. Añadir y limpiar metadatos finales
    reporte_final_dict["timestamp_analisis"] = datetime.now().isoformat()
    # ACTUALIZADO: Limpiamos el nombre del proyecto para una mejor visualización
    display_name = nombre_original_pdf.replace('.pdf', '').replace('_', ' ').strip()
    reporte_final_dict["nombre_proyecto_analizado"] = display_name
    reporte_final_dict["nombre_archivo_original"] = nombre_original_pdf

    reporte_final_dict["fragmentos_fuente"] = fuentes_recuperadas_serializables

    # Nombre del archivo JSON (usando el nombre original para la ruta)
    clean_filename = "".join(c if c.isalnum() else "_" for c in os.path.splitext(nombre_original_pdf)[0])
    output_filename_json = f"analisis_riesgos_{clean_filename}.json"
    output_file_path_json = os.path.join(output_path_dir, output_filename_json)

    try:
        with open(output_file_path_json, 'w', encoding='utf-8') as f:
            json.dump(reporte_final_dict, f, ensure_ascii=False, indent=4)
        logger.info(f"Reporte JSON guardado en: {output_file_path_json}")
        return output_file_path_json
    except Exception as e_save:
        logger.error(f"Error crítico al guardar el archivo JSON de resultados: {e_save}")
        logger.debug(traceback.format_exc())
        return None
