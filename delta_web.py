import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore

# Initialisation sécurisée
if not firebase_admin._apps:
    try:
        # On lit directement les secrets sans transformation compliquée
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Monsieur, il y a un problème avec la clé Firebase : {e}")
        st.stop()

db = firestore.client()
memoire_ref = db.collection("memoire_delta").document("session_boran")
client = Groq(api_key="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")

st.title("⚡ DELTA SYSTEM")

# Chargement de l'historique
if "messages" not in st.session_state:
    doc = memoire_ref.get()
    st.session_state.messages = doc.to_dict().get("historique", []) if doc.exists else []

# Affichage des messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Entrée utilisateur
if p := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    
    with st.chat_message("assistant"):
        r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=st.session_state.messages)
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
        # Sauvegarde
        memoire_ref.set({"historique": st.session_state.messages})
