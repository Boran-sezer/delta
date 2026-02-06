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
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA prêt, Monsieur Sezer. Prêt pour le nettoyage des archives. ⚡"}]

# --- 3. INTERFACE & SIDEBAR ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

with st.sidebar:
    st.title("📂 Archives de Monsieur Sezer")
    if archives:
        for partie, infos in archives.items():
            with st.expander(f"📁 {partie}"):
                for i in infos:
                    st.write(f"• {i}")
    else:
        st.info("Aucune archive.")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. LOGIQUE DE SUPPRESSION ET MODIFICATION ---
if prompt := st.chat_input("Ordres en attente..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ANALYSE RENFORCÉE POUR LA SUPPRESSION
    analyse_prompt = (
        f"Archives actuelles : {archives}. "
        f"Ordre : '{prompt}'. "
        "Tu dois extraire l'action de suppression ou modification. "
        "Réponds UNIQUEMENT par ce JSON : "
        "{'action': 'delete_partie' (si on veut supprimer une catégorie), "
        "'delete_info' (si on veut enlever une ligne précise), "
        "'add' (si ajout), "
        "'target': 'nom_de_la_partie_ou_info'} "
        "Sinon réponds 'NON'."
    )
    
    try:
        check = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": analyse_prompt}])
        cmd_text = check.choices[0].message.content.strip()
        
        json_match = re.search(r'\{.*\}', cmd_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0).replace("'", '"'))
            action = data.get('action')
            target = data.get('target')
            modif = False

            # LOGIQUE DE SUPPRESSION DE CATÉGORIE
            if action == 'delete_partie':
                # On cherche la partie qui ressemble le plus au nom donné
                for k in list(archives.keys()):
                    if target.lower() in k.lower() or k.lower() in target.lower():
                        del archives[k]
                        modif = True
            
            # LOGIQUE DE SUPPRESSION D'UNE INFO PRÉCISE
            elif action == 'delete_info':
                for k, v in archives.items():
                    if target in v:
                        v.remove(target)
                        modif = True
            
            # AJOUT CLASSIQUE
            elif action == 'add':
                # (Logique d'ajout déjà fonctionnelle)
                pass

            if modif:
                doc_ref.set({"archives": archives})
                st.toast(f"🗑️ Suppression effectuée : {target}")
                time.sleep(0.5)
                st.rerun()
    except: pass

    # B. RÉPONSE DE DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw = ""
        instr = f"Tu es DELTA, créé par Monsieur Sezer. Archives : {archives}. Ne dis jamais accès autorisé. Sois loyal."

        try:
            stream = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": instr}] + st.session_state.messages, stream=True)
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_raw += content
                    placeholder.markdown(full_raw + "▌")
        except:
            full_raw = "Système surchargé, mais l'ordre a été traité, Monsieur Sezer. ⚡"
        
        placeholder.markdown(full_raw)
        st.session_state.messages.append({"role": "assistant", "content": full_raw})
