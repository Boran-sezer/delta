import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import re

# --- 1. INITIALISATION ---
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

# --- 2. RÉCUPÉRATION MÉMOIRE ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA AI - Stabilité", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA : MOTEUR LLAMA 3.3 STABLE</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("Ordres, Monsieur Sezer..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # --- ANALYSEUR DE MÉMOIRE (MODÈLE STABLE 70B) ---
    sys_analyse = (
        f"Tu es l'intelligence de gestion de données de Monsieur Sezer Boran. Mémoire actuelle : {archives}. "
        f"Dernier message : '{prompt}'. "
        "Analyse si une information doit être apprise, modifiée ou supprimée. "
        "Réponds EXCLUSIVEMENT avec l'objet JSON complet des archives mis à jour. "
        "Ne donne aucune explication technique, juste le JSON."
    )
    
    try:
        # Utilisation du modèle 70B Versatile (Le plus stable sur Groq)
        check = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "system", "content": "Tu es un moteur de base de données JSON."}, {"role": "user", "content": sys_analyse}],
            temperature=0,
            response_format={"type": "json_object"} # Force le format JSON
        )
        verdict = check.choices[0].message.content
        
        json_match = re.search(r'\{.*\}', verdict, re.DOTALL)
        if json_match:
            nouvelles_archives = json.loads(json_match.group(0))
            if nouvelles_archives != archives:
                doc_ref.set({"archives": nouvelles_archives})
                archives = nouvelles_archives
                st.toast("💾 Firebase : Mémoire synchronisée")
    except Exception as e:
        st.error(f"Erreur système : {e}")

    # --- 5. RÉPONSE DE DELTA ---
    with st.chat_message("assistant"):
        instruction_delta = (
            f"Tu es DELTA. Tu parles à Monsieur Sezer Boran. "
            f"Données Firebase : {archives}. "
            "Réponse technique, percutante et brève."
        )
        placeholder = st.empty()
        full_response = ""
        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages,
                temperature=0.3, stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
        except: placeholder.markdown("Liaison interrompue.")
        st.session_state.messages.append({"role": "assistant", "content": full_response})
