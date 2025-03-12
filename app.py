import streamlit as st

# 📌 Configuration de la page principale
st.set_page_config(page_title="Application Fidealis", page_icon="📜")

# 📌 Menu de navigation
st.sidebar.title("🔍 Navigation")
page = st.sidebar.radio("Aller à :", ["Accueil", "Gestion des utilisateurs", "Traitement API"])

# 📌 Page d'accueil
if page == "Accueil":
    st.title("🏠 Accueil - Application Fidealis")
    st.write("Bienvenue dans l'application de gestion de Fidealis.")
    st.write("📌 Sélectionnez une page dans le menu de gauche pour commencer.")

# 📌 Gestion des utilisateurs
elif page == "Gestion des utilisateurs":
    st.title("👥 Gestion des utilisateurs")
    import gestion_utilisateurs

# 📌 Traitement API
elif page == "Traitement API":
    st.title("🔗 Traitement API")
    import api_processing
