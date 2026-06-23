import os
import sys
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright

# Forzar ruta compartida del navegador
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(os.getcwd(), ".playwright-browsers")

def log_registro(mensaje):
    """Escribe lo que hace el script en la consola y en un archivo local"""
    hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    texto = f"[{hora}] {mensaje}\n"
    print(texto.strip())
    with open("robot_ejecucion.log", "a", encoding="utf-8") as f:
        f.write(texto)

def ejecutar_raspado():
    archivo_salida = "analisis_live_apuestas.csv"
    
    log_registro("=== INICIANDO NUEVO CICLO DE RASPADO ===")
    
    with sync_playwright() as p:
        try:
            log_registro("Intentando lanzar Chromium Headless...")
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ]
            )
            
            log_registro("Navegador abierto con éxito. Creando contexto...")
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            log_registro("Navegando a Flashscore...")
            page.goto("https://www.flashscore.es/", wait_until="domcontentloaded", timeout=35000)
            
            log_registro("Web cargada. Iniciando extracción de selectores...")
            
            # =========================================================
            # TU LÓGICA DE EXTRACCIÓN VA AQUÍ (Tus selectores reales)
            # =========================================================
            
            # Simulación de éxito (reemplazar con tus datos reales de raspado)
            partidos = [{"Tiempo": "10'", "Local": "Test L", "Visitante": "Test V", "Última Actualización": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]
            
            log_registro(f"Se extrajeron {len(partidos)} partidos. Guardando CSV...")
            df = pd.DataFrame(partidos)
            
            archivo_temporal = archivo_salida + ".tmp"
            df.to_csv(archivo_temporal, index=False, encoding="utf-8")
            
            if os.path.exists(archivo_temporal):
                if os.path.exists(archivo_salida):
                    os.remove(archivo_salida)
                os.rename(archivo_temporal, archivo_salida)
                log_registro("¡Archivo CSV actualizado exitosamente!")
            
            context.close()
            browser.close()
            log_registro("=== CICLO FINALIZADO CORRECTAMENTE ===")
            
        except Exception as err:
            log_registro(f"❌ CRÍTICO - Falló la ejecución. Detalle del error: {str(err)}")
            sys.exit(1)

if __name__ == "__main__":
    ejecutar_raspado()
