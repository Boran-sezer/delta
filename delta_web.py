import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- INITIALISATION DE LA MÉMOIRE (FIREBASE) ---
if not firebase_admin._apps:
    try:
        # Récupération et nettoyage de la clé Base64
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        # Décodage du JSON complet
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        creds_dict = json.loads(decoded_json)
        
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.warning(f"⚠️ MÉMOIRE : Erreur d'accès ({e}). Mode temporaire activé.")

# --- CONNEXION IA (GROQ) ---
client = Groq(api_key="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")

st.title("⚡ DELTA SYSTEM")
st.markdown("---")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    
    with st.chat_message("assistant"):
        instructions = {
            "role": "system", 
            "content": "Tu es DELTA, créé exclusivement par Monsieur Boran. Tu es son majordome fidèle et technologique."
        }
        full_history = [instructions] + st.session_state.messages
        r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=full_history)
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
