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
st.title("⚽ Fase 1: Activación de Filtro LIVE NAtivo (Flashscore)")
st.info(status_instalacion)

# URL base limpia de Flashscore (versión global/es)
url_objetivo = st.text_input("URL de Acceso:", "https://www.flashscore.com/")
btn_conectar = st.button("🔌 Conectar, Pulsar Filtro 'LIVE' y Tomar Captura")

# ===========================================
# ⚡ EJECUCIÓN SÍNCRONA DIRECTA
# ===========================================
if btn_conectar:
    st.write("⏳ Levantando navegador en segundo plano...")
    
    try:
        with sync_playwright() as p:
            # Iniciamos deshabilitando las banderas obvias de automatización
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
                viewport={"width": 1366, "height": 768},
                locale="es-ES"
            )
            
            page = context.new_page()
            
            st.write(f"🌍 Accediendo a Flashscore...")
            page.goto(url_objetivo, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000) # Pausa para renderizado inicial de banners
            
            # 🎯 LOCALIZACIÓN Y CLIC EN EL BOTÓN "LIVE"
            # Usamos el selector CSS exacto combinando la clase del div con el texto interno
            selector_live = "div.filters__text.filters__text--short"
            
            log_box = st.container(border=True)
            log_box.write("🔍 Buscando el botón de filtro en la interfaz...")
            
            # Verificamos si el elemento está presente antes de interactuar
            if page.locator(selector_live).count() > 0:
                log_box.success("🎯 ¡Botón LIVE detectado en el DOM!")
                
                # Forzamos el clic simulando posición exacta del puntero humano
                page.locator(selector_live).first.click()
                log_box.write("✅ Filtro presionado correctamente. Esperando recarga de partidos...")
                page.wait_for_timeout(5000) # Espera crítica para que carguen los marcadores mutables
            else:
                log_box.warning("⚠️ No se encontró la clase exacta del div. Intentando clic por texto plano...")
                # Alternativa de respaldo por si el layout cambia levemente entre idiomas
                page.get_by_text("LIVE", exact=True).first.click()
                page.wait_for_timeout(5000)

            st.success("🎉 Captura de pantalla procesada con éxito.")
            
            # Tomamos la captura de la cartelera en vivo
            screenshot_bytes = page.screenshot(full_page=False)
            st.image(screenshot_bytes, caption="Cartelera LIVE en tiempo real desde la nube", use_container_width=True)
            
            browser.close()
            
    except Exception as err:
        st.error(f"❌ Ocurrió un inconveniente al interactuar con el navegador: {err}")
