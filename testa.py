import os
import requests
import streamlit as st
import psycopg2
from PIL import ImageOps, Image
from twilio.rest import Client
import base64



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

# 🚀 Connexion à la base de données
def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# 🚀 Création de la table si elle n'existe pas
def create_table():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sms_logs (
                id SERIAL PRIMARY KEY,
                utilisateur TEXT NOT NULL,
                numero TEXT NOT NULL,
                message TEXT NOT NULL,
                url TEXT NOT NULL,
                statut TEXT NOT NULL,
                date_heure TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        st.error(f"⚠️ Erreur lors de la création de la table : {e}")



# 🚀 Authentification
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
    # ✅ Création de la table au cas où elle n'existe pas
    create_table()

    # 🚀 Interface d'envoi de SMS
    st.title(f"📩 Envoi de SMS - Connecté en tant que {st.session_state['user']}")

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    # 📂 Upload CSV ou saisie manuelle des numéros
    uploaded_file = st.file_uploader("📂 Téléchargez un fichier CSV avec une colonne 'phone_number'", type=["csv"])
    manual_numbers = st.text_area("✍️ Ou entrez les numéros (séparés par une virgule)")

    phone_numbers = []

    # Configuration API Fidealis
    API_URL = os.getenv("API_URL")
    API_KEY = os.getenv("API_KEY")
    ACCOUNT_KEY = os.getenv("ACCOUNT_KEY")

    # Configuration API Google Maps
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


    # Fonction pour obtenir les coordonnées GPS à partir d'une adresse
    def get_coordinates(address):
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GOOGLE_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'OK':
                location = data['results'][0]['geometry']['location']
                return location['lat'], location['lng']
        return None, None


    # Fonction pour se connecter à l'API Fidealis
    def api_login():
        login_response = requests.get(
            f"{API_URL}?key={API_KEY}&call=loginUserFromAccountKey&accountKey={ACCOUNT_KEY}"
        )
        login_data = login_response.json()
        if 'PHPSESSID' in login_data:
            return login_data["PHPSESSID"]
        return None


    # Fonction pour appeler l'API Fidealis
    def api_upload_files(description, files, session_id):
        for i in range(0, len(files), 12):
            batch_files = files[i:i + 12]
            data = {
                "key": API_KEY,
                "PHPSESSID": session_id,
                "call": "setDeposit",
                "description": description,
                "type": "deposit",
                "hidden": "0",
                "sendmail": "1",
            }
            for idx, file in enumerate(batch_files, start=1):
                with open(file, "rb") as f:
                    encoded_file = base64.b64encode(f.read()).decode("utf-8")
                    data[f"filename{idx}"] = os.path.basename(file)
                    data[f"file{idx}"] = encoded_file
            requests.post(API_URL, data=data)


    # Fonction pour créer un collage
    def create_collage(images, output_path, max_images=3):
        min_height = min(img.size[1] for img in images)
        resized_images = [ImageOps.fit(img, (int(img.size[0] * min_height / img.size[1]), min_height)) for img in
                          images]
        total_width = sum(img.size[0] for img in resized_images) + (len(resized_images) - 1) * 20 + 50
        collage = Image.new("RGB", (total_width, min_height + 50), (255, 255, 255))
        x_offset = 25
        for img in resized_images:
            collage.paste(img, (x_offset, 25))
            x_offset += img.size[0] + 20
        collage.save(output_path)


    # Fonction pour créer tous les collages
    def create_all_collages(files, client_name):
        collages = []
        for i in range(0, len(files), 3):
            # Créer un groupe de 3 images (ou moins si les fichiers restants sont inférieurs à 3)
            group = files[i:i + 3]
            images = [Image.open(f) for f in group]

            # Nom du collage
            collage_name = f"c_{client_name}_{len(collages) + 1}.jpg"

            # Créer un collage pour ce groupe
            create_collage(images, collage_name, max_images=len(group))
            collages.append(collage_name)

        return collages


    # Function to get the quantity of product 4 (deposit package)
    def get_quantity_for_product_4(credit_data):
        if "4" in credit_data:
            return credit_data["4"]["quantity"]
        return "Product 4 not found."


    # Function to get the remaining credit for the client
    def get_credit(session_id):
        credit_url = f"{API_URL}?key={API_KEY}&PHPSESSID={session_id}&call=getCredits&product_ID="
        response = requests.get(credit_url)
        if response.status_code == 200:
            return response.json()  # Return the credit data
        return None


    # Interface utilisateur Streamlit
    st.title("Formulaire de dépôt FIDEALIS pour INFINY ")

    session_id = api_login()
    if session_id:
        # Appel pour obtenir les crédits pour le client
        credit_data = get_credit(session_id)

        # Vérifie si les données sont correctes
        if isinstance(credit_data, dict):
            # Isoler la quantité du produit 4
            product_4_quantity = get_quantity_for_product_4(credit_data)

            # Affichage des résultats en haut

            st.write(f"Crédit restant : {product_4_quantity}")
        else:
            st.error("Échec de la récupération des données de crédit.")
    else:
        st.error("Échec de la connexion.")

    client_name = st.text_input("Nom du client")
    address = st.text_input("Adresse complète (ex: 123 rue Exemple, Paris, France)")

    # Initialisation des champs Latitude et Longitude
    latitude = st.session_state.get("latitude", "")
    longitude = st.session_state.get("longitude", "")

    # Bouton pour générer automatiquement les coordonnées GPS
    if st.button("Générer les coordonnées GPS"):
        if address:
            lat, lng = get_coordinates(address)
            if lat is not None and lng is not None:
                st.session_state["latitude"] = str(lat)
                st.session_state["longitude"] = str(lng)
                latitude = str(lat)
                longitude = str(lng)
            else:
                st.error("Impossible de générer les coordonnées GPS pour l'adresse fournie.")

    # Champs Latitude et Longitude pré-remplis
    latitude = st.text_input("Latitude", value=latitude)
    longitude = st.text_input("Longitude", value=longitude)

    uploaded_files = st.file_uploader("Téléchargez les photos (JPEG/PNG)", accept_multiple_files=True,
                                      type=["jpg", "png"])

    if st.button("Soumettre"):
        if not client_name or not address or not latitude or not longitude or not uploaded_files:
            st.error("Veuillez remplir tous les champs et télécharger au moins une photo.")
        else:
            st.info("Préparation de l'envoi...")

            if session_id:
                # Sauvegarder les fichiers localement
                saved_files = []
                for idx, file in enumerate(uploaded_files):
                    save_path = f"{client_name}_temp_{idx + 1}.jpg"
                    with open(save_path, "wb") as f:
                        f.write(file.read())
                    saved_files.append(save_path)

                # Créer tous les collages
                st.info("Création des collages...")
                collages = create_all_collages(saved_files, client_name)

                # Renommer le premier collage pour inclure le nom du client
                first_collage = collages[0]
                renamed_first_collage = os.path.join(os.path.dirname(first_collage), f"{client_name}_1.jpg")
                os.rename(first_collage, renamed_first_collage)
                collages[0] = renamed_first_collage  # Met à jour le nom dans la liste

                # Description avec coordonnées GPS
                description = f"SCELLÉ NUMERIQUE Bénéficiaire: Nom: {client_name}, Adresse: {address}, Coordonnées GPS: Latitude {latitude}, Longitude {longitude}"

                # Appeler l'API avec les fichiers collages
                st.info("Envoi des données")
                api_upload_files(description, collages, session_id)
                st.success("Données envoyées avec succès !")
