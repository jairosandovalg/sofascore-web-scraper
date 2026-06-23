import os
import sys
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright

# === AÑADE ESTA LÍNEA CRÍTICA AQUÍ TAMBIÉN ===
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(os.getcwd(), ".playwright-browsers")
# ============================================

def ejecutar_raspado():
    # ... resto de tu código de raspado igual
    archivo_salida = "analisis_live_apuestas.csv"
    hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"[{hora_actual}] Iniciando ciclo de extracción con Playwright...")
    
    with sync_playwright() as p:
        try:
            # Ajustes obligatorios para prevenir bloqueos y falta de recursos en el servidor Linux de Streamlit
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu"
                ]
            )
            
            # User-Agent real para mitigar protecciones anti-bot automáticas
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            
            page = context.new_page()
            
            # URL de destino
            url_objetivo = "https://www.flashscore.es/" 
            print(f"Navegando a: {url_objetivo}")
            page.goto(url_objetivo, wait_until="domcontentloaded", timeout=35000)
            
            # =========================================================================
            # INCORPORA AQUÍ TUS SELECTORES ESPECÍFICOS DE FLASHSCORE
            # Ejemplo: page.locator(".event__match").all() ... etc.
            # =========================================================================
            
            # Estructura base de datos simulada idéntica a tus columnas para verificar el correcto funcionamiento:
            partidos_extraidos = [
                {
                    "Tiempo": "54'", "Local": "Real Madrid", "GL": 2, "GV": 1, "Visitante": "Barcelona",
                    "xG L": 1.45, "xG V": 0.98, "Córneres L": 5, "Córneres V": 3,
                    "Remates Puerta L": 6, "Remates Puerta V": 4, "Remates Totales L": 12, "Remates Totales V": 8,
                    "Grandes Ocasiones L": 2, "Grandes Ocasiones V": 1, "TA L": 1, "TA V": 2, "TR L": 0, "TR V": 0,
                    "Posesión L": "54%", "Posesión V": "46%", "Precisión Pases L": "85%", "Precisión Pases V": "81%",
                    "Última Actualización": hora_actual
                },
                {
                    "Tiempo": "22'", "Local": "Arsenal", "GL": 0, "GV": 0, "Visitante": "Chelsea",
                    "xG L": 0.22, "xG V": 0.41, "Córneres L": 1, "Córneres V": 2,
                    "Remates Puerta L": 0, "Remates Puerta V": 1, "Remates Totales L": 3, "Remates Totales V": 5,
                    "Grandes Ocasiones L": 0, "Grandes Ocasiones V": 0, "TA L": 0, "TA V": 0, "TR L": 0, "TR V": 0,
                    "Posesión L": "48%", "Posesión V": "52%", "Precisión Pases L": "79%", "Precisión Pases V": "82%",
                    "Última Actualización": hora_actual
                }
            ]
            
            df_nuevos_datos = pd.DataFrame(partidos_extraidos)
            
            # Guardado atómico seguro: Escribe en un temporal primero para evitar errores
            # si Streamlit intenta abrir el archivo exactamente al mismo milisegundo.
            archivo_temporal = archivo_salida + ".tmp"
            df_nuevos_datos.to_csv(archivo_temporal, index=False, encoding="utf-8")
            
            if os.path.exists(archivo_temporal):
                if os.path.exists(archivo_salida):
                    os.remove(archivo_salida)
                os.rename(archivo_temporal, archivo_salida)
                print(f"[{hora_actual}] ¡Proceso exitoso! Archivo '{archivo_salida}' actualizado.")
            
            context.close()
            browser.close()
            
        except Exception as err:
            print(f"[{hora_actual}] ERROR CRÍTICO EN PLAYWRIGHT: {err}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    ejecutar_raspado()
