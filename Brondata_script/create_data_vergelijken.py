import pandas as pd
import os
from functools import reduce
from tabulate import tabulate

datamap = "C:/Dashboard/werk/iv3data/%s.csv"

t = 'TaakveldBalanspost'
c = 'Categorie'
k = 'k_2ePlaatsing_2'
g = 'Gemeenten'

def pivotIv3(df):
  pv = df.pivot(index = [g, t], columns=c, values =[k])

  pv.columns = [col[-1] for col in pv.columns]
  batencolumns = [col for col in pv.columns if col.startswith("B")]
  lastencolumns = [col for col in pv.columns if col.startswith("L")]

  pv['Baten'] = pv[batencolumns].sum(axis=1)
  pv['Lasten'] = pv[lastencolumns].sum(axis=1)
  pv['Saldo'] = pv.apply(lambda row: row.Baten - row.Lasten, axis=1)

  df2 = pv.reset_index()

  return df2

def calc_mult(m0, mi):
  m0v = m0[k].sum()
  m0m = m0.loc[m0[g].str.startswith(mi)]
  m0mv = m0m[k].sum()
  multi = 1/(1-m0mv/m0v)

  return multi

def herindeling(jaar, df):

  herindelers = {
    'Meierijstad'       : [2017, {'Schijndel': 1, 'Sint-Oedenrode': 1, 'Veghel': 1}],
    'Leeuwarden'        : [2018, {'Leeuwarden': 1, 'Leeuwarderadeel': 1, 'Littenseradiel': 0.32}],
    'Midden-Groningen'  : [2018, {'Hoogezand-Sappemeer': 1, 'Menterwolde': 1, 'Slochteren': 1}],
    'Waadhoeke'         : [2018, {'Franekeradeel': 1, 'het Bildt': 1, 'Menameradiel': 1, 'Littenseradiel': 0.17}],
    'Westerwolde'       : [2018, {'Bellingwedde': 1, 'Vlagtwedde': 1}],
    'Zevenaar'          : [2018, {'Rijnwaarden': 1, 'Zevenaar': 1}],
    'Súdwest-Fryslân'   : [2018, {'Bolsward': 1, 'Nijefurd': 1, 'Sneek': 1, 'Wonseradeel': 1, 'Wûnseradiel': 1, 'Wymbritseradiel' : 1, 'Wymbritseradeel': 1, 'Littenseradiel': 0.51, 'Súdwest-Fryslân': 1}],
    'Groningen (gemeente)' : [2019, {'Groningen (gemeente)': 1, 'Haren': 1, 'Ten Boer': 1}],
    'Het Hogeland'      : [2019, {'Bedum': 1, 'De Marne': 1, 'Eemsmond': 1, 'Winsum': 0.884}],
    'Westerkwartier'    : [2019, {'Grootegast': 1, 'Leek': 1, 'Marum': 1, 'Zuidhorn': 1, 'Winsum': 0.1157}],
    'Altena'            : [2019, {'Aalburg': 1, 'Werkendam': 1, 'Woudrichem': 1}],
    'Beekdaelen'        : [2019, {'Nuth': 1, 'Onderbanken': 1, 'Schinnen': 1}],
    'Haarlemmermeer'    : [2019, {'Haarlemmerliede en Spaarnwoude': 1, 'Haarlemmermeer': 1}],
    'Hoeksche Waard'    : [2019, {'Binnenmaas': 1, 'Cromstrijen': 1, 'Korendijk': 1, 'Oud-Beijerland': 1, 'Strijen': 1, "'s-Gravendeel": 1}],
    'Noardeast-Fryslân' : [2019, {'Dongeradeel': 1, 'Ferwerderadiel': 1, 'Kollumerland en Nieuwkruisland': 1}],
    'Molenlanden'       : [2019, {'Graafstroom': 1, 'Liesveld': 1, 'Nieuw-Lekkerland': 1, 'Molenwaard' : 1, 'Giessenlanden': 1}],
    'Noordwijk'         : [2019, {'Noordwijk': 1, 'Noordwijkerhout': 1}],
    'Vijfheerenlanden'  : [2019, {'Leerdam': 1, 'Zederik': 1, 'Vianen': 1}],
    'West Betuwe'       : [2019, {'Geldermalsen': 1, 'Lingewaal': 1, 'Neerijnen': 1}],
    'Eemsdelta'         : [2021, {'Appingedam': 1, 'Delfzijl': 1, 'Loppersum': 1}],
    'Boxtel'            : [2021, {'Boxtel' : 1, 'Haaren': 0.25}],
    'Tilburg'           : [2021, {'Tilburg' : 1, 'Haaren': 0.25}],
    'Vught'             : [2021, {'Vught' : 1, 'Haaren': 0.25}],
    'Oisterwijk'        : [2021, {'Oisterwijk' : 1, 'Haaren': 0.25}],
    'Dijk en Waard'     : [2022, {'Heerhugowaard': 1, 'Langedijk': 1}],
    'Land van Cuijk'    : [2022, {'Boxmeer': 1, 'Cuijk': 1, 'Grave': 1, 'Mill en Sint Hubert': 1, 'Sint Anthonis': 1}],
    'Purmerend'         : [2022, {'Beemster': 1, 'Purmerend': 1}],
    'Amsterdam'         : [2022, {'Amsterdam': 1, 'Weesp': 1}],
    'Maashorst'         : [2022, {'Landerd': 1, 'Uden': 1}],
    'Voorne aan Zee'    : [2022, {"Brielle": 1, "Hellevoetsluis": 1, "Westvoorne": 1}], #2023
  }

  for nieuwe_gem, inf in herindelers.items():

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

