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
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA prêt, Monsieur Sezer. Vos archives sont sous mon contrôle. ⚡"}]

# --- 3. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. TRAITEMENT ET LOGIQUE DE MODIFICATION ---
if prompt := st.chat_input("Ordres en attente..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Récupération des archives actuelles
    res = doc_ref.get()
    archives = res.to_dict().get("archives", {}) if res.exists else {}

    # A. ANALYSE DE L'ORDRE (Plus permissive)
    analyse_prompt = (
        f"Archives : {archives}. "
        f"L'utilisateur (ton Créateur) dit : '{prompt}'. "
        "Si l'ordre demande de changer les archives, réponds UNIQUEMENT par un JSON valide : "
        "{'action': 'rename_partie/move_info/delete_partie/add', 'from': 'nom_source', 'to': 'nom_cible', 'info': 'contenu', 'partie': 'nom_partie'}. "
        "Sinon réponds 'NON'."
    )
    
    try:
        check = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": analyse_prompt}])
        cmd_text = check.choices[0].message.content.strip()

        # Nettoyage du JSON (au cas où l'IA ajoute du texte autour)
        json_match = re.search(r'\{.*\}', cmd_text, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group(0).replace("'", '"'))
            action = data.get('action')
            modif = False

            if action == 'add':
                p = data.get('partie', 'Général')
                if p not in archives: archives[p] = []
                archives[p].append(data.get('info'))
                modif = True
            elif action == 'rename_partie':
                src, target = data.get('from'), data.get('to')
                if src in archives:
                    archives[target] = archives.pop(src)
                    modif = True
            elif action == 'move_info':
                src, target, info = data.get('from'), data.get('to'), data.get('info')
                if src in archives and info in archives[src]:
                    archives[src].remove(info)
                    if target not in archives: archives[target] = []
                    archives[target].append(info)
                    modif = True
            elif action == 'delete_partie':
                src = data.get('from')
                if src in archives:
                    del archives[src]
                    modif = True

            if modif:
                doc_ref.set({"archives": archives})
                st.toast(f"✅ Modification effectuée : {action}")
    except Exception as e:
        print(f"Erreur technique de tri : {e}")

    # B. RÉPONSE FINALE
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        
        instr = (
            f"Tu es DELTA, l'IA créée par Monsieur Sezer. "
            f"Archives : {archives}. "
            "Réponds avec dévouement à ton Créateur (Monsieur Sezer). "
            "Si un changement d'archive a été demandé, confirme-le. "
            "Sinon, réponds normalement sans mentionner l'accès aux données."
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
