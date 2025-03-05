import csv
import json
import altair as alt
import pandas as pd
import streamlit as st
import matplotlib
import vl_convert as vlc

# Move dictionary definition here
taakvelden_dict = {
    "Gemeentefonds": ("0.7"),
    "Eigen inkomsten": ("0.3", "0.5", "0.6", "0.8", "0.9"),
    "Bestuur" : ("0.1 ", "0.2", "0.4"),
    "Veiligheid": ("1"),
    "Verkeer en vervoer": ("2"),
    "Economie": ("3"),
    "Onderwijs": ("4"),
    "SCR": ("5"),
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

@st.cache_resource
def get_data():
    filepath = "begroting_rekening_per_taakveld.pickle"

    data = pd.read_pickle(filepath)

    return data

def check_jaren(data, gemeenten):
    
    filtered_data = data[(data['Gemeenten'].str.startswith(tuple(gemeenten)))]
    
    jaren = list(filtered_data.Jaar.unique())
    
    if len(jaren) == 0:
        return False
    else:
        return jaren

def check_document(data, gemeenten, selected_jaar):
    filtered_data = data[
        (data['Gemeenten'].str.startswith(tuple(gemeenten)))
        & (data['Jaar'] == selected_jaar)
    ]
    
    documenten = tuple(filtered_data.Document.unique())
    
    return documenten
    
    

@st.cache_data
def filter_data(data, jaar, gemeenten, document, categorie):
    filtered_data = data[(data['Gemeenten'].str.startswith(gemeenten))
                            & (data['Jaar'] == jaar)
                            & (data['Document'] == document)
                            & (data['Categorie'] == categorie)
                    ]
    
    return filtered_data



def prep_hoofdtaakvelden(data):
    
    chart_data = []
    
    gemeenten = data.Gemeenten.unique()
     
    for gemeente in gemeenten:
        for key, value in taakvelden_dict.items():
            filtered_data = data[
                (data['Gemeenten'] == gemeente) &
                (data['Taakveld'].str.startswith(value))
            ]
            
            sum = filtered_data['Waarde'].sum()
            
            categorie = filtered_data['Categorie'].iloc[0]
            
            if categorie == "Saldo":
                sum = -1*sum
            
            if per_inwoner:
                inw = filtered_data['Inwonertal'].iloc[0]
                rec = round(1000*sum/inw, 0)
            else:
                rec = sum
                
            record = [gemeente, key, rec]
            chart_data.append(record)
    
    chart_df = pd.DataFrame(chart_data, columns=["Gemeente", "Hoofdtaakveld", "Waarde"])
    
    return chart_df

def prep_subtaakvelden(data, htv):
    chart_data = []
    
    tv_tuple = subtaakvelden[htv]
    
    taakvelden = data[
        (data['Taakveld'].str.startswith(tv_tuple))
    ].Taakveld.unique()
    
    gemeenten = data.Gemeenten.unique()
    
    for taakveld in taakvelden:
        for gemeente in gemeenten:
            filtered_data = data[
                (data['Gemeenten'] == gemeente) &
                (data['Taakveld'] == taakveld)
            ]
            
            sum = filtered_data['Waarde'].sum()
            
            categorie = filtered_data['Categorie'].iloc[0]
            
            if categorie == "Saldo":
                sum = -1*sum
            
            if per_inwoner:
                inw = filtered_data['Inwonertal'].iloc[0]
                rec = round(1000*sum/inw, 0)
            else:
                rec = sum
                
            record = [gemeente, taakveld, rec]
            chart_data.append(record)
    
    chart_df = pd.DataFrame(chart_data, columns=["Gemeente", "Taakveld", "Waarde"])
    
    return chart_df

# Wide screen
st.set_page_config(layout="wide")

# Sidebar
with st.sidebar:
    st.header("Selecteer hier de analyse")

    gemeente_options = list(get_data().Gemeenten.unique())
    groep_options = [x for x in gemeente_options if "inwoners" in x or "stedelijk" in x] + \
        ["Drenthe", "Groningen", "Fryslân", "Overijssel", "Gelderland", "Flevoland", 
         "Utrecht", "Noord-Holland", "Zuid-Holland", "Noord-Brabant", "Zeeland",
         "Limburg"]
    
    selected_gemeente = st.selectbox("Selecteer een gemeente",
                                     gemeente_options,
                                     key=0)
    
    vergelijk_gemeente = st.selectbox("Selecteer een gemeente om mee te vergelijken",
                                     gemeente_options,
                                     index=None,
                                     placeholder="Selecteer een optie",
                                     key=1)
    
    vergelijk_groep = st.selectbox("Selecteer een provincie, grootte- of stedelijkheidsklasse om mee te vergelijken",
                                     groep_options,
                                     index=None,
                                     placeholder="Selecteer een optie",
                                     key=2)

    selected_gemeenten = [selected_gemeente]
    
    if vergelijk_gemeente is not None:
        selected_gemeenten.append(vergelijk_gemeente)
    if vergelijk_groep is not None:
        selected_gemeenten.append(vergelijk_groep)
    
    selected_gemeenten = tuple(selected_gemeenten)

# Body
referral_container = st.container()
header_container = st.container()
select_data = st.container()
hoofd_tv = st.container()
sub_tv = st.container()

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
            "Met deze tool kunnen gemeenten worden vergeleken op hun baten, lasten en saldi op hoofd- en individuele taakvelden. Met het selectiemenu links kan worden vergeleken met andere gemeenten, en het totaal van gemeenten in een provincie, grootte- of stedelijkheidsklasse."
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
        
        jaar_options = check_jaren(get_data(), selected_gemeenten[0])
        if jaar_options:
            selected_jaar = st.slider("Welk jaar vergelijken?", min(jaar_options), max(jaar_options), max(jaar_options))
        
        c1, c2, c3 = st.columns([1,1,1])
        
        with c1:
            document_options = check_document(get_data(), selected_gemeenten, selected_jaar)
            selected_document = st.selectbox("Begroting of jaarrekening?", document_options)
        
        with c2:
            categorie_options = ("Baten", "Lasten", "Saldo")
            selected_categorie = st.selectbox("Baten, lasten of saldo?", categorie_options)
        
        with c3:
            som_options = ("Per inwoner", "Totaal")
            selected_som = st.selectbox("Som per inwoner of totaal?", som_options)
            
            per_inwoner = True if selected_som == "Per inwoner" else False
            scale = "€" if per_inwoner else "€ 1.000"
    
    gemeente_data = filter_data(get_data(), selected_jaar, selected_gemeenten, selected_document, selected_categorie)
    
    
with hoofd_tv:
    
    ch1, ch2, ch3 = st.columns([3, 6, 3])
    
    with ch2:
        som_header = "per inwoner" if per_inwoner else ""
        hoofd_header = f'{selected_categorie} op hoofdtaakvelden in {selected_jaar} {som_header} ({selected_document.lower()})'
        
        st.subheader(hoofd_header)
    
    c1, c2, c3 = st.columns([2, 6, 2])
    
    with c2:
        
        hoofdtaakvelden = prep_hoofdtaakvelden(gemeente_data)
        
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
        
with sub_tv:
    
    ch1, ch2, ch3 = st.columns([2, 3, 2])
    
    with ch2:
        
        htv = st.selectbox("Selecteer een hoofdtaakveld om op taakveldniveau te vergelijken", subtaakvelden)
        
    cj1, cj2, cj3 = st.columns([3, 6, 3])
    
    with cj2:
        som_header = "per inwoner" if per_inwoner else ""
        sub_header = f'{selected_categorie} {htv} in {selected_jaar} {som_header} ({selected_document.lower()})'
        
        st.subheader(sub_header)
    
    c1, c2, c3 = st.columns([2, 5, 2])
    
    with c2:
        subtaakvelden = prep_subtaakvelden(gemeente_data, htv)
        
        chart = alt.Chart(subtaakvelden).mark_bar().encode(
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
        