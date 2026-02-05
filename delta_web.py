import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        creds_dict = json.loads(decoded_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception:
        st.error("⚠️ Connexion Mémoire interrompue.")

db = firestore.client()
doc_profil = db.collection("memoire").document("profil_monsieur")

# --- CONNEXION GROQ ---
client = Groq(api_key="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")

# --- ÉTATS DE SESSION (SÉCURITÉ) ---
if "messages" not in st.session_state: st.session_state.messages = []
if "unlocked" not in st.session_state: st.session_state.unlocked = False
if "security_mode" not in st.session_state: st.session_state.security_mode = None
if "attempts" not in st.session_state: st.session_state.attempts = 0
if "pending_data" not in st.session_state: st.session_state.pending_data = None

# --- CHARGEMENT DU PROFIL ---
res_profil = doc_profil.get()
data = res_profil.to_dict() if res_profil.exists else {}
faits_publics = data.get("faits", [])
faits_verrouilles = data.get("faits_verrouilles", [])

# --- INTERFACE SIDEBAR ---
with st.sidebar:
    st.title("🧠 Archives")
    st.subheader("Informations")
    for i, f in enumerate(faits_publics):
        col1, col2 = st.columns([4, 1])
        col1.info(f)
        if col2.button("🗑️", key=f"p_{i}"):
            faits_publics.pop(i)
            doc_profil.update({"faits": faits_publics})
            st.rerun()
    
    if st.session_state.unlocked:
        st.subheader("🔐 Scellées")
        for i, f in enumerate(faits_verrouilles):
            col1, col2 = st.columns([4, 1])
            col1.warning(f)
            if col2.button("🗑️", key=f"s_{i}"):
                faits_verrouilles.pop(i)
                doc_profil.update({"faits_verrouilles": faits_verrouilles})
                st.rerun()
        if st.button("Refermer"): 
            st.session_state.unlocked = False
            st.rerun()

# --- CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    # 1. SI ON EST EN MODE VÉRIFICATION DE CODE
    if st.session_state.security_mode:
        code_correct = "20082008"
        code_secours = "B2008a2020@"
        
        success = False
        if st.session_state.attempts < 3:
            if p == code_correct: success = True
        else:
            if p == code_secours: success = True

        if success:
            mode = st.session_state.security_mode
            info = st.session_state.pending_data
            if mode == "PURGE":
                doc_profil.set({"faits": [], "faits_verrouilles": []})
                rep = "✅ Réinitialisation complète effectuée, Monsieur."
            elif mode == "LOCK":
                faits_verrouilles.append(info)
                doc_profil.update({"faits_verrouilles": faits_verrouilles})
                rep = "✅ Information scellée dans les archives verrouillées."
            elif mode == "UNLOCK":
                st.session_state.unlocked = True
                rep = "✅ Coffre-fort ouvert. Consultez la barre latérale."
            elif mode == "DELETE":
                t = info.lower()
                new_pub = [f for f in faits_publics if t not in f.lower()]
                new_priv = [f for f in faits_verrouilles if t not in f.lower()]
                doc_profil.set({"faits": new_pub, "faits_verrouilles": new_priv})
                rep = f"✅ Éléments liés à '{info}' supprimés."
            
            st.session_state.security_mode = None
            st.session_state.attempts = 0
        else:
            st.session_state.attempts += 1
            if st.session_state.attempts < 3:
                rep = f"❌ Code incorrect. Tentative {st.session_state.attempts}/3. Veuillez réessayer."
            elif st.session_state.attempts == 3:
                rep = "⚠️ 3 échecs détectés. Protocole de sécurité activé. Veuillez entrer le code de secours ultime."
            else:
                rep = "❌ Échec du code de secours. Procédure annulée."
                st.session_state.security_mode = None
                st.session_state.attempts = 0

    # 2. DÉTECTION DES NOUVEAUX ORDRES
    else:
        low_p = p.lower()
        if "réinitialisation complète" in low_p:
            st.session_state.security_mode = "PURGE"
            rep = "🔒 Ordre critique détecté. Veuillez entrer votre code d'accès pour confirmer la purge totale."
        elif "verrouille" in low_p:
            st.session_state.security_mode = "LOCK"
            st.session_state.pending_data = p.replace("verrouille", "").strip()
            rep = "🔒 Scellage demandé. Veuillez entrer votre code d'accès."
        elif "affiche les archives verrouillées" in low_p:
            st.session_state.security_mode = "UNLOCK"
            rep = "🔒 Accès restreint. Veuillez entrer votre code d'accès."
        elif "supprime précisément" in low_p:
            st.session_state.security_mode = "DELETE"
            st.session_state.pending_data = p.replace("supprime précisément", "").strip()
            rep = f"🔒 Suppression de '{st.session_state.pending_data}' demandée. Code requis."
        else:
            # RÉPONSE NORMALE IA
            with st.chat_message("assistant"):
                instr = {"role": "system", "content": f"Tu es DELTA, créé par Monsieur Boran. Infos: {faits_publics}."}
                r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
                rep = r.choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
