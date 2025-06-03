# scripts/dashboard_generator.py
import json
import os
import logging
import traceback
import datetime
import base64

logger = logging.getLogger(__name__)
CURRENT_YEAR = datetime.datetime.now().year

def image_to_base64(image_filename_in_static_images):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    image_path = os.path.join(project_root, "static", "images", image_filename_in_static_images)
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        ext = image_filename_in_static_images.split('.')[-1].lower()
        mime_type_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "svg": "image/svg+xml", "gif": "image/gif"}
        mime_type = mime_type_map.get(ext, f"image/{ext}")
        if mime_type == f"image/{ext}" and ext not in mime_type_map: 
             logger.warning(f"Tipo de imagen desconocido para {image_filename_in_static_images}, usando fallback genérico {mime_type}.")
        return f"data:{mime_type};base64,{encoded_string}"
    except FileNotFoundError:
        logger.error(f"¡IMAGEN NO ENCONTRADA! Verifica esta ruta: {image_path}")
        return "" 
    except Exception as e:
        logger.error(f"Error codificando imagen {image_path} a Base64: {e}")
        return ""

def generar_dashboard_html(ruta_json_resultados, ruta_output_dashboard_html, lista_pdfs_base_conocimiento, info_tesis_config=None):
    try:
        with open(ruta_json_resultados, 'r', encoding='utf-8') as f:
            datos_analisis = json.load(f)
    except Exception as e: 
        logger.error(f"Error abriendo o parseando JSON en {ruta_json_resultados}: {e}")
        return

    nombre_proyecto_analizado = datos_analisis.get("nombre_proyecto_analizado", "Proyecto No Especificado")
    riesgos_identificados = datos_analisis.get("riesgos_identificados_estructurados", [])

    info_tesis_default = {
        "titulo_tesis_h1": "TESIS FIN DE MAESTRÍA",
        "titulo_tesis_h2": "Innovación en entornos empresariales",
        "titulo_tesis_h3": "Sistemas RAG para la Optimización de la Gestión de Proyectos y Análisis Estratégico.",
        "app_subtitle": "ANALIZADOR DE RIESGOS CON IA.",
        "alumno": "Adriel J. Cuesta",
        "institucion_line1": "ITBA - Instituto Tecnológico Buenos Aires",
        "institucion_line2": "Maestría en Management & Analytics",
        "github_repo_url": "https://github.com/Adrielcuesta/tesismma"
    }
    it = info_tesis_default.copy() 
    if isinstance(info_tesis_config, dict): it.update(info_tesis_config) 
    
    logger.info("Codificando imágenes a Base64 (TODAS COMO .PNG)...")
    header_banner_base64 = image_to_base64("header_banner_abstract.png") 
    logo_inline_base64 = image_to_base64("logo-itba.png")                
    logo_itba_footer_base64 = image_to_base64("itba.png")               
    if not header_banner_base64: logger.warning("BANNER ('header_banner_abstract.png') NO SE PUDO CODIFICAR.")
    else: logger.info("Banner ('header_banner_abstract.png') codificado OK.")
    if not logo_inline_base64: logger.warning("LOGO INLINE ('logo-itba.png') NO SE PUDO CODIFICAR.")
    else: logger.info("Logo inline ('logo-itba.png') codificado OK.")
    if not logo_itba_footer_base64: logger.warning("LOGO FOOTER ('itba.png') NO SE PUDO CODIFICAR.")
    else: logger.info("Logo footer ('itba.png') codificado OK.")

    # Emojis para títulos de categorías de riesgo
    risk_category_emojis = {
        "Rojo": "🔥",
        "Ámbar": "⚠️",
        "Verde": "🟢", # Cambiado a Círculo Verde
        "Gris (Indeterminado)": "❓"
    }
    # Títulos base para las categorías de riesgo
    base_estado_map_titles = {
        "Rojo": "Riesgos Altos",
        "Ámbar": "Riesgos Medios",
        "Verde": "Riesgos Bajos",
        "Gris (Indeterminado)": "Riesgos Indeterminados"
    }
    # Construir estado_map combinando clase y título base (el emoji se añade en el HTML)
    estado_map = {
        key: {"clase": value_data["clase"], "titulo": base_estado_map_titles[key]}
        for key, value_data in {
            "Rojo": {"clase": "rojo"}, "Ámbar": {"clase": "ambar"},
            "Verde": {"clase": "verde"}, "Gris (Indeterminado)": {"clase": "gris"}
        }.items()
    }

    riesgos_agrupados = { key: [] for key in estado_map }
    for riesgo in riesgos_identificados:
        estado = riesgo.get("estado_RAG_sugerido", "Gris (Indeterminado)")
        riesgos_agrupados.get(estado, riesgos_agrupados["Gris (Indeterminado)"]).append(riesgo)
    orden_secciones = ["Rojo", "Ámbar", "Verde", "Gris (Indeterminado)"]

    val_institucion_line1 = it.get('institucion_line1', '')
    val_institucion_line2 = it.get('institucion_line2', '')
    footer_institucion_text = f"{val_institucion_line1} - {val_institucion_line2}".strip(" - ")
    if not footer_institucion_text: footer_institucion_text = "Información institucional no disponible"
    
    github_url_val = str(it.get("github_repo_url", "#")) 
    footer_github_link_html = f'<a href="{github_url_val}" target="_blank">Ver Repositorio del Proyecto en GitHub</a>'
    
    val_alumno = it.get('alumno', '')
    footer_copyright_text = f"&copy; {CURRENT_YEAR} {val_alumno}. Todos los derechos reservados."
    if not val_alumno: footer_copyright_text = f"&copy; {CURRENT_YEAR}. Todos los derechos reservados."
    
    html_parts = []
    html_parts.append(f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Análisis de Riesgos: {nombre_proyecto_analizado}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f0f2f5; color: #333; display: flex; flex-direction: column; align-items: center; }}
        .page-wrapper {{ width: 100%; display: flex; flex-direction: column; align-items: center; padding: 20px; box-sizing: border-box;}}
        .main-dashboard-container {{ background-color: #ffffff; padding: 30px 40px; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.1); width: 100%; max-width: 1000px; text-align: left; margin-bottom: 30px; }}
        .abstract-banner-container {{ width: 100%; height: 100px; margin-bottom: 25px; background-image: url("{header_banner_base64}"); background-size: cover; background-position: center; border-radius: 6px; background-color: #f0f0f0; }}
        .header-content {{ text-align: center; margin-bottom: 30px; }}
        .title-with-logo {{ display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 8px; }}
        .title-with-logo img.logo-inline {{ height: 37px; width: auto; }}
        .header-content h1 {{ color: #1a2533; font-size: 1.7em; margin: 0; font-weight: 600; }}
        .header-content h2 {{ color: #2c3e50; font-size: 1.3em; margin-top: 8px; margin-bottom: 5px; font-weight: 500; }}
        .header-content h3 {{ color: #4a5568; font-size: 1.1em; margin-bottom: 10px; font-weight: 400; }}
        .header-content h4.app-subtitle {{ color: #555; font-size: 1.0em; font-weight: bold; font-style: italic; margin-top: 2px; margin-bottom: 15px; }}
        .header-content p.student-name {{ color: #333; font-size: 1.1em; font-weight: bold; margin-top: 15px; margin-bottom: 20px; }}
        .section-title-emoji {{ margin-right: 8px; font-size: 1em; }} 
        .project-analysis-title {{ text-align: center; font-size: 1.5em; color: #1a2533; margin-top: 0; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 2px solid #e0e0e0;}}
        .risk-section {{ margin-bottom: 30px; }}
        .risk-section > h5 {{ font-size: 1.4em; color: #2c3e50; border-bottom: 1px solid #e0e0e0; padding-bottom: 10px; margin-bottom: 20px; }}
        .dashboard-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }}
        .risk-card {{ background-color: #fdfdfd; border: 1px solid #e9ecef; border-radius: 8px; padding: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out; border-top-width: 5px; border-top-style: solid; display: flex; flex-direction: column; }}
        .risk-card:hover {{ transform: translateY(-4px); box-shadow: 0 5px 15px rgba(0,0,0,0.08); }}
        .risk-card h6 {{ margin-top: 0; color: #34495e; font-size: 1.0em; margin-bottom: 8px; flex-grow: 1; }}
        .risk-card .risk-summary-details p {{ font-size: 0.8em; line-height: 1.4; margin-bottom: 4px; }}
        .risk-card .details-label {{ font-weight: 600; color: #555; }}
        .risk-card .details-value {{ color: #222; font-weight: 500; }}
        .risk-card.rojo {{ border-top-color: #e74c3c; }} .risk-card.ambar {{ border-top-color: #f39c12; }}
        .risk-card.verde {{ border-top-color: #2ecc71; }} .risk-card.gris {{ border-top-color: #95a5a6; }}
        .details-section {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; }}
        .details-section > h2 {{ text-align: center; font-size: 1.3em; color: #1a2533; margin-bottom: 20px; }}
        .risk-detail-item {{ margin-bottom: 20px; padding-bottom:15px; border-bottom: 1px dashed #ccc; }}
        .risk-detail-item:last-child {{ border-bottom: none; }}
        .risk-detail-item h4 {{ font-size: 1.0em; color: #34495e; margin-top:0; margin-bottom: 6px;}}
        .risk-detail-item p {{ font-size: 0.85em; line-height: 1.5; margin-bottom: 4px; }}
        .risk-detail-item .detail-label {{ font-weight: bold; color: #555; }}
        .kb-document-list-section {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0;}}
        .kb-document-list-section h5 {{ font-size: 1.1em; color: #2c3e50; margin-bottom: 10px; text-align: left; }}
        .kb-document-list-section ul {{ list-style-type: disc; padding-left: 20px; margin: 0; text-align: left;}}
        .kb-document-list-section li {{ font-size: 0.85em; color: #333; margin-bottom: 4px; }}
        .dashboard-page-footer {{ width: 100%; text-align: center; padding: 25px 20px; font-size: 0.9em; color: #6c757d; margin-top: 30px; border-top: 1px solid #d0d0d0; background-color: #f0f2f5; box-sizing: border-box;}}
        .dashboard-page-footer p {{ margin: 5px 0; }}
        .dashboard-page-footer img.logo-itba-footer {{ max-height: 45px; margin-bottom: 10px; opacity: 0.9; }}
        .dashboard-page-footer a {{ color: #007bff; text-decoration: none; }}
        .dashboard-page-footer a:hover {{ text-decoration: underline; }}
        @media (max-width: 768px) {{
            .main-dashboard-container {{ padding: 20px; }} .header-content h1 {{ font-size: 1.5em; }}
            .title-with-logo img.logo-inline {{ height: 28px; }} .abstract-banner-container {{ height: 70px; }}
            .dashboard-grid {{ grid-template-columns: 1fr; }} .kb-document-list-section ul {{ padding-left: 15px; }}
            .details-section > h2 {{ font-size: 1.2em; }} .risk-detail-item h4 {{ font-size: 0.95em; }}
            .risk-detail-item p {{ font-size: 0.8em; }}
        }}
    </style>
</head>
<body>
<div class="page-wrapper">
    <div class="main-dashboard-container">
        <div class="abstract-banner-container"></div> 
        <div class="header-content">
            <div class="title-with-logo">
                <img src="{logo_inline_base64}" alt="Logo RAG" class="logo-inline">
                <h1>{it.get("titulo_tesis_h1")}</h1>
            </div>
            <h2>{it.get("titulo_tesis_h2")}</h2>
            <h3>{it.get("titulo_tesis_h3")}</h3>
            <h4 class="app-subtitle">{it.get("app_subtitle")}</h4>
            <p class="student-name">Alumno: {it.get("alumno")}</p>
        </div>

        <h2 class="project-analysis-title">Resultados del Análisis de Riesgos para: {nombre_proyecto_analizado}</h2>
    """)

    for estado_key in orden_secciones:
        riesgos_en_seccion = riesgos_agrupados[estado_key]
        info_estado = estado_map[estado_key] 
        emoji_actual = risk_category_emojis.get(estado_key, '')
        if riesgos_en_seccion:
            html_parts.append(f"""
        <div class="risk-section">
            <h5><span class="section-title-emoji">{emoji_actual}</span>{info_estado['titulo']}</h5>
            <div class="dashboard-grid">
            """)
            for riesgo in riesgos_en_seccion:
                descripcion = riesgo.get("descripcion_riesgo", "N/A")
                impacto = riesgo.get("impacto_estimado_llm", "N/A")
                probabilidad = riesgo.get("probabilidad_estimada_llm", "N/A")
                clase_color_tarjeta = info_estado['clase']
                html_parts.append(f"""
                <div class="risk-card {clase_color_tarjeta}">
                    <h6>{descripcion}</h6>
                    <div class="risk-summary-details">
                        <p><span class="details-label">Impacto:</span> <span class="details-value">{impacto}</span></p>
                        <p><span class="details-label">Probabilidad:</span> <span class="details-value">{probabilidad}</span></p>
                    </div>
                </div>
                """)
            html_parts.append("""
            </div> 
        </div> 
            """)
    if not any(riesgos_agrupados.values()):
         html_parts.append("<p style='text-align:center; font-style:italic; margin: 30px 0;'>No se identificaron riesgos en este análisis.</p>")

    if riesgos_identificados: 
        html_parts.append(f"""
        <div class="details-section">
            <h2>Detalles de Riesgos Identificados</h2>
        """)
        for riesgo_idx, riesgo in enumerate(riesgos_identificados):
            descripcion = riesgo.get("descripcion_riesgo", "N/A")
            explicacion = riesgo.get("explicacion_riesgo_llm", "N/A")
            impacto = riesgo.get("impacto_estimado_llm", "N/A")
            probabilidad = riesgo.get("probabilidad_estimada_llm", "N/A")
            estado_rag = riesgo.get("estado_RAG_sugerido", "Gris (Indeterminado)")
            html_parts.append(f"""
            <div class="risk-detail-item">
                <h4><span class="section-title-emoji">ℹ️</span>{descripcion}</h4>
                <p><span class="detail-label">Explicación Detallada:</span> {explicacion}</p>
                <p><span class="detail-label">Impacto Estimado:</span> {impacto}</p>
                <p><span class="detail-label">Probabilidad Estimada:</span> {probabilidad}</p>
                <p><span class="detail-label">Nivel de Riesgo (RAG Sugerido):</span> {estado_rag}</p>
            </div>
            """)
        html_parts.append("</div>")
    
    if lista_pdfs_base_conocimiento:
        html_parts.append(f"""
        <div class="kb-document-list-section">
            <h5><span class="section-title-emoji">📚</span>Documentos de la Base de Conocimiento Utilizada</h5>
            <ul>
        """)
        for pdf_name in lista_pdfs_base_conocimiento:
            html_parts.append(f"            <li>{pdf_name}</li>\n")
        html_parts.append("""
            </ul>
        </div>
        """)
    
    html_parts.append(f"""
    </div> <div class="dashboard-page-footer">
        <img src="{logo_itba_footer_base64}" alt="Logo ITBA" class="logo-itba-footer">
        <p>{footer_institucion_text}</p>
        <p>{footer_github_link_html}</p> 
        <p>{footer_copyright_text}</p>
    </div>
</div> </body>
</html>
    """)
    
    final_html_content = "".join(html_parts)

    try:
        os.makedirs(os.path.dirname(ruta_output_dashboard_html), exist_ok=True)
        with open(ruta_output_dashboard_html, 'w', encoding='utf-8') as f_html:
            f_html.write(final_html_content)
        logger.info(f"Dashboard HTML (v14_final_emoji_fix) generado en: {ruta_output_dashboard_html}")
    except IOError as e:
        logger.error(f"Error al guardar el dashboard HTML en {ruta_output_dashboard_html}: {e}")
        logger.debug(traceback.format_exc())

if __name__ == '__main__':
    if not logging.getLogger().handlers: 
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    logger.info("Ejecutando dashboard_generator.py directamente para prueba (v14_final_emoji_fix)...")
    
    project_root_for_test = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    test_output_dir = os.path.join(project_root_for_test, "test_dashboard_output")
    os.makedirs(test_output_dir, exist_ok=True)
        
    dummy_json_path = os.path.join(test_output_dir, "dummy_analisis_resultados.json")
    dummy_dashboard_path = os.path.join(test_output_dir, "dummy_dashboard_output_v14_final_emojis.html")
    dummy_kb_docs = ["KB_Final_1.pdf", "KB_Final_2.pdf"]
    
    test_info_tesis = {
        "titulo_tesis_h1": "TESIS (v14 Emojis)",
        "titulo_tesis_h2": "Innovación (v14 Emojis)",
        "titulo_tesis_h3": "Sistemas RAG (v14 Emojis)",
        "app_subtitle": "ANALIZADOR IA (v14 Emojis)",
        "alumno": "Adriel J. Cuesta (v14 Emojis)",
        "institucion_line1": "ITBA (v14 Emojis)",
        "institucion_line2": "Maestría M&A (v14 Emojis)",
        "github_repo_url": "https://github.com/Adrielcuesta/tesismma" 
    }

    dummy_data = {
        "nombre_proyecto_analizado": "Proyecto Final Emojis - Test v14",
        "riesgos_identificados_estructurados": [
            {"descripcion_riesgo": "Riesgo Alto con Emoji OK","explicacion_riesgo_llm": "Explicación detallada.","impacto_estimado_llm": "Alto","probabilidad_estimada_llm": "Alta","estado_RAG_sugerido": "Rojo"},
            {"descripcion_riesgo": "Riesgo Medio con Emoji OK","explicacion_riesgo_llm": "Explicación detallada.","impacto_estimado_llm": "Medio","probabilidad_estimada_llm": "Media","estado_RAG_sugerido": "Ámbar"},
            {"descripcion_riesgo": "Riesgo Bajo con Emoji OK","explicacion_riesgo_llm": "Explicación detallada.","impacto_estimado_llm": "Bajo","probabilidad_estimada_llm": "Baja","estado_RAG_sugerido": "Verde"},
            {"descripcion_riesgo": "Riesgo Indeterminado con Emoji OK","explicacion_riesgo_llm": "Explicación detallada.","impacto_estimado_llm": "Desconocido","probabilidad_estimada_llm": "Desconocida","estado_RAG_sugerido": "Gris (Indeterminado)"},
        ]
    }
    with open(dummy_json_path, 'w', encoding='utf-8') as f_dummy:
        json.dump(dummy_data, f_dummy, ensure_ascii=False, indent=4)
    
    logger.info(f"Archivo JSON de prueba creado: {dummy_json_path}")
    generar_dashboard_html(dummy_json_path, dummy_dashboard_path, dummy_kb_docs, test_info_tesis)
    logger.info(f"Prueba completada. Revisa '{os.path.abspath(dummy_dashboard_path)}'.")