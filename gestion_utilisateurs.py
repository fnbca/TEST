import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Gestion des Utilisateurs", page_icon="👥")

st.title("👥 Gestion des Utilisateurs - Prime Énergie")

# Connexion PostgreSQL
def get_db_connection():
    return psycopg2.connect(
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"]
    )

# Récupérer les utilisateurs
def get_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom, email, telephone, date_inscription FROM Prime ORDER BY date_inscription DESC;")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return users
    except Exception as e:
        st.error(f"⚠️ Erreur lors de la récupération des utilisateurs : {e}")
        return []

# 📌 Affichage des utilisateurs enregistrés
st.header("📋 Liste des utilisateurs")
users = get_users()
if users:
    df = pd.DataFrame(users, columns=["ID", "Nom", "Email", "Téléphone", "Date d'inscription"])
    st.dataframe(df)
else:
    st.write("📭 Aucun utilisateur enregistré pour le moment.")
