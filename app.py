# D:\tesismma\app.py
import os
import sys
import logging
import traceback # Para un logging de errores más detallado
from flask import Flask, render_template_string, send_file, url_for, redirect, flash, request

# --- Configuración de Rutas para Importar Módulos del Proyecto ---
# Añade la raíz del proyecto al sys.path para que Flask pueda encontrar el paquete 'scripts'
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Importar la función de análisis y configuración ---
try:
    from scripts.main import run_analysis
    from scripts import config # Para acceder a PROJECT_INFO y otras configs si es necesario
except ImportError as e:
    # Este error es crítico si los módulos no se pueden importar.
    # Configurar un logger básico aquí por si la importación falla antes de configurar el de Flask.
    logging.basicConfig(level=logging.ERROR)
    logging.error(f"Error crítico al importar módulos necesarios (main, config): {e}")
    logging.error(f"Asegúrate de que app.py esté en la raíz del proyecto ('{PROJECT_ROOT}') y que la carpeta 'scripts' exista allí.")
    # Si la importación falla, definimos run_analysis como None para manejarlo en las rutas.
    run_analysis = None
    config = None 
# --- Fin Importaciones ---

# --- Creación de la Aplicación Flask ---
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24)) # Clave secreta para mensajes flash

# --- Configuración del Logging de Flask ---
# Usar el logger de Flask para mensajes de la aplicación web.
# El logger de main.py se encargará de sus propios mensajes de proceso.
if not app.debug: # No configurar si app.debug es True, ya que Flask lo maneja
    # En un entorno de producción (como Cloud Run), querremos un logging más formal.
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers.extend(gunicorn_logger.handlers)
    app.logger.setLevel(logging.INFO) # O logging.DEBUG si se necesita más detalle
else:
    # Para desarrollo local con app.run(debug=True), Flask configura su propio logger.
    # Podemos asegurarnos de que el nivel sea INFO o DEBUG.
    app.logger.setLevel(logging.INFO)
# --- Fin Configuración Logging Flask ---


# --- Información del Proyecto para la Plantilla ---
# Leemos desde config.py si está disponible y tiene INFO_TESIS
if config and hasattr(config, 'INFO_TESIS'):
    PROJECT_INFO = config.INFO_TESIS
else: # Fallback si config o INFO_TESIS no están disponibles
    PROJECT_INFO = {
        "titulo_tesis": "Sistema RAG para Análisis de Riesgos (Título por Defecto)",
        "institucion_line1": "ITBA (Info por Defecto)",
        "institucion_line2": "Maestría (Info por Defecto)",
        "alumno": "Adriel Cuesta (Info por Defecto)",
        "github_repo_url": "https://github.com/Adrielcuesta/tesismma", # Puedes hardcodear esto o ponerlo en config.py
        "project_title": "Análisis de Riesgos en Instalación de Maquinaria Industrial" # Título general de la app
    }
# --- Fin Información del Proyecto ---

