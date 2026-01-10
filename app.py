import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Optimisation Totale", layout="wide")
st.title("🚚 Planificateur de Chargement avec Gerbage Mixte")

# --- CONFIGURATION ---
L_UTILE = 13600  
H_UTILE = 2700   
SEUIL_LARGEUR_PLEINE = 1100 

uploaded_excel = st.sidebar.file_uploader("Base Excel (Palettes)", type=None)
uploaded_pdfs = st.file_uploader("Charger les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("🚀 GÉNÉRER LE PLAN OPTIMISÉ"):
            liste_unitaire_palettes = []

            # 1. EXTRACTION DE CHAQUE PALETTE INDIVIDUELLE
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
                                    
                                    # Pour chaque unité commandée, on crée une "palette" virtuelle
                                    for _ in range(qte):
                                        liste_unitaire_palettes.append({
                                            "Ref": ref_solo,
                                            "L": float(row['Longueur (mm)']),
                                            "l": float(row['Largeur (mm)']),
                                            "H": float(row['Hauteur (mm)']),
                                            "Empilable": str(row.get('Empilable', 'Oui')).strip().lower() == 'oui'
                                        })
                                    break

            # 2. LOGIQUE DE GERBAGE MIXTE (Empiler des refs différentes)
            # On sépare les empilables des non-empilables
            empilables = [p for p in liste_unitaire_palettes if p['Empilable']]
            non_empilables = [p for p in liste_unitaire_palettes if not p['Empilable']]
            
            piles_finales = [] # Liste de "colonnes" de palettes

            # On crée des piles avec les empilables
            while empilables:
                base = empilables.pop(0)
                hauteur_actuelle = base['H']
                pile = [base['Ref']]
                
                # On essaie d'ajouter d'autres articles sur la pile
                i = 0
                while i < len(empilables):
                    if hauteur_actuelle + empilables[i]['H'] <= H_UTILE:
                        hauteur_actuelle += empilables[i]['H']
                        pile.append(empilables.pop(i)['Ref'])
                    else:
                        i += 1
                piles_finales.append({"Refs": pile, "L": base['L'], "l": base['l']})

            # On ajoute les non-empilables (1 par pile)
            for p in non_empilables:
                piles_finales.append({"Refs": [p['Ref']], "L": p['L'], "l": p['l']})

            # 3. CALCUL DU MÉTRAGE (Largeur)
            total_mm = 0
            for pile in piles_finales:
                if pile['l'] > SEUIL_LARGEUR_PLEINE:
                    total_mm += pile['L']
                else:
                    total_mm += (pile['L'] / 2)

            # 4. AFFICHAGE
            st.divider()
            m_total = total_mm / 1000
            st.metric("Métrage Linéaire TOTAL (Gerbage mixte inclus)", f"{m_total:.2f} m")
            
            st.subheader("📦 Composition des piles de chargement")
            # Affichage simplifié des piles pour les collègues
            df_piles = pd.DataFrame([
                {"Contenu de la pile": " / ".join(p['Refs']), "Longueur au sol (mm)": p['L']} 
                for p in piles_finales
            ])
            st.table(df_piles)

    except Exception as e:
        st.error(f"Erreur : {e}")
