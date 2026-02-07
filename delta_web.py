import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- 1. INITIALISATION FIREBASE & API ---
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
st.set_page_config(page_title="DELTA CORE V2", layout="wide", page_icon="⚡")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA : SYSTÈME NERVEUX OPTIMISÉ</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("En attente de vos ordres..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # A. MISE À JOUR INTELLIGENTE (Filtre de pertinence)
    try:
        # On demande à l'IA d'être juge de ce qui mérite d'être archivé
        task = (
            f"Archives actuelles : {archives}. "
            f"Nouveau message : {prompt}. "
            "MISSION : Analyse si le message contient une information réelle sur Monsieur Sezer (goûts, âge, faits, corrections). "
            "1. Si c'est du bruit (salutations, remerciements, phrases vides) : retourne l'objet 'archives' identique. "
            "2. Si c'veut corriger ou ajouter une info : mets à jour et retourne le JSON complet. "
            "Retourne UNIQUEMENT le JSON."
        )
        
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Tu es le processeur sélectif de DELTA. Tu ignores le bruit et ne gardes que les faits."}, {"role": "user", "content": task}],
            response_format={"type": "json_object"}
        )
        nouvelles_archives = json.loads(check.choices[0].message.content)
        
        # Enregistrement si changement détecté
        if nouvelles_archives != archives:
            doc_ref.set({"archives": nouvelles_archives})
            archives = nouvelles_archives
            st.toast("💾 Mémoire mise à jour", icon="✅")
    except: pass

    # B. RÉPONSE DE DELTA (Intelligence Supérieure)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        instruction = (
            f"Tu es DELTA, l'IA de Monsieur Sezer. "
            f"Données actuelles sur lui : {archives}. "
            "DIRECTIVES : "
            "1. IDENTITÉ : Appelle-le toujours Monsieur Sezer. "
            "2. RÉCAPITULATIF : S'il demande ce que tu sais, liste les faits de manière élégante (liste ou phrases), sans mentionner le stockage technique ou le JSON. "
            "3. STYLE : Ton froid, efficace, technique. Ne sois pas trop poli."
        )

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages,
                temperature=0.4,
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_res += content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
        except:
            # Fallback en cas de quota atteint
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages
            )
            full_res = resp.choices[0].message.content
            placeholder.markdown(full_res)

        st.session_state.messages.append({"role": "assistant", "content": full_res})
