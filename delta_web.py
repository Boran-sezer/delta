import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        # Récupération de la clé encodée dans les secrets Streamlit
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        creds_dict = json.loads(decoded_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"⚠️ Erreur de connexion Mémoire : {e}")

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")

# --- CONNEXION GROQ ---
client = Groq(api_key="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")

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- CHARGEMENT DES DONNÉES DEPUIS FIREBASE ---
res = doc_ref.get()
if res.exists:
    faits = res.to_dict().get("faits", [])
else:
    faits = []
    doc_ref.set({"faits": []})

# --- BARRE LATÉRALE (ARCHIVES) ---
with st.sidebar:
    st.title("🧠 Archives de Monsieur")
    st.write("Informations mémorisées :")
    
    # Affichage des faits avec option de suppression
    for i, fait in enumerate(faits):
        col1, col2 = st.columns([4, 1])
        col1.info(fait)
        if col2.button("🗑️", key=f"del_{i}"):
            faits.pop(i)
            doc_ref.update({"faits": faits})
            st.rerun()

# --- INTERFACE DE CHAT ---
st.title("⚡ DELTA OS")

# Affichage de l'historique
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrée utilisateur
if prompt := st.chat_input("Quels sont vos ordres, Monsieur Boran ?"):
    # 1. Afficher le message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Préparation de l'instruction système avec la mémoire
    instruction = (
        "Tu es DELTA, une IA sophistiquée, majordome personnel de Monsieur Boran. "
        "Tu es loyal, efficace et tu as accès à ses archives personnelles pour personnaliser tes réponses. "
        f"Voici ce que tu sais sur lui : {', '.join(faits)}. "
        "Sois concis et utilise des émojis."
    )

    # 3. Appel à l'IA (Groq)
    with st.chat_message("assistant"):
        try:
            full_messages = [{"role": "system", "content": instruction}] + st.session_state.messages
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=full_messages,
                temperature=0.7
            )
            
            response = completion.choices[0].message.content
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

            # 4. ANALYSE POUR MÉMORISATION (Optionnel/Automatique)
            # Si le message semble contenir une info importante, l'IA pourrait suggérer de l'enregistrer
            # Ici, on reste sur la version simple : vous gérez manuellement via les archives.

        except Exception as e:
            st.error(f"Désolé Monsieur, une erreur système est survenue : {e}")
