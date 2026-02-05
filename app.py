import streamlit as st
import pandas as pd
import pdfplumber
import re

# =========================
# CONFIG CAMION
# =========================
L_UTILE = 13600
LARG_UTILE = 2460
H_UTILE = 2700

# =========================
# INTERFACE ULTRA CLAIR
# =========================
st.set_page_config(page_title="Chargement Camion", layout="wide")

st.markdown("""
<style>
    body {
        background-color: #FAFAFA;
    }
    .title {
        font-size: 40px;
        font-weight: 800;
        text-align: center;
        color: #2B2B2B;
        margin-bottom: 25px;
    }
    .card {
        padding: 18px;
        border-radius: 12px;
        background: #FFFFFF;
        border: 1px solid #E5E5E5;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 18px;
    }
    .metric {
        font-size: 30px;
        font-weight: 700;
        color: #2B2B2B;
    }
    .sub {
        font-size: 15px;
        color: #6A6A6A;
    }
    .section-title {
        font-size: 24px;
        font-weight: 700;
        color: #2B2B2B;
        margin-top: 25px;
        margin-bottom: 10px;
    }
    .upload-box {
        padding: 25px;
        border-radius: 12px;
        background: #FFFFFF;
        border: 1px solid #E5E5E5;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .stButton>button {
        background-color: #2B2B2B;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 16px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #444444;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='title'>🚚 Chargement Camion</div>", unsafe_allow_html=True)

# =========================
# UPLOAD ZONE (centrée)
# =========================
st.markdown("<div class='section-title'>📥 Import des fichiers</div>", unsafe_allow_html=True)

col_up1, col_up2 = st.columns([1,1])

with col_up1:
    st.markdown("<div class='upload-box'>Base articles (Excel)</div>", unsafe_allow_html=True)
    uploaded_excel = st.file_uploader("", type=["xlsx"], key="excel")

with col_up2:
    st.markdown("<div class='upload-box'>Bons PDF</div>", unsafe_allow_html=True)
    uploaded_pdfs = st.file_uploader("", type=["pdf"], accept_multiple_files=True, key="pdfs")

# =========================
# FONCTIONS MÉTIER
# =========================

def detect_matiere(desc):
    d = desc.lower()
    if "fer" in d: return "fer"
    if "carton" in d: return "carton"
    if "bois" in d: return "bois"
    return "inconnu"

def construire_base_articles(df):
    lignes = []
    for _, row in df.iterrows():
        refs = [r.strip() for r in str(row["Référence"]).split("/")]
        for r in refs:
            lignes.append({
                "Ref": r,
                "Description": row["Description"],
                "Largeur_mm": float(row["Largeur (mm)"]),
                "Longueur_mm": float(row["Longueur (mm)"]),
                "Hauteur_mm": float(row["Hauteur (mm)"]),
                "Poids_kg": float(row["Poids unitaire (kg)"]),
                "Empilable": str(row["Empilable (Oui/Non)"]).lower().startswith("o"),
                "Matiere": detect_matiere(str(row["Description"]))
            })
    return pd.DataFrame(lignes)

def extraire_commandes(df_refs, uploaded_pdfs):
    lignes_cmd = []
    for pdf_file in uploaded_pdfs:
        with pdfplumber.open(pdf_file) as pdf:
            texte = "\n".join(p.extract_text() for p in pdf.pages if p.extract_text())
        for ligne in texte.split("\n"):
            for _, art in df_refs.iterrows():
                r = art["Ref"]
                if len(r) > 3 and r in ligne:
                    nums = re.findall(r"\b\d+\b", ligne)
                    qte = int(nums[-1]) if nums else 1
                    lignes_cmd.append({"Ref": r, "Quantite": qte})
                    break
    return pd.DataFrame(lignes_cmd)

def construire_piles(df_full):
    piles = []
    pile_id = 0
    for _, art in df_full.iterrows():
        ref = art["Ref"]
        qte = int(art["Quantite"])
        L, l, h = art["Longueur_mm"], art["Largeur_mm"], art["Hauteur_mm"]
        empilable = art["Empilable"]
        mat = art["Matiere"]

        if (not empilable) or mat == "fer":
            for _ in range(qte):
                pile_id += 1
                piles.append({"PileID": pile_id, "Refs": [ref], "Mat": mat, "L": L, "l": l, "H": h})
        else:
            reste = qte
            while reste > 0:
                h_courant = 0
                refs_pile = []
                while reste > 0 and h_courant + h <= H_UTILE:
                    h_courant += h
                    refs_pile.append(ref)
                    reste -= 1
                pile_id += 1
                piles.append({"PileID": pile_id, "Refs": refs_pile, "Mat": mat, "L": L, "l": l, "H": h_courant})
    return piles

def calcul_metrage_par_surface(piles):
    surface = 0
    for p in piles:
        Lp, lp = min([(p["L"], p["l"]), (p["l"], p["L"])], key=lambda x: x[1])
        surface += Lp * lp
    return (surface / LARG_UTILE) / 1000

def construire_rangees(piles):
    rangees = []
    restantes = sorted(piles, key=lambda p: max(p["L"], p["l"]), reverse=True)

    while restantes:
        p1 = restantes.pop(0)
        L1, l1 = min([(p1["L"], p1["l"]), (p1["l"], p1["L"])], key=lambda x: x[1])

        best = None
        for idx, p2 in enumerate(restantes):
            for L2, l2 in [(p2["L"], p2["l"]), (p2["l"], p2["L"])]:
                if l1 + l2 <= LARG_UTILE:
                    best = (idx, L2, l2)
                    break
            if best: break

        if best:
            idx, L2, l2 = best
            p2 = restantes.pop(idx)
            rangees.append({"G": (p1, L1, l1), "D": (p2, L2, l2), "L_sol": max(L1, L2)})
        else:
            rangees.append({"G": (p1, L1, l1), "D": None, "L_sol": L1})

    return rangees

def detail_palettes(rangees):
    lignes = []
    curr_L = 0
    cam = 1
    rnum = 0

    for r in rangees:
        if curr_L + r["L_sol"] > L_UTILE:
            cam += 1
            curr_L = 0
            rnum = 0
        curr_L += r["L_sol"]
        rnum += 1

        for cote, label in [("G", "Gauche"), ("D", "Droite")]:
            bloc = r[cote]
            if bloc:
                pile, _, _ = bloc
                for niv, ref in enumerate(pile["Refs"], 1):
                    lignes.append({
                        "Camion": cam,
                        "Rangee": rnum,
                        "Cote": label,
                        "PileID": pile["PileID"],
                        "Niveau": niv,
                        "Ref": ref
                    })
    return pd.DataFrame(lignes)

# =========================
# MAIN
# =========================

if uploaded_excel and uploaded_pdfs and st.button("Analyser"):

    df_articles = pd.read_excel(uploaded_excel, sheet_name="Palettes")
    df_refs = construire_base_articles(df_articles)
    df_cmd = extraire_commandes(df_refs, uploaded_pdfs)

    if df_cmd.empty:
        st.error("Aucune référence trouvée.")
    else:
        df_full = df_cmd.merge(df_refs, on="Ref", how="left")
        piles = construire_piles(df_full)
        metrage = calcul_metrage_par_surface(piles)
        rangees = construire_rangees(piles)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='card'><div class='metric'>{metrage:.2f} m</div><div class='sub'>Métrage réel</div></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='card'><div class='metric'>{len(piles)}</div><div class='sub'>Piles créées</div></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='card'><div class='metric'>{len(rangees)}</div><div class='sub'>Rangées</div></div>", unsafe_allow_html=True)

        st.markdown("<div class='section-title'>🧱 Plan de chargement</div>", unsafe_allow_html=True)

        curr_L = 0
        cam = 1
        for r in rangees:
            if curr_L + r["L_sol"] > L_UTILE:
                cam += 1
                curr_L = 0
            curr_L += r["L_sol"]

            g = " / ".join(r["G"][0]["Refs"])
            d = " / ".join(r["D"][0]["Refs"]) if r["D"] else "VIDE"

            st.markdown(f"<div class='card'>Camion {cam}<br>Profondeur : {r['L_sol']} mm<br>Gauche : {g}<br>Droite : {d}</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-title'>📋 Détail palette par palette</div>", unsafe_allow_html=True)
        df_detail = detail_palettes(rangees)
        st.dataframe(df_detail.sort_values(["Camion", "Rangee", "Cote", "PileID", "Niveau"]))
