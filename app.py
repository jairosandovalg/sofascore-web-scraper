import streamlit as st
import os
import subprocess
import pandas as pd
import re
from playwright.sync_api import sync_playwright

# ===========================================
# 📦 AUTO-INSTALACIÓN DE NAVEGADORES
# ===========================================
try:
    import playwright
except ImportError:
    pass

@st.cache_resource
def verificar_e_instalar_browsers():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
        return "✅ Motor de navegación validado en el sistema."
    except Exception as e:
        return f"⚠️ Nota de inicialización: {e}"

status_instalacion = verificar_e_instalar_browsers()

# ===========================================
# 💻 CONFIGURACIÓN DE LA PÁGINA STREAMLIT
# ===========================================
st.set_page_config(page_title="Filtro Live Flashscore", page_icon="⚽", layout="wide")
st.title("⚽ Extractor Avanzado de Estadísticas en Vivo (Flashscore)")
st.info(status_instalacion)

url_objetivo = st.text_input("URL de Acceso:", "https://www.flashscore.pe/")
btn_conectar = st.button("🔌 Conectar, Filtrar 'En Directo' y Extraer Métricas de Apuestas")

# ===========================================
# ⚡ EJECUCIÓN SÍNCRONA CON DISPARO JAVASCRIPT NATIVO
# ===========================================
if btn_conectar:
    st.write("⏳ Levantando navegador en segundo plano...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, 
                args=[
                    "--no-sandbox", 
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1400, "height": 900},
                locale="es-ES"
            )
            
            page = context.new_page()
            
            st.write(f"🌍 Accediendo a la plataforma principal...")
            page.goto(url_objetivo, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000) 
            
            log_box = st.container(border=True)
            log_box.write("🔍 Localizando el botón dinámico conteniendo 'LIVE' o 'En Directo'...")
            
            locator_flexible = page.locator("div[class*='filters__text']:has-text('DIRECTO'), div[class*='filters__text']:has-text('LIVE')").first
            
            if locator_flexible.count() > 0:
                texto_detectado = locator_flexible.inner_text()
                log_box.success(f"🎯 ¡Elemento localizado! Texto real en pantalla: '{texto_detectado}'")
                
                locator_flexible.dispatch_event("click")
                log_box.write("🚀 Filtro aplicado con éxito. Esperando actualización de partidos en directo...")
                page.wait_for_timeout(6000) 
            else:
                log_box.warning("⚠️ No se encontró el selector flexible por clases. Intentando click por texto plano...")
                page.get_by_text("EN DIRECTO", exact=False).first.dispatch_event("click")
                page.wait_for_timeout(6000)

            # =================================================================
            # 🔥 BLOQUE DE ESTADÍSTICAS AVANZADO (PROCESAMIENTO DE MÉTRICAS LIVE)
            # =================================================================
            st.write("📊 Analizando la cartelera en vivo...")
            
            try:
                page.wait_for_selector("div[data-event-row='true']", timeout=12000)
            except:
                pass
                
            partidos = page.locator("div.event__match--live[data-event-row='true']").all()
            num_partidos = len(partidos)
            
            st.metric(label="⚽ Partidos en Directo Detectados", value=num_partidos)
            
            lista_partidos = []
            
            if num_partidos > 0:
                progreso_barra = st.progress(0)
                status_text = st.empty()
                
                for index, partido in enumerate(partidos):
                    try:
                        id_raiz = partido.get_attribute("id") 
                        id_partido = id_raiz.replace("g_1_", "") if id_raiz else None
                        
                        tiempo = partido.locator(".event__stage--block").inner_text().strip()
                        equipo_local = partido.locator(".event__homeParticipant").inner_text().strip()
                        equipo_visitante = partido.locator(".event__awayParticipant").inner_text().strip()
                        marcador_local = partido.locator(".event__score--home").inner_text().strip()
                        marcador_visitante = partido.locator(".event__score--away").inner_text().strip()
                        
                        status_text.write(f"⏳ Extrayendo estadísticas de: **{equipo_local} vs {equipo_visitante}**...")
                        
                        # Molde definitivo alineado al 100% con image_b7f26a.png
                        datos_partido = {
                            "ID Partido": id_partido, "Tiempo": tiempo,
                            "Local": equipo_local, "GL": marcador_local, "GV": marcador_visitante, "Visitante": equipo_visitante,
                            "xG L": "0.00", "xG V": "0.00",
                            "Posesión L": "50%", "Posesión V": "50%",
                            "Remates Totales L": "0", "Remates Totales V": "0",
                            "Remates Puerta L": "0", "Remates Puerta V": "0",
                            "Grandes Ocasiones L": "0", "Grandes Ocasiones V": "0",
                            "Córneres L": "0", "Córneres V": "0",
                            "Precisión Pases L": "0%", "Precisión Pases V": "0%",
                            "TA L": "0", "TA V": "0",  # Tarjetas Amarillas
                            "TR L": "0", "TR V": "0"   # Tarjetas Rojas
                        }
                        
                        if id_partido:
                            url_detalle = f"https://www.flashscore.pe/partido/{id_partido}/#/;match-summary/;match-statistics"
                            
                            sub_page = context.new_page()
                            sub_page.goto(url_detalle, timeout=30000, wait_until="domcontentloaded")
                            sub_page.wait_for_timeout(2500) 
                            
                            try:
                                boton_stats = sub_page.locator("button[data-testid='wcl-tab']:has-text('Estadísticas')").first
                                if boton_stats.count() > 0:
                                    boton_stats.dispatch_event("click")
                                    sub_page.wait_for_timeout(1000)
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
                                        
                                        # Mapeo exhaustivo de categorías
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
                                            lineas_l = val_local.split('\n')
                                            lineas_v = val_visitante.split('\n')
                                            
                                            datos_partido["Precisión Pases L"] = lineas_l[0]
                                            datos_partido["Precisión Pases V"] = lineas_v[0]
                                except:
                                    continue
                            
                            sub_page.close()
                        
                        lista_partidos.append(datos_partido)
                        
                    except Exception as e:
                        continue
                    
                    progreso_barra.progress((index + 1) / num_partidos)
                
                status_text.success("🎯 ¡Todas las métricas reglamentarias y de presión consolidadas!")
                
                # 3. Conversión y normalización de tipos numéricos
                df = pd.DataFrame(lista_partidos)
                
                columnas_enteras = [
                    "Remates Totales L", "Remates Totales V", "Remates Puerta L", "Remates Puerta V",
                    "Grandes Ocasiones L", "Grandes Ocasiones V", "Córneres L", "Córneres V",
                    "TA L", "TA V", "TR L", "TR V"
                ]
                for col in columnas_enteras:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                
                for col in ["xG L", "xG V"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                
                # Desplegar interfaz analítica avanzada ordenada por volumen de ataque
                st.subheader("🔥 Panel In-Play Completo (Métricas Críticas de Arbitraje y Ataque)")
                
                columnas_mostrar = [
                    "Tiempo", "Local", "GL", "GV", "Visitante", 
                    "xG L", "xG V",
                    "Córneres L", "Córneres V", 
                    "Remates Puerta L", "Remates Puerta V", 
                    "Remates Totales L", "Remates Totales V",
                    "Grandes Ocasiones L", "Grandes Ocasiones V",
                    "TA L", "TA V", "TR L", "TR V",
                    "Posesión L", "Posesión V",
                    "Precisión Pases L", "Precisión Pases V"
                ]
                
                st.dataframe(df[columnas_mostrar], use_container_width=True)
                
                # Guardar automáticamente la matriz para análisis
                df.to_csv("analisis_live_apuestas.csv", index=False, encoding="utf-8-sig")
                st.success(f"💾 Base de datos completa en tiempo real guardada en 'analisis_live_apuestas.csv'")
                
            else:
                st.warning("⚠️ Cero (0) partidos en directo localizados con los selectores actuales.")
                
            browser.close()
            
    except Exception as err:
        st.error(f"❌ Ocurrió un inconveniente general en la ejecución del navegador: {err}")
