import pandas as pd

# Constants
DATAMAP = "C:/Dashboard/werk/iv3data/%s.csv"
KLASSEN_BASE_PATH = "C:/Dashboard/werk/gemdata/per_jaar"

COLUMN_NAMES = {
    'taakveld': 'TaakveldBalanspost',
    'categorie': 'Categorie',
    'waarde_col': 'k_2ePlaatsing_2',
    'gemeenten': 'Gemeenten'
}

DOCDICT = {
    "Begroting": "000",
    "Jaarrekening": "005",
}

TAAKVELDGROEPEN = { 
    'Bestuur en burgerzaken': ("0.1 ", "0.2"),
    'Overhead': ("0.4"),
    'Belastingen': ("0.6"),
    'Gemeentefonds': ("0.7"), 
    'Overig bestuur en ondersteuning': ("0.3", "0.5", "0.8", "0.9"),
    'Veiligheid': ("1."),
    'Verkeer en vervoer': ("2."),
    'Economie': ("3."),
    'Onderwijs': ("4."),
    'SCR': ("5."),
    'Algemene voorzieningen': ("6.1", "6.2"),
    'Inkomensregelingen': ("6.3"),
    'Participatie': ("6.4", "6.5"),
    'Maatwerk Wmo': ("6.6", "6.71", "6.81"),
    'Maatwerk Jeugd': ("6.72", "6.73", "6.74", "6.82"),
    'Volksgezondheid en milieu': ("7."),
    'Grondexploitatie': ("8.2"),
    'Wonen en bouwen': ("8.1", "8.3"),
}

HERINDELERS = {
    'Meierijstad': [2017, {'Schijndel': 1, 'Sint-Oedenrode': 1, 'Veghel': 1}],
    'Leeuwarden': [2018, {'Leeuwarden': 1, 'Leeuwarderadeel': 1, 'Littenseradiel': 0.32}],
    'Midden-Groningen': [2018, {'Hoogezand-Sappemeer': 1, 'Menterwolde': 1, 'Slochteren': 1}],
    'Waadhoeke': [2018, {'Franekeradeel': 1, 'het Bildt': 1, 'Menameradiel': 1, 'Littenseradiel': 0.17}],
    'Westerwolde': [2018, {'Bellingwedde': 1, 'Vlagtwedde': 1}],
    'Zevenaar': [2018, {'Rijnwaarden': 1, 'Zevenaar': 1}],
    'Súdwest-Fryslân': [2018, {'Bolsward': 1, 'Nijefurd': 1, 'Sneek': 1, 'Wonseradeel': 1, 'Wûnseradiel': 1, 'Wymbritseradiel': 1, 'Wymbritseradeel': 1, 'Littenseradiel': 0.51, 'Súdwest-Fryslân': 1}],
    'Groningen (gemeente)': [2019, {'Groningen (gemeente)': 1, 'Haren': 1, 'Ten Boer': 1}],
    'Het Hogeland': [2019, {'Bedum': 1, 'De Marne': 1, 'Eemsmond': 1, 'Winsum': 0.884}],
    'Westerkwartier': [2019, {'Grootegast': 1, 'Leek': 1, 'Marum': 1, 'Zuidhorn': 1, 'Winsum': 0.1157}],
    'Altena': [2019, {'Aalburg': 1, 'Werkendam': 1, 'Woudrichem': 1}],
    'Beekdaelen': [2019, {'Nuth': 1, 'Onderbanken': 1, 'Schinnen': 1}],
    'Haarlemmermeer': [2019, {'Haarlemmerliede en Spaarnwoude': 1, 'Haarlemmermeer': 1}],
    'Hoeksche Waard': [2019, {'Binnenmaas': 1, 'Cromstrijen': 1, 'Korendijk': 1, 'Oud-Beijerland': 1, 'Strijen': 1, "'s-Gravendeel": 1}],
    'Noardeast-Fryslân': [2019, {'Dongeradeel': 1, 'Ferwerderadiel': 1, 'Kollumerland en Nieuwkruisland': 1}],
    'Molenlanden': [2019, {'Graafstroom': 1, 'Liesveld': 1, 'Nieuw-Lekkerland': 1, 'Molenwaard': 1, 'Giessenlanden': 1}],
    'Noordwijk': [2019, {'Noordwijk': 1, 'Noordwijkerhout': 1}],
    'Vijfheerenlanden': [2019, {'Leerdam': 1, 'Zederik': 1, 'Vianen': 1}],
    'West Betuwe': [2019, {'Geldermalsen': 1, 'Lingewaal': 1, 'Neerijnen': 1}],
    'Eemsdelta': [2021, {'Appingedam': 1, 'Delfzijl': 1, 'Loppersum': 1}],
    'Boxtel': [2021, {'Boxtel': 1, 'Haaren': 0.25}],
    'Tilburg': [2021, {'Tilburg': 1, 'Haaren': 0.25}],
    'Vught': [2021, {'Vught': 1, 'Haaren': 0.25}],
    'Oisterwijk': [2021, {'Oisterwijk': 1, 'Haaren': 0.25}],
    'Dijk en Waard': [2022, {'Heerhugowaard': 1, 'Langedijk': 1}],
    'Land van Cuijk': [2022, {'Boxmeer': 1, 'Cuijk': 1, 'Grave': 1, 'Mill en Sint Hubert': 1, 'Sint Anthonis': 1}],
    'Purmerend': [2022, {'Beemster': 1, 'Purmerend': 1}],
    'Amsterdam': [2022, {'Amsterdam': 1, 'Weesp': 1}],
    'Maashorst': [2022, {'Landerd': 1, 'Uden': 1}],
    'Voorne aan Zee': [2022, {"Brielle": 1, "Hellevoetsluis": 1, "Westvoorne": 1}],  # 2023
}


