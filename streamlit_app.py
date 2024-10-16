import csv

import altair as alt
import pandas as pd
import streamlit as st
import matplotlib

# Globals
JAAR_MINIMUM = 2017
JAAR_MAXIMUM = 2023


# Data import
@st.cache_resource
def get_data():
    filepath = "begroting_rekening.pickle"  # may replace with csv

    #data = pd.read_csv(filepath,
    #                   dtype={
    #                       'Gemeenten': 'category',
    #                       'Jaar': 'category',
    #                       'Stand': 'category',
    #                       'Taakveld': 'category',
    #                       'Document': 'category',
    #                       'Waarde': 'int32'
    #                   })

    data = pd.read_pickle(filepath)

    return data


# Provincie and Grootteklasse data
def get_classes():
    filepath = "gemeenteklassen.csv"

    with open(filepath, mode='r') as infile:
        reader = csv.reader(infile)
        rows = list(reader)

    provincie_dict = {row[0]: row[1] for row in rows}
    grootteklasse_dict = {row[0]: row[2] for row in rows}

    return provincie_dict, grootteklasse_dict


# Filter
@st.cache_data
def filter_data(data,
                gemeente,
                stand,
                jaarmin=JAAR_MINIMUM,
                jaarmax=JAAR_MAXIMUM,
                vergelijking=None):

    # Tuple of jaren (saved as category)
    jaar_range = tuple([str(i) for i in range(jaarmin, jaarmax + 1)])

    # Select by gemeente and Totaal/Per inwoner, no Provincie or Grootteklasse
    if not vergelijking:
        filtered_data = data[(data['Stand'] == stand)
                             & (data['Gemeenten'] == gemeente)
                             & (data['Jaar'].str.startswith(jaar_range))]

    # Select by gemeente and stand and vergelijking (Gemeente, Provincie, Grootteklasse)
    else:
        filtered_data = data[(data['Stand'] == stand)
                             & (data['Jaar'].str.startswith(jaar_range)
                                & ((data['Gemeenten'] == gemeente)
                                   | (data['Gemeenten'] == vergelijking)))]

    # Replace Overig bestuur en ondersteuning, too long
    filtered_data['Taakveld'] = filtered_data['Taakveld'].replace(
        'Overig bestuur en ondersteuning', 'Overig bestuur en onderst.')

    return filtered_data


# Saldo calculation
@st.cache_data
def calculate_saldo(data):
    saldo = data.loc[(data['Categorie'] == 'Saldo')].groupby(
        ['Jaar', 'Document'], observed=False)['Waarde'].sum().reset_index()

    saldo = saldo[(saldo['Waarde'] != 0)]

    return saldo


# Saldo graph
def show_saldo(saldo, legend=True):
    if legend:
        chart = alt.Chart(saldo).mark_line().encode(
            x=alt.X('Jaar:O'),
            y=alt.Y('Waarde:Q', title='€ 1.000'),
            color='Document:N',
        ).configure_legend(title=None)
    else:
        chart = alt.Chart(saldo).mark_line().encode(x=alt.X('Jaar:O'),
                                                    y=alt.Y('Waarde:Q',
                                                            title='€ 1.000'),
                                                    color=alt.Color(
                                                        'Document:N',
                                                        legend=None))

    return chart


# Saldo legend
def show_saldo_legend(saldo):
    chart = alt.Chart(saldo, height=25).mark_line().encode(
        color=alt.Color('Document:N')).configure_view(
            clip=False).configure_legend(title=None, orient="top")

    return chart


# Calculate baten/lasten begroting vs. jaarrekening
@st.cache_data
def calculate_begroting_rekening(data, baten_lasten, jaar):
    br_data = data[(data['Categorie'] == baten_lasten)
                   & (data['Jaar'] == str(jaar))]

    return br_data


