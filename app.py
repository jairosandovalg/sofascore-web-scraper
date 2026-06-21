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

            st.success("🎉 Captura de pantalla procesada con éxito.")
            
            # Tomamos la captura para ver los partidos en vivo reales cargados en la nube
            screenshot_bytes = page.screenshot(full_page=False)
            st.image(screenshot_bytes, caption="Cartelera LIVE en tiempo real procesada por inyección JS", use_container_width=True)
            
            browser.close()
            
    except Exception as err:
        st.error(f"❌ Ocurrió un inconveniente al interactuar con el navegador: {err}")
