import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Cible 17m", layout="wide")
st.title("🚚 Planificateur de Chargement - Cible 17m")

# --- PARAMÈTRES AJUSTÉS ---
L_UTILE = 13600 
H_UTILE = 2600  
# On passe à 1230mm pour autoriser deux machines de 1.20m côte à côte
SEUIL_LARGEUR_PLEINE = 1230 

uploaded_excel = st.sidebar.file_uploader("1. Base Excel", type=None)
uploaded_pdfs = st.file_uploader("2. Charger les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("🚀 GÉNÉRER LE PLAN (SEUIL 1.23M)"):
            all_palettes = []
            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    for ligne in texte.split('\n'):
                        for idx, row in df_articles.iterrows():
                            refs = [r.strip() for r in str(row['Référence']).split('/')]
                            for r in refs:
                                if len(r) > 3 and r in ligne:
                                    n = re.findall(r'\b\d+\b', ligne)
                                    qte = int(n[-2]) if n and n[-1] == r and len(n)>1 else int(n[-1]) if n else 1
                                    
                                    desc = str(row.get('Description', '')).lower()
                                    matiere = 'fer' if 'fer' in desc else 'carton' if 'carton' in desc else 'bois' if 'bois' in desc else 'inconnu'

                                    for _ in range(qte):
                                        all_palettes.append({
                                            "Ref": r, "L": float(row['Longueur (mm)']),
                                            "l": float(row['Largeur (mm)']), "H": float(row['Hauteur (mm)']),
                                            "Mat": matiere, "Dim_Key": f"{row['Longueur (mm)']}x{row['Largeur (mm)']}"
                                        })
                                    break

            piles = []
            # 1. CARTONS (Mélange total + Pyramide)
            cartons = sorted([p for p in all_palettes if p['Mat'] == 'carton'], key=lambda x: x['l'], reverse=True)
            while cartons:
                base = cartons.pop(0)
                h_actuelle, p_refs = base['H'], [base['Ref']]
                i = 0
                while i < len(cartons):
                    if h_actuelle + cartons[i]['H'] <= H_UTILE and cartons[i]['l'] <= base['l']:
                        h_actuelle += cartons[i]['H']
                        p_refs.append(cartons.pop(i)['Ref'])
                    else: i += 1
                piles.append({"Refs": p_refs, "L": base['L'], "l": base['l'], "Mat": "carton"})

            # 2. BOIS (Mêmes dimensions uniquement)
            bois_all = [p for p in all_palettes if p['Mat'] == 'bois']
            for d_key in set(p['Dim_Key'] for p in bois_all):
                groupe = [p for p in bois_all if p['Dim_Key'] == d_key]
                while groupe:
                    base = groupe.pop(0)
                    h_actuelle, p_refs = base['H'], [base['Ref']]
                    i = 0
                    while i < len(groupe):
                        if h_actuelle + groupe[i]['H'] <= H_UTILE:
                            h_actuelle += groupe[i]['H']
                            p_refs.append(groupe.pop(i)['Ref'])
                        else: i += 1
                    piles.append({"Refs": p_refs, "L": base['L'], "l": base['l'], "Mat": "bois"})

            # 3. FER
            for p in [p for p in all_palettes if p['Mat'] == 'fer']:
                piles.append({"Refs": [p['Ref']], "L": p['L'], "l": p['l'], "Mat": "fer"})

            # --- CALCUL DU MÉTRAGE ---
            total_mm = 0
            for p in piles:
                if p['l'] > SEUIL_LARGEUR_PLEINE:
                    total_mm += p['L']
                else:
                    total_mm += (p['L'] / 2)

            st.divider()
            st.metric("📏 MÉTRAGE LINÉAIRE TOTAL", f"{total_mm / 1000:.2f} m")
            
            # Affichage Camions
            camions, c_actuel = [], {"libre": L_UTILE, "piles": []}
            for p in piles:
                lg_sol = p['L'] if p['l'] > SEUIL_LARGEUR_PLEINE else p['L']/2
                if lg_sol <= c_actuel["libre"]:
                    c_actuel["piles"].append(p)
                    c_actuel["libre"] -= lg_sol
                else:
                    camions.append(c_actuel)
                    c_actuel = {"libre": L_UTILE - lg_sol, "piles": [p]}
            camions.append(c_actuel)

            for idx, c in enumerate(camions, 1):
                with st.expander(f"🚛 CAMION N°{idx} - {(L_UTILE-c['libre'])/1000:.2f} m", expanded=True):
                    st.table([{"Pile": " / ".join(p['Refs']), "Matériau": p['Mat'], "Largeur": f"{p['l']} mm"} for p in c['piles']])
    except Exception as e:
        st.error(f"Erreur : {e}")
