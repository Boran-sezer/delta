import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time

# --- 1. CONFIG ---
CODE_ACT = "20082008"
CODE_MASTER = "B2008a2020@"

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

# --- 2. ÉTATS ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "DELTA prêt. ⚡"}]
if "locked" not in st.session_state: st.session_state.locked = False

# --- 3. MÉMOIRE ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. SÉCURITÉ ---
if st.session_state.locked:
    st.error("🚨 BLOQUÉ")
    if st.text_input("CODE MAÎTRE :", type="password") == CODE_MASTER:
        st.session_state.locked = False
        st.rerun()
    st.stop()

# --- 5. GÉNÉRATEUR ULTRA-CONCIS ---
def flux_delta(prompt):
    instr = (
        "Tu es DELTA, majordome de Monsieur SEZER. "
        "SOIS ULTRA-CONCIS. Interdiction de faire des phrases longues ou des politesses excessives. "
        "Réponds en une phrase maximum si possible. "
        "Ne mentionne jamais tes archives. "
        f"Infos : {faits}. "
        "Si besoin d'archiver : 'ACTION_ARCHIVE: [info]'."
    )
    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": instr}] + st.session_state.messages,
        stream=True
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content: yield content

# --- 6. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        
        for chunk in flux_delta(prompt):
            full_raw += chunk
            if "ACTION_ARCHIVE" in full_raw: break
            for char in chunk:
                displayed += char
                placeholder.markdown(displayed + "▌")
                time.sleep(0.02)
        
        clean = full_raw.split("ACTION_ARCHIVE")[0].strip()
        placeholder.markdown(clean)

        if "ACTION_ARCHIVE:" in full_raw:
            info = full_raw.split("ACTION_ARCHIVE:")[1].strip()
            if info not in faits:
                faits.append(info)
                doc_ref.set({"faits": faits}, merge=True)

    st.session_state.messages.append({"role": "assistant", "content": clean})
