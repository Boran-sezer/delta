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

# --- INITIALISATION FIREBASE & GROQ ---
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

    # 1. SI ON EST DÉJÀ EN MODE SÉCURITÉ (ATTENTE DE CODE)
    if st.session_state.security_mode:
        code_normal = "20082008"
        code_promax = "B2008a2020@"
        
        # Déterminer quel code on attend
        # Tentative 1, 2, 3 -> Code Normal
        # Tentative 4 -> Code Pro Max
        if st.session_state.attempts < 3:
            if p == code_normal:
                doc_profil.set({"faits": [], "faits_verrouilles": []})
                rep = "✅ **SYSTÈME RÉINITIALISÉ.** La mémoire est vide."
                st.session_state.security_mode = False
                st.session_state.attempts = 0
            else:
                st.session_state.attempts += 1
                if st.session_state.attempts < 3:
                    rep = f"❌ **CODE INCORRECT.** Recommencez ({st.session_state.attempts}/3)."
                else:
                    rep = "⚠️ **3 ÉCHECS.** Protocole de secours : Entrez le CODE PRO MAX (B2008a2020@)."
        
        else: # On est à la 4ème tentative (Code Pro Max)
            if p == code_promax:
                doc_profil.set({"faits": [], "faits_verrouilles": []})
                rep = "✅ **ACCÈS PRO MAX VALIDÉ.** Purge effectuée."
                st.session_state.security_mode = False
                st.session_state.attempts = 0
            else:
                rep = "🔴 **ROUGE**"
                st.session_state.security_mode = False
                st.session_state.attempts = 0

    # 2. DÉTECTION DE L'ORDRE (PRIORITÉ ABSOLUE SUR L'IA)
    elif "réinitialisation" in low_p:
        st.session_state.security_mode = True
        st.session_state.attempts = 0
        rep = "🔒 **MODE SÉCURITÉ.** Entrez le code d'accès pour confirmer la réinitialisation."

    # 3. RÉPONSE IA NORMALE
    else:
        with st.chat_message("assistant"):
            instr = {"role": "system", "content": "Tu es DELTA, majordome de Monsieur Boran. Sois bref."}
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
            rep = r.choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
