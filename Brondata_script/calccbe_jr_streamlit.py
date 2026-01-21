"""
Build the dataset used by `📈_Begroting_en_jaarrekening_vergelijken.py`.

This script reads Iv3 CSV extracts (per year + document code), aggregates them to
"taakveldgroepen", applies municipality mergers ("herindelingen"), optionally
adds population-based "Per inwoner" values (if a population column is present),
and finally writes `begroting_rekening.pickle` (and optionally CSV).

Key outputs (long format):
- Gemeenten, Jaar, Stand, Taakveld, Document, Categorie, Waarde

Run:
  python Brondata_script/calccbe_jr_streamlit.py --iv3-dir path/to/iv3data --out begroting_rekening.pickle
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import pandas as pd

# Defaults (kept hard-coded to match the original script behavior/paths)
DEFAULT_IV3_DIR = Path(r"C:\Dashboard\werk\iv3data")
DEFAULT_CLASSES_CSV = Path(r"C:\Dashboard\werk\gemdata\gemeenteklassen2.csv")
DEFAULT_YEAR_START = 2017
DEFAULT_YEAR_END = 2024
DEFAULT_OUT_PICKLE = Path("begroting_rekening.pickle")
DEFAULT_OUT_CSV = Path("begroting_rekening.csv")

# Iv3 column names
COL_TAAKVELD = "TaakveldBalanspost"
COL_CATEGORIE = "Categorie"
COL_GEMEENTE = "Gemeenten"


# Aggregation groups (used by the Streamlit app)
TAAKVELDGROEPEN: dict[str, tuple[str, ...]] = {
    "Bestuur en burgerzaken": ("0.1 ", "0.2"),
    "Overhead": ("0.4",),
    "Belastingen": ("0.6",),
    "Gemeentefonds": ("0.7",),
    "Overig bestuur en ondersteuning": ("0.3", "0.5", "0.8", "0.9"),
    "Veiligheid": ("1.",),
    "Verkeer en vervoer": ("2.",),
    "Economie": ("3.",),
    "Onderwijs": ("4.",),
    "SCR": ("5.",),
    "Algemene voorzieningen": ("6.1", "6.2"),
    "Inkomensregelingen": ("6.3",),
    "Participatie": ("6.4", "6.5"),
    "Maatwerk Wmo": ("6.6", "6.71", "6.81"),
    "Maatwerk Jeugd": ("6.72", "6.73", "6.74", "6.82"),
    "Volksgezondheid en milieu": ("7.",),
    "Grondexploitatie": ("8.2",),
    "Wonen en bouwen": ("8.1", "8.3"),
}


def pivot_iv3(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """
    Pivot Iv3 raw records to a Gemeenten x Taakveld table, and calculate
    Baten/Lasten/Saldo.
    """
    pv = df.pivot(index=[COL_GEMEENTE, COL_TAAKVELD], columns=COL_CATEGORIE, values=[value_col])
    pv.columns = [col[-1] for col in pv.columns]  # flatten multi-index

    batencolumns = [col for col in pv.columns if str(col).startswith("B")]
    lastencolumns = [col for col in pv.columns if str(col).startswith("L")]

    pv["Baten"] = pv[batencolumns].sum(axis=1) if batencolumns else 0
    pv["Lasten"] = pv[lastencolumns].sum(axis=1) if lastencolumns else 0
    pv["Saldo"] = pv["Baten"] - pv["Lasten"]

    return pv.reset_index()


def herindeling_rules() -> dict[str, tuple[int, dict[str, float]]]:
    # year threshold + constituent municipalities w/ weight
    return {
        "Meierijstad": (2017, {"Schijndel": 1, "Sint-Oedenrode": 1, "Veghel": 1}),
        "Leeuwarden": (2018, {"Leeuwarden": 1, "Leeuwarderadeel": 1, "Littenseradiel": 0.32}),
        "Midden-Groningen": (2018, {"Hoogezand-Sappemeer": 1, "Menterwolde": 1, "Slochteren": 1}),
        "Waadhoeke": (2018, {"Franekeradeel": 1, "het Bildt": 1, "Menameradiel": 1, "Littenseradiel": 0.17}),
        "Westerwolde": (2018, {"Bellingwedde": 1, "Vlagtwedde": 1}),
        "Zevenaar": (2018, {"Rijnwaarden": 1, "Zevenaar": 1}),
        "Súdwest-Fryslân": (
            2018,
            {
                "Bolsward": 1,
                "Nijefurd": 1,
                "Sneek": 1,
                "Wonseradeel": 1,
                "Wûnseradiel": 1,
                "Wymbritseradiel": 1,
                "Wymbritseradeel": 1,
                "Littenseradiel": 0.51,
                "Súdwest-Fryslân": 1,
            },
        ),
        "Groningen (gemeente)": (2019, {"Groningen (gemeente)": 1, "Haren": 1, "Ten Boer": 1}),
        "Het Hogeland": (2019, {"Bedum": 1, "De Marne": 1, "Eemsmond": 1, "Winsum": 0.884}),
        "Westerkwartier": (2019, {"Grootegast": 1, "Leek": 1, "Marum": 1, "Zuidhorn": 1, "Winsum": 0.1157}),
        "Altena": (2019, {"Aalburg": 1, "Werkendam": 1, "Woudrichem": 1}),
        "Beekdaelen": (2019, {"Nuth": 1, "Onderbanken": 1, "Schinnen": 1}),
        "Haarlemmermeer": (2019, {"Haarlemmerliede en Spaarnwoude": 1, "Haarlemmermeer": 1}),
        "Hoeksche Waard": (
            2019,
            {"Binnenmaas": 1, "Cromstrijen": 1, "Korendijk": 1, "Oud-Beijerland": 1, "Strijen": 1, "'s-Gravendeel": 1},
        ),
        "Noardeast-Fryslân": (2019, {"Dongeradeel": 1, "Ferwerderadiel": 1, "Kollumerland en Nieuwkruisland": 1}),
        "Molenlanden": (2019, {"Graafstroom": 1, "Liesveld": 1, "Nieuw-Lekkerland": 1, "Molenwaard": 1, "Giessenlanden": 1}),
        "Noordwijk": (2019, {"Noordwijk": 1, "Noordwijkerhout": 1}),
        "Vijfheerenlanden": (2019, {"Leerdam": 1, "Zederik": 1, "Vianen": 1}),
        "West Betuwe": (2019, {"Geldermalsen": 1, "Lingewaal": 1, "Neerijnen": 1}),
        "Eemsdelta": (2021, {"Appingedam": 1, "Delfzijl": 1, "Loppersum": 1}),
        "Boxtel": (2021, {"Boxtel": 1, "Haaren": 0.25}),
        "Tilburg": (2021, {"Tilburg": 1, "Haaren": 0.25}),
        "Vught": (2021, {"Vught": 1, "Haaren": 0.25}),
        "Oisterwijk": (2021, {"Oisterwijk": 1, "Haaren": 0.25}),
        "Dijk en Waard": (2022, {"Heerhugowaard": 1, "Langedijk": 1}),
        "Land van Cuijk": (2022, {"Boxmeer": 1, "Cuijk": 1, "Grave": 1, "Mill en Sint Hubert": 1, "Sint Anthonis": 1}),
        "Purmerend": (2022, {"Beemster": 1, "Purmerend": 1}),
        "Amsterdam": (2022, {"Amsterdam": 1, "Weesp": 1}),
        "Maashorst": (2022, {"Landerd": 1, "Uden": 1}),
        "Voorne aan Zee": (2022, {"Brielle": 1, "Hellevoetsluis": 1, "Westvoorne": 1}),  # 2023
    }


def apply_herindeling_for_year(values: pd.Series, jaar: int) -> pd.Series:
    """
    Apply herindelingen on a per-year Series indexed by Gemeenten.
    """
    rules = herindeling_rules()
    s = values.copy()
    for nieuwe_gem, (threshold_year, oude_gemeenten) in rules.items():
        if jaar <= threshold_year:
            for oude_gem, factor in oude_gemeenten.items():
                if oude_gem not in s.index:
                    continue
                if nieuwe_gem in s.index:
                    s.loc[nieuwe_gem] = s.loc[nieuwe_gem] + factor * s.loc[oude_gem]
                else:
                    s.loc[nieuwe_gem] = factor * s.loc[oude_gem]
                s = s.drop(index=oude_gem)
    return s


def aggregate_to_taakveldgroepen(pv: pd.DataFrame) -> pd.DataFrame:
    """
    From pivoted Iv3 data, aggregate to TAAKVELDGROEPEN and return long rows.
    """
    rows: list[pd.DataFrame] = []
    for group_name, prefixes in TAAKVELDGROEPEN.items():
        sub = pv[pv[COL_TAAKVELD].astype(str).str.startswith(prefixes)]
        if sub.empty:
            continue
        agg = sub.groupby(COL_GEMEENTE, as_index=False)[["Baten", "Lasten", "Saldo"]].sum()
        long = agg.melt(id_vars=[COL_GEMEENTE], value_vars=["Baten", "Lasten", "Saldo"], var_name="Categorie", value_name="Waarde")
        long.insert(1, "Taakveld", group_name)
        rows.append(long)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=[COL_GEMEENTE, "Taakveld", "Categorie", "Waarde"])


def build_year_document(
    *,
    iv3_csv: Path,
    jaar: int,
    document_label: str,
    value_col: str,
) -> pd.DataFrame:
    """
    Build long-format rows for one year + one document (Begroting/Jaarrekening).
    """
    if not iv3_csv.exists():
        raise FileNotFoundError(f"Iv3 file not found: {iv3_csv}")

    raw = pd.read_csv(iv3_csv)
    pv = pivot_iv3(raw, value_col=value_col)
    pv = pv[~pv[COL_TAAKVELD].astype(str).str.startswith(("A", "P"))]

    df = aggregate_to_taakveldgroepen(pv)
    df.insert(1, "Jaar", str(jaar))
    df.insert(2, "Document", document_label)

    # apply herindeling per (Taakveld, Categorie)
    out_parts: list[pd.DataFrame] = []
    for (taakveld, categorie), part in df.groupby(["Taakveld", "Categorie"], dropna=False):
        s = part.set_index(COL_GEMEENTE)["Waarde"]
        s2 = apply_herindeling_for_year(s, jaar)
        p2 = s2.rename("Waarde").reset_index()
        p2.insert(1, "Taakveld", taakveld)
        p2.insert(2, "Categorie", categorie)
        p2.insert(3, "Jaar", str(jaar))
        p2.insert(4, "Document", document_label)
        out_parts.append(p2)

    out = pd.concat(out_parts, ignore_index=True) if out_parts else df
    return out[[COL_GEMEENTE, "Jaar", "Taakveld", "Categorie", "Document", "Waarde"]]


def add_standen(
    df: pd.DataFrame,
    *,
    population_df: pd.DataFrame | None,
    population_col: str | None,
) -> pd.DataFrame:
    """
    Add `Stand` dimension. Always emits "Totaal". If population data is present,
    also emits "Per inwoner" (in € 1, assuming `Waarde` is in € 1.000).
    """
    totaal = df.copy()
    totaal.insert(2, "Stand", "Totaal")

    if population_df is None or not population_col:
        return totaal

    # Prefer population already present on df (e.g. because we merged classes earlier).
    if population_col in df.columns:
        merged = df.copy()
        pop_col_effective = population_col
    else:
        pop = population_df[[COL_GEMEENTE, population_col]].dropna()
        merged = df.merge(pop, on=COL_GEMEENTE, how="left", suffixes=("", "_pop"))
        # if df already had a column with the same name, pandas would have suffixed it
        pop_col_effective = population_col if population_col in merged.columns else f"{population_col}_pop"

    merged = merged.dropna(subset=[pop_col_effective])
    merged["Waarde"] = 1000 * merged["Waarde"] / merged[pop_col_effective]
    per_inw = merged.drop(columns=[pop_col_effective])
    per_inw.insert(2, "Stand", "Per inwoner")

    return pd.concat([totaal, per_inw], ignore_index=True)


def add_aggregates(df: pd.DataFrame, *, population_col: str | None = None) -> pd.DataFrame:
    """
    Add aggregate rows for:
    - Nederland (sum)
    - Provincie (sum)
    - Grootteklasse (sum)

    If `Stand == Per inwoner`, aggregation is based on sums of totals + sums of population.
    """
    if "Provincie" not in df.columns or "Grootteklasse" not in df.columns:
        return df

    base_cols = ["Jaar", "Stand", "Document", "Categorie", "Taakveld"]

    def _sum_group(group_name: str, key_col: str) -> pd.DataFrame:
        if df["Stand"].nunique() == 1 and df["Stand"].iloc[0] == "Totaal":
            grp = df.groupby([key_col] + base_cols, as_index=False)["Waarde"].sum()
            grp = grp.rename(columns={key_col: COL_GEMEENTE})
            return grp

        if population_col and population_col in df.columns:
            grp = df.groupby([key_col] + [c for c in base_cols if c != "Stand"], as_index=False).agg(
                Waarde=("Waarde", "sum"),
                pop=(population_col, "sum"),
            )
            grp_t = grp.copy()
            grp_t.insert(2, "Stand", "Totaal")
            grp_t = grp_t.drop(columns=["pop"])

            grp_p = grp.copy()
            grp_p["Waarde"] = 1000 * grp_p["Waarde"] / grp_p["pop"]
            grp_p.insert(2, "Stand", "Per inwoner")
            grp_p = grp_p.drop(columns=["pop"])

            out = pd.concat([grp_t, grp_p], ignore_index=True)
            out = out.rename(columns={key_col: COL_GEMEENTE})
            return out

        # Fallback: just sum the already per-inwoner values (not ideal, but avoids crash)
        grp = df.groupby([key_col] + base_cols, as_index=False)["Waarde"].mean()
        grp = grp.rename(columns={key_col: COL_GEMEENTE})
        return grp

    # Nederland
    nl = df.groupby(base_cols, as_index=False)["Waarde"].sum()
    nl[COL_GEMEENTE] = "Nederland"

    prov = _sum_group("Provincie", "Provincie")
    gro = _sum_group("Grootteklasse", "Grootteklasse")

    return pd.concat([df, nl, prov, gro], ignore_index=True)


def load_classes(classes_csv: Path) -> tuple[pd.DataFrame, str | None]:
    """
    Load classes CSV. Supports both:
    - repo `gemeenteklassen.csv` (no population)
    - richer files with population columns like Inwoners/Inwonertal
    """
    kldf = pd.read_csv(classes_csv, sep=None, engine="python")
    pop_col = None
    for candidate in ["Inwoners", "Inwonertal", "Population", "Populatie"]:
        if candidate in kldf.columns:
            pop_col = candidate
            break
    return kldf, pop_col


def build_dataset(
    *,
    iv3_dir: Path,
    years: Iterable[int],
    classes_csv: Path,
    value_col: str,
) -> pd.DataFrame:
    docdict = {
        "Begroting": "000",
        "Jaarrekening": "005",
    }

    classes_df, pop_col = load_classes(classes_csv)

    parts: list[pd.DataFrame] = []
    for jaar in years:
        for doc_label, doc_code in docdict.items():
            iv3_path = iv3_dir / f"{jaar}{doc_code}.csv"
            part = build_year_document(iv3_csv=iv3_path, jaar=jaar, document_label=doc_label, value_col=value_col)
            parts.append(part)

    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    df = df.merge(classes_df, on=COL_GEMEENTE, how="left")

    df = add_standen(df, population_df=classes_df if pop_col else None, population_col=pop_col)
    df = add_aggregates(df, population_col=pop_col)

    # Keep only columns used by Streamlit app (extra class columns harmless, but keep tidy)
    keep_cols = [COL_GEMEENTE, "Jaar", "Stand", "Taakveld", "Document", "Categorie", "Waarde"]
    return df[keep_cols]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate begroting_rekening dataset for Streamlit.")
    p.add_argument(
        "--iv3-dir",
        type=Path,
        required=False,
        default=DEFAULT_IV3_DIR,
        help="Directory containing Iv3 CSVs like 2017000.csv.",
    )
    p.add_argument(
        "--classes-csv",
        type=Path,
        required=False,
        default=DEFAULT_CLASSES_CSV,
        help="CSV with Provincie/Grootteklasse (+ optional population).",
    )
    p.add_argument("--value-col", type=str, default="k_2ePlaatsing_2", help="Iv3 value column to use.")
    p.add_argument("--year-start", type=int, default=DEFAULT_YEAR_START)
    p.add_argument("--year-end", type=int, default=DEFAULT_YEAR_END)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT_PICKLE)
    # Old script always wrote CSV too; keep that as default.
    p.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    years = range(args.year_start, args.year_end + 1)
    df = build_dataset(iv3_dir=args.iv3_dir, years=years, classes_csv=args.classes_csv, value_col=args.value_col)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(args.out)

    if args.out_csv is not None:
        df.to_csv(args.out_csv, index=False)

    print(f"Wrote {len(df):,} rows to {args.out}")
    if args.out_csv is not None:
        print(f"Wrote CSV to {args.out_csv}")


if __name__ == "__main__":
    main()