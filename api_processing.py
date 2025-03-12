import streamlit as st
import requests

st.set_page_config(page_title="Traitement API", page_icon="🔗")

st.title("🔗 Interactions avec l'API Fidealis")

API_URL = st.secrets["API_URL"]
API_KEY = st.secrets["API_KEY"]

# 📌 Fonction d'appel API
def get_fidealis_data():
    response = requests.get(f"{API_URL}?key={API_KEY}&call=getCredits")
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"❌ Erreur API : {response.status_code}")
        return None

if st.button("🔍 Vérifier les crédits API"):
    data = get_fidealis_data()
    if data:
        st.json(data)
