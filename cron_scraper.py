import os
import sys
import time
import pandas as pd
import re
import gc  # Importamos el recolector de basura nativo
from playwright.sync_api import sync_playwright

# Intervalo seguro y óptimo de actualización en segundos
INTERVALO_REFRESCO = 20 

def ejecutar_raspado():
    # Iniciamos el contexto de Playwright DENTRO de la función para que se destruya al finalizar
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, 
            args=[
                "--no-sandbox", 
                "--disable-dev-shm-usage",
                "--disable-gpu",               # Desactiva la aceleración por hardware para ahorrar RAM crítica
                "--js-flags=--max-old-space-size=256", # Limita el uso de memoria javascript dentro de las pestañas
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1200, "height": 800},
            locale="es-ES"
        )
        
        page = context.new_page()
        page.goto("https://www.flashscore.pe/", timeout=45000, wait_until="domcontentloaded")
        time.sleep(3)
        
        # Filtro en directo nativo
        locator_flexible = page.locator("div[class*='filters__text']:has-text('DIRECTO'), div[class*='filters__text']:has-text('LIVE')").first
        if locator_flexible.count() > 0:
            locator_flexible.dispatch_event("click")
            time.sleep(4)
        else:
            page.get_by_text("EN DIRECTO", exact=False).first.dispatch_event("click")
            time.sleep(4)

        partidos = page.locator("div.event__match--live[data-event-row='true']").all()
        num_partidos = len(partidos)
        print(f"⚽ [{time.strftime('%X')}] Partidos detectados: {num_partidos}")
        
        lista_partidos = []
        
        if num_partidos > 0:
            for partido in partidos:
                try:
                    id_raiz = partido.get_attribute("id") 
                    id_partido = id_raiz.replace("g_1_", "") if id_raiz else None
                    
                    tiempo = partido.locator(".event__stage--block").inner_text().strip()
                    equipo_local = partido.locator(".event__homeParticipant").inner_text().strip()
                    equipo_visitante = partido.locator(".event__awayParticipant").inner_text().strip()
                    marcador_local = partido.locator(".event__score--home").inner_text().strip()
                    marcador_visitante = partido.locator(".event__score--away").inner_text().strip()
                    
                    datos_partido = {
                        "Última Actualización": time.strftime('%X'), "ID Partido": id_partido, "Tiempo": tiempo,
                        "Local": equipo_local, "GL": marcador_local, "GV": marcador_visitante, "Visitante": equipo_visitante,
                        "xG L": "0.00", "xG V": "0.00", "Posesión L": "50%", "Posesión V": "50%",
                        "Remates Totales L": "0", "Remates Totales V": "0", "Remates Puerta L": "0", "Remates Puerta V": "0",
                        "Grandes Ocasiones L": "0", "Grandes Ocasiones V": "0", "Córneres L": "0", "Córneres V": "0",
                        "Precisión Pases L": "0%", "Precisión Pases V": "0%", "TA L": "0", "TA V": "0", "TR L": "0", "TR V": "0"
                    }
                    
                    if id_partido:
                        url_detalle = f"https://www.flashscore.pe/partido/{id_partido}/#/;match-summary/;match-statistics"
                        sub_page = context.new_page()
                        sub_page.goto(url_detalle, timeout=20000, wait_until="domcontentloaded")
                        time.sleep(1.5)
                        
                        try:
                            boton_stats = sub_page.locator("button[data-testid='wcl-tab']:has-text('Estadísticas')").first
                            if boton_stats.count() > 0:
                                boton_stats.dispatch_event("click")
                                time.sleep(0.5)
                        except:
                            pass 
                        
                        filas_estadisticas = sub_page.locator("div[data-testid='wcl-statistics']").all()
                        for fila in filas_estadisticas:
                            try:
                                categoria = fila.locator("div[data-testid='wcl-statistics-category']").inner_text().strip()
                                valores = fila.locator("div[data-testid='wcl-statistics-value']").all()
                                
                                if len(valores) == 2:
                                    val_local = valores[0].inner_text().strip()
                                    val_visitante = valores[1].inner_text().strip()
                                    
                                    if "Goles esperados" in categoria:
                                        datos_partido["xG L"] = val_local
                                        datos_partido["xG V"] = val_visitante
                                    elif "Posesión" in categoria:
                                        datos_partido["Posesión L"] = val_local
                                        datos_partido["Posesión V"] = val_visitante
                                    elif "Remates totales" in categoria:
                                        datos_partido["Remates Totales L"] = val_local
                                        datos_partido["Remates Totales V"] = val_visitante
                                    elif "Remates a puerta" in categoria:
                                        datos_partido["Remates Puerta L"] = val_local
                                        datos_partido["Remates Puerta V"] = val_visitante
                                    elif "Grandes ocasiones" in categoria:
                                        datos_partido["Grandes Ocasiones L"] = val_local
                                        datos_partido["Grandes Ocasiones V"] = val_visitante
                                    elif "Córneres" in categoria or "Córners" in categoria:
                                        datos_partido["Córneres L"] = val_local
                                        datos_partido["Córneres V"] = val_visitante
                                    elif "Tarjetas amarillas" in categoria:
                                        datos_partido["TA L"] = val_local
                                        datos_partido["TA V"] = val_visitante
                                    elif "Tarjetas rojas" in categoria:
                                        datos_partido["TR L"] = val_local
                                        datos_partido["TR V"] = val_visitante
                                    elif "Pases" in categoria and "Precisión" not in categoria:
                                        datos_partido["Precisión Pases L"] = val_local.split('\n')[0]
                                        datos_partido["Precisión Pases V"] = val_visitante.split('\n')[0]
                            except:
                                continue
                        # Cerramos la pestaña inmediatamente para liberar memoria por partido
                        sub_page.close()
                    lista_partidos.append(datos_partido)
                except:
                    continue
            
            # Formatear y consolidar matriz
            df = pd.DataFrame(lista_partidos)
            columnas_enteras = ["Remates Totales L", "Remates Totales V", "Remates Puerta L", "Remates Puerta V", "Grandes Ocasiones L", "Grandes Ocasiones V", "Córneres L", "Córneres V", "TA L", "TA V", "TR L", "TR V"]
            for col in columnas_enteras:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            for col in ["xG L", "xG V"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
            df.to_csv("analisis_live_apuestas.csv", index=False, encoding="utf-8-sig")
            print("✅ Archivo de intercambio reescrito con éxito.")
            
        browser.close() # 🌟 CERRAMOS CHROMIUM POR COMPLETO (Saca toda la RAM del contenedor)

if __name__ == "__main__":
    # Bucle infinito blindado 24/7 a prueba de caídas
    while True:
        try:
            ejecutar_raspado()
        except Exception as e:
            # Si el script se cae por falta de red, timeout o bloqueo, imprime el error y no muere
            print(f"⚠️ Alerta controlada: Ocurrió un fallo en el ciclo de raspado ({e}). Reiniciando motor en 10s...")
            time.sleep(10)
            continue
        
        # 🔥 LIMPIEZA AGRESIVA DE MEMORIA RAM DE PYTHON
        gc.collect() 
        
        print(f"💤 Ciclo terminado. Esperando {INTERVALO_REFRESCO} segundos...\n")
        time.sleep(INTERVALO_REFRESCO)
