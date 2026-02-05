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
if "action_en_attente" not in st.session_state: st.session_state.action_en_attente = None

# --- CHARGEMENT DU PROFIL ---
res_profil = doc_profil.get()
data = res_profil.to_dict() if res_profil.exists else {}
faits_publics = data.get("faits", [])
faits_verrouilles = data.get("faits_verrouilles", [])

# --- BARRE LATÉRALE (FIXE) ---
with st.sidebar:
    st.title("🛡️ SÉCURITÉ & ARCHIVES")
    
    # ZONE DE CODE PERMANENTE SI ACTION DEMANDÉE
    if st.session_state.action_en_attente:
        st.warning(f"⚠️ ACTION : {st.session_state.action_en_attente['type']}")
        code_secret = st.text_input("Saisir Code (20082008) :", type="password")
        
        if st.button("🚀 VALIDER L'ORDRE"):
            if code_secret == "20082008":
                act = st.session_state.action_en_attente
                if act['type'] == "RÉINITIALISATION":
                    doc_profil.set({"faits": [], "faits_verrouilles": []})
                    st.success("Mémoire purgée.")
                elif act['type'] == "VERROUILLAGE":
                    faits_verrouilles.append(act['info'])
                    doc_profil.update({"faits_verrouilles": faits_verrouilles})
                    st.success("Scellé effectué.")
                elif act['type'] == "OUVERTURE":
                    st.session_state.unlocked = True
                elif act['type'] == "SUPPRESSION":
                    t = act['info'].lower()
                    new_pub = [f for f in faits_publics if t not in f.lower()]
                    new_priv = [f for f in faits_verrouilles if t not in f.lower()]
                    doc_profil.set({"faits": new_pub, "faits_verrouilles": new_priv})
                
                st.session_state.action_en_attente = None
                st.rerun()
            else:
                st.error("CODE INCORRECT")
        
        if st.button("✖️ ANNULER"):
            st.session_state.action_en_attente = None
            st.rerun()
        st.markdown("---")

    # AFFICHAGE DES ARCHIVES
    st.subheader("📁 Infos Publiques")
    for i, f in enumerate(faits_publics):
        col1, col2 = st.columns([4, 1])
        col1.info(f)
        if col2.button("🗑️", key=f"p_{i}"):
            faits_publics.pop(i)
            doc_profil.update({"faits": faits_publics})
            st.rerun()
            
    if st.session_state.unlocked:
        st.subheader("🔐 Infos Scellées")
        for i, f in enumerate(faits_verrouilles):
            col1, col2 = st.columns([4, 1])
            col1.warning(f)
            if col2.button("🗑️", key=f"s_{i}"):
                faits_verrouilles.pop(i)
                doc_profil.update({"faits_verrouilles": faits_verrouilles})
                st.rerun()
        if st.button("🔒 Refermer"):
            st.session_state.unlocked = False
            st.rerun()

# --- CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    
    low_p = p.lower()
    
    # DÉTECTION DES ORDRES
    if "réinitialisation complète" in low_p:
        st.session_state.action_en_attente = {"type": "RÉINITIALISATION"}
        rep = "Ordre de purge détecté. Veuillez valider dans la barre latérale ⬅️."
    elif "verrouille" in low_p:
        st.session_state.action_en_attente = {"type": "VERROUILLAGE", "info": p.replace("verrouille", "").strip()}
        rep = "Information prête à être scellée. Code requis dans la barre latérale ⬅️."
    elif "affiche les archives verrouillées" in low_p:
        st.session_state.action_en_attente = {"type": "OUVERTURE"}
        rep = "Accès au coffre demandé. Authentifiez-vous sur la gauche ⬅️."
    elif "supprime précisément" in low_p:
        st.session_state.action_en_attente = {"type": "SUPPRESSION", "info": p.replace("supprime précisément", "").strip()}
        rep = "Cible identifiée. Confirmation requise à gauche ⬅️."
    else:
        # RÉPONSE IA
        with st.chat_message("assistant"):
            instr = {"role": "system", "content": f"Tu es DELTA, majordome de Monsieur Boran. Voici ce que tu sais : {faits_publics}."}
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
            rep = r.choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