def pivotIv3(df, k_col=None):
    """Pivot the dataframe and calculate Baten, Lasten, and Saldo."""
    if k_col is None:
        k_col = COLUMN_NAMES['waarde_col']
    
    t = COLUMN_NAMES['taakveld']
    c = COLUMN_NAMES['categorie']
    g = COLUMN_NAMES['gemeenten']
    
    pv = df.pivot(index=[g, t], columns=c, values=[k_col])
    
    pv.columns = [col[-1] for col in pv.columns]
    batencolumns = [col for col in pv.columns if col.startswith("B")]
    lastencolumns = [col for col in pv.columns if col.startswith("L")]
    
    pv['Baten'] = pv[batencolumns].sum(axis=1)
    pv['Lasten'] = pv[lastencolumns].sum(axis=1)
    pv['Saldo'] = pv.apply(lambda row: row.Baten - row.Lasten, axis=1)
    
    df2 = pv.reset_index()
    
    return df2


def calc_mult(m0, mi):
    """Calculate multiplier for a given municipality."""
    k = COLUMN_NAMES['waarde_col']
    g = COLUMN_NAMES['gemeenten']
    
    m0v = m0[k].sum()
    m0m = m0.loc[m0[g].str.startswith(mi)]
    m0mv = m0m[k].sum()
    multi = 1/(1-m0mv/m0v)
    
    return multi


def herindeling(jaar, df):
    """Apply municipality reorganizations (herindelingen) to the dataframe."""
    for nieuwe_gem, inf in HERINDELERS.items():
        if jaar <= inf[0]:
            oude_gemeenten = inf[1]
            for oude_gem, factor in oude_gemeenten.items():
                if nieuwe_gem in df.index and oude_gem in df.index:
                    df.loc[nieuwe_gem] += factor * df.loc[oude_gem]
                elif oude_gem in df.index:
                    df.loc[nieuwe_gem] = factor * df.loc[oude_gem]
                else:
                    pass
                    
                if oude_gem in df.index:
                    df = df.drop(oude_gem)
    
    return df


def get_waarde_column(jaar):
    """Get the appropriate value column name based on year."""
    if jaar == 2026:
        return 'k_1ePlaatsing_1'
    return COLUMN_NAMES['waarde_col']


def filter_taakvelden(taakvelden):
    """Filter out taakvelden that start with A or P."""
    return [i for i in taakvelden if not i.startswith(("A", "P"))]


def create_taakveld_dataframe(pv, taakveld, categorie, jaar, document_naam):
    """Create a dataframe for a specific taakveld and categorie."""
    t = COLUMN_NAMES['taakveld']
    g = COLUMN_NAMES['gemeenten']
    
    tvalues = pv.loc[pv[t].str.startswith(taakveld)].groupby(g)[categorie].sum().rename('Waarde')
    tvalueframe = tvalues.to_frame()
    tvalueframe.insert(0, 'Categorie', categorie)
    tvalueframe.insert(0, 'Taakveld', taakveld)
    tvalueframe.insert(0, 'Document', document_naam)
    tvalueframe.insert(0, 'Jaar', jaar)
    
    return tvalueframe


def process_document(jaar, document_naam, doc_code):
    """Process a single document (Begroting or Jaarrekening) for a given year."""
    # Skip if year is beyond available data
    if jaar > 2025 or (jaar == 2025 and document_naam == "Jaarrekening"):
        return None
    
    # Get appropriate value column
    k_col = get_waarde_column(jaar)
    
    # Load and pivot data
    document = str(jaar) + doc_code
    df = pd.read_csv(DATAMAP % document)
    pv = pivotIv3(df, k_col=k_col)
    
    # Get and filter taakvelden
    taakvelden = pv[COLUMN_NAMES['taakveld']].unique()
    taakvelden = filter_taakvelden(taakvelden)
    
    # Create dataframes for each taakveld and categorie
    dataframes = []
    for tv in taakvelden:
        for categorie in ['Baten', 'Lasten', 'Saldo']:
            tvalueframe = create_taakveld_dataframe(pv, tv, categorie, jaar, document_naam)
            dataframes.append(tvalueframe)
    
    # Combine all dataframes
    if dataframes:
        combined_df = pd.concat(dataframes)
        return combined_df
    return None


