import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore

# Connexion Cloud
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        # Réparation de la clé privée pour le Cloud
        fb_dict["private_key"] = fb_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur de configuration : {e}")
        st.stop()

db = firestore.client()
memoire_ref = db.collection("memoire_delta").document("session_boran")
client = Groq(api_key="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")

st.title("⚡ DELTA SYSTEM")

# Gestion de la mémoire
if "messages" not in st.session_state:
    doc = memoire_ref.get()
    st.session_state.messages = doc.to_dict().get("historique", []) if doc.exists else []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# Interaction
if p := st.chat_input("Vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    with st.chat_message("assistant"):
        r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=st.session_state.messages)
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
        memoire_ref.set({"historique": st.session_state.messages})
