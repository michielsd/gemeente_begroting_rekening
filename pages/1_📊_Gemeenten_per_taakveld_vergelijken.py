import csv
import json
import altair as alt
import pandas as pd
import streamlit as st
import matplotlib
import vl_convert as vlc
from io import BytesIO
from pyxlsb import open_workbook as open_xlsb

# Move dictionary definition here
taakvelden_dict = {
    "Gemeentefonds": ("0.7"),
    "Eigen inkomsten": ("0.3", "0.5", "0.6", "0.8", "0.9"),
    "Bestuur" : ("0.1 ", "0.2", "0.4"),
    "Veiligheid": ("1"),
    "Verkeer en vervoer": ("2"),
    "Economie": ("3"),
    "Onderwijs": ("4"),
    "Sport, cultuur": ("5"),
    "Sociaal domein": ("6"),
    "Volksgezondheid": ("7"),
    "Wonen en bouwen": ("8"),
}

subtaakvelden = {
    "Gemeentefonds": ("0.7"),
    "Eigen inkomsten": ("0.3", "0.5", "0.6", "0.8", "0.9"),
    "Bestuur" : ("0.1 ", "0.2", "0.4"),
    "Veiligheid": ("1"),
    "Verkeer en vervoer": ("2"),
    "Economie": ("3"),
    "Onderwijs": ("4"),
    "Sport, cultuur en recreatie (SCR)": ("5"),
    "Sociaal domein - Algemene voorzieningen": ("6.1", "6.2"),
    "Sociaal domein - Inkomen en participatie": ("6.3", "6.4", "6.5"),
    "Sociaal domein - Wmo": ("6.6", "6.71", "6.791", "6.81", "6.91"),
    "Sociaal domein - Jeugd": ("6.72", "6.73", "6.74", "6.75", "6.76", "6.792", "6.82", "6.92"),
    "Volksgezondheid": ("7"),
    "Wonen en bouwen": ("8"),
}

# Constants
EURO_TO_THOUSAND_FACTOR = 1000  # Convert from €1000 to € per inhabitant

def calculate_waarde(filtered_data, per_inwoner=False):
    """Calculate the final value for a gemeente-taakveld combination.
    
    Args:
        filtered_data: DataFrame slice for specific gemeente and taakveld
        per_inwoner: If True, return value per inhabitant, else total
        
    Returns:
        Calculated value (float)
    """
    if len(filtered_data) == 0:
        return 0
    
    sum_value = filtered_data['Waarde'].sum()
    categorie = filtered_data['Categorie'].iloc[0]
    
    # Saldo is defined as netto lasten (lasten - baten), so negate
    if categorie == "Saldo":
        sum_value = -1 * sum_value
    
    if per_inwoner:
        inwonertal = filtered_data['Inwonertal'].iloc[0]
        if inwonertal > 0:
            return round(EURO_TO_THOUSAND_FACTOR * sum_value / inwonertal, 0)
        else:
            return 0
    else:
        return sum_value

