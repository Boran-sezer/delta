import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- 1. INITIALISATION SYSTÈME ---
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

# --- 2. MÉMOIRE ET ARCHIVES ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA LUX-CORE", layout="wide", page_icon="⚡")
st.markdown("<style>.stApp { background: #050a0f; color: #e0e0e0; }</style>", unsafe_allow_html=True)
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA : CORE SYSTEM</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. TRAITEMENT COMMANDES ---
if prompt := st.chat_input("Ordre..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # MISE À JOUR MÉMOIRE (Lux Style)
    try:
        task = (
            f"Archives: {archives}. Entrée: '{prompt}'. "
            "Action: Extraire faits réels ou corrections. Ignorer bruit. "
            "Sortie: JSON uniquement."
        )
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Mémoire vive DELTA."}, {"role": "user", "content": task}],
            response_format={"type": "json_object"}
        )
        nouvelles_archives = json.loads(check.choices[0].message.content)
        if nouvelles_archives != archives:
            archives = nouvelles_archives
            doc_ref.set({"archives": archives})
            st.toast("💾 Synchronisé", icon="✅")
    except: pass

    # GÉNÉRATION RÉPONSE
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        instruction = (
            f"Tu es DELTA. Créateur: Monsieur Sezer. "
            f"Données: {archives}. DATE: 2026. "
            "DIRECTIVES: "
            "1. CONCISION ABSOLUE: Pas de politesse, pas de blabla. Direct à l'essentiel. "
            "2. IDENTITÉ: Appelle l'utilisateur 'Monsieur Sezer'. "
            "3. VÉRITÉ: Ne jamais contredire les infos de l'utilisateur."
        )

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages,
                temperature=0.1,
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_res += content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
        except:
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages
            )
            full_res = resp.choices[0].message.content
            placeholder.markdown(full_res)

        st.session_state.messages.append({"role": "assistant", "content": full_res})

