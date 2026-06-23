import streamlit as st
import pandas as pd
import os
import subprocess
import sys
from streamlit_autorefresh import st_autorefresh

# --- NUEVO: Instala los binarios aislados de Playwright si no existen ---
@st.cache_resource
def instalar_dependencias_playwright():
    try:
        # Esto descarga únicamente el Chromium interno de Playwright sin romper apt-get
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"Error inicializando componentes del navegador: {e}")

instalar_dependencias_playwright()
# -----------------------------------------------------------------------

# CONFIGURACIÓN DE LA INTERFAZ
st.set_page_config(page_title="Radar Live 24/7", page_icon="⚽", layout="wide")
# ... (el resto de tu código de app.py se queda exactamente igual)
