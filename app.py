import streamlit as st
import os
import subprocess
import pandas as pd
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
            
            # Selector flexible basado en el HTML proveído para el botón del filtro "En Directo"
            locator_flexible = page.locator("div[class*='filters__text']:has-text('DIRECTO'), div[class*='filters__text']:has-text('LIVE')").first
            
            if locator_flexible.count() > 0:
                texto_detectado = locator_flexible.inner_text()
                log_box.success(f"🎯 ¡Elemento localizado! Texto real en pantalla: '{texto_detectado}'")
                
                # Inyección nativa en el DOM para evitar que capas intermedias bloqueen el clic
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
            
            # 1. Esperar a que los elementos de partidos en vivo reales estén renderizados
            try:
                page.wait_for_selector("div[data-event-row='true']", timeout=12000)
            except:
                pass
                
            # 2. Localizar todos los contenedores de partidos en vivo reales según el HTML provisto
            partidos = page.locator("div.event__match--live[data-event-row='true']").all()
            num_partidos = len(partidos)
            
            st.metric(label="⚽ Partidos en Directo Detectados", value=num_partidos)
            
            lista_partidos = []
            
            if num_partidos > 0:
                # Indicadores de carga visuales en Streamlit
                progreso_barra = st.progress(0)
                status_text = st.empty()
                
                for index, partido in enumerate(partidos):
                    try:
                        # Extraer ID único del partido desde el atributo 'id' (ej: "g_1_IJNPSidm" -> "IJNPSidm")
                        id_raiz = partido.get_attribute("id") 
                        id_partido = id_raiz.replace("g_1_", "") if id_raiz else None
                        
                        # Datos básicos visibles en la cartelera principal
                        tiempo = partido.locator(".event__stage--block").inner_text().strip()
                        equipo_local = partido.locator(".event__homeParticipant").inner_text().strip()
                        equipo_visitante = partido.locator(".event__awayParticipant").inner_text().strip()
                        marcador_local = partido.locator(".event__score--home").inner_text().strip()
                        marcador_visitante = partido.locator(".event__score--away").inner_text().strip()
                        
                        status_text.write(f"⏳ Extrayendo estadísticas de: **{equipo_local} vs {equipo_visitante}**...")
                        
                        # Diccionario molde inicializado a ceros por si el partido no posee métricas aún
                        datos_partido = {
                            "ID Partido": id_partido,
                            "Tiempo": tiempo,
                            "Local": equipo_local,
                            "GL": marcador_local,
                            "GV": marcador_visitante,
                            "Visitante": equipo_visitante,
                            "Posesión L": "50%", "Posesión V": "50%",
                            "Remates Totales L": "0", "Remates Totales V": "0",
                            "Remates Puerta L": "0", "Remates Puerta V": "0",
                            "Córneres L": "0", "Córneres V": "0"
                        }
                        
                        # 🚀 CONEXIÓN PARALELA A LA URL DE ESTADÍSTICAS DIRECTAS (MULTI-TABS)
                        if id_partido:
                            # Construcción dinámica de la sub-página de estadísticas
                            url_detalle = f"https://www.flashscore.pe/partido/{id_partido}/#/;match-summary/;match-statistics"
                            
                            sub_page = context.new_page()
                            sub_page.goto(url_detalle, timeout=30000, wait_until="domcontentloaded")
                            sub_page.wait_for_timeout(2500) # Tiempo técnico prudente para la carga del DOM reactivo
                            
                            # Aseguramos el foco sobre la pestaña de estadísticas si el hash no se dispara solo
                            try:
                                boton_stats = sub_page.locator("button[data-testid='wcl-tab']:has-text('Estadísticas')").first
                                if boton_stats.count() > 0:
                                    boton_stats.dispatch_event("click")
                                    sub_page.wait_for_timeout(1000)
                            except:
                                pass 
                            
                            # Procesamiento de filas dinámicas usando el modelo HTML real provisto
                            filas_estadisticas = sub_page.locator("div[data-testid='wcl-statistics']").all()
                            
                            for fila in filas_estadisticas:
                                try:
                                    categoria = fila.locator("div[data-testid='wcl-statistics-category']").inner_text().strip()
                                    valores = fila.locator("div[data-testid='wcl-statistics-value']").all()
                                    
                                    if len(valores) == 2:
                                        val_local = valores[0].inner_text().strip()
                                        val_visitante = valores[1].inner_text().strip()
                                        
                                        # Guardar según la métrica correspondiente para tus alertas de apuestas
                                        if "Posesión" in categoria:
                                            datos_partido["Posesión L"] = val_local
                                            datos_partido["Posesión V"] = val_visitante
                                        elif "Remates totales" in categoria:
                                            datos_partido["Remates Totales L"] = val_local
                                            datos_partido["Remates Totales V"] = val_visitante
                                        elif "Remates a puerta" in categoria:
                                            datos_partido["Remates Puerta L"] = val_local
                                            datos_partido["Remates Puerta V"] = val_visitante
                                        elif "Córneres" in categoria or "Córners" in categoria:
                                            datos_partido["Córneres L"] = val_local
                                            datos_partido["Córneres V"] = val_visitante
                                except:
                                    continue
                            
                            # Liberar recursos y cerrar pestaña secundaria de inmediato
                            sub_page.close()
                        
                        lista_partidos.append(datos_partido)
                        
                    except Exception as e:
                        # Si falla el raspado de un partido individual, continúa con el resto de la cartelera
                        continue
                    
                    # Actualizar barra de progreso dinámicamente
                    progreso_barra.progress((index + 1) / num_partidos)
                
                status_text.success("🎯 ¡Procesamiento de estadísticas en vivo completado!")
                
                # 3. Conversión de tipos de datos para permitir el filtrado y ordenamiento en Streamlit
                df = pd.DataFrame(lista_partidos)
                columnas_numericas = ["Remates Totales L", "Remates Totales V", "Remates Puerta L", "Remates Puerta V", "Córneres L", "Córneres V"]
                
                for col in columnas_numericas:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                
                # Desplegar interfaz interactiva
                st.subheader("🔥 Panel de Control In-Play (Estadísticas de Presión)")
                st.dataframe(
                    df[[
                        "Tiempo", "Local", "GL", "GV", "Visitante", 
                        "Córneres L", "Córneres V", 
                        "Remates Puerta L", "Remates Puerta V", 
                        "Remates Totales L", "Remates Totales V", 
                        "Posesión L", "Posesión V", "ID Partido"
                    ]], 
                    use_container_width=True
                )
                
                # Guardar automáticamente la matriz para análisis
                df.to_csv("analisis_live_apuestas.csv", index=False, encoding="utf-8-sig")
                st.success(f"💾 Matriz reactiva guardada con éxito ({len(df)} registros) en 'analisis_live_apuestas.csv'")
                
            else:
                st.warning("⚠️ Cero (0) partidos en directo localizados con los selectores actuales.")
                
            # Cierre limpio del motor de navegación al finalizar el proceso
            browser.close()
            
    except Exception as err:
        st.error(f"❌ Ocurrió un inconveniente general en la ejecución del navegador: {err}")
