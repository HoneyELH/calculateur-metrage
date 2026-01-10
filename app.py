import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Plan de Chargement", layout="wide")
st.title("🚛 Répartition des Articles par Camion")

# --- PARAMÈTRES FIXES ---
L_UTILE = 13600  # 13.6m
H_UTILE = 2600   # Hauteur 2.6m
SEUIL_LARGEUR_PLEINE = 1100 

uploaded_excel = st.sidebar.file_uploader("1. Base Excel", type=None)
uploaded_pdfs = st.file_uploader("2. Charger les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("📦 GÉNÉRER LES PLANS DE CAMION"):
            all_palettes = []
            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    for ligne in texte.split('\n'):
                        for _, row in df_articles.iterrows():
                            refs = [r.strip() for r in str(row['Référence']).split('/')]
                            for r in refs:
                                if len(r) > 3 and r in ligne:
                                    n = re.findall(r'\b\d+\b', ligne)
                                    qte = int(n[-2]) if n and n[-1] == r and len(n)>1 else int(n[-1]) if n else 1
                                    for _ in range(qte):
                                        all_palettes.append({
                                            "Ref": r, "L": float(row['Longueur (mm)']),
                                            "l": float(row['Largeur (mm)']), "H": float(row['Hauteur (mm)']),
                                            "Emp": str(row.get('Empilable', 'Oui')).strip().lower() == 'oui'
                                        })
                                    break

            # 1. CRÉATION DES PILES MIXTES (Max 2.6m)
            emp = [p for p in all_palettes if p['Emp']]
            n_emp = [p for p in all_palettes if not p['Emp']]
            piles = []
            while emp:
                base = emp.pop(0)
                h_actuelle = base['H']
                p_refs = [base['Ref']]
                i = 0
                while i < len(emp):
                    if h_actuelle + emp[i]['H'] <= H_UTILE:
                        h_actuelle += emp[i]['H']
                        p_refs.append(emp.pop(i)['Ref'])
                    else: i += 1
                piles.append({"Refs": p_refs, "L": base['L'], "l": base['l']})
            for p in n_emp:
                piles.append({"Refs": [p['Ref']], "L": p['L'], "l": p['l']})

            # 2. RÉPARTITION DANS LES CAMIONS (Max 13.6m)
            camions = []
            c_actuel = {"libre": L_UTILE, "piles": []}
            for p in piles:
                longueur_sol = p['L'] if p['l'] > SEUIL_LARGEUR_PLEINE else p['L']/2
                if longueur_sol <= c_actuel["libre"]:
                    c_actuel["piles"].append(p)
                    c_actuel["libre"] -= longueur_sol
                else:
                    camions.append(c_actuel)
                    c_actuel = {"libre": L_UTILE - longueur_sol, "piles": [p]}
            camions.append(c_actuel)

            # 3. AFFICHAGE DES CAMIONS
            for idx, c in enumerate(camions, 1):
                occ = (L_UTILE - c['libre']) / 1000
                with st.expander(f"🚛 CAMION N°{idx} - Occupation : {occ:.2f} m / 13.60 m", expanded=True):
                    # Inventaire simplifié pour le chargement
                    data = []
                    for p in c['piles']:
                        data.append({"Pile (Bas vers Haut)": " ⬆️ ".join(p['Refs']), "Longueur sol": f"{p['L']} mm"})
                    st.table(pd.DataFrame(data))
    except Exception as e:
        st.error(f"Erreur : {e}")
