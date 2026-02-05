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
if "pending_action" not in st.session_state: st.session_state.pending_action = None

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
        col1.info(f"{f}")
        if col2.button("🗑️", key=f"pub_{i}"):
            faits_publics.pop(i)
            doc_profil.update({"faits": faits_publics})
            st.rerun()
    
    if st.session_state.unlocked:
        st.subheader("🔐 Scellées")
        for i, f in enumerate(faits_verrouilles):
            col1, col2 = st.columns([4, 1])
            col1.warning(f"{f}")
            if col2.button("🗑️", key=f"priv_{i}"):
                faits_verrouilles.pop(i)
                doc_profil.update({"faits_verrouilles": faits_verrouilles})
                st.rerun()
        if st.button("Fermer le coffre"):
            st.session_state.unlocked = False
            st.rerun()

# --- AFFICHAGE DU CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- ZONE DE SÉCURITÉ ACTIVE ---
if st.session_state.pending_action:
    with st.chat_message("assistant"):
        st.warning(f"🔒 ACTION : {st.session_state.pending_action['type']}. Veuillez saisir le code.")
        code_input = st.text_input("CODE DE SÉCURITÉ :", type="password", key="security_key")
        
        col_a, col_b = st.columns(2)
        if col_a.button("✅ VALIDER"):
            if code_input == "20082008":
                act = st.session_state.pending_action
                if act['type'] == "PURGE":
                    doc_profil.set({"faits": [], "faits_verrouilles": []})
                    st.success("Mémoire effacée.")
                elif act['type'] == "LOCK":
                    faits_verrouilles.append(act['info'])
                    doc_profil.update({"faits_verrouilles": faits_verrouilles})
                    st.success("Information scellée.")
                elif act['type'] == "UNLOCK":
                    st.session_state.unlocked = True
                    st.success("Coffre ouvert.")
                elif act['type'] == "DELETE_TARGET":
                    t = act['info'].lower()
                    new_pub = [f for f in faits_publics if t not in f.lower()]
                    new_priv = [f for f in faits_verrouilles if t not in f.lower()]
                    doc_profil.set({"faits": new_pub, "faits_verrouilles": new_priv})
                    st.success("Cible supprimée.")
                
                st.session_state.pending_action = None
                st.rerun()
            else:
                st.error("CODE INCORRECT.")
        
        if col_b.button("❌ ANNULER"):
            st.session_state.pending_action = None
            st.rerun()
    st.stop()

# --- ENTRÉE DES ORDRES ---
if p := st.chat_input("Vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    low_p = p.lower()
    
    # Détection des commandes de sécurité
    if "réinitialisation complète" in low_p:
        st.session_state.pending_action = {"type": "PURGE"}
        st.rerun()
    elif "verrouille" in low_p:
        secret = p.replace("verrouille", "").strip()
        st.session_state.pending_action = {"type": "LOCK", "info": secret}
        st.rerun()
    elif "affiche les archives verrouillées" in low_p:
        st.session_state.pending_action = {"type": "UNLOCK"}
        st.rerun()
    elif "supprime précisément" in low_p:
        cible = p.replace("supprime précisément", "").strip()
        st.session_state.pending_action = {"type": "DELETE_TARGET", "info": cible}
        st.rerun()
    
    # Réponse normale
    else:
        with st.chat_message("assistant"):
            ctx = f"Infos: {faits_publics}."
            instr = {"role": "system", "content": f"Tu es DELTA, créé par Monsieur Boran. {ctx} Majordome fidèle."}
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
            rep = r.choices[0].message.content
            st.markdown(rep)
            st.session_state.messages.append({"role": "assistant", "content": rep})
