import csv
import json
from io import BytesIO

import altair as alt
import pandas as pd
import streamlit as st
import matplotlib
import vl_convert as vlc

# ============================================================================
# CONSTANTS
# ============================================================================

DATA_FILE = "begroting_rekening.pickle"
CLASSES_FILE = "gemeenteklassen.csv"
ROOT_FACTOR = 0.4  # For gradient map calculation

TAAKVELD_REPLACEMENTS = {
    'Overig bestuur en ondersteuning': 'Overig bestuur en onderst.'
}

TAVELD_GROUPS = {
    "Inkomsten": [
        "Gemeentefonds", "Belastingen", "Overig bestuur en onderst.",
        "Grondexploitatie", "Economie",
    ],
    "Klassiek domein": [
        "Bestuur en burgerzaken", "Overhead", "Veiligheid",
        "Verkeer en vervoer", "Onderwijs", "SCR",
        "Volksgezondheid en milieu", "Wonen en bouwen",
    ],
    "Sociaal domein": [
        "Algemene voorzieningen", "Inkomensregelingen", "Participatie",
        "Maatwerk Wmo", "Maatwerk Jeugd",
    ]
}

ALLEEN_PER_INWONER = [
    "Groningen", "Friesland", "Drenthe", "Overijssel", "Gelderland",
    "Flevoland", "Utrecht", "Noord-Brabant", "Limburg", "Noord-Holland",
    "Zuid-Holland", "Zeeland", "100.000 tot 150.000 inwoners",
    "10.000 tot 20.000 inwoners", "150.000 tot 250.000 inwoners",
    "20.000 tot 50.000 inwoners", "Noord-Brabant",
    "250.000 inwoners of meer", "50.000 tot 100.000 inwoners",
    "5.000 tot 10.000 inwoners", "minder dan 5.000 inwoners"
]

# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