taakveldgroepen = { 
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

doc = "000"

docdict = {
  "Begroting" : "000",
  "Jaarrekening" : "005",
}

pd.set_option('display.max_columns', None)

DF = []
for jaar in range(2017,2026):
  
  bejr = []
  for naam, doc in docdict.items():
    
    if jaar > 2023 and naam == "Jaarrekening": # Regionale indeling 2025 is 2024
      pass
    else:
    
      dataframes = []
      document = str(jaar) + doc
      df = pd.read_csv(datamap % document)
      pv = pivotIv3(df)
      taakvelden = pv.TaakveldBalanspost.unique()
      taakvelden = [i for i in taakvelden if not i.startswith(("A", "P"))]
    
      for tv in taakvelden:
        tvalues = pv.loc[pv[t].str.startswith(tv)].groupby(g)['Baten'].sum().rename('Waarde')
        tvalueframe = tvalues.to_frame()
        tvalueframe.insert(0, 'Categorie', 'Baten')
        tvalueframe.insert(0, 'Taakveld', tv)
        tvalueframe.insert(0, 'Document', naam)
        tvalueframe.insert(0, 'Jaar', jaar)
        dataframes.append(tvalueframe)

      for tv in taakvelden:
        tvalues = pv.loc[pv[t].str.startswith(tv)].groupby(g)['Lasten'].sum().rename('Waarde')
        tvalueframe = tvalues.to_frame()
        tvalueframe.insert(0, 'Categorie', 'Lasten')
        tvalueframe.insert(0, 'Taakveld', tv)
        tvalueframe.insert(0, 'Document', naam)
        tvalueframe.insert(0, 'Jaar', jaar)
        dataframes.append(tvalueframe)

      for tv in taakvelden:
        tvalues = pv.loc[pv[t].str.startswith(tv)].groupby(g)['Saldo'].sum().rename('Waarde')
        tvalueframe = tvalues.to_frame()
        tvalueframe.insert(0, 'Categorie', 'Saldo')
        tvalueframe.insert(0, 'Taakveld', tv)
        tvalueframe.insert(0, 'Document', naam)
        tvalueframe.insert(0, 'Jaar', jaar)
        dataframes.append(tvalueframe)
    
      combined_df = pd.concat(dataframes)
    
      bejr.append(combined_df)

  outputdf = pd.concat(bejr)
  
  #import gemeenteklassen
  klassenlocatie = f"C:/Dashboard/werk/gemdata/per_jaar/{jaar}.csv"
  kldf = pd.read_csv(klassenlocatie, sep=";", decimal=",")
  
  merged_df = pd.merge(outputdf, kldf, on="Gemeenten")

  DF.append(merged_df)

DF = pd.concat(DF)

# Group by alle gemeenten
all_groups = DF.groupby(['Jaar', 'Document', 'Categorie', 'Taakveld']).agg({
    'Waarde': 'sum',
    'Inwonertal': 'sum'
}).reset_index()

# Add 'Nederland' as Gemeenten column
all_groups['Gemeenten'] = 'Nederland'
DF = pd.concat([DF, all_groups], ignore_index=True)

# Group by provincie first
provincie_groups = DF.groupby(['Provincie', 'Jaar', 'Document', 'Categorie', 'Taakveld']).agg({
    'Waarde': 'sum',
    'Inwonertal': 'sum'
}).reset_index()

# Add the provincie rows to the main dataframe
provincie_groups = provincie_groups.rename(columns={'Provincie': 'Gemeenten'})
DF = pd.concat([DF, provincie_groups], ignore_index=True)

# Group by gemeentegrootte
grootteklasse_groups = DF.groupby(['Gemeentegrootte', 'Jaar', 'Document', 'Categorie', 'Taakveld']).agg({
    'Waarde': 'sum',
    'Inwonertal': 'sum'
}).reset_index()

# Add the gemeentegrootte rows to the main dataframe
grootteklasse_groups = grootteklasse_groups.rename(columns={'Gemeentegrootte': 'Gemeenten'})
DF = pd.concat([DF, grootteklasse_groups], ignore_index=True)

# Group by stedelijkheid
stedelijkheid_groups = DF.groupby(['Stedelijkheid', 'Jaar', 'Document', 'Categorie', 'Taakveld']).agg({
    'Waarde': 'sum',
    'Inwonertal': 'sum'
}).reset_index()

# Add the stedelijkheid rows to the main dataframe
stedelijkheid_groups = stedelijkheid_groups.rename(columns={'Stedelijkheid': 'Gemeenten'})
DF = pd.concat([DF, stedelijkheid_groups], ignore_index=True)

DF = DF.drop(columns=['Provincie', 'Gemeentegrootte', 'Stedelijkheid'])
DF = DF.dropna(subset=['Gemeenten'])


print(DF)

outputname = "begroting_rekening_per_taakveld.pickle"
#DF.to_csv(outputname, sep=",", decimal=".", float_format='%.4f')
DF.to_pickle(outputname)