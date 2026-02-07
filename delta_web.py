import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- 1. CONNEXION ---
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

# --- 2. DONNÉES ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA CORE", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA : CORE SYSTEM</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. TRAITEMENT ---
if prompt := st.chat_input("Ordres directs..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # A. ARCHIVAGE ULTRA-SIMPLE (Invisible)
    try:
        # On demande juste la modif, pas tout le dictionnaire
        task = f"Infos actuelles: {archives}. Nouveau message: {prompt}. Si info importante, donne UNIQUEMENT un JSON avec la clé 'update' (ex: {{'update': {{'CAT': 'INFO'}}}}). Sinon {{}}."
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Tu es un extracteur de données strict."}, {"role": "user", "content": task}],
            response_format={"type": "json_object"}
        )
        data = json.loads(check.choices[0].message.content)
        if "update" in data:
            for cat, val in data["update"].items():
                if cat not in archives: archives[cat] = []
                if val not in archives[cat]: archives[cat].append(val)
            doc_ref.set({"archives": archives})
            st.toast("💾 Mémoire synchronisée")
    except: pass

    # B. RÉPONSE (Priorité Stabilité)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # On définit le modèle selon la disponibilité
        model_to_use = "llama-3.3-70b-versatile"
        
        instruction = f"Tu es DELTA. Tu parles à Monsieur Sezer Boran. Voici ce que tu sais de lui: {archives}. Réponds de façon brève, en français, et n'affiche JAMAIS de code JSON."

        try:
            stream = client.chat.completions.create(
                model=model_to_use,
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages,
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_res += content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
        except Exception as e:
            # Si le gros modèle crash (Rate limit), on bascule sur le petit DIRECTEMENT
            st.warning("Passage en mode léger (Quota atteint)")
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages
            )
            full_res = resp.choices[0].message.content
            placeholder.markdown(full_res)

        st.session_state.messages.append({"role": "assistant", "content": full_res})
