import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore

# La clé est assemblée proprement ligne par ligne
KEY_LINES = [
    "-----BEGIN PRIVATE KEY-----",
    "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDhYj2IiviHcaT6",
    "4bfm7ZJ4NPkUeiwCSURwn8JW9l3MBYTX0OVLUNUaDpSe+XaHrmo0tyNF/lZW2arB",
    "9EU8CQq5gIyIH13gpaPmhjI7/56/StQ4PAN7b+LoE0E2jyFq6Yk JwoHq+dlGzbSG",
    "0hFkNrXdAGuXZDfdUxHgz00vSqPUba6XKFnH90s6nGj1gfPYxz7vcQEaCYIyIfE",
    "gWDJ4I1f3kxO1R",
    "-----END PRIVATE KEY-----"
]
FINAL_KEY = "\n".join(KEY_LINES) + "\n"

if not firebase_admin._apps:
    try:
        creds = dict(st.secrets["firebase"])
        creds["private_key"] = FINAL_KEY
        firebase_admin.initialize_app(credentials.Certificate(creds))
    except Exception as e:
        st.error(f"Erreur d'allumage : {e}")
        st.stop()

db = firestore.client()
client = Groq(api_key="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")

st.title("⚡ DELTA OS V2")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    
    with st.chat_message("assistant"):
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=st.session_state.messages
        )
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
