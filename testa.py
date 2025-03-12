import streamlit as st
import os
import base64
import requests
import psycopg2
from psycopg2 import sql
import pandas as pd
from twilio.rest import Client
from PIL import Image, ImageOps

# 🚀 Configuration depuis les secrets de Streamlit
API_URL = st.secrets["API_URL"]
API_KEY = st.secrets["API_KEY"]
ACCOUNT_KEY = st.secrets["ACCOUNT_KEY"]
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

TWILIO_ACCOUNT_SID = st.secrets["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = st.secrets["TWILIO_AUTH_TOKEN"]
TWILIO_PHONE_NUMBER = st.secrets["TWILIO_PHONE_NUMBER"]
FORM_URL = st.secrets["FORM_URL"]

DB_HOST = st.secrets["DB_HOST"]
DB_NAME = st.secrets["DB_NAME"]
DB_USER = st.secrets["DB_USER"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_PORT = st.secrets["DB_PORT"]

users = {
    "admin": st.secrets["admin"],
    "user1": st.secrets["user1"],
    "user2": st.secrets["user2"]
}

# 🚀 Connexion à la base de données Reno
def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# 🚀 Création de la table pour stocker les logs des dépôts
def create_log_table():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fidealis_logs (
                id SERIAL PRIMARY KEY,
                utilisateur TEXT NOT NULL,
                client TEXT NOT NULL,
                adresse TEXT NOT NULL,
                latitude TEXT NOT NULL,
                longitude TEXT NOT NULL,
                fichiers TEXT NOT NULL,
                statut TEXT NOT NULL,
                date_heure TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"⚠️ Erreur lors de la création de la table : {e}")

# 🚀 Fonction pour enregistrer un dépôt dans les logs
def log_deposit(utilisateur, client, adresse, latitude, longitude, fichiers, statut):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO fidealis_logs (utilisateur, client, adresse, latitude, longitude, fichiers, statut)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (utilisateur, client, adresse, latitude, longitude, ", ".join(fichiers), statut))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"⚠️ Erreur lors de l'insertion dans la base : {e}")

# 🚀 Authentification utilisateur
if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = False

if not st.session_state["authentication_status"]:
    st.title("🔒 Connexion requise")
    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")

    if st.button("🔑 Se connecter"):
        if username in users and users[username] == password:
            st.session_state["authentication_status"] = True
            st.session_state["user"] = username
            st.rerun()
        else:
            st.error("❌ Identifiants incorrects. Veuillez réessayer.")

else:
    # ✅ Création de la table des logs si elle n'existe pas
    create_log_table()

    st.title("📜 Formulaire de dépôt FIDEALIS")

    # 📌 Connexion à l'API Fidealis
    def api_login():
        login_response = requests.get(
            f"{API_URL}?key={API_KEY}&call=loginUserFromAccountKey&accountKey={ACCOUNT_KEY}"
        )
        login_data = login_response.json()
        return login_data.get("PHPSESSID", None)

    session_id = api_login()
    if session_id:
        st.success("✅ Connecté à Fidealis")
    else:
        st.error("❌ Échec de la connexion à Fidealis")

    # 📌 Fonction pour obtenir les crédits restants
    def get_credit(session_id):
        credit_url = f"{API_URL}?key={API_KEY}&PHPSESSID={session_id}&call=getCredits"
        response = requests.get(credit_url)
        return response.json() if response.status_code == 200 else None

    if session_id:
        credit_data = get_credit(session_id)
        product_4_quantity = credit_data["4"]["quantity"] if credit_data and "4" in credit_data else "Non disponible"
        st.write(f"💰 Crédit restant : {product_4_quantity}")

    # 📌 Obtenir les coordonnées GPS d'une adresse
    def get_coordinates(address):
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GOOGLE_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'OK':
                location = data['results'][0]['geometry']['location']
                return location['lat'], location['lng']
        return None, None

    client_name = st.text_input("👤 Nom du client")
    address = st.text_input("🏠 Adresse complète")

    uploaded_files = st.file_uploader("📷 Téléchargez les photos", accept_multiple_files=True, type=["jpg", "png"])

    if st.button("📩 Soumettre"):
        if not client_name or not address or not uploaded_files:
            st.error("⚠️ Veuillez remplir tous les champs et télécharger au moins une photo.")
        else:
            st.info("🛠️ Traitement des fichiers...")

            saved_files = []
            for idx, file in enumerate(uploaded_files):
                save_path = f"{client_name}_temp_{idx + 1}.jpg"
                with open(save_path, "wb") as f:
                    f.write(file.read())
                saved_files.append(save_path)

            description = f"SCELLÉ NUMERIQUE Bénéficiaire: {client_name}, Adresse: {address}"

            # 📌 Appel API pour upload
            def api_upload_files(description, files, session_id):
                data = {
                    "key": API_KEY,
                    "PHPSESSID": session_id,
                    "call": "setDeposit",
                    "description": description,
                    "type": "deposit",
                    "hidden": "0",
                    "sendmail": "1",
                }
                for idx, file in enumerate(files, start=1):
                    with open(file, "rb") as f:
                        encoded_file = base64.b64encode(f.read()).decode("utf-8")
                        data[f"filename{idx}"] = os.path.basename(file)
                        data[f"file{idx}"] = encoded_file
                requests.post(API_URL, data=data)

            api_upload_files(description, saved_files, session_id)
            log_deposit(st.session_state["user"], client_name, address, "", "", saved_files, "Succès")
            st.success("✅ Données envoyées avec succès !")

    # 🚀 Affichage des logs
    st.title("📊 Historique des dépôts")
    def get_logs(utilisateur):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "SELECT * FROM fidealis_logs WHERE utilisateur = %s ORDER BY date_heure DESC;"
            cursor.execute(query, (utilisateur,))
            logs = cursor.fetchall()
            cursor.close()
            conn.close()
            return logs
        except Exception as e:
            st.error(f"⚠️ Erreur lors de la récupération des logs : {e}")
            return []

    logs = get_logs(st.session_state["user"])
    if logs:
        df_logs = pd.DataFrame(logs, columns=["ID", "Utilisateur", "Client", "Adresse", "Latitude", "Longitude", "Fichiers", "Statut", "Date & Heure"])
        st.dataframe(df_logs)
    else:
        st.write("📭 Aucun dépôt enregistré pour le moment.")

    # 🚪 Déconnexion
    if st.button("🚪 Se déconnecter"):
        st.session_state["authentication_status"] = False
        st.rerun()
