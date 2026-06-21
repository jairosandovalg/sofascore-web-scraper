import streamlit as st
import os
import subprocess
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth

# ===========================================
# 📦 AUTO-INSTALACIÓN DE NAVEGADORES (CRUCIAL PARA LA NUBE)
# ===========================================
# Si los navegadores de Playwright no están en el servidor, los descargamos dinámicamente
try:
    import playwright
except ImportError:
    pass

@st.cache_resource
def verificar_e_instalar_browsers():
    try:
        # Intentamos un comando rápido para obligar a Playwright a instalar su Chromium ligero
        subprocess.run(["playwright", "install", "chromium"], check=True)
        return "✅ Navegadores validados e instalados correctamente."
    except Exception as e:
        return f"⚠️ Nota de inicialización: {e}"

# Ejecutamos la verificación al arrancar
status_instalacion = verificar_e_instalar_browsers()

# ===========================================
# 💻 CONFIGURACIÓN DE LA PÁGINA STREAMLIT
# ===========================================
st.set_page_config(page_title="Test de Conexión", page_icon="🌐", layout="wide")
st.title("🌐 Punto de Partida: Verificación de Entrada")
st.info(status_instalacion)

url_objetivo = st.text_input("URL a verificar:", "https://www.sofascore.com/es")
btn_conectar = st.button("🔌 Intentar Conectar y Tomar Captura")

# ===========================================
# ⚡ EJECUCIÓN SÍNCRONA DIRECTA
# ===========================================
if btn_conectar:
    st.write("⏳ Abriendo navegador en segundo plano...")
    
    try:
        with sync_playwright() as p:
            # Lanzamos el navegador con argumentos estándar para contenedores Linux
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            page = context.new_page()
            
            # Aplicamos protección anti-bloqueo básica
            stealth(page)
            
            st.write(f"🌍 Navegando directo a: {url_objetivo} ...")
            page.goto(url_objetivo, timeout=60000, wait_until="domcontentloaded")
            
            # Esperamos 5 segundos fijos para comprobar que la página responde y carga datos
            page.wait_for_timeout(5000)
            
            st.success("🎉 ¡Conexión establecida! Guardando captura de pantalla...")
            
            # Tomamos una foto de lo que está viendo el navegador en la nube
            screenshot_bytes = page.screenshot(full_page=False)
            
            # Mostramos la foto real directamente en la interfaz de Streamlit
            st.image(screenshot_bytes, caption="Vista en tiempo real desde el servidor de la nube", use_container_width=True)
            
            # Imprimimos el título de la página web para reconfirmar
            st.write(f"**Título de la página capturada:** {page.title()}")
            
            browser.close()
            
    except Exception as err:
        st.error(f"❌ Error al intentar acceder a la página: {err}")
