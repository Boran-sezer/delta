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
st.set_page_config(page_title="DELTA AI - R1", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA : DEEP REASONING</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("Ordres, Monsieur Sezer..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # --- ANALYSEUR PAR RAISONNEMENT (DEEPSEEK R1) ---
    # Ce modèle va littéralement "réfléchir" à l'importance de l'info
    sys_analyse = (
        f"Tu es l'unité de raisonnement logique de Monsieur Sezer. Mémoire actuelle : {archives}. "
        f"Dernière interaction : '{prompt}'. "
        "MISSION : Analyse si ce message contient une information structurelle, technique ou personnelle vitale. "
        "Si oui, réorganise l'entièreté du JSON pour qu'il soit optimal. Supprime l'inutile, fusionne les doublons. "
        "Réponds EXCLUSIVEMENT avec le JSON complet. Si rien ne justifie une modification, réponds : IGNORE."
    )
    
    try:
        # Utilisation de DeepSeek-R1 pour une analyse ultra-logique
        check = client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b", 
            messages=[{"role": "system", "content": "Tu es un moteur d'analyse logique de haut niveau."}, {"role": "user", "content": sys_analyse}],
            temperature=0.1 # Basse température pour une précision maximale
        )
        verdict = check.choices[0].message.content.strip()
        
        # On extrait le JSON (DeepSeek peut inclure sa 'pensée' entre des balises <think>)
        json_match = re.search(r'\{.*\}', verdict, re.DOTALL)
        if json_match:
            nouvelles_archives = json.loads(json_match.group(0))
            if nouvelles_archives != archives:
                archives = nouvelles_archives
                doc_ref.set({"archives": archives})
                st.toast("🧠 Raisonnement appliqué : Mémoire restructurée")
    except: pass

    # --- 5. RÉPONSE DE DELTA ---
    with st.chat_message("assistant"):
        instruction_delta = (
            f"Tu es DELTA. Tu parles à Monsieur Sezer Boran. "
            f"Archives : {archives}. "
            "Sois percutant, froid, technique et extrêmement efficace."
        )
        placeholder = st.empty()
        full_response = ""
        try:
            # On reste sur Llama 3.3 pour la rapidité de conversation
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
