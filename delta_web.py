import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

st.set_page_config(page_title="DELTA LUX", layout="wide")
st.markdown("<style>.stApp { background: #050a0f; color: #e0e0e0; } button { display: none; }</style>", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input(""):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    try:
        task = f"Archives: {archives}. Info: {prompt}. Update JSON. No talk."
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Memory update only. JSON output."}, {"role": "user", "content": task}],
            response_format={"type": "json_object"}
        )
        nouvelles_archives = json.loads(check.choices[0].message.content)
        if nouvelles_archives != archives:
            doc_ref.set({"archives": nouvelles_archives})
            archives = nouvelles_archives
    except: pass

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        instruction = (
            f"Tu es DELTA. Créateur: Monsieur Sezer. Data: {archives}. Date: 2026. "
            "DIRECTIVES: Réponse ultra-courte. Pas de phrases d'introduction. Pas de politesse. "
            "Donne l'info brute. Appelle l'utilisateur Monsieur Sezer uniquement à la fin."
        )

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages,
                temperature=0.0,
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_res += content
                    placeholder.markdown(full_res)
        except:
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages
            )
            full_res = resp.choices[0].message.content
            placeholder.markdown(full_res)

        st.session_state.messages.append({"role": "assistant", "content": full_res})
