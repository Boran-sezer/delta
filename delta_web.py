import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        creds_dict = json.loads(decoded_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur de connexion : {e}")

db = firestore.client()
# On crée un document unique pour votre mémoire (ex: "discussion_principale")
doc_ref = db.collection("memoire").document("chat_history")

# --- CONNEXION IA (GROQ) ---
client = Groq(api_key="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")

st.title("⚡ DELTA SYSTEM")

# --- CHARGEMENT DE LA MÉMOIRE DEPUIS LE CLOUD ---
if "messages" not in st.session_state:
    doc = doc_ref.get()
    if doc.exists:
        st.session_state.messages = doc.to_dict().get("history", [])
    else:
        st.session_state.messages = []

# Affichage des messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- LOGIQUE D'ENVOI ET SAUVEGARDE ---
if p := st.chat_input("Vos ordres, Monsieur ?"):
    # Ajouter le message utilisateur
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"):
        st.markdown(p)
    
    # Réponse de DELTA
    with st.chat_message("assistant"):
        instructions = {"role": "system", "content": "Tu es DELTA, créé par Monsieur Boran. Tu es son majordome fidèle."}
        full_history = [instructions] + st.session_state.messages
        r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=full_history)
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
    
    # --- SAUVEGARDE DANS LE CLOUD ---
    # C'est ici que la magie opère pour la synchronisation !
    doc_ref.set({"history": st.session_state.messages})
