import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="Hako-Toro : Optimisation 17m", layout="wide")
st.title("🚚 Plan de Chargement - Objectif 17m")

# --- PARAMÈTRES RÉELS DU CAMION ---
L_UTILE = 13600  #
LARG_UTILE = 2460 #
H_UTILE = 2600   # Hauteur max
# SEUIL AJUSTÉ : Permet de doubler les machines de 1.17m et 1.20m
SEUIL_DOUBLE = 1210 

uploaded_excel = st.sidebar.file_uploader("1. Base Excel", type=None)
uploaded_pdfs = st.file_uploader("2. Charger les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("🚀 CALCULER LE MÉTRAGE (Cible 17m)"):
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
                                    mat = 'fer' if 'fer' in desc else 'carton' if 'carton' in desc else 'bois' if 'bois' in desc else 'inconnu'

                                    for _ in range(qte):
                                        all_palettes.append({
                                            "Ref": r, "L": float(row['Longueur (mm)']),
                                            "l": float(row['Largeur (mm)']), "H": float(row['Hauteur (mm)']),
                                            "Mat": mat, "Dim_Key": f"{row['Longueur (mm)']}x{row['Largeur (mm)']}"
                                        })
                                    break

            # --- LOGIQUE DE GERBAGE ---
            piles = []
            # 1. CARTONS (Mélange + Pyramide)
            cartons = sorted([p for p in all_palettes if p['Mat'] == 'carton'], key=lambda x: x['l'], reverse=True)
            while cartons:
                base = cartons.pop(0)
                h, refs = base['H'], [base['Ref']]
                i = 0
                while i < len(cartons):
                    if h + cartons[i]['H'] <= H_UTILE and cartons[i]['l'] <= base['l']:
                        h += cartons[i]['H']; refs.append(cartons.pop(i)['Ref'])
                    else: i += 1
                piles.append({"Refs": refs, "L": base['L'], "l": base['l'], "Mat": "carton"})

            # 2. BOIS (Mêmes dimensions seulement)
            bois = [p for p in all_palettes if p['Mat'] == 'bois']
            for dk in set(p['Dim_Key'] for p in bois):
                grp = [p for p in bois if p['Dim_Key'] == dk]
                while grp:
                    base = grp.pop(0)
                    h, refs = base['H'], [base['Ref']]
                    i = 0
                    while i < len(grp):
                        if h + grp[i]['H'] <= H_UTILE:
                            h += grp[i]['H']; refs.append(grp.pop(i)['Ref'])
                        else: i += 1
                    piles.append({"Refs": refs, "L": base['L'], "l": base['l'], "Mat": "bois"})

            # 3. FER (Seul au sol)
            for p in [p for p in all_palettes if p['Mat'] == 'fer']:
                piles.append({"Refs": [p['Ref']], "L": p['L'], "l": p['l'], "Mat": "fer"})

            # --- CALCUL MÉTRAGE RÉEL (Double colonne) ---
            p_larges = [p for p in piles if p['l'] > SEUIL_DOUBLE]
            p_etroites = [p for p in piles if p['l'] <= SEUIL_DOUBLE]
            
            # Les étroites sont chargées sur deux colonnes (Gauche/Droite)
            col1, col2 = 0, 0
            for p in p_etroites:
                if col1 <= col2: col1 += p['L']
                else: col2 += p['L']
            
            total_mm = sum(p['L'] for p in p_larges) + max(col1, col2)

            st.divider()
            st.metric("📏 MÉTRAGE LINÉAIRE TOTAL", f"{total_mm / 1000:.2f} m")
            
            # Affichage Camions
            camions, c_act = [], {"libre": L_UTILE, "piles": []}
            for p in (p_larges + p_etroites):
                occ = p['L'] if p['l'] > SEUIL_DOUBLE else p['L']/2
                if occ <= c_act["libre"]:
                    c_act["piles"].append(p)
                    c_act["libre"] -= occ
                else:
                    camions.append(c_act)
                    c_act = {"libre": L_UTILE - occ, "piles": [p]}
            camions.append(c_act)

            for idx, c in enumerate(camions, 1):
                occ_m = (L_UTILE - c['libre']) / 1000
                with st.expander(f"🚛 CAMION N°{idx} - {occ_m:.2f} m", expanded=True):
                    st.table([{"Pile": " / ".join(p['Refs']), "Mat": p['Mat'], "Largeur": p['l']} for p in c['piles']])

    except Exception as e:
        st.error(f"Erreur : {e}")
