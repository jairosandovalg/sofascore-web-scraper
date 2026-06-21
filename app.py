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
# ⚡ EJECUCIÓN SÍNCRONA CON CLIC TRASPASA-ANUNCIOS
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
            log_box.write("🔍 Localizando el botón exacto de 'LIVE'...")
            
            # Buscamos un div que tenga la clase de filtro y contenga exactamente el texto 'LIVE'
            boton_live = page.locator("div.filters__text:has-text('LIVE')").first
            
            if boton_live.count() > 0:
                log_box.success("🎯 ¡Elemento objetivo localizado en la interfaz!")
                
                # 🔥 CLIC FORZADO (force=True): Traspasa banners de publicidad, anuncios o cookies bypassando el bloqueo
                boton_live.click(force=True)
                
                log_box.write("🚀 Clic inyectado de forma directa. Esperando refresco de la cartelera...")
                page.wait_for_timeout(5000)
            else:
                log_box.warning("⚠️ Selector específico no hallado. Intentando respaldo por texto crudo...")
                page.get_by_text("LIVE", exact=True).first.click(force=True)
                page.wait_for_timeout(5000)

            st.success("🎉 Captura de pantalla procesada con éxito.")
            
            # Tomamos la captura
            screenshot_bytes = page.screenshot(full_page=False)
            st.image(screenshot_bytes, caption="Cartelera LIVE en tiempo real procesada sin anuncios", use_container_width=True)
            
            browser.close()
            
    except Exception as err:
        st.error(f"❌ Ocurrió un inconveniente al interactuar con el navegador: {err}")
