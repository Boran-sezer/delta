import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡")

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state: st.session_state.messages = []
if "sec_active" not in st.session_state: st.session_state.sec_active = False
if "essais" not in st.session_state: st.session_state.essais = 0

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

# --- AFFICHAGE CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- LE MOTEUR DE DÉCISION ---
if p := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    
    low_p = p.lower().strip()

    # 🛡️ 1. DÉTECTION PRIORITAIRE (COURT-CIRCUIT)
    if "réinitialisation" in low_p or st.session_state.sec_active:
        
        # Premier déclenchement
        if not st.session_state.sec_active:
            st.session_state.sec_active = True
            st.session_state.essais = 0
            rep = "🔒 **PROTOCOLE DE SÉCURITÉ.** Entrez le code."
        
        # Vérification des codes
        else:
            code_normal = "20082008"
            code_promax = "B2008a2020@"
            
            if st.session_state.essais < 3:
                if p == code_normal:
                    doc_profil.set({"faits": [], "faits_verrouilles": []})
                    rep = "✅ **SYSTÈME PURGÉ.**"
                    st.session_state.sec_active = False
                else:
                    st.session_state.essais += 1
                    if st.session_state.essais < 3:
                        rep = f"❌ **CODE FAUX.** Recommencez ({st.session_state.essais}/3)."
                    else:
                        rep = "⚠️ **3 ÉCHECS.** Entrez le CODE PRO MAX (B2008a2020@)."
            else:
                if p == code_promax:
                    doc_profil.set({"faits": [], "faits_verrouilles": []})
                    rep = "✅ **ACCÈS PRO MAX VALIDÉ.** Purge effectuée."
                    st.session_state.sec_active = False
                else:
                    rep = "🔴 **ROUGE**"
                    st.session_state.sec_active = False
        
        # ON FORCE L'AFFICHAGE ET ON STOPPE TOUT (L'IA ne sera jamais appelée)
        with st.chat_message("assistant"):
            st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
        st.stop() # <--- COURT-CIRCUIT : L'IA est bloquée ici

    # 🤖 2. IA NORMALE (Uniquement si le code n'a pas été stoppé au-dessus)
    with st.chat_message("assistant"):
        instr = {"role": "system", "content": "Tu es DELTA. Sois bref."}
        r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
        rep_ia = r.choices[0].message.content
        st.markdown(rep_ia)
        st.session_state.messages.append({"role": "assistant", "content": rep_ia})
