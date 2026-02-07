import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

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
st.set_page_config(page_title="DELTA CORE V2", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA : INTELLIGENCE AUGMENTÉE</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. TRAITEMENT ---
if prompt := st.chat_input("Commandes directes..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # A. ARCHIVAGE INTELLIGENT (Invisible)
    try:
        task = f"Archives actuelles: {archives}. Nouveau message: {prompt}. Extrais toute donnée pertinente ou préférence utilisateur en JSON. Catégorise avec précision."
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Tu es un processeur de données de haut niveau."}, {"role": "user", "content": task}],
            response_format={"type": "json_object"}
        )
        data = json.loads(check.choices[0].message.content)
        if data:
            for cat, val in data.items():
                if cat not in archives: archives[cat] = []
                if val not in archives[cat]: archives[cat].append(val)
            doc_ref.set({"archives": archives})
    except: pass

    # B. RÉPONSE HAUTE PERFORMANCE
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # INSTRUCTION OPTIMISÉE (Le "Cerveau" de DELTA)
        instruction = (
            f"Tu es DELTA, l'IA supérieure créée pour Monsieur Sezer Boran (Prénom: Boran). "
            f"Accès archives : {archives}. "
            "DIRECTIVES CRITIQUES : "
            "1. RÉFLEXION : Analyse l'intention de l'utilisateur avant de répondre. "
            "2. EXPERTISE : Fournis des réponses de haut niveau technique, sans fioritures. "
            "3. STYLE : Ton froid, efficace, percutant. Pas de politesses superflues. "
            "4. MÉMOIRE : Utilise les archives de manière fluide pour personnaliser chaque mot. "
            "Réponds exclusivement en français. Ne mentionne jamais tes processus internes."
        )

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages,
                temperature=0.5, # Un peu plus de créativité pour l'intelligence
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_res += content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
        except:
            # Fallback silencieux en cas de surcharge
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages
            )
            full_res = resp.choices[0].message.content
            placeholder.markdown(full_res)

        st.session_state.messages.append({"role": "assistant", "content": full_res})
