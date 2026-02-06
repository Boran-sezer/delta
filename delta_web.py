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

# --- 2. RÉCUPÉRATION ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Archives de Monsieur Sezer")
    if archives:
        for cat, items in archives.items():
            with st.expander(f"📁 {cat}"):
                for i in items: st.write(f"• {i}")
    else:
        st.info("Archives vides.")

if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA paré, Monsieur Sezer. ⚡"}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LE CERVEAU (LOGIQUE DE DÉCISION) ---
if prompt := st.chat_input("Ordre ou message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Analyse simplifiée mais ultra-puissante
    analyse_prompt = (
        f"Archives : {list(archives.keys())}. "
        f"Message : '{prompt}'. "
        "Réponds UNIQUEMENT par un JSON : "
        "- Si RENOMMER catégorie: {'action': 'rename', 'old': 'nom', 'new': 'nom'} "
        "- Si AJOUTER/ARCHIVER : {'action': 'add', 'cat': 'nom', 'val': 'texte'} "
        "- Si SUPPRIMER catégorie: {'action': 'delete', 'cat': 'nom'} "
        "- Sinon: {'action': 'none'}"
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Tu es un terminal JSON strict."}, {"role": "user", "content": analyse_prompt}],
            temperature=0
        )
        data = json.loads(re.search(r'\{.*\}', check.choices[0].message.content).group(0).replace("'", '"'))
        action = data.get('action')
        modif = False

        if action == 'rename':
            o, n = data.get('old'), data.get('new')
            if o in archives:
                archives[n] = archives.pop(o)
                modif = True
        elif action == 'add':
            c, v = data.get('cat', 'Général'), data.get('val')
            if v and v not in archives.get(c, []):
                if c not in archives: archives[c] = []
                archives[c].append(v)
                modif = True
        elif action == 'delete':
            c = data.get('cat')
            if c in archives:
                del archives[c]
                modif = True

        if modif:
            doc_ref.set({"archives": archives})
            st.toast("✅ Base mise à jour")
            time.sleep(0.4)
            st.rerun()
    except: pass

    # B. RÉPONSE (AVEC LES ARCHIVES EN MÉMOIRE)
    with st.chat_message("assistant"):
        # On donne TOUTES les archives à l'IA pour qu'elle sache de quoi elle parle
        mem_context = "Tu connais ces infos sur Monsieur Sezer : " + str(archives)
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": f"Tu es DELTA. {mem_context}. Sois bref et précis."}] + st.session_state.messages
            )
            txt = resp.choices[0].message.content
        except:
            txt = "Mise à jour effectuée, Monsieur Sezer. ⚡"
        
        st.markdown(txt)
        st.session_state.messages.append({"role": "assistant", "content": txt})
