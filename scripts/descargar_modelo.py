    # scripts/descargar_modelo.py
    import os
    import certifi # Para manejo de SSL
    from sentence_transformers import SentenceTransformer
    
    # ---- INICIO DE LA MODIFICACIÓN PARA SSL/CERTIFI ----
    # Intenta configurar certifi para esta descarga específica.
    # Si el script principal (config.py) ya lo hizo a nivel de entorno, esto podría ser redundante
    # pero no hace daño tenerlo aquí para un script independiente.
    try:
        original_ssl_cert_file = os.environ.get('SSL_CERT_FILE')
        original_requests_ca_bundle = os.environ.get('REQUESTS_CA_BUNDLE')
        
        certifi_path = certifi.where()
        os.environ['SSL_CERT_FILE'] = certifi_path
        os.environ['REQUESTS_CA_BUNDLE'] = certifi_path
        print(f"INFO (descargar_modelo.py): Intentando usar bundle de certifi en: {certifi_path}")
    except Exception as e_certifi_setup:
        print(f"ADVERTENCIA (descargar_modelo.py): No se pudo establecer SSL con certifi: {e_certifi_setup}")
    # ---- FIN DE LA MODIFICACIÓN PARA SSL/CERTIFI ----

    # Importar config DESPUÉS de configurar SSL si config.py también importa bibliotecas de red.
    # O, para un script simple, definir PROJECT_ROOT aquí.
    try:
        from config import PROJECT_ROOT, MODELOS_LOCALES_PATH # Asumiendo que MODELOS_LOCALES_PATH está en config
    except ImportError:
        # Definición fallback si config.py no es accesible o no tiene MODELOS_LOCALES_PATH
        # Asume que este script está en 'scripts/' y 'modelos_locales' está en la raíz del proyecto
        PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        MODELOS_LOCALES_PATH = os.path.join(PROJECT_ROOT, "modelos_locales")


    MODEL_ID_TO_DOWNLOAD = "sentence-transformers/all-MiniLM-L6-v2"
    MODEL_SAVE_SUBFOLDER = "all-MiniLM-L6-v2" # Nombre de la subcarpeta específica para este modelo
    
    # Construir la ruta de guardado completa
    FULL_SAVE_PATH = os.path.join(MODELOS_LOCALES_PATH, MODEL_SAVE_SUBFOLDER)

    if not os.path.exists(FULL_SAVE_PATH):
        os.makedirs(FULL_SAVE_PATH)
        print(f"Directorio creado: {FULL_SAVE_PATH}")
    else:
        print(f"Directorio ya existe: {FULL_SAVE_PATH}")

    print(f"\nDescargando y guardando el modelo '{MODEL_ID_TO_DOWNLOAD}' en '{FULL_SAVE_PATH}'...")
    try:
        model = SentenceTransformer(MODEL_ID_TO_DOWNLOAD)
        model.save(FULL_SAVE_PATH)
        print(f"Modelo '{MODEL_ID_TO_DOWNLOAD}' guardado exitosamente en {FULL_SAVE_PATH}")
        print("Archivos guardados:")
        for item in os.listdir(FULL_SAVE_PATH):
            print(f" - {item}")

    except Exception as e:
        print(f"--------------------------------------------------------------------")
        print(f"ERROR al descargar o guardar el modelo '{MODEL_ID_TO_DOWNLOAD}':")
        print(f"Tipo: {type(e)}, Mensaje: {str(e)}")
        print(f"--------------------------------------------------------------------")
        import traceback
        traceback.print_exc()
        print(f"--------------------------------------------------------------------")
        print("Asegúrate de tener conexión a internet.")
        print("Si es un problema de SSL (CERTIFICATE_VERIFY_FAILED):")
        print("  1. Verifica tu conexión y configuración de red/proxy.")
        print(f"  2. Considera descargar los archivos manualmente desde huggingface.co/{MODEL_ID_TO_DOWNLOAD}/tree/main y colocarlos en '{FULL_SAVE_PATH}'")
    finally:
        # Restaurar variables de entorno SSL si se modificaron
        if 'original_ssl_cert_file' in locals() and original_ssl_cert_file is not None:
            os.environ['SSL_CERT_FILE'] = original_ssl_cert_file
        elif 'SSL_CERT_FILE' in os.environ and 'original_ssl_cert_file' in locals(): # si era None antes
            del os.environ['SSL_CERT_FILE']

        if 'original_requests_ca_bundle' in locals() and original_requests_ca_bundle is not None:
            os.environ['REQUESTS_CA_BUNDLE'] = original_requests_ca_bundle
        elif 'REQUESTS_CA_BUNDLE' in os.environ and 'original_requests_ca_bundle' in locals():
             del os.environ['REQUESTS_CA_BUNDLE']
    