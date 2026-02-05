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
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state: st.session_state.messages = []

# --- CHARGEMENT DES ARCHIVES ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- SIDEBAR (ARCHIVES) ---
with st.sidebar:
    st.title("🧠 Archives")
    if st.button("🗑️ TOUT EFFACER"):
        doc_ref.update({"faits": []})
        st.rerun()
    st.write("---")
    for i, fait in enumerate(faits):
        col1, col2 = st.columns([4, 1])
        col1.info(fait)
        if col2.button("🗑️", key=f"del_{i}"):
            faits.pop(i)
            doc_ref.update({"faits": faits})
            st.rerun()

# --- INTERFACE DE CHAT ---
st.title("⚡ DELTA OS")

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Vos ordres, Monsieur ?"):
    low_p = p.lower().strip()
    
    # 🛠️ AUTO-DÉTECTION DE L'ARCHIVAGE (Plus flexible)
    keywords = ["archive", "mémorise", "enregistre", "souviens-toi"]
    if any(word in low_p for word in keywords):
        # On extrait l'info (on enlève le mot clé s'il est au début)
        info = p
        for word in keywords: info = info.replace(word, "").replace(":", "").strip()
        
        if info:
            faits.append(info)
            doc_ref.update({"faits": faits})
            st.toast(f"Mémoire mise à jour : {info}") # Petit message discret en bas

    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    with st.chat_message("assistant"):
        # --- 🛡️ INSTRUCTION ANTI-AMNÉSIE ---
        instr = (
            "Tu es DELTA, le majordome de Monsieur Boran. "
            "TU AS LA CAPACITÉ DE STOCKER DES DONNÉES via ta base de données Firebase. "
            f"Voici tes archives actuelles : {faits}. "
            "Si Monsieur te demande de retenir quelque chose, confirme-lui que c'est fait et que c'est stocké dans tes archives. "
            "Ne dis JAMAIS que tu ne peux pas mémoriser. Sois bref et efficace."
        )
        
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages
        )
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
        
        # On force un rerun si une info a été ajoutée pour l'afficher dans la sidebar
        if any(word in low_p for word in keywords):
            st.rerun()
