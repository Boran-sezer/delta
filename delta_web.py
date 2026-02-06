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

# --- 2. ÉTATS ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "DELTA opérationnel. En attente d'ordres. ⚡"}]
if "locked" not in st.session_state: st.session_state.locked = False
if "auth_done" not in st.session_state: st.session_state.auth_done = False

# --- 3. RÉCUPÉRATION MÉMOIRE ---
res = doc_ref.get()
faits = res.to_dict().get("faits", []) if res.exists else []

# --- 4. LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME VERROUILLÉ")
    if st.text_input("CODE MAÎTRE :", type="password", key="l_key") == CODE_MASTER:
        st.session_state.locked = False
        st.rerun()
    st.stop()

# --- 5. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 6. GESTION DES ORDRES ---
if prompt := st.chat_input("Ordres ?"):
    p_low = prompt.lower()
    
    # A. VERROUILLAGE
    if "verrouille" in p_low:
        st.session_state.locked = True
        st.rerun()

    # B. SÉCURITÉ MÉMOIRE (BLOQUAGE AVANT IA)
    if any(w in p_low for w in ["mémoire", "archive", "souviens", "notes"]) and not st.session_state.auth_done:
        with st.chat_message("assistant"):
            st.warning("🔒 Code de sécurité requis.")
            c = st.text_input("CODE :", type="password", key="c_key")
            if st.button("VALIDER"):
                if c == CODE_ACT:
                    st.session_state.auth_done = True
                    st.rerun()
                else: st.error("Refusé.")
        st.stop()

    # C. RÉPONSE IA
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        
        # Instruction ultra-stricte
        instr = (
            f"Tu es DELTA, majordome de Monsieur SEZER. Ultra-concis. "
            f"Archives : {faits}. "
            "Si on demande de supprimer : réponds 'ACTION_DELETE: [mot]'. "
            "Si nouvelle info : 'ACTION_ARCHIVE: [info]'. "
            "Si accès mémoire validé : liste les faits brièvement."
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
                if "ACTION_" in full_raw: break
                for char in content:
                    displayed += char
                    placeholder.markdown(displayed + "▌")
                    time.sleep(0.01)

        clean = full_raw.split("ACTION_")[0].strip()
        if not clean: clean = "Ordre exécuté, Monsieur SEZER."
        placeholder.markdown(clean)

        # D. TRAITEMENT ACTIONS
        if "ACTION_DELETE:" in full_raw:
            cible = full_raw.split("ACTION_DELETE:")[1].strip().lower()
            faits = [f for f in faits if cible not in f.lower()]
            doc_ref.set({"faits": faits}, merge=True)
            st.toast("Supprimé.")

        if "ACTION_ARCHIVE:" in full_raw:
            info = full_raw.split("ACTION_ARCHIVE:")[1].strip()
            if info not in faits:
                faits.append(info)
                doc_ref.set({"faits": faits}, merge=True)
                st.toast("Mémorisé.")

        st.session_state.messages.append({"role": "assistant", "content": clean})
    
    st.session_state.auth_done = False # Reset sécurité
    st.rerun()
