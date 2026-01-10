import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Optimisation 2.60m", layout="wide")
st.title("🚚 Planificateur de Chargement (Hauteur 2.60m)")

# --- CONFIGURATION MISE À JOUR ---
L_UTILE = 13600  
H_UTILE = 2600   # Changement ici : 2600 mm au lieu de 2700 mm
SEUIL_LARGEUR_PLEINE = 1100 

uploaded_excel = st.sidebar.file_uploader("Base Excel (Palettes)", type=None)
uploaded_pdfs = st.file_uploader("Charger les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("🚀 RECALCULER AVEC 2.60M"):
            liste_unitaire_palettes = []

            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    lignes = texte.split('\n')
                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
                            liste_refs = [r.strip() for r in str(row['Référence']).split('/')]
                            for ref_solo in liste_refs:
                                if len(ref_solo) > 3 and ref_solo in ligne:
                                    nombres = re.findall(r'\b\d+\b', ligne)
                                    qte = 1
                                    if nombres:
                                        val = nombres[-1]
                                        qte = int(nombres[-2]) if val == ref_solo and len(nombres) > 1 else int(val)
                                    
                                    for _ in range(qte):
                                        liste_unitaire_palettes.append({
                                            "Ref": ref_solo,
                                            "L": float(row['Longueur (mm)']),
                                            "l": float(row['Largeur (mm)']),
                                            "H": float(row['Hauteur (mm)']),
                                            "Empilable": str(row.get('Empilable', 'Oui')).strip().lower() == 'oui'
                                        })
                                    break

            # LOGIQUE DE GERBAGE MIXTE (Max 2600 mm)
            empilables = [p for p in liste_unitaire_palettes if p['Empilable']]
            non_empilables = [p for p in liste_unitaire_palettes if not p['Empilable']]
            piles_finales = []

            while empilables:
                base = empilables.pop(0)
                hauteur_actuelle = base['H']
                pile = [base['Ref']]
                i = 0
                while i < len(empilables):
                    if hauteur_actuelle + empilables[i]['H'] <= H_UTILE:
                        hauteur_actuelle += empilables[i]['H']
                        pile.append(empilables.pop(i)['Ref'])
                    else:
                        i += 1
                piles_finales.append({"Refs": pile, "L": base['L'], "l": base['l']})

            for p in non_empilables:
                piles_finales.append({"Refs": [p['Ref']], "L": p['L'], "l": p['l']})

            total_mm = 0
            for pile in piles_finales:
                if pile['l'] > SEUIL_LARGEUR_PLEINE:
                    total_mm += pile['L']
                else:
                    total_mm += (pile['L'] / 2)

            st.divider()
            st.metric("Métrage Linéaire TOTAL", f"{total_mm / 1000:.2f} m")
            
            st.subheader("📦 Composition des piles (Max 2.60 m)")
            df_piles = pd.DataFrame([
                {"Contenu de la pile": " / ".join(p['Refs']), "Longueur au sol (mm)": p['L']} 
                for p in piles_finales
            ])
            st.table(df_piles)

    except Exception as e:
        st.error(f"Erreur : {e}")
