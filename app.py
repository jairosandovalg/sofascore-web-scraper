import streamlit as st
import os
import subprocess
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
st.title("⚽ Fase 1: Activación de Filtro LIVE Nativo (Flashscore)")
st.info(status_instalacion)

url_objetivo = st.text_input("URL de Acceso:", "https://www.flashscore.com/")
btn_conectar = st.button("🔌 Conectar, Pulsar Filtro 'LIVE' y Tomar Captura")

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
            
            st.write(f"🌍 Accediendo a Flashscore...")
            page.goto(url_objetivo, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000) 
            
            log_box = st.container(border=True)
            log_box.write("🔍 Localizando el botón dinámico conteniendo 'LIVE'...")
            
            # Selector flexible: busca cualquier div con clase 'filters__text' que tenga la palabra 'LIVE'
            locator_flexible = page.locator("div[class*='filters__text']:has-text('LIVE')").first
            
            if locator_flexible.count() > 0:
                texto_detectado = locator_flexible.inner_text()
                log_box.success(f"🎯 ¡Elemento localizado! Texto real en pantalla: '{texto_detectado}'")
                
                # 🔥 DISPARO POR JAVASCRIPT DIRECTO: Traspasa problemas de 'Element is not visible'
                # Obliga al navegador a ejecutar el evento de clic directamente en el nodo del DOM
                locator_flexible.dispatch_event("click")
                
                log_box.write("🚀 Evento JavaScript 'click' inyectado con éxito. Esperando actualización de partidos...")
                page.wait_for_timeout(6000) # Tiempo para que cargue la nueva lista en vivo
            else:
                log_box.warning("⚠️ No se encontró el selector flexible. Intentando click por texto crudo...")
                page.get_by_text("LIVE Games", exact=False).first.dispatch_event("click")
                page.wait_for_timeout(6000)

            # =================================================================
            # 🔥 AQUÍ EMPIEZA TU NUEVO BLOQUE DE ESTADÍSTICAS (REEMPLAZA LA CAPTURA)
            # =================================================================
            st.write("📊 Extrayendo datos de la cartelera en vivo...")
            
            # 1. Creamos una lista para almacenar los datos estructurados
            lista_partidos = []
            
            # =================================================================
            # 🔥 BLOQUE DE ESTADÍSTICAS OPTIMIZADO (HTML REAL)
            # =================================================================
            st.write("📊 Analizando la cartelera en vivo de Flashscore...")
            
            # 1. Esperar a que los elementos de partidos en vivo estén cargados en el DOM
            page.wait_for_selector("div[data-event-row='true']", timeout=10000)
            
            # 2. Localizar todos los contenedores de partidos en vivo reales
            # Usamos el atributo nativo de Flashscore 'data-event-row="true"' combinado con la clase de vivo
            partidos = page.locator("div.event__match--live[data-event-row='true']").all()
            num_partidos = len(partidos)
            
            st.metric(label="⚽ Partidos en Directo Detectados", value=num_partidos)
            
            lista_partidos = []
            
            if num_partidos > 0:
                for partido in partidos:
                    try:
                        # Extraer ID único del partido (servirá para armar URLs directas de estadísticas)
                        id_raiz = partido.get_attribute("id") # Retorna algo como "g_1_IJNPSidm"
                        id_partido = id_raiz.replace("g_1_", "") if id_raiz else None
                        
                        # Extraer URL de acceso al detalle
                        enlace_elemento = partido.locator("a.eventRowLink")
                        url_partido = enlace_elemento.get_attribute("href")
                        
                        # Extraer datos visibles en la tabla principal
                        tiempo = partido.locator(".event__stage--block").inner_text()
                        equipo_local = partido.locator(".event__homeParticipant").inner_text()
                        equipo_visitante = partido.locator(".event__awayParticipant").inner_text()
                        marcador_local = partido.locator(".event__score--home").inner_text()
                        marcador_visitante = partido.locator(".event__score--away").inner_text()
                        
                        # Guardamos la información estructurada
                        lista_partidos.append({
                            "ID Partido": id_partido,
                            "Tiempo": tiempo.strip(),
                            "Local": equipo_local.strip(),
                            "GL": marcador_local.strip(),
                            "GV": marcador_visitante.strip(),
                            "Visitante": equipo_visitante.strip(),
                            "URL Detalle": url_partido
                        })
                    except Exception as e:
                        # Si un partido cambia de estado abruptamente, saltamos al siguiente
                        continue
                
                # 3. Procesar con Pandas y mostrar en Streamlit
                import pandas as pd
                df = pd.DataFrame(lista_partidos)
                
                st.subheader("📋 Lista de Encuentros Activos")
                # Configuramos st.dataframe para que el enlace sea cliqueable en la UI si deseas revisarlo
                st.dataframe(
                    df, 
                    column_config={"URL Detalle": st.column_config.LinkColumn("Enlace Detalle")},
                    use_container_width=True
                )
                
                # Guardar el estado actual de la cartelera
                df.to_csv("cartelera_live.csv", index=False, encoding="utf-8-sig")
                st.success(f"💾 Se han detectado y guardado {len(df)} partidos en 'cartelera_live.csv'")
                
            else:
                st.warning("⚠️ Cero (0) partidos en directo localizados con los selectores actuales.")
