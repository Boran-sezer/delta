import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time

# --- 1. CONFIGURATION ---
CODE_ACT = "20082008"
CODE_MASTER = "B2008a2020@"

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
    st.session_state.messages = [{"role": "assistant", "content": "DELTA opérationnel. ⚡"}]
if "locked" not in st.session_state: st.session_state.locked = False
if "ask_auth" not in st.session_state: st.session_state.ask_auth = False
if "target_prompt" not in st.session_state: st.session_state.target_prompt = None

# --- 3. CHARGEMENT MÉMOIRE ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. SÉCURITÉ LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME VERROUILLÉ")
    if st.text_input("CODE MAÎTRE :", type="password", key="lock") == CODE_MASTER:
        st.session_state.locked = False
        st.rerun()
    st.stop()

# --- 5. FONCTION DE RÉPONSE ---
def reponse_delta(prompt, mode="normal"):
    if mode == "archives":
        instr = f"Tu es DELTA. Liste ces informations de manière brute et courte : {faits}."
    else:
        instr = (
            f"Tu es DELTA, majordome de Monsieur SEZER. Sois ultra-concis. "
            f"Archives : {faits}. "
            "Si Monsieur demande de supprimer, réponds : 'ACTION_DELETE: [mot]'."
            "Sinon : 'ACTION_ARCHIVE: [info]'."
        )

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages,
            stream=True
        )
        
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_raw += content
                if "ACTION_" in full_raw: break
                for char in content:
                    displayed += char
                    placeholder.markdown(displayed + "▌")
                    time.sleep(0.01)
        
        clean = full_raw.split("ACTION_")[0].strip()
        if not clean and "ACTION_DELETE" in full_raw:
            clean = "Mémoire mise à jour, Monsieur SEZER."
        
        placeholder.markdown(clean)
        st.session_state.messages.append({"role": "assistant", "content": clean})

        # ACTIONS SUR LA BASE DE DONNÉES
        if "ACTION_DELETE:" in full_raw:
            cible = full_raw.split("ACTION_DELETE:")[1].strip().lower()
            nouveaux_faits = [f for f in faits if cible not in f.lower()]
            doc_ref.set({"faits": nouveaux_faits}, merge=True)
            st.rerun()

        if "ACTION_ARCHIVE:" in full_raw:
            info = full_raw.split("ACTION_ARCHIVE:")[1].strip()
            if info not in faits:
                faits.append(info)
                doc_ref.set({"faits": faits}, merge=True)

# --- 6. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# FORMULAIRE DE SÉCURITÉ (Bloque tout affichage mémoire)
if st.session_state.ask_auth:
    with st.chat_message("assistant"):
        st.warning("🔒 Accès restreint. Identifiez-vous.")
        code = st.text_input("CODE :", type="password", key="auth_key")
        if st.button("VALIDER"):
            if code == CODE_ACT:
                st.session_state.ask_auth = False
                reponse_delta("Affichage", mode="archives")
                st.rerun()
            else:
                st.error("Accès refusé.")
    st.stop()

# ENTRÉE UTILISATEUR
if prompt := st.chat_input("Vos ordres ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    p_low = prompt.lower()
    
    # 1. Vérification Verrouillage
    if "verrouille" in p_low:
        st.session_state.locked = True
        st.rerun()
    
    # 2. Vérification Sécurité Mémoire (SCAN TOTAL)
    mots_interdits = ["mémoire", "archive", "souviens", "faits", "notes", "qu'est-ce que tu sais"]
    if any(w in p_low for w in mots_interdits):
        st.session_state.ask_auth = True
        st.rerun()
    
    # 3. Traitement normal (inclut suppression)
    else:
        reponse_delta(prompt)
        st.rerun()
