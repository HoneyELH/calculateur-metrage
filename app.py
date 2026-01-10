import streamlit as st
import pandas as pd
import pdfplumber
import re

# =========================
# CONFIGURATION CAMION
# =========================
L_UTILE = 13600     # mm
LARG_UTILE = 2460  # mm
H_UTILE = 2600     # mm

st.set_page_config(page_title="Hako-Toro", layout="wide")
st.title("🚚 Planification Optimisée")

uploaded_excel = st.sidebar.file_uploader("1️⃣ Base Excel", type=["xlsx"])
uploaded_pdfs = st.sidebar.file_uploader("2️⃣ Bons PDF", type="pdf", accept_multiple_files=True)

# =========================
# FONCTION BEST-FIT
# =========================
def best_fit_pair(p1, candidates, largeur_max):
    best = None
    best_waste = largeur_max

    for p2 in candidates:
        for (L1, l1) in p1['dims']:
            for (L2, l2) in p2['dims']:
                if l1 + l2 <= largeur_max:
                    waste = largeur_max - (l1 + l2)
                    if waste < best_waste:
                        best_waste = waste
                        best = (p2, L1, l1, L2, l2)

    return best


# =========================
# TRAITEMENT
# =========================
if uploaded_excel and uploaded_pdfs and st.button("🚀 GÉNÉRER LE PLAN 17M"):

    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name="Palettes")
        all_palettes = []

        # =========================
        # LECTURE PDF
        # =========================
        for pdf_file in uploaded_pdfs:
            with pdfplumber.open(pdf_file) as pdf:
                texte = "\n".join(
                    p.extract_text() for p in pdf.pages if p.extract_text()
                )

            for ligne in texte.split("\n"):
                for _, row in df_articles.iterrows():
                    refs = [r.strip() for r in str(row["Référence"]).split("/")]
                    for r in refs:
                        if len(r) > 3 and r in ligne:
                            n = re.findall(r"\b\d+\b", ligne)
                            qte = int(n[-1]) if n else 1

                            desc = str(row.get("Description", "")).lower()
                            if "fer" in desc:
                                mat = "fer"
                            elif "carton" in desc:
                                mat = "carton"
                            elif "bois" in desc:
                                mat = "bois"
                            else:
                                mat = "inconnu"

                            for _ in range(qte):
                                all_palettes.append({
                                    "Ref": r,
                                    "d1": float(row["Longueur (mm)"]),
                                    "d2": float(row["Largeur (mm)"]),
                                    "H": float(row["Hauteur (mm)"]),
                                    "Mat": mat
                                })
                            break

        # =========================
        # GERBAGE VERTICAL
        # =========================
        piles = []
        all_palettes.sort(key=lambda x: (x["Mat"], x["Ref"]))

        while all_palettes:
            base = all_palettes.pop(0)

            # FER → pile seule
            if base["Mat"] == "fer":
                piles.append({
                    "Refs": [base["Ref"]],
                    "dims": [(base["d1"], base["d2"]), (base["d2"], base["d1"])],
                    "Mat": "fer"
                })
                continue

            h = base["H"]
            refs = [base["Ref"]]
            i = 0

            while i < len(all_palettes):
                p = all_palettes[i]
                if (
                    p["Ref"] == base["Ref"]
                    and h + p["H"] <= H_UTILE
                ):
                    h += p["H"]
                    refs.append(all_palettes.pop(i)["Ref"])
                else:
                    i += 1

            piles.append({
                "Refs": refs,
                "dims": [(base["d1"], base["d2"]), (base["d2"], base["d1"])],
                "Mat": base["Mat"]
            })

        # =========================
        # JUMELAGE BEST-FIT
        # =========================
        piles.sort(key=lambda p: max(d[0] for d in p["dims"]), reverse=True)
        used = [False] * len(piles)
        rangees = []

        for i, p1 in enumerate(piles):
            if used[i]:
                continue

            used[i] = True
            remaining = [
                piles[j] for j in range(i + 1, len(piles)) if not used[j]
            ]

            best = best_fit_pair(p1, remaining, LARG_UTILE)

            if best:
                p2, L1, l1, L2, l2 = best
                j = piles.index(p2)
                used[j] = True

                rangees.append({
                    "G": {"Refs": p1["Refs"], "L": L1, "l": l1},
                    "D": {"Refs": p2["Refs"], "L": L2, "l": l2},
                    "L_sol": max(L1, L2)
                })
            else:
                # pile seule
                L1, l1 = max(p1["dims"], key=lambda x: x[1])
                rangees.append({
                    "G": {"Refs": p1["Refs"], "L": L1, "l": l1},
                    "D": None,
                    "L_sol": L1
                })

        # =========================
        # AFFICHAGE
        # =========================
        total_mm = sum(r["L_sol"] for r in rangees)
        st.header(f"📏 MÉTRAGE LINÉAIRE TOTAL : {total_mm / 1000:.2f} m")

        curr_L = 0
        cam_num = 1

        for r in rangees:
            if curr_L + r["L_sol"] > L_UTILE:
                st.divider()
                cam_num += 1
                curr_L = 0

            curr_L += r["L_sol"]

            gauche = " / ".join(r["G"]["Refs"])
            droite = (
                " / ".join(r["D"]["Refs"]) if r["D"] else "VIDE"
            )

            st.write(
                f"🚛 **Camion {cam_num}** | "
                f"Section {r['L_sol']} mm | "
                f"Gauche: {gauche} ({r['G']['l']} mm) | "
                f"Droite: {droite}"
            )

    except Exception as e:
        st.error(f"❌ Erreur : {e}")
