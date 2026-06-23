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
    
    log_registro("=== INICIANDO NUEVO CICLO DE RASPADO INTEGRAL ===")
    
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
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 1000}
            )
            page = context.new_page()
            
            # 1. Navegar a la página principal
            log_registro("Navegando a Flashscore...")
            page.goto("https://www.flashscore.es/", wait_until="domcontentloaded", timeout=40000)
            
            # Aceptar cookies si aparece el banner para evitar bloqueos visuales
            try:
                page.click("#onetrust-accept-btn-handler", timeout=3000)
                log_registro("Cookies aceptadas.")
            except:
                pass

            # 2. ENTRAR AL BOTÓN DE PARTIDOS EN DIRECTO ("EN DIRECTO")
            log_registro("Filtrando por partidos 'En Directo'...")
            # Selector clásico del filtro live de Flashscore
            boton_directo = page.locator(".filters__tab").by_text("EN DIRECTO")
            if boton_directo.count() > 0:
                boton_directo.click()
                page.wait_for_timeout(2000) # Esperar que filtre el DOM
            else:
                log_registro("No se encontró el botón dinámico 'EN DIRECTO', se procede con el estado actual.")

            # 3. CAPTURAR LA LISTA DE PARTIDOS EN VIVO
            # Flashscore agrupa los partidos en vivo con selectores de evento en directo
            partidos_en_linea = page.locator(".event__match--live").all()
            total_partidos = len(partidos_en_linea)
            log_registro(f"Se detectaron {total_partidos} partidos en directo disponibles.")
            
            lista_datos_finales = []
            
            # 4. ITERAR CADA PARTIDO PARA IR A SUS ESTADÍSTICAS
            for i in range(total_partidos):
                try:
                    # Re-localizar para evitar elementos desprendidos por refrescos dinámicos
                    match_elem = page.locator(".event__match--live").nth(i)
                    
                    # Extraer datos básicos visibles en la lista principal
                    local = match_elem.locator(".event__participant--home").text_content().strip()
                    visitante = match_elem.locator(".event__participant--away").text_content().strip()
                    
                    # Intentar obtener el tiempo y goles actuales
                    try:
                        tiempo = match_elem.locator(".event__stage").text_content().strip()
                        gl = match_elem.locator(".event__score--home").text_content().strip()
                        gv = match_elem.locator(".event__score--away").text_content().strip()
                    except:
                        tiempo, gl, gv = "0'", "0", "0"

                    log_registro(f"Procesando [{i+1}/{total_partidos}]: {local} {gl}-{gv} {visitante} ({tiempo})")
                    
                    # ABRE EL PARTIDO EN UNA NUEVA PESTAÑA (Flashscore abre los detalles en un popup o pestaña independiente)
                    with context.expect_page() as new_page_info:
                        # Forzar el clic en el contenedor del partido para detonar la apertura
                        match_elem.click()
                    
                    detalles_page = new_page_info.value
                    detalles_page.bring_to_front()
                    detalles_page.wait_for_load_state("domcontentloaded", timeout=15000)
                    
                    # Diccionario base para este partido
                    datos_partido = {
                        "Tiempo": tiempo, "Local": local, "GL": gl, "GV": gv, "Visitante": visitante,
                        "Última Actualización": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # 5. IR A LA PARTE DE ESTADÍSTICAS DENTRO DEL PARTIDO
                    try:
                        # Buscar el botón o pestaña de ESTADÍSTICAS dentro del detalle del partido
                        pestana_estadisticas = detalles_page.locator("a").by_text("Estadísticas")
                        if pestana_estadisticas.count() > 0:
                            pestana_estadisticas.first.click()
                            detalles_page.wait_for_selector(".stat__row", timeout=5000)
                            
                            # 6. EXTRACCIÓN Y MAPEO DE FILAS DE ESTADÍSTICAS
                            filas_stat = detalles_page.locator(".stat__row").all()
                            for fila in filas_stat:
                                try:
                                    nombre_stat = fila.locator(".stat__categoryName").text_content().strip()
                                    valor_local = fila.locator(".stat__homeValue").text_content().strip()
                                    valor_visitante = fila.locator(".stat__awayValue").text_content().strip()
                                    
                                    # Mapeo dinámico según el nombre de la estadística encontrada
                                    if "Posesión" in nombre_stat:
                                        datos_partido["Posesión L"] = valor_local
                                        datos_partido["Posesión V"] = valor_visitante
                                    elif "Remates a puerta" in nombre_stat or "Remates Puerta" in nombre_stat:
                                        datos_partido["Remates Puerta L"] = valor_local
                                        datos_partido["Remates Puerta V"] = valor_visitante
                                    elif "Remates totales" in nombre_stat or "Remates Totales" in nombre_stat:
                                        datos_partido["Remates Totales L"] = valor_local
                                        datos_partido["Remates Totales V"] = valor_visitante
                                    elif "Córneres" in nombre_stat or "Saques de esquina" in nombre_stat:
                                        datos_partido["Córneres L"] = valor_local
                                        datos_partido["Córneres V"] = valor_visitante
                                    elif "Goles esperados" in nombre_stat or "xG" in nombre_stat:
                                        datos_partido["xG L"] = valor_local
                                        datos_partido["xG V"] = valor_visitante
                                    elif "Grandes ocasiones" in nombre_stat:
                                        datos_partido["Grandes Ocasiones L"] = valor_local
                                        datos_partido["Grandes Ocasiones V"] = valor_visitante
                                    elif "Tarjetas Amarillas" in nombre_stat or "TA" in nombre_stat:
                                        datos_partido["TA L"] = valor_local
                                        datos_partido["TA V"] = valor_visitante
                                    elif "Tarjetas Rojas" in nombre_stat or "TR" in nombre_stat:
                                        datos_partido["TR L"] = valor_local
                                        datos_partido["TR V"] = valor_visitante
                                    elif "Precisión de pases" in nombre_stat:
                                        datos_partido["Precisión Pases L"] = valor_local
                                        datos_partido["Precisión Pases V"] = valor_visitante
                                except Exception as e_fila:
                                    pass
                        else:
                            log_registro(f"Estadísticas aún no disponibles para {local} vs {visitante}.")
                    except Exception as e_stats:
                        log_registro(f"No se pudieron leer las filas de estadística de este encuentro.")
                    
                    # Cerrar la pestaña de detalles para liberar memoria antes de ir al siguiente
                    detalles_page.close()
                    lista_datos_finales.append(datos_partido)
                    
                except Exception as e_partido:
                    log_registro(f"Error procesando el índice de partido {i}: {e_partido}")
                    try:
                        detalles_page.close()
                    except:
                        pass

            # 7. CONVERTIR A DATAFRAME Y SALVADO SEGURO EN CSV
            if lista_datos_finales:
                df_final = pd.DataFrame(lista_datos_finales)
                
                # Escribir usando intercambio atómico temporal
                archivo_temporal = archivo_salida + ".tmp"
                df_final.to_csv(archivo_temporal, index=False, encoding="utf-8")
                
                if os.path.exists(archivo_temporal):
                    if os.path.exists(archivo_salida):
                        os.remove(archivo_salida)
                    os.rename(archivo_temporal, archivo_salida)
                    log_registro(f"¡Sincronización exitosa! {len(lista_datos_finales)} partidos guardados en {archivo_salida}")
            else:
                log_registro("No se recopilaron datos en este barrido (Lista vacía).")

            context.close()
            browser.close()
            log_registro("=== CICLO FINALIZADO CORRECTAMENTE ===")
            
        except Exception as err:
            log_registro(f"❌ CRÍTICO - Falló la ejecución general. Detalle del error: {str(err)}")
            sys.exit(1)

if __name__ == "__main__":
    ejecutar_raspado()
