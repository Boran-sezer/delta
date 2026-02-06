import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time

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
    st.session_state.messages = [{"role": "assistant", "content": "DELTA opérationnel, Créateur. Accès libre et gestion intelligente activés. ⚡"}]

# --- 3. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA - SYSTÈME OUVERT</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. TRAITEMENT, TRI AUTOMATIQUE ET RÉPONSE ---
if prompt := st.chat_input("Vos ordres, Créateur ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # A. TRI AUTOMATIQUE DANS LES PARTIES (Modèle Rapide)
    analyse_prompt = (
        f"L'utilisateur dit : '{prompt}'. Est-ce une info personnelle à classer ? "
        "Si oui, réponds UNIQUEMENT en JSON : {'partie': 'Catégorie', 'info': 'Détail'}. "
        "Sinon réponds 'NON'."
    )
    check = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": analyse_prompt}])
    reponse_tri = check.choices[0].message.content.strip()

    if "{" in reponse_tri:
        try:
            data = json.loads(reponse_tri.replace("'", '"'))
            res = doc_ref.get()
            archives = res.to_dict().get("archives", {}) if res.exists else {}
            
            partie = data['partie']
            if partie not in archives: archives[partie] = []
            if data['info'] not in archives[partie]:
                archives[partie].append(data['info'])
                doc_ref.set({"archives": archives})
                st.toast(f"📂 Classé dans [{partie}] : {data['info']}")
        except: pass

    # B. RÉPONSE DE DELTA AVEC ACCÈS DIRECT AUX ARCHIVES
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        
        # Récupération des archives pour que l'IA puisse décider seule de les utiliser
        res = doc_ref.get()
        archives = res.to_dict().get("archives", {}) if res.exists else {}
        
        instr = (
            f"Tu es DELTA, le majordome de Monsieur SEZER (ton Créateur). "
            f"Voici tes archives organisées par parties : {archives}. "
            "IMPORTANT : Ne montre ou ne cite ces archives QUE si la question du Créateur le nécessite. "
            "Si on te demande qui tu es ou ce que tu sais, sois bref. "
            "Réponds avec dévouement et efficacité."
        )

        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages,
            stream=True
        )

        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_raw += content
                for char in content:
                    displayed += char
                    placeholder.markdown(displayed + "▌")
                    time.sleep(0.01)

        placeholder.markdown(full_raw)
        st.session_state.messages.append({"role": "assistant", "content": full_raw})
