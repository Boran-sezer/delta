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

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state: st.session_state.messages = []
if "unlocked" not in st.session_state: st.session_state.unlocked = False

# --- CHARGEMENT DU PROFIL ---
res_profil = doc_profil.get()
data = res_profil.to_dict() if res_profil.exists else {}
faits_publics = data.get("faits", [])
faits_verrouilles = data.get("faits_verrouilles", [])

# --- FONCTION DE SÉCURITÉ (LA MODALE) ---
@st.dialog("🔒 AUTHENTIFICATION REQUISE")
def verifier_code(action, info=None):
    st.write(f"Action : **{action}**")
    code = st.text_input("Entrez le code de sécurité (20082008) :", type="password")
    if st.button("VALIDER L'ACCÈS"):
        if code == "20082008":
            if action == "PURGE TOTALE":
                doc_profil.set({"faits": [], "faits_verrouilles": []})
                st.success("Mémoire effacée.")
            elif action == "SUPPRESSION CIBLÉE":
                t = info.lower()
                new_pub = [f for f in faits_publics if t not in f.lower()]
                new_priv = [f for f in faits_verrouilles if t not in f.lower()]
                doc_profil.set({"faits": new_pub, "faits_verrouilles": new_priv})
                st.success("Cible éliminée.")
            elif action == "SCELLAGE":
                faits_verrouilles.append(info)
                doc_profil.update({"faits_verrouilles": faits_verrouilles})
                st.success("Info scellée.")
            elif action == "DÉVERROUILLAGE":
                st.session_state.unlocked = True
            
            st.rerun()
        else:
            st.error("CODE INCORRECT.")

# --- INTERFACE ---
st.title("⚡ DELTA SYSTEM")

with st.sidebar:
    st.title("🧠 Archives")
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
        if st.button("Fermer le coffre"):
            st.session_state.unlocked = False
            st.rerun()

# --- CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    low_p = p.lower()
    
    if "réinitialisation complète" in low_p:
        verifier_code("PURGE TOTALE")
    elif "supprime précisément" in low_p:
        target = p.replace("supprime précisément", "").strip()
        verifier_code("SUPPRESSION CIBLÉE", target)
    elif "verrouille" in low_p:
        secret = p.replace("verrouille", "").strip()
        verifier_code("SCELLAGE", secret)
    elif "affiche les archives verrouillées" in low_p:
        verifier_code("DÉVERROUILLAGE")
    else:
        with st.chat_message("assistant"):
            ctx = f"Infos: {faits_publics}. Coffre: {faits_verrouilles if st.session_state.unlocked else 'Caché'}."
            instr = {"role": "system", "content": f"Tu es DELTA, majordome de Monsieur Boran. {ctx}"}
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
            rep = r.choices[0].message.content
            st.markdown(rep)
            st.session_state.messages.append({"role": "assistant", "content": rep})