def load_gemeenteklassen(jaar):
    """Load gemeenteklassen data for a given year."""
    if jaar == 2026:
        klassenlocatie = f"{KLASSEN_BASE_PATH}/2025.csv"
    else:
        klassenlocatie = f"{KLASSEN_BASE_PATH}/{jaar}.csv"
    
    kldf = pd.read_csv(klassenlocatie, sep=";", decimal=",")
    return kldf


def process_year(jaar):
    """Process all documents for a single year and merge with gemeenteklassen."""
    bejr = []
    
    for naam, doc in DOCDICT.items():
        result = process_document(jaar, naam, doc)
        if result is not None:
            bejr.append(result)
    
    if len(bejr) == 0:
        return None
    elif len(bejr) == 1:
        outputdf = bejr[0]
    else:
        outputdf = pd.concat(bejr)
    
    # Merge with gemeenteklassen
    kldf = load_gemeenteklassen(jaar)
    merged_df = pd.merge(outputdf, kldf, on="Gemeenten")
    
    return merged_df


def add_aggregate_groups(df):
    """Add aggregate groups (Nederland, Provincie, Gemeentegrootte, Stedelijkheid)."""
    # Group by all gemeenten (Nederland)
    all_groups = df.groupby(['Jaar', 'Document', 'Categorie', 'Taakveld']).agg({
        'Waarde': 'sum',
        'Inwonertal': 'sum'
    }).reset_index()
    all_groups['Gemeenten'] = 'Nederland'
    df = pd.concat([df, all_groups], ignore_index=True)
    
    # Group by provincie
    provincie_groups = df.groupby(['Provincie', 'Jaar', 'Document', 'Categorie', 'Taakveld']).agg({
        'Waarde': 'sum',
        'Inwonertal': 'sum'
    }).reset_index()
    provincie_groups = provincie_groups.rename(columns={'Provincie': 'Gemeenten'})
    df = pd.concat([df, provincie_groups], ignore_index=True)
    
    # Group by gemeentegrootte
    grootteklasse_groups = df.groupby(['Gemeentegrootte', 'Jaar', 'Document', 'Categorie', 'Taakveld']).agg({
        'Waarde': 'sum',
        'Inwonertal': 'sum'
    }).reset_index()
    grootteklasse_groups = grootteklasse_groups.rename(columns={'Gemeentegrootte': 'Gemeenten'})
    df = pd.concat([df, grootteklasse_groups], ignore_index=True)
    
    # Group by stedelijkheid
    stedelijkheid_groups = df.groupby(['Stedelijkheid', 'Jaar', 'Document', 'Categorie', 'Taakveld']).agg({
        'Waarde': 'sum',
        'Inwonertal': 'sum'
    }).reset_index()
    stedelijkheid_groups = stedelijkheid_groups.rename(columns={'Stedelijkheid': 'Gemeenten'})
    df = pd.concat([df, stedelijkheid_groups], ignore_index=True)
    
    # Clean up
    df = df.drop(columns=['Provincie', 'Gemeentegrootte', 'Stedelijkheid'])
    df = df.dropna(subset=['Gemeenten'])
    
    return df


def process_all_years(start_year=2017, end_year=2027):
    """Process all years and combine into a single dataframe."""
    all_dataframes = []
    
    for jaar in range(start_year, end_year):
        result = process_year(jaar)
        if result is not None:
            all_dataframes.append(result)
    
    if not all_dataframes:
        return pd.DataFrame()
    
    combined_df = pd.concat(all_dataframes)
    return combined_df


def save_output(df, output_path="begroting_rekening_per_taakveld.pickle"):
    """Save the final dataframe to a pickle file."""
    df.to_pickle(output_path)
    # Alternative CSV output (commented out):
    # df.to_csv(output_path.replace('.pickle', '.csv'), sep=",", decimal=".", float_format='%.4f')


def main():
    """Main function to execute the data processing pipeline."""
    pd.set_option('display.max_columns', None)
    
    # Process all years
    print("Processing data...")
    df = process_all_years()
    
    # Add aggregate groups
    print("Adding aggregate groups...")
    df = add_aggregate_groups(df)
    
    # Display results
    print(df)
    
    # Save output
    print("Saving output...")
    save_output(df)
    print("Done!")


if __name__ == "__main__":
    main()