@st.cache_resource
def get_data():
    """Load budget/reckoning data with error handling.
    
    Returns:
        DataFrame with gemeente data, or empty DataFrame on error
    """
    filepath = "begroting_rekening_per_taakveld.pickle"
    
    try:
        data = pd.read_pickle(filepath)
        
        if data.empty:
            st.error("⚠️ Data file is empty. Please check the data source.")
            return pd.DataFrame()
        
        # Validate required columns exist
        required_columns = ['Gemeenten', 'Jaar', 'Document', 'Categorie', 
                          'Taakveld', 'Waarde', 'Inwonertal']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            st.error(f"⚠️ Missing required columns in data: {missing_columns}")
            return pd.DataFrame()
        
        return data
        
    except FileNotFoundError:
        st.error(f"❌ Data file '{filepath}' not found. Please ensure the file exists.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        st.exception(e)  # Show full traceback in debug mode
        return pd.DataFrame()

def check_jaren(data, gemeenten):
    """Check available years for given gemeenten.
    
    Args:
        data: Source DataFrame
        gemeenten: Single gemeente name (str) or tuple of gemeente names
        
    Returns:
        List of available years, or False if no data
    """
    if data.empty:
        return False
    
    # Normalize to tuple
    if isinstance(gemeenten, str):
        gemeenten_pattern = (gemeenten,)
    else:
        gemeenten_pattern = gemeenten
    
    try:
        filtered_data = data[data['Gemeenten'].str.startswith(gemeenten_pattern)]
        jaren = list(filtered_data.Jaar.unique())
        
        return jaren if len(jaren) > 0 else False
    except Exception as e:
        st.warning(f"⚠️ Error checking years: {str(e)}")
        return False

def check_document(data, gemeenten, selected_jaar):
    """Check available documents for given gemeenten and year.
    
    Args:
        data: Source DataFrame
        gemeenten: Single gemeente name (str) or tuple of gemeente names
        selected_jaar: Selected year (int)
        
    Returns:
        Tuple of available document types
    """
    if data.empty:
        return tuple()
    
    # Normalize to tuple
    if isinstance(gemeenten, str):
        gemeenten_pattern = (gemeenten,)
    else:
        gemeenten_pattern = gemeenten
    
    try:
        filtered_data = data[
            (data['Gemeenten'].str.startswith(gemeenten_pattern)) &
            (data['Jaar'] == selected_jaar)
        ]
        
        return tuple(filtered_data.Document.unique())
    except Exception as e:
        st.warning(f"⚠️ Error checking documents: {str(e)}")
        return tuple()
    
    

@st.cache_data
def filter_data(data, jaar, gemeenten, document, categorie):
    """Filter data by year, gemeenten, document, and category.
    
    Args:
        data: Source DataFrame
        jaar: Year (int)
        gemeenten: Single gemeente name (str) or tuple of gemeente names
        document: Document type (str)
        categorie: Category (str)
        
    Returns:
        Filtered DataFrame
    """
    if data.empty:
        return pd.DataFrame()
    
    # Normalize gemeenten to tuple for consistent handling
    if isinstance(gemeenten, str):
        gemeenten_pattern = (gemeenten,)
    elif isinstance(gemeenten, tuple):
        gemeenten_pattern = gemeenten
    else:
        st.warning(f"⚠️ Unexpected type for gemeenten: {type(gemeenten)}")
        return pd.DataFrame()
    
    try:
        filtered_data = data[
            (data['Gemeenten'].str.startswith(gemeenten_pattern)) &
            (data['Jaar'] == jaar) &
            (data['Document'] == document) &
            (data['Categorie'] == categorie)
        ]
        
        return filtered_data
        
    except KeyError as e:
        st.warning(f"⚠️ Column not found in data: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"⚠️ Error filtering data: {str(e)}")
        return pd.DataFrame()



def prep_hoofdtaakvelden(data, per_inwoner=False):
    """Prepare data for hoofdtaakvelden chart.
    
    Args:
        data: Filtered DataFrame with gemeente data
        per_inwoner: If True, calculate values per inhabitant, else use totals
        
    Returns:
        DataFrame with columns: Gemeente, Hoofdtaakveld, Waarde
    """
    chart_data = []
    gemeenten = data.Gemeenten.unique()
    
    for gemeente in gemeenten:
        for key, value in taakvelden_dict.items():
            filtered_data = data[
                (data['Gemeenten'] == gemeente) &
                (data['Taakveld'].str.startswith(value))
            ]
            
            waarde = calculate_waarde(filtered_data, per_inwoner)
            chart_data.append([gemeente, key, waarde])
    
    return pd.DataFrame(chart_data, columns=["Gemeente", "Hoofdtaakveld", "Waarde"])

def prep_subtaakvelden(data, htv=None, per_inwoner=False):
    """Prepare data for subtaakvelden chart.
    
    Args:
        data: Filtered DataFrame with gemeente data
        htv: Optional hoofdtaakveld to filter by
        per_inwoner: If True, calculate values per inhabitant, else use totals
        
    Returns:
        DataFrame with columns: Gemeente, Taakveld, Waarde
    """
    chart_data = []
    
    if htv:
        tv_tuple = subtaakvelden[htv]
        taakvelden = data[
            (data['Taakveld'].str.startswith(tv_tuple))
        ].Taakveld.unique()
    else:
        taakvelden = data.Taakveld.unique()
    
    gemeenten = data.Gemeenten.unique()
    
    for taakveld in taakvelden:
        for gemeente in gemeenten:
            filtered_data = data[
                (data['Gemeenten'] == gemeente) &
                (data['Taakveld'] == taakveld)
            ]
            
            waarde = calculate_waarde(filtered_data, per_inwoner)
            chart_data.append([gemeente, taakveld, waarde])
    
    return pd.DataFrame(chart_data, columns=["Gemeente", "Taakveld", "Waarde"])

def to_excel(df, cat):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name=cat)
        workbook = writer.book
        worksheet = writer.sheets[cat]
        
        # Set column widths
        worksheet.set_column('A:A', 20)  # Index column
        worksheet.set_column('B:Z', 20)  # Data columns
        
        # Create European number format
        num_format = workbook.add_format({'num_format': '#,##0'})
        
        # Apply format to all data cells
        for col in range(1, len(df.columns) + 2):  # +2 because of index column
            worksheet.set_column(col, col, None, num_format)
            
    processed_data = output.getvalue()
    return processed_data

# Wide screen
st.set_page_config(layout="wide")

# Load data once at the beginning
with st.spinner("📊 Data wordt geladen..."):
    data = get_data()

# Early exit if no data
if data.empty:
    st.error("❌ Geen data beschikbaar. De applicatie kan niet worden gestart.")
    st.stop()

# Sidebar
with st.sidebar:
    st.header("Selecteer hier de analyse")

    gemeente_options = list(data.Gemeenten.unique())
    groep_options = ["Nederland"] + [x for x in gemeente_options if "inwoners" in x or "stedelijk" in x] + \
        ["Drenthe", "Groningen", "Fryslân", "Overijssel", "Gelderland", "Flevoland", 
         "Utrecht", "Noord-Holland", "Zuid-Holland", "Noord-Brabant", "Zeeland",
         "Limburg"]
    
    selected_gemeente = st.selectbox("Selecteer een gemeente",
                                     gemeente_options,
                                     key=0)
    
    vergelijk_gemeente1 = st.selectbox("Selecteer een gemeente om mee te vergelijken",
                                     gemeente_options,
                                     index=None,
                                     placeholder="Selecteer een optie",
                                     key=1)
    vergelijk_gemeente2 = st.selectbox("Selecteer een gemeente om mee te vergelijken",
                                     gemeente_options,
                                     index=None,
                                     placeholder="Selecteer een optie",
                                     key=2)
    vergelijk_gemeente3 = st.selectbox("Selecteer een gemeente om mee te vergelijken",
                                     gemeente_options,
                                     index=None,
                                     placeholder="Selecteer een optie",
                                     key=3)
    
    vergelijk_groep = st.selectbox("Selecteer een provincie, grootte- of stedelijkheidsklasse of alle gemeenten om mee te vergelijken",
                                     groep_options,
                                     index=None,
                                     placeholder="Selecteer een optie",
                                     key=4)

    selected_gemeenten = [selected_gemeente]
    
    if vergelijk_gemeente1 is not None:
        selected_gemeenten.append(vergelijk_gemeente1)
    if vergelijk_gemeente2 is not None:
        selected_gemeenten.append(vergelijk_gemeente2)
    if vergelijk_gemeente3 is not None:
        selected_gemeenten.append(vergelijk_gemeente3)
    if vergelijk_groep is not None:
        selected_gemeenten.append(vergelijk_groep)
    
    selected_gemeenten = tuple(selected_gemeenten)

# Body
referral_container = st.container()
header_container = st.container()
select_data = st.container()
hoofd_tv = st.container()
sub_tv = st.container()
table_tv = st.container()

with referral_container:
    ch1, ch2, ch3 = st.columns([1,3,1])
    
    with ch2:
        st.markdown("*Linksboven in de sidebar👈 kan worden genavigeerd naar 📈 Analyse verschil tussen begroting en rekening*")
    
    st.markdown("---")

with header_container:
    ch1, ch2, ch3 = st.columns([2, 4, 2])

    with ch2:
        st.title("📊 Vergelijk taakvelden tussen gemeenten")
        st.markdown(
            "Met deze tool kunnen gemeenten worden vergeleken op hun baten, lasten en saldi op hoofd- en individuele taakvelden. Met het selectiemenu links kan worden vergeleken met andere gemeenten, alle gemeenten samen of het totaal van gemeenten in een provincie, grootte- of stedelijkheidsklasse. Met de knop onderaan kunnen de gegevens worden gedownload."
        )
        st.markdown(
            "Een saldo is gedefinieerd als netto lasten (lasten min baten). Onderstaande berekeningen zijn gemaakt op basis van onbewerkte Iv3-data, aangeleverd door gemeenten bij het CBS. Deze website is gemaakt door BZK."
        )
        
        st.markdown(
            "Dit is een voorlopige versie, fouten voorbehouden. Vragen of opmerkingen? Stuur een mail naar <postbusiv3@minbzk.nl>."
        )


with select_data:
    
    htv_order = tuple(key for key, value in taakvelden_dict.items())
    
    ch1, ch2, ch3 = st.columns([2, 3, 2])
    
    with ch2:
        
        jaar_options = check_jaren(data, selected_gemeenten[0])
        selected_jaar = None
        if jaar_options:
            selected_jaar = st.slider("Welk jaar vergelijken?", min(jaar_options), max(jaar_options), max(jaar_options))
        else:
            st.warning(f"Geen data beschikbaar voor {selected_gemeenten[0]}")
        
        c1, c2, c3 = st.columns([1,1,1])
        
        selected_document = None
        if selected_jaar is not None:
            with c1:
                document_options = check_document(data, selected_gemeenten, selected_jaar)
                if len(document_options) > 0:
                    selected_document = st.selectbox("Begroting of jaarrekening?", document_options)
                else:
                    st.warning("Geen documenten beschikbaar voor deze selectie")
        else:
            with c1:
                st.info("Selecteer eerst een jaar")
        
        with c2:
            categorie_options = ("Baten", "Lasten", "Saldo")
            selected_categorie = st.selectbox("Baten, lasten of saldo?", categorie_options)
        
        with c3:
            som_options = ("Per inwoner", "Totaal")
            selected_som = st.selectbox("Som per inwoner of totaal?", som_options)
            
            per_inwoner = True if selected_som == "Per inwoner" else False
            scale = "€" if per_inwoner else "€ 1.000"
    
    if selected_jaar is not None and selected_document is not None:
        gemeente_data = filter_data(data, selected_jaar, selected_gemeenten, selected_document, selected_categorie)
    else:
        gemeente_data = pd.DataFrame()
    
    # Initialize variables for use in later sections
    htv = None
    subtaakvelden_df = None
    hoofdtaakvelden = None
    
with hoofd_tv:
    
    if selected_jaar is not None and selected_document is not None:
        if len(gemeente_data) > 0:
            ch1, ch2, ch3 = st.columns([3, 6, 3])
            
            with ch2:
                som_header = " per inwoner" if per_inwoner else ""
                hoofd_header = f'{selected_categorie} op hoofdtaakvelden in {selected_jaar}{som_header} ({selected_document.lower()})'
                
                st.subheader(hoofd_header)
            
            c1, c2, c3 = st.columns([2, 6, 2])
            
            with c2:
                with st.spinner("📊 Grafiek wordt gegenereerd..."):
                    hoofdtaakvelden = prep_hoofdtaakvelden(gemeente_data, per_inwoner=per_inwoner)
                    
                    chart = alt.Chart(hoofdtaakvelden).mark_bar().encode(
                        x=alt.X('Hoofdtaakveld:N', title='Hoofdtaakveld', sort=htv_order),
                        y=alt.Y('Waarde:Q', title=scale),
                        color=alt.Color('Gemeente:N', sort=selected_gemeenten),
                        xOffset=alt.XOffset('Gemeente:N', sort=selected_gemeenten)
                    ).properties(
                        height=450,
                        usermeta={
                            "embedOptions": {
                                "formatLocale": vlc.get_format_locale("nl-NL"),
                            }
                        }
                    )
                    
                    st.altair_chart(chart, use_container_width=True)
        else:
            st.warning(f"Geen data beschikbaar voor {selected_jaar} en {selected_document.lower()}")
    else:
        st.info("Selecteer een gemeente, jaar en document om de grafiek te zien.")
        
with sub_tv:
    
    if selected_jaar is not None and selected_document is not None:
        if len(gemeente_data) > 0:
            ch1, ch2, ch3 = st.columns([2, 3, 2])
            
            with ch2:
                
                htv = st.selectbox("Selecteer een hoofdtaakveld om op taakveldniveau te vergelijken", subtaakvelden)
                
            cj1, cj2, cj3 = st.columns([3, 6, 3])
            
            with cj2:
                som_header = " per inwoner" if per_inwoner else ""
                sub_header = f'{selected_categorie} {htv.lower()} in {selected_jaar} {som_header} ({selected_document.lower()})'
                
                st.subheader(sub_header)
            
            c1, c2, c3 = st.columns([2, 5, 2])
            
            with c2:
                if htv is not None:
                    with st.spinner("📊 Grafiek wordt gegenereerd..."):
                        subtaakvelden_df = prep_subtaakvelden(gemeente_data, htv, per_inwoner=per_inwoner)
                        
                        chart = alt.Chart(subtaakvelden_df).mark_bar().encode(
                            y=alt.Y('Taakveld:N', title='', axis=alt.Axis(labelLimit=200)),
                            x=alt.X('Waarde:Q', title=scale, stack=None),
                            color=alt.Color('Gemeente:N', sort=selected_gemeenten),
                            yOffset=alt.YOffset('Gemeente:N', sort=selected_gemeenten)
                        ).properties(
                            usermeta={
                                "embedOptions": {
                                    "formatLocale": vlc.get_format_locale("nl-NL"),
                                }
                            }
                        )
                        
                        st.altair_chart(chart, use_container_width=True)
        else:
            st.warning(f"Geen data beschikbaar voor {selected_jaar} en {selected_document.lower()}")

with table_tv:
    
    if selected_jaar is not None and selected_document is not None:
        if len(gemeente_data) > 0:
            ch1, ch2, ch3 = st.columns([2, 4, 2])
            
            with ch2:
                st.header("Gegevens downloaden")
                
                st.markdown(
                    "Met de knop hieronder kunnen de gegevens in bovenstaande grafieken worden gedownload.")
                st.markdown(
                    "De opties in onderstaande menu zijn gebaseerd op de selectie in het menu hierboven. Selecteer een ander jaar, baten, lasten of saldi, begroting of jaarrekening of ander hoofdtaakveld om de tabellen van die gegevens te downloaden. Er is ook de optie om de baten, lasten of saldi van alle taakvelden in een jaar te downloaden."
                )
            
            c1, c2, c3 = st.columns([2, 3, 2])
            
            with c2:
                
                ht_option = f"{selected_categorie} hoofdtaakvelden {selected_document.lower()} {selected_jaar}"
                
                # Only include subtaakvelden options if htv is selected
                table_options = [ht_option]
                if htv is not None:
                    st_option = f"{selected_categorie} {htv.lower()} {selected_document.lower()} {selected_jaar}"
                    table_options.append(st_option)
                at_option = f"{selected_categorie} alle taakvelden {selected_document.lower()} {selected_jaar}"
                table_options.append(at_option)
            
                ttv = st.selectbox("Selecteer een tabel om te downloaden", 
                                   table_options, index=None, placeholder="Kies een optie"
                )
            
                st.markdown("")
                httable = sttable = None
                
                if ttv == ht_option and hoofdtaakvelden is not None:
                    # Pivot the table to have hoofdtaakveld as index and gemeenten as columns
                    httable = hoofdtaakvelden.pivot(index='Hoofdtaakveld', columns='Gemeente', values='Waarde')
                    
                    output_table = httable.style.format(
                                                        thousands='.',
                                                        precision=0
                                                )
                                
                    sheet_title = f'{selected_categorie}{som_header}'
                    df_xlsx = to_excel(output_table, sheet_title)
                    st.download_button(label=f'📥 Download {ht_option}',
                                        data=df_xlsx ,
                                        file_name= f'{ht_option}.xlsx')
                    
                if ttv == st_option and subtaakvelden_df is not None:
                    # Pivot the table to have hoofdtaakveld as index and gemeenten as columns
                    sttable = subtaakvelden_df.pivot(index='Taakveld', columns='Gemeente', values='Waarde')

                    output_table = sttable.style.format(
                                                        thousands='.',
                                                        precision=0
                                                )
                                
                    sheet_title = f'{selected_categorie}{som_header}'
                    df_xlsx = to_excel(output_table, sheet_title)
                    st.download_button(label=f'📥 Download {st_option}',
                                        data=df_xlsx ,
                                        file_name= f'{st_option.replace("-", "_")}.xlsx')
                    
                if ttv == at_option:
                    alle_taakvelden = prep_subtaakvelden(gemeente_data, None, per_inwoner=per_inwoner)
                    attable = alle_taakvelden.pivot(index='Taakveld', columns='Gemeente', values='Waarde')
                    
                    output_table = attable.style.format(
                                                        thousands='.',
                                                        precision=0
                                                )
                                
                    sheet_title = f'{selected_categorie}{som_header}'
                    df_xlsx = to_excel(output_table, sheet_title)
                    st.download_button(label=f'📥 Download {at_option}',
                                        data=df_xlsx ,
                                        file_name= f'{at_option.replace("-", "_")}.xlsx')
        else:
            st.warning(f"Geen data beschikbaar voor {selected_jaar} en {selected_document.lower()}")
            
            