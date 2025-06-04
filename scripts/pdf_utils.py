# scripts/pdf_utils.py
import logging
import traceback
from weasyprint import HTML, CSS
# from weasyprint.fonts import FontConfiguration # Descomentar si necesitas configuración de fuentes avanzada

logger = logging.getLogger(__name__)

def generate_pdf_from_html_file(html_file_path, output_pdf_path):
    """
    Genera un PDF a partir de un archivo HTML existente.
    El CSS se asume que está incrustado en el HTML o es accesible.
    """
    try:
        logger.info(f"Intentando generar PDF desde HTML: {html_file_path}")
        
        # Opcional: Configuración de fuentes o CSS específico para impresión
        # font_config = FontConfiguration()
        # print_css = CSS(string='''
        #     @page { size: A4; margin: 1.5cm; }
        #     body { font-family: 'Segoe UI', Tahoma, sans-serif; /* Asegura consistencia de fuente */ }
        #     .abstract-banner-container { page-break-after: always; } /* Ejemplo: salto de página después del banner */
        # ''', font_config=font_config)

        html_doc = HTML(filename=html_file_path) # WeasyPrint puede leer directamente desde el archivo
        
        # Si necesitas aplicar CSS adicional específico para PDF:
        # html_doc.write_pdf(output_pdf_path, stylesheets=[print_css])
        
        # Si el CSS incrustado en el HTML es suficiente:
        html_doc.write_pdf(output_pdf_path)

        logger.info(f"PDF generado exitosamente en: {output_pdf_path}")
        return True
    except Exception as e:
        logger.error(f"Error generando PDF desde el archivo HTML '{html_file_path}': {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    # Bloque de prueba para pdf_utils.py
    # Crea un archivo HTML de prueba simple para convertir
    if not logging.getLogger().handlers: 
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    logger.info("Ejecutando pdf_utils.py directamente para prueba...")
    
    # Usar un dashboard HTML generado previamente por dashboard_generator.py para la prueba
    # Asumimos que estás en la raíz del proyecto al ejecutar esto
    # y que ya has generado un dashboard de prueba.
    test_html_filename = os.path.join("test_dashboard_output", "dummy_dashboard_output_v13_emojis.html") # O el último nombre que usaste
    test_pdf_output_filename = os.path.join("test_dashboard_output", "test_output_from_html.pdf")

    if os.path.exists(test_html_filename):
        logger.info(f"Archivo HTML de prueba encontrado: {test_html_filename}")
        if generate_pdf_from_html_file(test_html_filename, test_pdf_output_filename):
            logger.info(f"PDF de prueba generado: {os.path.abspath(test_pdf_output_filename)}")
        else:
            logger.error("Falló la generación del PDF de prueba.")
    else:
        logger.warning(f"No se encontró el archivo HTML de prueba '{test_html_filename}'. "
                       "Ejecuta primero dashboard_generator.py para crear un HTML de ejemplo.")
    logger.info("Prueba de pdf_utils.py completada.")