def show_begroting_rekening(br_data):
    br_chart = alt.Chart(br_data).mark_bar().encode(
        y=alt.Y('Document:N',
                title='',
                axis=alt.Axis(labels=False, ticks=False)
                ),  # Group by Document (Begroting and Jaarrekening) vertically
        x=alt.X('Waarde:Q', title='€ 1.000'),
        color='Document:N',
        row=alt.Row(
            'Taakveld:N',
            sort=alt.EncodingSortField(field="Waarde", order='descending'),
            spacing=5,
            header=alt.Header(
                labelAngle=0,
                labelAlign='left',
                title=None,
                labelFontSize=15,
                labelPadding=15  # Adjust padding to fix spacing
            ))).configure_axis(labelFontSize=15).configure_header(
                title=None  # Remove the header title
            ).configure_legend(title=None)

    return br_chart


# Calculate baten/lasten/saldo begroting vs. jaarrekening
@st.cache_data
def create_tables(data, categorie, gemeente):

    # Filter data
    df = data.loc[data['Categorie'] == categorie]

    # Check Gemeenten in dataframe
    gemeenten = df['Gemeenten'].astype(str).unique().tolist()
    jaren = df['Jaar'].astype(str).unique().tolist()

    if len(gemeenten) == 1:

        # Calculate table
        table = calculate_difference(df)
    elif len(gemeenten) == 2:

        vergelijking = gemeenten[1] if gemeenten[0] == gemeente else gemeenten[
            0]
        table_headers = [gemeente, vergelijking]
        table_suffixes = [
            "                                                            {}".
            format(gemeente),
            "                                                            {}".
            format(vergelijking)
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

    inkomsten_table = table.loc[[
        "Gemeentefonds",
        "Belastingen",
        "Overig bestuur en onderst.",
        "Grondexploitatie",
        "Economie",
    ]]

    klassiek_domein_table = table.loc[[
        "Bestuur en burgerzaken",
        "Overhead",
        "Veiligheid",
        "Verkeer en vervoer",
        "Onderwijs",
        "SCR",
        "Volksgezondheid en milieu",
        "Wonen en bouwen",
    ]]

    sociaal_domein_table = table.loc[[
        "Algemene voorzieningen",
        "Inkomensregelingen",
        "Participatie",
        "Maatwerk Wmo",
        "Maatwerk Jeugd",
    ]]

    tables = {
        "Inkomsten": inkomsten_table,
        "Klassiek domein": klassiek_domein_table,
        "Sociaal domein": sociaal_domein_table
    }

    return tables, table.columns


def calculate_difference(df):
    # Remove unused columns
    df = df.drop(columns=['Gemeenten', 'Categorie'])

    # Separate into jaarrekening and begroting
    jaarrekening = df.loc[df['Document'] == 'Jaarrekening']
    begroting = df.loc[df['Document'] == 'Begroting']

    # Merge and calculate difference
    merged_df = pd.merge(jaarrekening,
                         begroting,
                         on=['Jaar', 'Taakveld'],
                         suffixes=('_jr', '_bg'))
    merged_df['Verschil'] = merged_df['Waarde_jr'] - merged_df['Waarde_bg']
    merged_df['Verschil'] = merged_df['Verschil'].astype(int)

    # Remove Jaren with empty values
    merged_df = merged_df[((merged_df['Verschil'] != merged_df['Waarde_bg']) &
                           (merged_df['Waarde_bg'] != 0)) | 
                          ((merged_df['Verschil'] != -merged_df['Waarde_jr']) &
                           (merged_df['Waarde_jr'] != 0)) |
                          ((merged_df['Waarde_jr'] == 0) &
                           (merged_df['Waarde_bg'] == 0))]
                            

    # Pivot table and change column headers
    pv = merged_df.pivot(index='Taakveld', columns='Jaar', values=['Verschil'])
    pv.columns = pv.columns.droplevel(0)

    return pv


def style_table(table, categorie):
    table = table.style.format(
        thousands=',',
    )
    
    gm = calculate_gradient_map(table, categorie)
    styled_pv = table.style.background_gradient(cmap="RdBu",
                                                gmap=gm,
                                                axis=None)

    return styled_pv


def calculate_gradient_map(x, categorie):
    x1 = x.map(lambda i: 0 if i == "" else i)

    x_min = abs(x1.values.min())
    x_max = abs(x1.values.max())

    if abs(x_min) > x_max:
        # If minimum is higher than maximum, multiply by fraction max/min
        x2 = x1.map(lambda i: i * (x_min / x_max) / x_min
                    if i > 0 else i / x_min)
    else:
        # If maximum is higher: multiply by fraction min/max
        x2 = x1.map(lambda i: i * (x_max / x_min) / x_max
                    if i < 0 else i / x_max)

    # Take root to raise lower values
    rf = 0.4  # Root factor
    x3 = x2.map(lambda i: i**rf if i >= 0 else -(abs(i)**rf))

    if categorie == "Lasten":
        x3 = x3.map(lambda i: -i)  # Reverse gradient map for lasten

    return x3


# Wide screen
st.set_page_config(layout="wide")

# Sidebar
with st.sidebar:
    st.header("Selecteer hier de analyse")

    # Toggle for comparing yes/no
    vergelijken = st.toggle("Vergelijken")

    gemeente_options = get_data().Gemeenten.unique()
    selected_gemeente = st.selectbox("Selecteer een gemeente",
                                     gemeente_options,
                                     key=0)

    alleen_per_inwoner = [
        "Groningen", "Friesland", "Drenthe", "Overijssel", "Gelderland",
        "Flevoland", "Utrecht", "Noord-Brabant", "Limburg", "Noord-Holland",
        "Zuid-Holland", "Zeeland", "100.000 tot 150.000 inwoners",
        "10.000 tot 20.000 inwoners", "150.000 tot 250.000 inwoners",
        "20.000 tot 50.000 inwoners", "Noord-Brabant",
        "250.000 inwoners of meer", "50.000 tot 100.000 inwoners",
        "5.000 tot 10.000 inwoners", "minder dan 5.000 inwoners"
    ]

    # If vergelijken: no options for stand, must be Per inwoner
    if not vergelijken and selected_gemeente not in alleen_per_inwoner:
        stand_options = get_data().Stand.unique()
        selected_stand = st.selectbox("Selecteer totaal of per inwoner",
                                      stand_options,
                                      disabled=False)
    else:
        stand_options = ["Per inwoner"]
        selected_stand = st.selectbox("Selecteer totaal of per inwoner",
                                      stand_options,
                                      disabled=True)

    # If vergelijken, with what Provincie, Grootteklasse or Gemeente
    if vergelijken:

        vergelijking_options = [
            'Provincie', 'Grootteklasse', 'Nederland', 'Andere gemeente'
        ]
        selected_vergelijking = st.selectbox("Selecteer vergelijking",
                                             vergelijking_options)

        if selected_vergelijking == "Andere gemeente":
            gemeente_vergelijking = st.selectbox("Selecteer een gemeente",
                                                 gemeente_options,
                                                 key=1)

        provincie_dict, grootteklasse_dict = get_classes()

        if selected_vergelijking == "Nederland":
            vergelijking = "Nederland"
        elif selected_vergelijking == 'Provincie':
            vergelijking = provincie_dict.get(selected_gemeente)
        elif selected_vergelijking == 'Grootteklasse':
            vergelijking = grootteklasse_dict.get(selected_gemeente)
        else:
            vergelijking = gemeente_vergelijking

# Body
header_container = st.container()
saldo_container = st.container()
taakveld_chart_container = st.container()
taakveld_table_container = st.container()
toelichting_container = st.container()

with header_container:
    ch1, ch2, ch3 = st.columns([2, 4, 2])

    with ch2:
        st.title("📊 Analyse verschil tussen begroting en rekening")
        st.markdown(
            "Deze tool laat voor elke gemeente zien waardoor de realisatie afwijkt van de begroting. Er kan worden vergeleken met het gemiddelde voor de grootteklasse of provincie, met andere gemeenten of met heel Nederland."
        )
        st.markdown(
            "Onderstaande berekeningen zijn gemaakt op basis van onbewerkte Iv3-data, aangeleverd door gemeenten bij het CBS. Deze website is gemaakt door BZK."
        )
        st.markdown(
            "Dit is een voorlopige versie, fouten voorbehouden. Vragen of opmerkingen? Stuur een mail naar <postbusiv3@minbzk.nl>."
        )

with saldo_container:

    if not vergelijken:
        cs1, cs2, cs3 = st.columns([2, 4, 2])

        with cs2:
            st.header("Begroot en gerealiseerd exploitatiesaldo per jaar")

            chart_data = calculate_saldo(
                filter_data(get_data(), selected_gemeente, selected_stand))
            chart = show_saldo(chart_data)

            st.markdown(f"Resultaat {selected_gemeente} vóór mutatie reserves")
            st.altair_chart(chart, theme="streamlit", use_container_width=True)

    else:
        csh1, csh2, csh3 = st.columns([2, 4, 2])

        with csh2:
            st.header("Begroot en gerealiseerd exploitatiesaldo per jaar")

        cs1, cs2, cs3, cs4 = st.columns([1, 3, 3, 1])

        with cs2:
            chart_data = calculate_saldo(
                filter_data(get_data(), selected_gemeente, selected_stand))
            chart = show_saldo(chart_data, legend=False)

            st.markdown(f"Resultaat {selected_gemeente} vóór mutatie reserves")
            st.altair_chart(chart, theme="streamlit", use_container_width=True)
        with cs3:
            chart_data = calculate_saldo(
                filter_data(get_data(), vergelijking, selected_stand))
            chart = show_saldo(chart_data, legend=False)

            st.markdown(f"Resultaat {vergelijking} vóór mutatie reserves")
            st.altair_chart(chart, theme="streamlit", use_container_width=True)

        with csh2:
            legend = show_saldo_legend(chart_data)
            st.altair_chart(legend,
                            theme="streamlit",
                            use_container_width=True)

if not vergelijken:
    with taakveld_chart_container:

        cvh1, cvh2, cvh3 = st.columns([2, 4, 2])

        with cvh2:
            st.header("Begrote en gerealiseerde standen per taakveld")

            # Dropdown menus for selecting Categorie and Jaar
            baten_lasten_options = ["Baten", "Lasten"]
            jaar_options = filter_data(get_data(), selected_gemeente,
                                       selected_stand).Jaar.unique()

            selected_baten_lasten = st.selectbox("Selecteer een categorie",
                                                 baten_lasten_options)
            selected_jaar = st.selectbox("Selecteer een jaar",
                                         jaar_options,
                                         index=(len(jaar_options) - 1))

        cv1, cv2, cv3 = st.columns([2, 4, 4])

        with cv2:

            # Pull data based on selected options
            br_data = calculate_begroting_rekening(
                filter_data(get_data(), selected_gemeente, selected_stand),
                selected_baten_lasten,
                selected_jaar,
            )

            # Define and create chart
            chart = show_begroting_rekening(br_data)

            st.altair_chart(chart, theme="streamlit", use_container_width=True)

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

        selected_table_option = st.selectbox("Selecteer een categorie",
                                             table_option_dict.keys())

        # Select range of years
        jaar_min, jaar_max = st.slider(
            label="Selecteer het jaarbereik",
            min_value=JAAR_MINIMUM,
            max_value=JAAR_MAXIMUM,
            value=(JAAR_MAXIMUM - 2 if vergelijken else JAAR_MAXIMUM - 4,
                   JAAR_MAXIMUM),
            step=1)

    if not vergelijken:
        ct1, ct2, ct3 = st.columns([2, 4, 2])

        with ct2:
            # Pull data based on selected options and style
            tables, table_columns = create_tables(
                filter_data(get_data(), selected_gemeente, selected_stand,
                            jaar_min, jaar_max), selected_table_option,
                selected_gemeente)

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
                styled_table = style_table(table, selected_table_option)

                st.markdown(table_name)
                st.dataframe(styled_table,
                             column_config={
                                 "Taakveld":
                                 st.column_config.TextColumn("Taakveld")
                             },
                             use_container_width=True,
                             height=36 * (table.shape[0] + 1))
    else:
        ct1, ct2, ct3 = st.columns([1, 7, 1])

        with ct2:

            tables, table_columns = create_tables(
                filter_data(get_data(),
                            selected_gemeente,
                            selected_stand,
                            jaarmin=jaar_min,
                            jaarmax=jaar_max,
                            vergelijking=vergelijking), selected_table_option,
                selected_gemeente)

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
                styled_table = style_table(table, selected_table_option)

                st.markdown(table_name)
                st.dataframe(styled_table,
                             column_config=column_config_dict,
                             use_container_width=True,
                             height=36 * (table.shape[0] + 1))

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
