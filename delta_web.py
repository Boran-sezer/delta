import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore

# Initialisation avec réparation de clé
if not firebase_admin._apps:
    try:
        creds_dict = dict(st.secrets["firebase"])
        # REPARATION CRITIQUE ICI :
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur de clé : {e}")
        st.stop()

db = firestore.client()
client = Groq(api_key="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")

st.title("⚡ DELTA SYSTEM ONLINE")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    with st.chat_message("assistant"):
        r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=st.session_state.messages)
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
