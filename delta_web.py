import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time
import re

# --- 1. CONNEXION FIREBASE ---
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

# --- 2. RÉCUPÉRATION DES DONNÉES ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA AI", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("Commandes, Monsieur Sezer..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    if "archive" in prompt.lower():
        with st.chat_message("assistant"):
            st.markdown("### 🗄️ GESTIONNAIRE DE MÉMOIRE")
            for section, items in archives.items():
                with st.expander(f"📁 {section.upper()}"):
                    for i, item in enumerate(items): st.write(f"{i+1}. {item}")
        st.stop()

    # --- ANALYSEUR DE MÉMOIRE FLEXIBLE ---
    # Ici, on demande à l'IA de trouver l'info même si l'orthographe est différente
    sys_analyse = (
        f"Tu es l'architecte de mémoire de Monsieur Sezer. Archives : {archives}. "
        f"Ordre : '{prompt}'. "
        "Si l'utilisateur demande de supprimer ou déplacer, identifie l'info même si l'orthographe est imprécise. "
        "Réponds UNIQUEMENT en JSON :\n"
        "1. {'action':'add', 'cat':'NOM', 'val':'INFO'}\n"
        "2. {'action':'move', 'from':'NOM', 'to':'NOM', 'old_val':'INFO_EXACTE_DANS_ARCHIVE', 'new_val':'INFO'}\n"
        "3. {'action':'delete', 'cat':'NOM', 'val':'INFO_EXACTE_DANS_ARCHIVE'}\n"
        "Si aucune action, réponds {'action':'none'}."
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Gestionnaire de données intelligent."}, {"role": "user", "content": sys_analyse}],
            temperature=0
        )
        match = re.search(r'\{.*\}', check.choices[0].message.content, re.DOTALL)
        if match:
            data = json.loads(match.group(0).replace("'", '"'))
            action = data.get('action')
            
            if action == 'add':
                c, v = data.get('cat'), data.get('val')
                if c not in archives: archives[c] = []
                if v not in archives[c]: 
                    archives[c].append(v)
                    st.toast(f"✅ Enregistré")
            
            elif action == 'move':
                f, t, ov, nv = data.get('from'), data.get('to'), data.get('old_val'), data.get('new_val')
                if f in archives and ov in archives[f]:
                    archives[f].remove(ov)
                    if not archives[f]: del archives[f]
                    if t not in archives: archives[t] = []
                    archives[t].append(nv)
                    st.toast(f"🔄 Déplacé")
            
            elif action == 'delete':
                c, v = data.get('cat'), data.get('val')
                if c in archives and v in archives[c]:
                    archives[c].remove(v)
                    if not archives[c]: del archives[c]
                    st.toast(f"🗑️ Supprimé")
            
            if action != 'none':
                doc_ref.set({"archives": archives})
    except: pass

    # --- RÉPONSE DELTA ---
    with st.chat_message("assistant"):
        instr = f"Tu es DELTA. Tu parles à Monsieur Sezer. Mémoire : {archives}. Bref."
        placeholder = st.empty()
        full_response = ""
        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instr}] + st.session_state.messages,
                temperature=0.3, stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
        except: placeholder.markdown("Erreur.")
        st.session_state.messages.append({"role": "assistant", "content": full_response})
