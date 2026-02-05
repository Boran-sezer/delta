import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore

# Reconstruction chirurgicale de la clé pour éviter le bug InvalidLength
KEY_PART1 = "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDhYj2IiviHcaT6"
KEY_PART2 = "4bfm7ZJ4NPkUeiwCSURwn8JW9l3MBYTX0OVLUNUaDpSe+XaHrmo0tyNF/lZW2arB"
KEY_PART3 = "9EU8CQq5gIyIH13gpaPmhjI7/56/StQ4PAN7b+LoE0E2jyFq6Yk JwoHq+dlGzbSG"
KEY_PART4 = "0hFkNrXdAGuXZDfdUxHgz00vSqPUba6XKFnH90s6nGj1gfPYxz7vcQEaCYIyIfE"
KEY_PART5 = "gWDJ4I1f3kxO1R"

CLE_PROPRE = f"-----BEGIN PRIVATE KEY-----\n{KEY_PART1}\n{KEY_PART2}\n{KEY_PART3}\n{KEY_PART4}\n{KEY_PART5}\n-----END PRIVATE KEY-----\n"

if not firebase_admin._apps:
    try:
        # On utilise les secrets pour tout, sauf la clé qu'on a reconstruite au-dessus
        config = dict(st.secrets["firebase"])
        config["private_key"] = CLE_PROPRE
        
        cred = credentials.Certificate(config)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Alerte Système : {e}")
        st.stop()

db = firestore.client()
client = Groq(api_key="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")

st.title("⚡ DELTA OS - PROTOCOLE FINAL")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Commandes ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    with st.chat_message("assistant"):
        r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=st.session_state.messages)
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
