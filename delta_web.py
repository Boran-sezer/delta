import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- 1. CONFIGURATION DES ACCÈS ---
CODE_ACT = "20082008"
CODE_MASTER = "B2008a2020@"

# Initialisation Firebase (via Secrets Streamlit)
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur de connexion Firebase : {e}")

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- 2. GESTION DES ÉTATS (SESSION STATE) ---
if "locked" not in st.session_state: st.session_state.locked = False
if "auth" not in st.session_state: st.session_state.auth = False
if "essais" not in st.session_state: st.session_state.essais = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "show_auth_form" not in st.session_state: st.session_state.show_auth_form = False
if "pending_prompt" not in st.session_state: st.session_state.pending_prompt = None

# --- 3. CHARGEMENT DE LA MÉMOIRE ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. SÉCURITÉ : MODE LOCKDOWN (VÉROUILLAGE TOTAL) ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME EN MODE LOCKDOWN - ACCÈS TOTALEMENT BLOQUÉ")
    m_input = st.text_input("ENTREZ LE CODE MAÎTRE POUR RÉINITIALISER :", type="password", key="m_key")
    if st.button("DÉBLOQUER LE NOYAU"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.session_state.essais = 0
            st.success("Système réinitialisé. DELTA est de nouveau opérationnel.")
            st.rerun()
        else:
            st.error("CODE MAÎTRE INCORRECT.")
    st.stop()

# --- 5. FONCTION DE RÉPONSE IA ---
def reponse_delta(user_input):
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Instruction système (DELTA ne doit jamais dire les codes)
    instr = (
        f"Tu es DELTA IA, le majordome de Monsieur Boran. Ne mentionne JAMAIS les codes secrets. "
        f"Voici tes archives actuelles : {faits}. "
        "Si Monsieur demande ses archives, liste-les clairement. "
        "Si tu apprends une info importante, termine impérativement par 'ACTION_ARCHIVE: [info]'."
    )
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": instr}] + st.session_state.messages
    )
    
    response = completion.choices[0].message.content
    
    # Gestion de l'archivage automatique vers Firestore
    if "ACTION_ARCHIVE:" in response:
        info = response.split("ACTION_ARCHIVE:")[1].strip()
        if info not in faits:
            faits.append(info)
            doc_ref.update({"faits": faits})
            st.toast(f"Mémorisé : {info}", icon="🧠")
        response = response.split("ACTION_ARCHIVE:")[0].strip()
        
    st.session_state.messages.append({"role": "assistant", "content": response})

# --- 6. INTERFACE DE CHAT ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Saisie utilisateur
if prompt := st.chat_input("Quels sont vos ordres, Monsieur Boran ?"):
    # Détection d'actions sensibles
    sensible = any(word in prompt.lower() for word in ["archive", "mémoire", "effacer", "supprimer", "montre"])
    
    # Commande de verrouillage manuel
    if "verrouille" in prompt.lower() or "lock" in prompt.lower():
        st.session_state.locked = True
        st.rerun()

    if sensible and not st.session_state.auth:
        st.session_state.show_auth_form = True
        st.session_state.pending_prompt = prompt
        st.rerun()
    else:
        reponse_delta(prompt)
        # On s'assure que l'auth ne reste pas active pour la prochaine fois
        st.session_state.auth = False 
        st.rerun()

# --- 7. FORMULAIRE DE SÉCURITÉ DYNAMIQUE ---
if st.session_state.show_auth_form:
    with st.chat_message("assistant"):
        st.warning("🔒 Identification requise pour accéder aux systèmes de mémoire.")
        c = st.text_input("CODE D'ACTION :", type="password", key="action_key")
        
        if st.button("VALIDER L'ACCÈS"):
            if c == CODE_ACT:
                st.session_state.auth = True
                st.session_state.show_auth_form = False
                st.session_state.essais = 0
                
                # Exécute la demande qui était en attente
                if st.session_state.pending_prompt:
                    reponse_delta(st.session_state.pending_prompt)
                    st.session_state.pending_prompt = None
                
                # REVERROUILLAGE IMMÉDIAT (One-Shot)
                st.session_state.auth = False 
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3:
                    st.session_state.locked = True
                    st.rerun()
                st.error(f"CODE INCORRECT. TENTATIVE {st.session_state.essais}/3")
