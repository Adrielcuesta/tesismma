# scripts/dashboard_generator.py
import json
import os

def generar_dashboard_html(ruta_json_resultados, ruta_output_dashboard_html, lista_pdfs_base_conocimiento):
    """
    Genera un dashboard HTML a partir de los resultados del análisis de riesgos.

    Args:
        ruta_json_resultados (str): Ruta al archivo JSON con los resultados del análisis.
        ruta_output_dashboard_html (str): Ruta donde se guardará el archivo HTML del dashboard.
        lista_pdfs_base_conocimiento (list): Lista de strings con los nombres de los PDFs de la base de conocimiento.
    """
    try:
        with open(ruta_json_resultados, 'r', encoding='utf-8') as f:
            datos_analisis = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo JSON de resultados en {ruta_json_resultados}")
        return
    except json.JSONDecodeError:
        print(f"Error: No se pudo decodificar el archivo JSON en {ruta_json_resultados}")
        return

    nombre_proyecto_analizado = datos_analisis.get("nombre_proyecto_analizado", "No especificado")
    riesgos_estructurados = datos_analisis.get("riesgos_identificados_estructurados", [])

    # Mapeo de colores para los bordes de las tarjetas
    color_map = {
        "Rojo": "red",
        "Ámbar": "orange", # O "gold" o "yellow"
        "Verde": "green",
        "Gris (Indeterminado)": "grey"
    }

    # Inicio del HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análisis de Riesgos del Proyecto: {nombre_proyecto_analizado}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f4f7f6;
            color: #333;
        }}
        .header-container {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header-container h1 {{
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        .header-container h2 {{
            color: #555;
            font-weight: normal;
            font-size: 1.2em;
            margin-top: 0;
        }}
        .dashboard-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .risk-card {{
            background-color: #ffffff;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            border-left-width: 5px;
            border-left-style: solid;
        }}
        .risk-card h3 {{
            margin-top: 0;
            color: #34495e;
            font-size: 1.1em;
        }}
        .risk-card p {{
            font-size: 0.9em;
            line-height: 1.6;
            margin-bottom: 10px;
        }}
        .risk-card .details {{
            font-weight: bold;
            color: #7f8c8d;
        }}
        .footer-info {{
            margin-top: 40px;
            padding: 20px;
            background-color: #e9ecef;
            border-radius: 8px;
            text-align: center;
        }}
        .footer-info h3 {{
            color: #495057;
            margin-bottom: 15px;
        }}
        .footer-info ul {{
            list-style-type: none;
            padding: 0;
        }}
        .footer-info li {{
            display: inline-block;
            margin: 0 10px;
            padding: 5px 10px;
            background-color: #ffffff;
            border-radius: 4px;
            font-size: 0.9em;
            color: #007bff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        /* Clases de colores para bordes */
        {'.border-rojo { border-left-color: red; }'}
        {'.border-ambar { border-left-color: orange; }'}
        {'.border-verde { border-left-color: green; }'}
        {'.border-gris { border-left-color: grey; }'}
    </style>
</head>
<body>
    <div class="header-container">
        <h1>Análisis de Riesgos del Proyecto</h1>
        <h2>Proyecto: {nombre_proyecto_analizado}</h2>
    </div>

    <div class="dashboard-container">
"""

    # Generar tarjetas de riesgo
    if riesgos_estructurados:
        for riesgo in riesgos_estructurados:
            descripcion = riesgo.get("descripcion_riesgo", "N/A")
            explicacion = riesgo.get("explicacion_riesgo_llm", "N/A")
            impacto = riesgo.get("impacto_estimado_llm", "N/A")
            probabilidad = riesgo.get("probabilidad_estimada_llm", "N/A")
            estado_rag = riesgo.get("estado_RAG_sugerido", "Gris (Indeterminado)")
            
            color_clase = "border-" + color_map.get(estado_rag, "gris").lower()

            html_content += f"""
        <div class="risk-card {color_clase}">
            <h3>{descripcion}</h3>
            <p>{explicacion}</p>
            <p><span class="details">Impacto:</span> {impacto} | <span class="details">Probabilidad:</span> {probabilidad}</p>
        </div>
"""
    else:
        html_content += "<p>No se identificaron riesgos estructurados en este análisis.</p>"

    html_content += """
    </div>
"""

    # Añadir información de la base de conocimiento
    if lista_pdfs_base_conocimiento:
        html_content += """
    <div class="footer-info">
        <h3>Documentos de la Base de Conocimiento</h3>
        <ul>
"""
        for pdf_name in lista_pdfs_base_conocimiento:
            html_content += f"            <li>{pdf_name}</li>\n"
        html_content += """
        </ul>
    </div>
"""
    else:
        html_content += """
    <div class="footer-info">
        <h3>Documentos de la Base de Conocimiento</h3>
        <p>No se especificaron documentos de la base de conocimiento.</p>
    </div>
"""

    # Fin del HTML
    html_content += """
</body>
</html>
"""

    # Guardar el archivo HTML
    try:
        with open(ruta_output_dashboard_html, 'w', encoding='utf-8') as f_html:
            f_html.write(html_content)
        print(f"Dashboard HTML generado exitosamente en: {ruta_output_dashboard_html}")
    except IOError as e:
        print(f"Error al guardar el dashboard HTML en {ruta_output_dashboard_html}: {e}")

if __name__ == '__main__':
    # Ejemplo de uso para prueba (requiere un archivo JSON de ejemplo)
    # print("Probando generación de dashboard...")
    # dummy_json_path = "D:/tesismma/datos/Resultados/analisis_riesgos_Proyecto_a_analizar_v1_20250529_190000.json" # Reemplazar con un JSON real
    # dummy_html_path = "D:/tesismma/datos/Resultados/analisis_riesgos_Proyecto_a_analizar_v1_20250529_190000_dashboard.html"
    # dummy_bc_pdfs = ["Manual_Seguridad_General.pdf", "PMBOK_Guia_Riesgos.pdf", "Lecciones_Aprendidas_Instalaciones.pdf"]
    
    # Crear un JSON dummy si no existe para probar
    # if not os.path.exists(dummy_json_path):
    #     dummy_data = {
    #         "nombre_proyecto_analizado": "Proyecto Ejemplo V1.0",
    #         "riesgos_identificados_estructurados": [
    #             {"descripcion_riesgo": "Falla eléctrica principal", "explicacion_riesgo_llm": "Debido a sobrecarga.", "impacto_estimado_llm": "Alto", "probabilidad_estimada_llm": "Media", "estado_RAG_sugerido": "Rojo"},
    #             {"descripcion_riesgo": "Retraso en proveedor clave", "explicacion_riesgo_llm": "Capacidad limitada del proveedor.", "impacto_estimado_llm": "Medio", "probabilidad_estimada_llm": "Media", "estado_RAG_sugerido": "Ámbar"},
    #             {"descripcion_riesgo": "Error menor en documentación", "explicacion_riesgo_llm": "Se detecta en revisión.", "impacto_estimado_llm": "Bajo", "probabilidad_estimada_llm": "Baja", "estado_RAG_sugerido": "Verde"}
    #         ]
    #     }
    #     with open(dummy_json_path, 'w', encoding='utf-8') as f_dummy:
    #         json.dump(dummy_data, f_dummy, indent=4)
    #     print(f"JSON de prueba creado en {dummy_json_path}")

    # generar_dashboard_html(dummy_json_path, dummy_html_path, dummy_bc_pdfs)
    print("Módulo dashboard_generator.py cargado. Contiene funciones para generar el dashboard HTML.")