@st.cache_resource
def get_data():
    """
    Load and return the budget/reckoning data with error handling.
    
    Returns:
        pd.DataFrame: The loaded data, or empty DataFrame if loading fails.
    """
    filepath = DATA_FILE
    
    try:
        data = pd.read_pickle(filepath)
        
        if data.empty:
            st.error("⚠️ Data file is empty. Please check the data source.")
            return pd.DataFrame()
        
        # Validate required columns exist
        required_cols = ['Gemeenten', 'Jaar', 'Stand', 'Taakveld', 'Document', 'Waarde', 'Categorie']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            st.error(f"⚠️ Missing required columns in data: {', '.join(missing_cols)}")
            return pd.DataFrame()
        
        return data
        
    except FileNotFoundError:
        st.error(f"❌ Data file '{filepath}' not found. Please ensure the file exists.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        return pd.DataFrame()


@st.cache_resource
def get_year_range():
    """
    Extract minimum and maximum years from the data.
    
    Returns:
        tuple: (min_year, max_year) as integers.
    """
    data = get_data()
    if data.empty:
        return None, None
    
    try:
        jaren = data['Jaar'].astype(int).unique()
        return int(jaren.min()), int(jaren.max())
    except Exception as e:
        st.warning(f"Could not extract year range: {str(e)}")
        return None, None


@st.cache_data
def get_classes():
    """
    Load provincie and grootteklasse mappings from CSV file.
    
    Returns:
        tuple: (provincie_dict, grootteklasse_dict) mapping gemeente names.
    """
    filepath = CLASSES_FILE
    
    try:
        with open(filepath, mode='r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            rows = list(reader)
        
        if not rows:
            st.warning(f"⚠️ {filepath} is empty.")
            return {}, {}
        
        provincie_dict = {row[0]: row[1] for row in rows if len(row) > 1}
        grootteklasse_dict = {row[0]: row[2] for row in rows if len(row) > 2}
        
        return provincie_dict, grootteklasse_dict
        
    except FileNotFoundError:
        st.warning(f"⚠️ Classes file '{filepath}' not found. Comparison features may be limited.")
        return {}, {}
    except Exception as e:
        st.warning(f"⚠️ Error loading classes file: {str(e)}")
        return {}, {}


@st.cache_data
def filter_data(data,
                gemeente,
                stand,
                jaarmin=None,
                jaarmax=None,
                vergelijking=None):
    """
    Filter data based on gemeente, stand, year range, and optional comparison.
    
    Args:
        data: DataFrame to filter
        gemeente: Name of the gemeente to filter by
        stand: "Totaal" or "Per inwoner"
        jaarmin: Minimum year (optional)
        jaarmax: Maximum year (optional)
        vergelijking: Comparison entity name (optional)
        
    Returns:
        pd.DataFrame: Filtered data
    """
    # Validate input data
    if data.empty:
        st.warning("⚠️ No data available for filtering.")
        return pd.DataFrame()
    
    # Validate gemeente exists in data
    if gemeente not in data['Gemeenten'].values:
        st.warning(f"⚠️ Gemeente '{gemeente}' not found in data.")
        return pd.DataFrame()
    
    # Validate stand exists in data
    if stand not in data['Stand'].values:
        st.warning(f"⚠️ Stand '{stand}' not found in data.")
        return pd.DataFrame()
    
    # Get year range from data if not provided
    if jaarmin is None or jaarmax is None:
        jaar_min, jaar_max = get_year_range()
        if jaar_min is None or jaar_max is None:
            st.warning("⚠️ Could not determine year range.")
            return pd.DataFrame()
        if jaarmin is None:
            jaarmin = jaar_min
        if jaarmax is None:
            jaarmax = jaar_max

    # Tuple of jaren (saved as category)
    jaar_range = tuple([str(i) for i in range(jaarmin, jaarmax + 1)])

    # Select by gemeente and Totaal/Per inwoner, no Provincie or Grootteklasse
    if not vergelijking:
        filtered_data = data[(data['Stand'] == stand)
                             & (data['Gemeenten'] == gemeente)
                             & (data['Jaar'].str.startswith(jaar_range))].copy()

    # Select by gemeente and stand and vergelijking (Gemeente, Provincie, Grootteklasse)
    else:
        # Validate vergelijking exists
        if vergelijking not in data['Gemeenten'].values:
            st.warning(f"⚠️ Comparison entity '{vergelijking}' not found in data.")
            return pd.DataFrame()
        
        filtered_data = data[(data['Stand'] == stand)
                             & (data['Jaar'].str.startswith(jaar_range)
                                & ((data['Gemeenten'] == gemeente)
                                   | (data['Gemeenten'] == vergelijking)))].copy()

    # Replace long taakveld names
    if not filtered_data.empty:
        filtered_data.loc[:, 'Taakveld'] = filtered_data['Taakveld'].replace(
            TAAKVELD_REPLACEMENTS
        )

    return filtered_data


@st.cache_data
def calculate_saldo(data):
    """
    Calculate saldo (balance) grouped by year and document type.
    
    Args:
        data: DataFrame containing financial data
        
    Returns:
        pd.DataFrame: Saldo values per year and document
    """
    if data.empty:
        return pd.DataFrame()
    
    saldo = data.loc[(data['Categorie'] == 'Saldo')].groupby(
        ['Jaar', 'Document'], observed=False)['Waarde'].sum().reset_index()

    saldo = saldo[(saldo['Waarde'] != 0)]

    return saldo


def show_saldo(saldo, stand, legend=True):
    """
    Create an Altair line chart showing saldo over time.
    
    Args:
        saldo: DataFrame with saldo data
        stand: "Per inwoner" or "Totaal" to determine axis title
        legend: Whether to show legend
        
    Returns:
        alt.Chart: Configured Altair chart
    """
    if saldo.empty:
        return None
    
    if stand == "Per inwoner":
        axis_title = "€ 1"
    else:
        axis_title = "€ 1.000"

    if legend:
        chart = alt.Chart(saldo).mark_line(point=True).encode(
            x=alt.X('Jaar:O'),
            y=alt.Y('Waarde:Q', title=axis_title),
            color='Document:N',
            tooltip=['Jaar', 'Waarde:Q', 'Document']
        ).configure_legend(title=None).properties(
            usermeta={
                "embedOptions": {
                    "formatLocale": vlc.get_format_locale("nl-NL"),
                }
            }
        ).interactive()
    else:
        chart = alt.Chart(saldo).mark_line(point=True).encode(
            x=alt.X('Jaar:O'),
            y=alt.Y('Waarde:Q', title=axis_title),
            color=alt.Color('Document:N', legend=None),
            tooltip=['Jaar', 'Waarde:Q', 'Document']
        ).interactive()

    return chart


def show_saldo_legend(saldo):
    """
    Create a legend-only chart for saldo.
    
    Args:
        saldo: DataFrame with saldo data
        
    Returns:
        alt.Chart: Legend chart
    """
    if saldo.empty:
        return None
    
    chart = alt.Chart(saldo, height=25).mark_line().encode(
        color=alt.Color('Document:N')
    ).configure_view(
        clip=False
    ).configure_legend(title=None, orient="top")

    return chart


@st.cache_data
def calculate_begroting_rekening(data, baten_lasten, jaar):
    """
    Filter data for specific category (baten/lasten) and year.
    
    Args:
        data: DataFrame to filter
        baten_lasten: Category name ("Baten" or "Lasten")
        jaar: Year as string or int
        
    Returns:
        pd.DataFrame: Filtered data
    """
    if data.empty:
        return pd.DataFrame()
    
    br_data = data[(data['Categorie'] == baten_lasten)
                   & (data['Jaar'] == str(jaar))]

    return br_data


def show_begroting_rekening(br_data, stand):
    """
    Create a bar chart comparing begroting vs jaarrekening per taakveld.
    
    Args:
        br_data: DataFrame with begroting/rekening data
        stand: "Per inwoner" or "Totaal" to determine axis title
        
    Returns:
        alt.Chart: Configured Altair chart
    """
    if br_data.empty:
        return None
    
    if stand == "Per inwoner":
        axis_title = "€ 1"
    else:
        axis_title = "€ 1.000"
    
    br_chart = alt.Chart(br_data).mark_bar().encode(
        y=alt.Y('Document:N',
                title='',
                axis=alt.Axis(labels=False, ticks=False)
                ),
        x=alt.X('Waarde:Q', title=axis_title),
        color='Document:N',
        tooltip=['Taakveld', 'Document', 'Waarde:Q'],
        row=alt.Row(
            'Taakveld:N',
            sort=alt.EncodingSortField(field="Waarde", order='descending'),
            spacing=5,
            header=alt.Header(
                labelAngle=0,
                labelAlign='left',
                title=None,
                labelFontSize=15,
                labelPadding=15
            )
        )
    ).configure_axis(labelFontSize=15).configure_header(
        title=None
    ).configure_legend(title=None).interactive()

    return br_chart


@st.cache_data
def create_tables(data, categorie, gemeente):
    """
    Create comparison tables grouped by taakveld categories.
    
    Args:
        data: DataFrame with financial data
        categorie: Category to analyze ("Baten", "Lasten", or "Saldo")
        gemeente: Name of the gemeente
        
    Returns:
        tuple: (tables_dict, table_columns) where tables_dict contains grouped tables
    """
    if data.empty:
        return {}, []

    # Filter data
    df = data.loc[data['Categorie'] == categorie].copy()

    if df.empty:
        st.warning(f"⚠️ No data found for category '{categorie}'.")
        return {}, []

    # Check Gemeenten in dataframe
    gemeenten = df['Gemeenten'].astype(str).unique().tolist()
    jaren = df['Jaar'].astype(str).unique().tolist()

    if len(gemeenten) == 1:
        # Calculate table
        table = calculate_difference(df)
    elif len(gemeenten) == 2:
        vergelijking = gemeenten[1] if gemeenten[0] == gemeente else gemeenten[0]
        table_headers = [gemeente, vergelijking]
        table_suffixes = [
            "                                                            {}".format(gemeente),
            "                                                            {}".format(vergelijking)
        ]

        tables = []
        for g in table_headers:
            dfg = df.loc[(df['Gemeenten'] == g)]
            tables.append(calculate_difference(dfg))

        table = pd.merge(tables[0],
                         tables[1],
                         on=['Taakveld'],
                         suffixes=(table_suffixes))

        table = table.fillna(0)
        table = table.astype(int)

        # add in blank column for readability
        column_position = len(jaren)
        table.insert(column_position, ' ', "")
    else:
        st.warning("⚠️ Unexpected number of gemeenten in data.")
        return {}, []

    # Create grouped tables using constants
    tables = {}
    for group_name, taakvelden in TAVELD_GROUPS.items():
        try:
            group_table = table.loc[taakvelden]
            tables[group_name] = group_table
        except KeyError as e:
            # Some taakvelden might not exist in the data
            missing = [tv for tv in taakvelden if tv not in table.index]
            if missing:
                st.warning(f"⚠️ Some taakvelden not found for {group_name}: {', '.join(missing)}")
            # Try to get available taakvelden
            available = [tv for tv in taakvelden if tv in table.index]
            if available:
                tables[group_name] = table.loc[available]

    return tables, table.columns


def calculate_difference(df):
    """
    Calculate the difference between jaarrekening and begroting values.
    
    Args:
        df: DataFrame containing jaarrekening and begroting data
        
    Returns:
        pd.DataFrame: Pivoted DataFrame with differences per taakveld and year
        
    Raises:
        ValueError: If required columns are missing
    """
    if df.empty:
        return pd.DataFrame()
    
    required_cols = ['Gemeenten', 'Categorie', 'Document', 'Jaar', 'Taakveld', 'Waarde']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Remove unused columns
    df = df.drop(columns=['Gemeenten', 'Categorie']).copy()

    # Separate into jaarrekening and begroting
    jaarrekening = df.loc[df['Document'] == 'Jaarrekening']
    begroting = df.loc[df['Document'] == 'Begroting']
    
    if jaarrekening.empty or begroting.empty:
        return pd.DataFrame()

    # Merge and calculate difference
    merged_df = pd.merge(jaarrekening,
                         begroting,
                         on=['Jaar', 'Taakveld'],
                         suffixes=('_jr', '_bg'),
                         how='outer')
    
    # Fill NaN values with 0 for calculation
    merged_df['Waarde_jr'] = merged_df['Waarde_jr'].fillna(0)
    merged_df['Waarde_bg'] = merged_df['Waarde_bg'].fillna(0)
    
    merged_df['Verschil'] = merged_df['Waarde_jr'] - merged_df['Waarde_bg']
    merged_df['Verschil'] = merged_df['Verschil'].astype(int)

    # Remove Jaren with empty values
    merged_df = merged_df[((merged_df['Verschil'] != merged_df['Waarde_bg']) &
                           (merged_df['Waarde_bg'] != 0)) | 
                          ((merged_df['Verschil'] != -merged_df['Waarde_jr']) &
                           (merged_df['Waarde_jr'] != 0)) |
                          ((merged_df['Waarde_jr'] == 0) &
                           (merged_df['Waarde_bg'] == 0))]

    if merged_df.empty:
        return pd.DataFrame()

    # Pivot table and change column headers
    pv = merged_df.pivot(index='Taakveld', columns='Jaar', values='Verschil')
    
    if isinstance(pv.columns, pd.MultiIndex):
        pv.columns = pv.columns.droplevel(0)

    return pv


def style_table(table, categorie):
    """
    Apply gradient styling to table based on values.
    
    Args:
        table: DataFrame to style
        categorie: Category name for gradient direction
        
    Returns:
        Styled DataFrame
    """
    if table.empty:
        return table.style
    
    gm = calculate_gradient_map(table, categorie)
    styled_pv = table.style.background_gradient(
        cmap="RdBu",
        gmap=gm,
        axis=None
    ).format(
        thousands='.',
    )

    return styled_pv


def calculate_gradient_map(x, categorie):
    """
    Calculate gradient map values for table styling.
    
    Args:
        x: DataFrame to calculate gradient for
        categorie: Category name ("Baten", "Lasten", or "Saldo")
        
    Returns:
        DataFrame with gradient map values
    """
    if x.empty:
        return x
    
    x1 = x.map(lambda i: 0 if i == "" else i)

    x_min = abs(x1.values.min())
    x_max = abs(x1.values.max())
    
    if x_min == 0 and x_max == 0:
        return x1

    if abs(x_min) > x_max:
        # If minimum is higher than maximum, multiply by fraction max/min
        x2 = x1.map(lambda i: i * (x_min / x_max) / x_min
                    if i > 0 else i / x_min)
    else:
        # If maximum is higher: multiply by fraction min/max
        x2 = x1.map(lambda i: i * (x_max / x_min) / x_max
                    if i < 0 else i / x_max)

    # Take root to raise lower values
    x3 = x2.map(lambda i: i**ROOT_FACTOR if i >= 0 else -(abs(i)**ROOT_FACTOR))

    if categorie == "Lasten":
        x3 = x3.map(lambda i: -i)  # Reverse gradient map for lasten

    return x3


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

def export_table_to_excel(tables: dict, categorie: str, gemeente: str) -> BytesIO:
    """
    Export tables to Excel format.
    
    Args:
        tables: Dictionary of table names and DataFrames
        categorie: Category name for filename
        gemeente: Gemeente name for filename
        
    Returns:
        BytesIO: Excel file in memory
    """
    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for table_name, table in tables.items():
                # Excel sheet name limit is 31 characters
                sheet_name = table_name[:31]
                table.to_excel(writer, sheet_name=sheet_name)
                
                # Get the workbook and worksheet objects
                workbook = writer.book
                worksheet = writer.sheets[sheet_name]
                
                # Set column widths
                worksheet.set_column('A:A', 30)  # Taakveld column
                for col_num in range(1, len(table.columns) + 1):
                    worksheet.set_column(col_num, col_num, 15)
                
                # Create number format
                num_format = workbook.add_format({'num_format': '#,##0'})
                
                # Apply format to data cells
                for row in range(1, len(table) + 1):
                    for col in range(1, len(table.columns) + 1):
                        worksheet.write(row, col, table.iloc[row-1, col-1], num_format)
        
        output.seek(0)
        return output
    except Exception as e:
        st.error(f"Error creating Excel file: {str(e)}")
        return BytesIO()


def export_chart_data(chart_data: pd.DataFrame, filename: str) -> str:
    """
    Export chart data to CSV format.
    
    Args:
        chart_data: DataFrame to export
        filename: Suggested filename
        
    Returns:
        str: CSV data as string
    """
    if chart_data.empty:
        return ""
    return chart_data.to_csv(index=False)


def validate_data_quality(data: pd.DataFrame) -> dict:
    """
    Check data quality and return report.
    
    Args:
        data: DataFrame to validate
        
    Returns:
        dict: Quality report with statistics
    """
    if data.empty:
        return {'status': 'empty', 'message': 'Data is empty'}
    
    report = {
        'total_rows': len(data),
        'missing_values': data.isnull().sum().to_dict(),
        'duplicate_rows': data.duplicated().sum(),
        'year_range': (data['Jaar'].min(), data['Jaar'].max()) if 'Jaar' in data.columns else None,
        'gemeenten_count': data['Gemeenten'].nunique() if 'Gemeenten' in data.columns else 0
    }
    return report


# ============================================================================
# MAIN APPLICATION
# ============================================================================

# Wide screen
st.set_page_config(layout="wide", page_title="Begroting en Jaarrekening Vergelijken")

# Load data once at the start
with st.spinner("📊 Data laden..."):
    data = get_data()

# Stop execution if no data
if data.empty:
    st.error("❌ Geen data beschikbaar. Controleer de data bestanden.")
    st.stop()

# Validate data quality (optional, can be shown in expander)
data_quality = validate_data_quality(data)

# Sidebar
with st.sidebar:
    st.header("Selecteer hier de analyse")
    
    # Help section
    with st.expander("ℹ️ Hoe gebruik ik deze tool?"):
        st.markdown("""
        1. **Selecteer een gemeente** uit de dropdown
        2. **Kies of je wilt vergelijken** met andere entiteiten
        3. **Selecteer het jaarbereik** dat je wilt analyseren
        4. **Bekijk de grafieken en tabellen** hieronder
        5. **Download de gegevens** indien gewenst
        """)
    
    # Data refresh button
    if st.button("🔄 Vernieuw Data", help="Wis de cache en laad data opnieuw"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("✅ Cache gewist! Data wordt opnieuw geladen.")
        st.rerun()

    # Toggle for comparing yes/no
    vergelijken = st.toggle("Vergelijken", help="Vergelijk met provincie, grootteklasse of andere gemeente")

    gemeente_options = sorted(data.Gemeenten.unique())
    selected_gemeente = st.selectbox(
        "Selecteer een gemeente",
        gemeente_options,
        key=0,
        help="Kies een gemeente om te analyseren"
    )

    # If vergelijken: no options for stand, must be Per inwoner
    if not vergelijken and selected_gemeente not in ALLEEN_PER_INWONER:
        stand_options = sorted(data.Stand.unique())
        selected_stand = st.selectbox(
            "Selecteer totaal of per inwoner",
            stand_options,
            disabled=False,
            help="Kies of je absolute waarden of waarden per inwoner wilt zien"
        )
    else:
        stand_options = ["Per inwoner"]
        selected_stand = st.selectbox(
            "Selecteer totaal of per inwoner",
            stand_options,
            disabled=True,
            help="Voor vergelijkingen wordt alleen 'Per inwoner' gebruikt"
        )

    # If vergelijken, with what Provincie, Grootteklasse or Gemeente
    vergelijking = None
    if vergelijken:
        vergelijking_options = [
            'Provincie', 'Grootteklasse', 'Nederland', 'Andere gemeente'
        ]
        selected_vergelijking = st.selectbox(
            "Selecteer vergelijking",
            vergelijking_options,
            help="Kies waarmee je wilt vergelijken"
        )

        if selected_vergelijking == "Andere gemeente":
            gemeente_vergelijking = st.selectbox(
                "Selecteer een gemeente",
                gemeente_options,
                key=1,
                help="Kies een andere gemeente om mee te vergelijken"
            )

        provincie_dict, grootteklasse_dict = get_classes()

        if selected_vergelijking == "Nederland":
            vergelijking = "Nederland"
        elif selected_vergelijking == 'Provincie':
            vergelijking = provincie_dict.get(selected_gemeente)
            if not vergelijking:
                st.warning(f"⚠️ Geen provincie gevonden voor {selected_gemeente}")
        elif selected_vergelijking == 'Grootteklasse':
            vergelijking = grootteklasse_dict.get(selected_gemeente)
            if not vergelijking:
                st.warning(f"⚠️ Geen grootteklasse gevonden voor {selected_gemeente}")
        else:
            vergelijking = gemeente_vergelijking if 'gemeente_vergelijking' in locals() else None

# Body
referral_container = st.container()
header_container = st.container()
saldo_container = st.container()
taakveld_chart_container = st.container()
taakveld_table_container = st.container()
toelichting_container = st.container()

with referral_container:
    ch1, ch2, ch3 = st.columns([1,3,1])
    
    with ch2:
        st.markdown("*Linksboven in de sidebar👈 kan worden genavigeerd naar 📊Gemeenten per taakveld vergelijken*")
    
    st.markdown("---")

with header_container:
    ch1, ch2, ch3 = st.columns([2, 4, 2])

    with ch2:
        st.title("📈 Analyse verschil tussen begroting en rekening")
        st.markdown(
            "Deze tool laat voor elke gemeente zien waardoor de realisatie afwijkt van de begroting. Er kan worden vergeleken met het gemiddelde voor de grootteklasse of provincie, met andere gemeenten of met heel Nederland."
        )
        st.info("💡 Tip: Gebruik de jaarbereik slider om te focussen op specifieke periodes")
        st.markdown(
            "Onderstaande berekeningen zijn gemaakt op basis van onbewerkte Iv3-data, aangeleverd door gemeenten bij het CBS. Deze website is gemaakt door BZK."
        )
        st.markdown(
            "Dit is een voorlopige versie, fouten voorbehouden. Vragen of opmerkingen? Stuur een mail naar <postbusiv3@minbzk.nl>."
        )
        
        # Data quality info (collapsible)
        with st.expander("📊 Data kwaliteit informatie"):
            st.json(data_quality)

with saldo_container:
    if not vergelijken:
        cs1, cs2, cs3 = st.columns([2, 4, 2])
        per_inwoner_string = " per inwoner" if selected_stand == "Per inwoner" else ""
        
        with cs2:
            st.header("Begroot en gerealiseerd exploitatiesaldo per jaar")
            
            with st.spinner("Berekenen saldo..."):
                filtered_data = filter_data(data, selected_gemeente, selected_stand)
                chart_data = calculate_saldo(filtered_data)
            
            if not chart_data.empty:
                chart = show_saldo(chart_data, selected_stand)
                if chart:
                    st.markdown(f"Resultaat {selected_gemeente} vóór mutatie reserves{per_inwoner_string}")
                    st.altair_chart(chart, theme="streamlit", use_container_width=True)
                    
                    # Export button for chart data
                    csv_data = export_chart_data(chart_data, f"saldo_{selected_gemeente}.csv")
                    if csv_data:
                        st.download_button(
                            label="📥 Download saldo data (CSV)",
                            data=csv_data,
                            file_name=f"saldo_{selected_gemeente}_{selected_stand}.csv",
                            mime="text/csv"
                        )
                else:
                    st.warning("⚠️ Kon grafiek niet genereren.")
            else:
                st.warning(f"⚠️ Geen saldo data beschikbaar voor {selected_gemeente}")

    else:
        if vergelijking is None:
            st.warning("⚠️ Selecteer een vergelijking optie in de sidebar.")
        else:
            csh1, csh2, csh3 = st.columns([2, 4, 2])

            with csh2:
                st.header("Begroot en gerealiseerd exploitatiesaldo per jaar")

            cs1, cs2, cs3, cs4 = st.columns([1, 3, 3, 1])

            with cs2:
                with st.spinner(f"Berekenen saldo voor {selected_gemeente}..."):
                    filtered_data_1 = filter_data(data, selected_gemeente, selected_stand)
                    chart_data_1 = calculate_saldo(filtered_data_1)
                
                if not chart_data_1.empty:
                    chart = show_saldo(chart_data_1, selected_stand, legend=False)
                    if chart:
                        st.markdown(f"Resultaat {selected_gemeente} vóór mutatie reserves per inwoner")
                        st.altair_chart(chart, theme="streamlit", use_container_width=True)
                    else:
                        st.warning("⚠️ Kon grafiek niet genereren.")
                else:
                    st.warning(f"⚠️ Geen data voor {selected_gemeente}")
                    
            with cs3:
                with st.spinner(f"Berekenen saldo voor {vergelijking}..."):
                    filtered_data_2 = filter_data(data, vergelijking, selected_stand)
                    chart_data_2 = calculate_saldo(filtered_data_2)
                
                if not chart_data_2.empty:
                    chart = show_saldo(chart_data_2, selected_stand, legend=False)
                    if chart:
                        st.markdown(f"Resultaat {vergelijking} vóór mutatie reserves per inwoner")
                        st.altair_chart(chart, theme="streamlit", use_container_width=True)
                    else:
                        st.warning("⚠️ Kon grafiek niet genereren.")
                else:
                    st.warning(f"⚠️ Geen data voor {vergelijking}")

            with csh2:
                if not chart_data_2.empty:
                    legend = show_saldo_legend(chart_data_2)
                    if legend:
                        st.altair_chart(legend, theme="streamlit", use_container_width=True)

if not vergelijken:
    with taakveld_chart_container:
        cvh1, cvh2, cvh3 = st.columns([2, 4, 2])

        with cvh2:
            st.header("Begrote en gerealiseerde standen per taakveld")

            # Dropdown menus for selecting Categorie and Jaar
            baten_lasten_options = ["Baten", "Lasten"]
            filtered_data = filter_data(data, selected_gemeente, selected_stand)
            
            if not filtered_data.empty:
                jaar_options = sorted(filtered_data.Jaar.unique())
                
                selected_baten_lasten = st.selectbox(
                    "Selecteer een categorie",
                    baten_lasten_options,
                    help="Kies tussen Baten (inkomsten) of Lasten (uitgaven)"
                )
                selected_jaar = st.selectbox(
                    "Selecteer een jaar",
                    jaar_options,
                    index=(len(jaar_options) - 1) if jaar_options else 0,
                    help="Kies het jaar dat je wilt analyseren"
                )

                cv1, cv2, cv3 = st.columns([2, 4, 4])

                with cv2:
                    with st.spinner("Berekenen begroting vs jaarrekening..."):
                        # Pull data based on selected options
                        br_data = calculate_begroting_rekening(
                            filtered_data,
                            selected_baten_lasten,
                            selected_jaar,
                        )

                    if not br_data.empty:
                        # Define and create chart
                        chart = show_begroting_rekening(br_data, selected_stand)
                        
                        if chart:
                            st.altair_chart(chart, theme="streamlit", use_container_width=True)
                            
                            # Export button
                            csv_data = export_chart_data(br_data, f"taakveld_{selected_gemeente}_{selected_jaar}.csv")
                            if csv_data:
                                st.download_button(
                                    label="📥 Download taakveld data (CSV)",
                                    data=csv_data,
                                    file_name=f"taakveld_{selected_gemeente}_{selected_baten_lasten}_{selected_jaar}.csv",
                                    mime="text/csv"
                                )
                        else:
                            st.warning("⚠️ Kon grafiek niet genereren.")
                    else:
                        st.warning(f"⚠️ Geen data beschikbaar voor {selected_baten_lasten} in {selected_jaar}")
            else:
                st.warning(f"⚠️ Geen data beschikbaar voor {selected_gemeente}")

with taakveld_table_container:
    cth1, cth2, cth3 = st.columns([2, 4, 2])

    with cth2:
        st.header("Verschil tussen begroting en rekening per taakveld")

        # Dropdown menus for selecting Categorie
        table_option_dict = {
            "Saldo":
            "Saldo (baten min lasten) jaarrekening minus saldo (baten - lasten) primaire begroting in € 1.000",
            "Baten":
            "Baten jaarrekening minus baten primaire begroting in € 1.000",
            "Lasten":
            "Lasten jaarrekening minus lasten primaire begroting in € 1.000",
        }

        toelichting_dict = {
            "Saldo":
            "Positief betekent: het gerealiseerde saldo baten min lasten is hoger dan begroot (meer baten of minder lasten); negatief betekent: het gerealiseerde saldo baten min lasten is lager dan begroot (meer lasten of minder baten)",
            "Baten":
            "Positief betekent: de gerealiseerde baten zijn hoger dan begroot, negatief betekent: de gerealiseerde baten zijn lager dan begroot",
            "Lasten":
            "Positief betekent: de gerealiseerde lasten zijn hoger dan begroot, negatief betekent: de gerealiseerde lasten zijn lager dan begroot",
        }

        selected_table_option = st.selectbox(
            "Selecteer een categorie",
            table_option_dict.keys(),
            help="Kies welke categorie je wilt analyseren: Saldo, Baten of Lasten"
        )

        # Select range of years
        jaar_min_range, jaar_max_range = get_year_range()
        if jaar_min_range is None or jaar_max_range is None:
            st.error("⚠️ Kon jaarbereik niet bepalen. Controleer de data.")
            st.stop()
        
        jaar_min, jaar_max = st.slider(
            label="Selecteer het jaarbereik",
            min_value=jaar_min_range,
            max_value=jaar_max_range,
            value=(max(jaar_min_range, jaar_max_range - 2) if vergelijken else max(jaar_min_range, jaar_max_range - 4),
                   jaar_max_range),
            step=1,
            help="Kies het bereik van jaren dat je wilt analyseren"
        )

    if not vergelijken:
        ct1, ct2, ct3 = st.columns([2, 4, 2])

        with ct2:
            with st.spinner("Berekenen tabellen..."):
                # Pull data based on selected options and style
                filtered_data = filter_data(data, selected_gemeente, selected_stand,
                                            jaar_min, jaar_max)
                tables, table_columns = create_tables(
                    filtered_data, selected_table_option, selected_gemeente)

            if tables:
                # Create table
                st.subheader(table_option_dict.get(selected_table_option))
                st.markdown(toelichting_dict.get(selected_table_option))

                column_config_dict = {
                    i: st.column_config.NumberColumn(i, width="small")
                    for i in table_columns if i != " "
                }
                column_config_dict["Taakveld"] = st.column_config.TextColumn(
                    "Taakveld", width="medium")

                for table_name, table in tables.items():
                    if not table.empty:
                        styled_table = style_table(table, selected_table_option)

                        st.markdown(f"**{table_name}**")
                        st.dataframe(styled_table,
                                     column_config={
                                         "Taakveld":
                                         st.column_config.TextColumn("Taakveld")
                                     },
                                     use_container_width=True,
                                     height=36 * (table.shape[0] + 1))

                # Export button
                col1, col2 = st.columns([3, 1])
                with col2:
                    excel_data = export_table_to_excel(tables, selected_table_option, selected_gemeente)
                    if excel_data.getvalue():
                        st.download_button(
                            label="📥 Download Excel",
                            data=excel_data,
                            file_name=f"begroting_rekening_{selected_gemeente}_{selected_table_option}_{jaar_min}_{jaar_max}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
            else:
                st.warning(f"⚠️ Geen tabellen beschikbaar voor {selected_table_option}")
    else:
        if vergelijking is None:
            st.warning("⚠️ Selecteer een vergelijking optie in de sidebar.")
        else:
            ct1, ct2, ct3 = st.columns([1, 7, 1])

            with ct2:
                with st.spinner("Berekenen vergelijkingstabellen..."):
                    filtered_data = filter_data(data,
                                                selected_gemeente,
                                                selected_stand,
                                                jaarmin=jaar_min,
                                                jaarmax=jaar_max,
                                                vergelijking=vergelijking)
                    tables, table_columns = create_tables(
                        filtered_data, selected_table_option, selected_gemeente)

                if tables:
                    # Create table
                    st.subheader(table_option_dict.get(selected_table_option))
                    st.markdown(toelichting_dict.get(selected_table_option))

                    # Headers for gemeente, vergelijking
                    ctt1, ctt2, ctt3, ctt4 = st.columns([1, 1, 1, 1])
                    with ctt2:
                        st.markdown("**{}**".format(selected_gemeente))
                    with ctt4:
                        st.markdown("**{}**".format(vergelijking))

                    column_config_dict = {
                        i: st.column_config.NumberColumn(i, width="small")
                        for i in table_columns if i != " "
                    }
                    column_config_dict["Taakveld"] = st.column_config.TextColumn(
                        "Taakveld")

                    for table_name, table in tables.items():
                        if not table.empty:
                            styled_table = style_table(table, selected_table_option)

                            st.markdown(f"**{table_name}**")
                            st.dataframe(styled_table,
                                         column_config=column_config_dict,
                                         use_container_width=True,
                                         height=36 * (table.shape[0] + 1))

                    # Export button
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        excel_data = export_table_to_excel(tables, selected_table_option, 
                                                          f"{selected_gemeente}_vs_{vergelijking}")
                        if excel_data.getvalue():
                            st.download_button(
                                label="📥 Download Excel",
                                data=excel_data,
                                file_name=f"begroting_rekening_{selected_gemeente}_vs_{vergelijking}_{selected_table_option}_{jaar_min}_{jaar_max}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                else:
                    st.warning(f"⚠️ Geen tabellen beschikbaar voor vergelijking")

with toelichting_container:
    ctc1, ctc2, ctc3 = st.columns([2, 4, 2])

    with ctc2:

        # Create the DataFrame with multiline cell content
        taakveld_toelichting = pd.DataFrame(
            data={
                "Taakveldgroep": [
                    "Bestuur en burgerzaken", "Bestuur en burgerzaken",
                    "Overig bestuur en onderst.", "Overhead",
                    "Overig bestuur en onderst.", "Belastingen", "Belastingen",
                    "Belastingen", "Belastingen", "Gemeentefonds",
                    "Overig bestuur en onderst.", "Overig bestuur en onderst.",
                    "Veiligheid", "Veiligheid", "Verkeer en vervoer",
                    "Verkeer en vervoer", "Verkeer en vervoer",
                    "Verkeer en vervoer", "Verkeer en vervoer", "Economie",
                    "Economie", "Economie", "Economie", "Onderwijs",
                    "Onderwijs", "Onderwijs", "SCR", "SCR", "SCR", "SCR",
                    "SCR", "SCR", "SCR", "Algemene voorzieningen",
                    "Algemene voorzieningen", "Inkomensregelingen",
                    "Participatie", "Participatie", "Maatwerk Wmo",
                    "Maatwerk Wmo", "Maatwerk Wmo", "Maatwerk Wmo",
                    "Maatwerk Wmo", "Maatwerk Jeugd", "Maatwerk Jeugd",
                    "Maatwerk Jeugd", "Maatwerk Jeugd", "Maatwerk Jeugd",
                    "Maatwerk Jeugd", "Maatwerk Jeugd", "Maatwerk Jeugd",
                    "Maatwerk Jeugd", "Maatwerk Jeugd", "Maatwerk Wmo",
                    "Maatwerk Wmo", "Maatwerk Jeugd", "Maatwerk Jeugd",
                    "Volksgezondheid en milieu", "Volksgezondheid en milieu",
                    "Volksgezondheid en milieu", "Volksgezondheid en milieu",
                    "Volksgezondheid en milieu", "Wonen en bouwen",
                    "Grondexploitatie", "Wonen en bouwen"
                ],
                "Taakveld": [
                    "0.1 Bestuur", "0.2 Burgerzaken",
                    "0.3 Beheer overige gebouwen en gronden", "0.4 Overhead",
                    "0.5 Treasury", "0.61 OZB woningen",
                    "0.62 OZB niet-woningen", "0.63 Parkeerbelasting",
                    "0.64 Belastingen overig",
                    "0.7 Algemene uitkering en overige uitkeringen gemeentefonds",
                    "0.8 Overige baten en lasten",
                    "0.9 Vennootschapsbelasting (Vpb)",
                    "1.1 Crisisbeheersing en brandweer",
                    "1.2 Openbare orde en veiligheid",
                    "2.1 Verkeer en vervoer", "2.2 Parkeren",
                    "2.3 Recreatieve havens",
                    "2.4 Economische havens en waterwegen",
                    "2.5 Openbaar vervoer", "3.1 Economische ontwikkeling",
                    "3.2 Fysieke bedrijfsinfrastructuur",
                    "3.3 Bedrijvenloket en bedrijfsregelingen",
                    "3.4 Economische promotie", "4.1 Openbaar basisonderwijs",
                    "4.2 Onderwijshuisvesting",
                    "4.3 Onderwijsbeleid en leerlingzaken",
                    "5.1 Sportbeleid en activering", "5.2 Sportaccommodaties",
                    "5.3 Cultuurpresentatie, cultuurproductie en cultuurparticipatie",
                    "5.4 Musea", "5.5 Cultureel erfgoed", "5.6 Media",
                    "5.7 Openbaar groen en (openlucht) recreatie",
                    "6.1 Samenkracht en burgerparticipatie",
                    "6.2 Toegang en eerstelijnsvoorzieningen",
                    "6.3 Inkomensregelingen", "6.4 WSW en beschut werk",
                    "6.5 Arbeidsparticipatie",
                    "6.6 Maatwerkvoorzieningen (Wmo)",
                    "6.71a Huishoudelijke hulp (Wmo)",
                    "6.71b Begeleiding (Wmo)", "6.71c Dagbesteding (Wmo)",
                    "6.71d Overige maatwerkarrangementen (Wmo)",
                    "6.72a Jeugdzorg begeleiding",
                    "6.72b Jeugdzorg behandeling",
                    "6.72c Jeugdhulp dagbesteding",
                    "6.72d Jeugdhulp zonder verblijf overig",
                    "6.73a Pleegzorg ", "6.73b Gezinsgericht ",
                    "6.73c Jeugdhulp met verblijf overig",
                    "6.74a Jeugd behandeling GGZ zonder verblijf",
                    "6.74b Jeugdhulp crisis/LTA/GGZ-verblijf",
                    "6.74c Gesloten plaatsing", "6.81a Beschermd wonen (Wmo)",
                    "6.81b Maatschappelijke- en vrouwenopvang (Wmo)",
                    "6.82a Jeugdbescherming", "6.82b Jeugdreclassering",
                    "7.1 Volksgezondheid", "7.2 Riolering", "7.3 Afval",
                    "7.4 Milieubeheer", "7.5 Begraafplaatsen en crematoria",
                    "8.1 Ruimte en leefomgeving",
                    "8.2 Grondexploitatie (niet-bedrijventerreinen)",
                    "8.3 Wonen en bouwen"
                ]
            })

        st.markdown("___Toelichting___")
        st.markdown(
            "De taakveldgroepen zijn gebaseerd op de hoofdtaakvelden van Iv3. In onderstaande tabel staat weergegeven welke taakvelden bij welke taakveldgroep horen"
        )
        st.table(
            taakveld_toelichting.groupby("Taakveldgroep")['Taakveld'].apply(
                lambda x: ", ".join(x)))
