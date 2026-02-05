import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state: st.session_state.messages = []
if "security_mode" not in st.session_state: st.session_state.security_mode = False
if "attempts" not in st.session_state: st.session_state.attempts = 0

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client()
doc_profil = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    rep = ""
    low_p = p.lower().strip()

    # 🛡️ 1. LOGIQUE DE SÉCURITÉ (PRIORITÉ ABSOLUE)
    # Si on est déjà en mode sécurité OU si on demande une réinitialisation
    if st.session_state.security_mode or "réinitialisation" in low_p:
        
        # Si c'est le premier déclenchement
        if not st.session_state.security_mode:
            st.session_state.security_mode = True
            st.session_state.attempts = 0
            rep = "🔒 **MODE SÉCURITÉ ACTIVÉ.** Veuillez entrer le code d'accès."
        
        # Si on attend le code
        else:
            code_normal = "20082008"
            code_promax = "B2008a2020@"
            
            # Gestion des essais
            if st.session_state.attempts < 3:
                if p == code_normal:
                    doc_profil.set({"faits": [], "faits_verrouilles": []})
                    rep = "✅ **SYSTÈME RÉINITIALISÉ.**"
                    st.session_state.security_mode = False
                    st.session_state.attempts = 0
                else:
                    st.session_state.attempts += 1
                    if st.session_state.attempts < 3:
                        rep = f"❌ **CODE INCORRECT.** Recommencez (Essai {st.session_state.attempts}/3)."
                    else:
                        rep = "⚠️ **3 ÉCHECS.** Protocole de secours : Entrez le CODE PRO MAX (B2008a2020@)."
            
            else: # 4ème essai (Code Pro Max)
                if p == code_promax:
                    doc_profil.set({"faits": [], "faits_verrouilles": []})
                    rep = "✅ **ACCÈS PRO MAX VALIDÉ.** Purge effectuée."
                    st.session_state.security_mode = False
                    st.session_state.attempts = 0
                else:
                    rep = "🔴 **ROUGE**"
                    st.session_state.security_mode = False
                    st.session_state.attempts = 0

    # 🤖 2. RÉPONSE IA NORMALE (Seulement si PAS de sécurité)
    else:
        with st.chat_message("assistant"):
            instr = {"role": "system", "content": "Tu es DELTA, majordome de Monsieur Boran. Sois efficace."}
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
            rep = r.choices[0].message.content

    # AFFICHAGE FINAL
    with st.chat_message("assistant"):
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
