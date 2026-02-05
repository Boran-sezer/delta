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

# --- FONCTION DE SÉCURITÉ (POUR LES ACTIONS SENSIBLES) ---
@st.dialog("🔑 SÉCURITÉ")
def demande_code(type_action, info=None):
    st.write(f"Action demandée : **{type_action}**")
    code = st.text_input("Code (20082008) :", type="password")
    if st.button("CONFIRMER"):
        if code == "20082008":
            if type_action == "RÉINITIALISATION TOTALE":
                doc_profil.set({"faits": [], "faits_verrouilles": []})
                st.success("Toutes les données sont purgées.")
            elif type_action == "SUPPRESSION CIBLÉE":
                t = info.lower()
                new_pub = [f for f in faits_publics if t not in f.lower()]
                new_priv = [f for f in faits_verrouilles if t not in f.lower()]
                doc_profil.set({"faits": new_pub, "faits_verrouilles": new_priv})
                st.success("Élément supprimé.")
            elif type_action == "VERROUILLAGE":
                faits_verrouilles.append(info)
                doc_profil.update({"faits_verrouilles": faits_verrouilles})
                st.success("Info scellée.")
            elif type_action == "ACCÈS COFFRE":
                st.session_state.unlocked = True
            st.rerun()
        else:
            st.error("CODE INCORRECT")

# --- INTERFACE ---
st.title("⚡ DELTA SYSTEM")

with st.sidebar:
    st.title("🧠 Archives")
    st.subheader("Informations")
    for i, f in enumerate(faits_publics):
        col1, col2 = st.columns([4, 1])
        col1.info(f"{f}")
        # Suppression SANS code pour les archives normales
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
        if st.button("Fermer"): st.session_state.unlocked = False; st.rerun()

# --- CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    low_p = p.lower()
    
    # 1. Analyse des commandes de sécurité
    if "réinitialisation complète" in low_p:
        demande_code("RÉINITIALISATION TOTALE")
    elif "supprime précisément" in low_p:
        cible = p.replace("supprime précisément", "").strip()
        demande_code("SUPPRESSION CIBLÉE", cible)
    elif "verrouille" in low_p:
        secret = p.replace("verrouille", "").strip()
        demande_code("VERROUILLAGE", secret)
    elif "affiche les archives verrouillées" in low_p:
        demande_code("ACCÈS COFFRE")
    
    # 2. Réponse standard et tri intelligent
    else:
        with st.chat_message("assistant"):
            contexte = f"Infos connues : {', '.join(faits_publics)}. "
            instr = {
                "role": "system", 
                "content": f"Tu es DELTA, majordome de Monsieur Boran. {contexte} Analyse le message de Monsieur. S'il y a une info importante à retenir (goût, nom, habitude), réponds en commençant par [SAVE: l'info] sinon réponds normalement."
            }
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
            rep_brute = r.choices[0].message.content
            
            # Extraction auto
            if "[SAVE:" in rep_brute:
                info_a_sauver = rep_brute.split("[SAVE:")[1].split("]")[0].strip()
                if info_a_sauver not in faits_publics:
                    faits_publics.append(info_a_sauver)
                    doc_profil.update({"faits": faits_publics})
                rep_finale = rep_brute.split("]")[1].strip() if "]" in rep_brute else rep_brute
            else:
                rep_finale = rep_brute

            st.markdown(rep_finale)
            st.session_state.messages.append({"role": "assistant", "content": rep_finale})
