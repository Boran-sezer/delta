import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time
import re

# --- 1. CONFIGURATION ---
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

# --- 2. ÉTATS DE SESSION ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA opérationnel, Monsieur Sezer. ⚡"}]

# --- 3. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. TRAITEMENT ---
if prompt := st.chat_input("Ordres en attente..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    res = doc_ref.get()
    archives = res.to_dict().get("archives", {}) if res.exists else {}

    # ANALYSE DE L'ORDRE (On utilise le petit modèle 8b ici car il a des limites plus hautes)
    analyse_prompt = f"Archives : {archives}. Ordre : '{prompt}'. Réponds en JSON : {{'action': '...', ...}} ou 'NON'."
    try:
        check = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": analyse_prompt}])
        # ... (Logique de tri identique)
    except: pass

    # RÉPONSE DE DELTA AVEC SÉCURITÉ ANTI-SATURATION
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw = ""
        
        instr = f"Tu es DELTA, créé par Monsieur Sezer. Archives : {archives}. Respecte Monsieur Sezer."

        # Tentative avec le modèle puissant
        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instr}] + st.session_state.messages,
                stream=True
            )
        except Exception as e:
            # SI RATE LIMIT -> On bascule sur le modèle 8B instantanément
            if "rate_limit" in str(e).lower():
                st.warning("⚠️ Charge système élevée, passage en mode rapide.")
                stream = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "system", "content": instr}] + st.session_state.messages,
                    stream=True
                )
            else:
                st.error("Erreur critique.")
                st.stop()

        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_raw += content
                placeholder.markdown(full_raw + "▌")
        
        placeholder.markdown(full_raw)
        st.session_state.messages.append({"role": "assistant", "content": full_raw})