# --- Plantilla HTML para la Página de Inicio ---
# (Movida a un archivo separado sería más limpio para HTML más complejos)
HOME_PAGE_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ project_info.get('project_title', 'Análisis de Riesgos') }}</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; display: flex; flex-direction: column; align-items: center; min-height: 95vh; }
        .container { background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 100%; max-width: 800px; text-align: center; margin-bottom: auto; }
        h1 { color: #1a2533; margin-bottom: 10px; font-size: 2em; }
        h2 { color: #4a5568; font-weight: 400; font-size: 1.2em; margin-top: 0; margin-bottom: 20px; }
        p { line-height: 1.6; margin-bottom: 15px; }
        .button {
            display: inline-block; background-color: #007bff; color: white; padding: 12px 25px;
            border: none; border-radius: 5px; cursor: pointer; font-size: 18px;
            text-decoration: none; transition: background-color 0.3s ease;
        }
        .button:hover { background-color: #0056b3; }
        .button-disabled { background-color: #cccccc; cursor: not-allowed; }
        .loader {
            border: 5px solid #f3f3f3; border-top: 5px solid #3498db;
            border-radius: 50%; width: 40px; height: 40px;
            animation: spin 1s linear infinite; margin: 30px auto 0 auto; display: none; /* Oculto por defecto */
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .flash-messages { list-style-type: none; padding: 0; margin-bottom: 20px; }
        .flash-messages li { padding: 10px; margin-bottom: 10px; border-radius: 4px; }
        .flash-messages .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .flash-messages .info { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .footer { width: 100%; text-align: center; padding: 20px 0; font-size: 0.9em; color: #777; margin-top:30px;}
        .footer p { margin: 5px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ project_info.get('project_title', 'Análisis de Riesgos con RAG') }}</h1>
        <h2>{{ project_info.get('titulo_tesis', 'Trabajo Final de Maestría') }}</h2>
        <p><strong>Estudiante:</strong> {{ project_info.get('alumno', 'Adriel Cuesta') }}</p>
        <p>Este sistema utiliza Generación Aumentada por Recuperación (RAG) para analizar riesgos en la instalación de maquinaria industrial.</p>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <ul class="flash-messages">
                {% for category, message in messages %}
                    <li class="{{ category }}">{{ message }}</li>
                {% endfor %}
                </ul>
            {% endif %}
        {% endwith %}

        <form id="analysisForm" action="{{ url_for('analyze_project_route') }}" method="post">
            <button type="submit" id="analyzeButton" class="button">Iniciar Análisis del Proyecto Configurado</button>
        </form>
        <div id="loader" class="loader"></div>
    </div>

    <div class="footer">
        <p>{{ project_info.get('institucion_line1', 'ITBA') }} - {{ project_info.get('institucion_line2', 'Maestría') }}</p>
        <p><a href="{{ project_info.get('github_repo_url', '#') }}" target="_blank">Ver Repositorio en GitHub</a></p>
    </div>

    <script>
        document.getElementById('analysisForm').addEventListener('submit', function() {
            document.getElementById('loader').style.display = 'block';
            document.getElementById('analyzeButton').disabled = true;
            document.getElementById('analyzeButton').classList.add('button-disabled');
            document.getElementById('analyzeButton').innerText = 'Procesando...';
        });
    </script>
</body>
</html>
"""
# --- Fin Plantilla HTML ---

@app.route('/')
def home():
    """Ruta de inicio que muestra información del proyecto y el botón de análisis."""
    app.logger.info("Acceso a la ruta de inicio ('/').")
    if run_analysis is None or config is None:
        # Esto podría pasar si la importación inicial falló.
        flash("Error crítico: La aplicación no está configurada correctamente. Revise los logs del servidor.", "error")
    return render_template_string(HOME_PAGE_HTML, project_info=PROJECT_INFO)

@app.route('/analyze', methods=['POST'])
def analyze_project_route():
    """Ruta que ejecuta el análisis y sirve el dashboard HTML resultante."""
    app.logger.info("Solicitud POST a /analyze recibida. Iniciando análisis...")

    if run_analysis is None:
        app.logger.error("Intento de análisis, pero run_analysis no está disponible (error de importación).")
        flash("Error del servidor: La función de análisis no está cargada.", "error")
        return redirect(url_for('home'))

    try:
        # Llamar a la función refactorizada de main.py
        # run_analysis() ahora devuelve la ruta relativa al dashboard o None
        app.logger.info("Llamando a scripts.main.run_analysis()...")
        dashboard_relative_path = run_analysis()
        app.logger.info(f"scripts.main.run_analysis() completado. Ruta del dashboard devuelta: {dashboard_relative_path}")

        if dashboard_relative_path:
            # send_file necesita la ruta relativa al directorio raíz de la aplicación (donde está app.py)
            # o una ruta absoluta. PROJECT_ROOT es la raíz de la aplicación.
            dashboard_absolute_path = os.path.join(PROJECT_ROOT, dashboard_relative_path)
            app.logger.info(f"Intentando servir archivo: {dashboard_absolute_path}")
            if os.path.exists(dashboard_absolute_path):
                return send_file(dashboard_absolute_path)
            else:
                app.logger.error(f"El dashboard se reportó como generado en '{dashboard_relative_path}', pero el archivo no existe en la ruta absoluta: '{dashboard_absolute_path}'.")
                flash(f"Error: El análisis pareció completarse, pero no se encontró el archivo del dashboard ({dashboard_relative_path}).", "error")
        else:
            # Esto podría ser por un error esperado (SSL local) o un error real en el proceso.
            # main.py ya debería haber logueado la causa específica.
            app.logger.warning("run_analysis() no devolvió una ruta de dashboard (posiblemente un error durante el análisis).")
            flash("El proceso de análisis no generó un dashboard. Revisa los logs del servidor para más detalles (puede ser el error SSL esperado localmente).", "info")
    
    except Exception as e:
        app.logger.error(f"Excepción inesperada en la ruta /analyze: {e}")
        app.logger.error(traceback.format_exc()) # Log completo del traceback
        flash(f"Ocurrió un error interno inesperado en el servidor: {str(e)}", "error")
    
    # Si llegamos aquí, algo falló o el dashboard no se pudo servir. Redirigir a home.
    return redirect(url_for('home'))

if __name__ == '__main__':
    # Esto es para desarrollo local.
    # Cloud Run usará Gunicorn y obtendrá el puerto de la variable de entorno PORT.
    app.logger.info("Iniciando servidor Flask de desarrollo en modo DEBUG...")
    # Es importante usar el puerto que Cloud Run espera (8080) si se testea localmente
    # en un entorno que simule Cloud Run.
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host='0.0.0.0', port=port)