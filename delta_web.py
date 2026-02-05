import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64

if not firebase_admin._apps:
    try:
        # Récupération des infos de base
        creds_dict = dict(st.secrets["firebase"])
        
        # Décodage de la clé "incassable"
        encoded_key = st.secrets["firebase_key"]["encoded_key"]
        decoded_key = base64.b64decode(encoded_key).decode("utf-8")
        
        # Injection de la clé décodée
        creds_dict["private_key"] = decoded_key
        
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur système critique : {e}")
        st.stop()

db = firestore.client()
client = Groq(api_key="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")

st.title("⚡ DELTA - ACCÈS TOTAL")

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
        st.session_state.messages.append({"role": "assistant", "content": rep})].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
