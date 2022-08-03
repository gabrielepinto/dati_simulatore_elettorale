

## THINGS TO DO
### fare update del value degli slider tra di loro
### crea slider dinamicamente
### fare un bel grafico
import dash
import dash_core_components as dcc


import dash_html_components as html
## this is for the style
import dash_bootstrap_components as dbc
###
import folium
import pandas as pd
import numpy as np
import geopandas as gpd
import random   
import plotly.express as px
import plotly.graph_objects as go
import os
import dash_table
from dash.exceptions import PreventUpdate




#instantiate Dash
external_stylesheets =[dbc.themes.UNITED]
app = dash.Dash(__name__,external_stylesheets=external_stylesheets)
app.title="simulatorelezioni"
server = app.server



folder_head="dati_app/"





def aumento_voti_territorio(data,increase=0.35,
                            partito="LEGA",
                            unit_name="COLLEGIOUNINOMINALE",
                            unit='Piemonte 1 - U01'):
    '''
    data= sono i dati elettorali
    increase = la percentuale a cui si vuole portare quel partito
    partito = nome partito
    unit_name = a quale livello vuoi cambiare percentuale
    unit = nome del colleggio o area
    '''
    ## calcolo percentuale
    perc_attuale=data.loc[(data["LISTA"]==partito)&(data[unit_name]==unit),"VOTI_LISTA"].sum()/data.loc[(data[unit_name]==unit),"VOTI_LISTA"].sum()

    ### individua l'/le unità da modificare
    unit_to_edit=data.loc[(data["LISTA"]==partito)&(data[unit_name]==unit),"VOTI_LISTA"]
    nuovo_valore=data.loc[unit_to_edit.index,"VOTI_LISTA"]=unit_to_edit*(increase/perc_attuale)
    diff_da_riallocare=nuovo_valore-unit_to_edit
    # ### individua quelle da aggiustare
    units_to_adjust=data.loc[(~data.index.isin(unit_to_edit.index))&(data["LISTA"]==partito)].index
    pesi=data.loc[units_to_adjust,"VOTANTI"]/data.loc[units_to_adjust,"VOTANTI"].sum()
    data.loc[units_to_adjust,"VOTI_LISTA"]=data.loc[units_to_adjust,"VOTI_LISTA"]-pesi*diff_da_riallocare.values[0]

    return data


def aumento_voti_partito(data,increase=0.25,
                            partito="FORZA ITALIA"):
    '''
    data= sono i dati elettorali
    increase = la percentuale a cui si vuole portare quel partito
    partito = nome partito
    '''
    ## percentuale attuale
    perc_attuale=data.loc[(data["LISTA"]==partito),"VOTI_LISTA"].sum()/data["VOTI_LISTA"].sum()
    ### individua l'/le unità da modificare
    unit_to_edit=data.loc[(data["LISTA"]==partito),"VOTI_LISTA"]
    nuovo_valore=data.loc[unit_to_edit.index,"VOTI_LISTA"]=unit_to_edit*(increase/perc_attuale)
    diff_da_riallocare=(nuovo_valore-unit_to_edit).sum()
    ### individua quelle da aggiustare
    units_to_adjust=data.loc[data["LISTA"]!=partito].index
    pesi=data.loc[units_to_adjust,"VOTI_LISTA"]/data.loc[units_to_adjust,"VOTI_LISTA"].sum()
    data.loc[units_to_adjust,"VOTI_LISTA"]=data.loc[units_to_adjust,"VOTI_LISTA"]-pesi*diff_da_riallocare
    
    return data




def sporziona_hare(vot,seat):
    quota=vot.sum()/seat
    apportion=vot/quota
    apportion=apportion.astype("int")
    ### partiti ai quali aggiungere dei voti
    seggi_rimanenti=seat-sum(apportion) 
    index_to_add=(-(vot-apportion*quota)).argsort()[:seggi_rimanenti]
    apportion[index_to_add]+=1
    return apportion



def compute_uninom(camera,diz):
    '''
    camera: sono i dati della camera in formato long
    diz: dizionario della coalizione
    '''
    ### calcola i voti per ogni lista in ogni collegio
    uninom=camera.groupby(["COLLEGIOUNINOMINALE","LISTA"],as_index=False)["VOTI_LISTA"].sum()
    ## aggiungi coalizione
    uninom["COALIZIONE"]=uninom["LISTA"].replace(diz)
    ## raggruppa e calcola risultato per coalizione
    uninom=uninom.groupby(["COLLEGIOUNINOMINALE","COALIZIONE"],as_index=False)["VOTI_LISTA"].sum().pivot(index="COLLEGIOUNINOMINALE",columns="COALIZIONE",values="VOTI_LISTA").fillna(0)


    ## partiti
    partiti=uninom.columns
    #### prendi il primo partito/coalizione per ogni collegio
    seggi=uninom[partiti].apply(lambda x:(-x).argsort()[0],axis=1).value_counts()
    ### assegna seggio
    uninom_camera=pd.DataFrame({"partiti":pd.Series(partiti).loc[seggi.index],"seggi":seggi.values})


    ### questo è per visualizzare breakdown da partito mentre uninom_camera è quello che li visualizza per coalizione
    ### gli uninominali di coalizione vengono assegnati ad ogni partito in base alla loro percentuale all'interno della coalizione
    uninom_camera_per_partito=pd.DataFrame()
    for i,row in uninom_camera.iterrows():
        percentuali_within_list=camera.loc[camera["LISTA"].isin(row.partiti.split("*"))].groupby("LISTA",as_index=False)["VOTI_LISTA"].sum()
        ##
        perc_partiti=pd.merge(pd.DataFrame({"LISTA":row.partiti.split("*")}),percentuali_within_list).set_index("LISTA").transpose()
        seggi=sporziona_hare(perc_partiti.values[0],row.seggi)


        uninom_camera_per_partito=uninom_camera_per_partito.append(pd.DataFrame({"partiti":perc_partiti.columns,"seggi":seggi}))
    uninom_camera_per_partito=uninom_camera_per_partito.sort_values("seggi",ascending=False).reset_index(drop=True)
    uninom_camera_per_partito=uninom_camera_per_partito.loc[uninom_camera_per_partito["seggi"]!=0,:].reset_index(drop=True)
    return(uninom_camera_per_partito.sort_values("seggi",ascending=False).reset_index(drop=True))
    


def compute_plurinom_camera(camera,seggi_plurinominale=245):
    
    plurinom=pd.DataFrame(camera.groupby("LISTA")["VOTI_LISTA"].sum()).transpose()
    partiti=[x for x in plurinom.columns if x not in (["seggi","colleggio"])]

    voti_totali= plurinom[partiti].sum().sum()
    voti_partiti= plurinom[partiti].apply(lambda x:x.sum())
    percentuali_partiti = voti_partiti/voti_totali
    partiti_non_superano_soglia=percentuali_partiti.loc[percentuali_partiti<=0.03].index
    ###SVP
    controllo_plurinom=camera.groupby(["CIRCOSCRIZIONE","LISTA"],as_index=False)["VOTI_LISTA"].sum()
    controllo_plurinom["TOTALE_VOTI_CIRCOSCRIZIONE"]=controllo_plurinom.groupby("CIRCOSCRIZIONE")["VOTI_LISTA"].transform("sum")
    controllo_plurinom["PERC_CIRCOSCRIZIONE"]=controllo_plurinom["VOTI_LISTA"]/controllo_plurinom["TOTALE_VOTI_CIRCOSCRIZIONE"]
    partiti_20_percento=controllo_plurinom.loc[controllo_plurinom["PERC_CIRCOSCRIZIONE"]>=0.2,"LISTA"].unique()
    ### aggiungi quelli che non hanno il 3 per cento ma hanno il 20
    partiti_non_superano_soglia=[x for x in partiti_non_superano_soglia if x not in  partiti_20_percento]

    ## droppa

    plurinom.drop(partiti_non_superano_soglia,axis=1,inplace=True)
    partiti=[x for x in partiti if x not in partiti_non_superano_soglia]


    seggi=sporziona_hare(plurinom[partiti].sum().values,
                  seggi_plurinominale)
    plurinom_camera=pd.DataFrame({"partiti":partiti,"seggi":seggi})
    return(plurinom_camera.sort_values("seggi",ascending=False).reset_index(drop=True))


    

def cp(partito,mean=0):
    perc_attuale=camera.loc[camera["LISTA"]==partito,"VOTI_LISTA"].sum()/camera["VOTI_LISTA"].sum()
    return np.round(perc_attuale*mean,6)

def compute_gauge_data(result,diz):
    gauge_data=pd.DataFrame(result.groupby("partiti")["seggi"].sum()).reset_index(drop=False)
    gauge_data["color"]=gauge_data.partiti.apply(lambda x:diz_colori[x])
    gauge_data["order"]=gauge_data.partiti.apply(lambda x:diz_order[x])
    gauge_data["coalizione"]=gauge_data["partiti"].replace(diz)

    list_gauge=[]
    z=0
    for i,row in gauge_data.sort_values("order",ascending=True).iterrows():
        list_gauge.append({"range":[z,z+row.seggi],"color":row.color})
        z+=row.seggi
    return gauge_data,list_gauge

def create_fig_gauge(maggioranza,lista_gauge,maggioranza_richiesta=201,totale_posti=400,nome_graf="Camera"):
    fig_gauge = go.Figure(go.Indicator(
    domain = {'x': [0, 1], 'y': [0, 1]},
    value = maggioranza,
    mode = "gauge+number+delta",
    title = {'text': nome_graf},
    delta = {'reference': +totale_posti/2 },
    gauge = {'bar': {'color': "lightgrey","thickness":0.2},
        'axis': {'range': [None, totale_posti]},
            'steps' : lista_gauge,
            ### questo + il valore della barragrigia
            'threshold' : {'line': {'color': "red", 'width': 4}, 'thickness': 0.3, 'value': maggioranza_richiesta}}))
    return fig_gauge

def compute_plurinom_senato(camera):
    plurinom=pd.DataFrame(camera.groupby("LISTA")["VOTI_LISTA"].sum()).transpose()
    partiti=[x for x in plurinom.columns if x not in (["seggi","colleggio"])]
    voti_totali= plurinom[partiti].sum().sum()
    voti_partiti= plurinom[partiti].apply(lambda x:x.sum())
    percentuali_partiti = voti_partiti/voti_totali
    partiti_non_superano_soglia=percentuali_partiti.loc[percentuali_partiti<=0.03].index
    ###SVP
    controllo_plurinom=camera.groupby(["CODICE_REGIONE","LISTA"],as_index=False)["VOTI_LISTA"].sum()
    controllo_plurinom["TOTALE_VOTI_REGIONE"]=controllo_plurinom.groupby("CODICE_REGIONE")["VOTI_LISTA"].transform("sum")
    controllo_plurinom["PERC_REGIONE"]=controllo_plurinom["VOTI_LISTA"]/controllo_plurinom["TOTALE_VOTI_REGIONE"]
    partiti_20_percento=controllo_plurinom.loc[controllo_plurinom["PERC_REGIONE"]>=0.2,"LISTA"].unique()
    ### aggiungi quelli che non hanno il 3 per cento ma hanno il 20
    partiti_non_superano_soglia=[x for x in partiti_non_superano_soglia if x not in  partiti_20_percento]

    ## droppa
    plurinom.drop(partiti_non_superano_soglia,axis=1,inplace=True)
    partiti=[x for x in partiti if x not in partiti_non_superano_soglia]
    ### assegna seggi per ogni regione...
    plurinom_camera=pd.DataFrame()
    for i,row in seggi_senato.iterrows():
        plurinom_una_regione=pd.DataFrame(camera[camera["CODICE_REGIONE"]==row.CODICE_REGIONE].groupby("LISTA")["VOTI_LISTA"].sum()).transpose()    
        seggi=sporziona_hare(plurinom_una_regione[partiti].sum().values,
                      row.seggi)
        plurinom_camera=plurinom_camera.append(pd.DataFrame({"partiti":partiti,"seggi":seggi}))
    plurinom_camera=plurinom_camera.groupby("partiti",as_index=False)["seggi"].sum()
    return(plurinom_camera.sort_values("seggi",ascending=False).reset_index(drop=True))
    
def tabella_uninom(camera,diz):
    uninom=camera.groupby(["COLLEGIOUNINOMINALE","LISTA"],as_index=False)["VOTI_LISTA"].sum()
    ## aggiungi coalizione
    uninom["COALIZIONE"]=uninom["LISTA"].replace(diz)
    ## raggruppa e calcola risultato per coalizione
    uninom=uninom.groupby(["COLLEGIOUNINOMINALE","COALIZIONE"],as_index=False)["VOTI_LISTA"].sum().pivot(index="COLLEGIOUNINOMINALE",columns="COALIZIONE",values="VOTI_LISTA").fillna(0)
    partiti=uninom.columns
    uninom=(uninom.div(uninom.sum(axis=1), axis=0)*100).round(1)
    uninom["MARGINE"]=uninom.apply(lambda x:np.round(x.sort_values()[-1]-x.sort_values()[-2],2),axis=1)
    uninom["VINCITORE"]=uninom[partiti].apply(lambda x:(-x).argsort()[0],axis=1).replace(dict(zip([x for x in range(0,uninom.columns.shape[0])],uninom.columns)))
    return uninom


### QUI I DATI

camera=pd.read_csv(folder_head+"camera_bilanciato.csv",encoding="windows-1252",sep=";")
senato=pd.read_csv(folder_head+"senato_bilanciato.csv",encoding="windows-1252",sep=";")
seggi_senato=pd.read_excel(folder_head+"seggi_senato.xlsx")


geo_camera=gpd.read_file(folder_head+"COLLEGI_ELETTORALI_NUOVI/camera")
geo_camera.rename({"COLLEGIOUN":"COLLEGIOUNINOMINALE"},axis=1,inplace=True)
geo_camera.to_crs("EPSG:4326",inplace=True)

geo_senato=gpd.read_file(folder_head+"COLLEGI_ELETTORALI_NUOVI/senato")
geo_senato.rename({"COLLEGIOUN":"COLLEGIOUNINOMINALE"},axis=1,inplace=True)
geo_senato.to_crs("EPSG:4326",inplace=True)





dr=pd.read_excel(folder_head+"stime_partiti.xlsx",sheet_name="COALIZIONI")
lista_coalizione=dr.columns[1:]
diz_coalizione=dict(zip(dr["LISTA"],dr[lista_coalizione[0]]))

descrizione_coalizione=list(pd.read_excel(folder_head+"stime_partiti.xlsx",sheet_name="DESCRIZIONE_COALIZIONI")["descrizione"])


df_color=pd.read_excel(folder_head+"stime_partiti.xlsx",sheet_name="COLORI")
diz_colori=dict(zip(df_color["LISTA"],df_color["COLOR"]))
diz_order=dict(zip(df_color["LISTA"],df_color["left-right"]))
## fai il grafico
#result=compute_uninom(camera=camera)    
#fig=px.bar(result,x="partiti",y="seggi",color="partiti",width=1500, height=600)
result=compute_uninom(camera=camera,diz=diz_coalizione)
result["Seggio"]="uninominale"
result2=compute_plurinom_camera(camera=camera)
result2["Seggio"]="plurinominale"
result=result.append(result2)
result=result.append(pd.DataFrame({"seggi":[8],"Seggio":"plurinominale","partiti":"ESTERO"}))
result.sort_values(["seggi","Seggio"],ascending=False,inplace=True)

### calcola risultati per il  senato
result_senato=compute_uninom(camera=senato,diz=diz_coalizione)
result_senato["Seggio"]="uninominale"
result2_senato=compute_plurinom_senato(camera=senato)
result2_senato["Seggio"]="plurinominale"
result_senato=result_senato.append(result2_senato)
result_senato=result_senato.append(pd.DataFrame({"seggi":[4],"Seggio":"plurinominale","partiti":"ESTERO"}))
result_senato.sort_values(["seggi","Seggio"],ascending=False,inplace=True)

### vedi figura
fig=px.bar(result,title="camera",x="partiti",y="seggi",color="partiti",color_discrete_map=diz_colori,facet_col="Seggio",width=700, height=500)
fig_senato=px.bar(result_senato,title="senato",x="partiti",y="seggi",color="partiti",color_discrete_map=diz_colori,facet_col="Seggio",width=700, height=500)
### GAUGE
gauge_data,lista_gauge=compute_gauge_data(result=result,diz=diz_coalizione)
maggioranza=gauge_data.groupby("coalizione")["seggi"].sum().loc["FDI*LEGA*FI"]
fig_gauge=create_fig_gauge(maggioranza=maggioranza,lista_gauge=lista_gauge,maggioranza_richiesta=201,totale_posti=400)

gauge_data_senato,lista_gauge_senato=compute_gauge_data(result=result_senato,diz=diz_coalizione)
maggioranza=gauge_data_senato.groupby("coalizione")["seggi"].sum().loc["FDI*LEGA*FI"]
fig_gauge_senato=create_fig_gauge(maggioranza=maggioranza,lista_gauge=lista_gauge_senato,maggioranza_richiesta=101,totale_posti=200,nome_graf="senato")

## modifica
result["parlamento"]="camera"
result_senato["parlamento"]="senato"
all_camere=result.append(result_senato)
all_camere=all_camere.groupby(["parlamento","partiti"],as_index=False)["seggi"].sum()

all_camere["order"]=all_camere.partiti.apply(lambda x:diz_order[x])

fig_bar=px.bar(all_camere.sort_values("order"), x="parlamento", y="seggi", color_discrete_map=diz_colori,color="partiti", text="partiti")




homepage=[html.H1("Simulatore Elezioni Rosatellum  ",style={"color":"white","background-color":"deeppink"} ),
    html.H4("Puoi scegliere lo scenario di coalizione dal menu a tendina e cambiare le percentuali utilizzando gli slider. L'aggiornamento di tabelle, mappe e grafici può prendere fino a 30 secondi"
    ,style={"color":"black","font-size":12})]


homepage.append(dcc.Loading(
            id="loading-1",
            type="default",
            children=html.Div(id="loading-output-1"),fullscreen=True))



#homepage.append(html.H1("Scegli scenario di coalizione:",style={"font-size":12}))

homepage.append(dcc.Dropdown(id='lista_coalizione',style={'width': '600px'},
multi=False,options=[{"label":y,"value":x} for x,y in zip(lista_coalizione,descrizione_coalizione)],value=lista_coalizione[0]))



homepage.append(html.H4(""))



parties=list(camera.groupby("LISTA")["VOTI_LISTA"].sum().sort_values(ascending=False).index)
# homepage.append(dcc.Graph(id='grafico-gauge',figure=fig,style={'width': '50%', 'display': 'inline-block',"width":500, "height":300}))
# homepage.append(dcc.Graph(id='grafico-gauge-senato',figure=fig_senato,style={'width': '50%', 'display': 'inline-block',"width":500, "height":300}))

homepage.append(html.H4("La barra grigia rappresenta maggioranza di CDX, il numero mostra il totale dei parlamentari e lo scarto rispetto alla maggioranza assoluta",style={"font-size":12}))




homepage.append(dcc.Graph(id='grafico-gauge',style={'width': '25%', 'display': 'inline-block'}))
homepage.append(dcc.Graph(id='grafico-gauge-senato',style={'width': '25%', 'display': 'inline-block'}))
homepage.append(dcc.Graph(id='grafico-barra-parlamento',style={'width': '50%', 'display': 'inline-block'}))


for x in range(0,5):
    homepage.append(html.H1(""))



for party in parties:
    ## add title
    homepage.append(html.H4("% {0}".format(party),style={"font-size":12,"color":diz_colori[party],"font-weight":"bold"}))
    ### add slider
    homepage.append(html.Div([dcc.Slider(min=0.000001,max=0.35,step=0.001,value=cp(party,mean=1),id='slider-{0}'.format(party),tooltip={"placement": "bottom", "always_visible": True})],style= {"marginRight":500}))
## layout first


homepage.append(dcc.Graph(id='grafico',style={'width': '50%', 'display': 'inline-block'}))
homepage.append(dcc.Graph(id='grafico-senato',style={'width': '50%', 'display': 'inline-block',}))


homepage.append(html.H4("I dati della  simulazione sono disponibili qui (https://github.com/gabrielepinto/dati_simulatore_elettorale), Ideato e sviluppato da Gabriele Pinto, gabriele_pintorm@hotmail.com, www.gabrielepinto.com",style={"color":"black","font-size":16}))


homepage.append(html.H4(""))
#homepage.append(dcc.Graph(id="grafico-barra-camera"))

###
#homepage.append(dash_table.DataTable(df.to_dict('records'), [{"name": i, "id": i} for i in df.columns]))
homepage.append(html.H4(""))
homepage.append(html.H4("Camera: risultati collegi uninominali"))
homepage.append(dcc.Graph(id="mappa_camera",style={'width': '50%', 'display': 'inline-block'}))
homepage.append(dcc.Graph(id="mappa_camera_margine",style={'width': '50%', 'display': 'inline-block'}))
homepage.append(html.Div(id="tabella_camera"))

homepage.append(html.H4("Senato: risultati collegi uninominali"))
homepage.append(dcc.Graph(id="mappa_senato",style={'width': '50%', 'display': 'inline-block'}))
homepage.append(dcc.Graph(id="mappa_senato_margine",style={'width': '50%', 'display': 'inline-block'}))
homepage.append(html.Div(id="tabella_senato"))




app.layout = html.Div(homepage,style={'marginTop': 25,'marginLeft': 25})








# DEFINE INPUT AND OUTPUT ARRAY
## output
output_array=[dash.dependencies.Output('grafico', 'figure'),dash.dependencies.Output('grafico-gauge', 'figure'),
    dash.dependencies.Output('grafico-senato', 'figure'),dash.dependencies.Output('grafico-gauge-senato', 'figure'),
    dash.dependencies.Output('grafico-barra-parlamento', 'figure'),
    dash.dependencies.Output("tabella_camera","children"),dash.dependencies.Output("tabella_senato","children"),
    dash.dependencies.Output("mappa_camera","figure"),dash.dependencies.Output("mappa_senato","figure"),
    dash.dependencies.Output("mappa_camera_margine","figure"),dash.dependencies.Output("mappa_senato_margine","figure")]
for party in parties:
    output_array.append(dash.dependencies.Output('slider-{0}'.format(party),'value'))

output_array.append(dash.dependencies.Output("loading-output-1", "children"))
### input
all_sliders=[dash.dependencies.Input('slider-{0}'.format(party), 'value') for party in parties]
all_sliders.append(dash.dependencies.Input('lista_coalizione','value'))

@app.callback(
    output_array,
    all_sliders)
def update_output(value1,value2,value3,value4,value5,value6,value7,value8,value9,value10,value11,value12,tipo_coalizione):    
    
    ### aggiorna in base all ultimo che è stato cambiato
    valuez=np.array([value1,value2,value3,value4,value5,value6,value7,value8,value9,value10,value11,value12])
    act_values=np.array([cp(party,1)for party in parties])
    
    if (valuez!=act_values).any():
        to_edit=np.where(valuez!=act_values)[0][0]
        aumento_voti_partito(camera,increase=valuez[to_edit],partito=parties[to_edit])    
        

    ### aumenta
    for i in range(0,10):
        for part,incr in zip(parties,[value1,value2,value3,value4,value5,value6,value7,value8,value9,value10,value11,value12]):
            ### aumenta voti paritto
            aumento_voti_partito(camera,increase=incr,partito=part)
            aumento_voti_partito(senato,increase=incr,partito=part)

    ## UPDATE COALIZIONI
    dr=pd.read_excel(folder_head+"stime_partiti.xlsx",sheet_name="COALIZIONI")
    diz_coalizione=dict(zip(dr["LISTA"],dr[tipo_coalizione]))

        
    ### calcola risultati per la camera
    result=compute_uninom(camera=camera,diz=diz_coalizione)
    result["Seggio"]="uninominale"
    result2=compute_plurinom_camera(camera=camera)
    result2["Seggio"]="plurinominale"
    result=result.append(result2)
    result=result.append(pd.DataFrame({"seggi":[8],"Seggio":"plurinominale","partiti":"ESTERO"}))
    result.sort_values(["seggi","Seggio"],ascending=False,inplace=True)

    ### calcola risultati per il  senato
    result_senato=compute_uninom(camera=senato,diz=diz_coalizione)
    result_senato["Seggio"]="uninominale"
    result2_senato=compute_plurinom_senato(camera=senato)
    result2_senato["Seggio"]="plurinominale"
    result_senato=result_senato.append(result2_senato)
    result_senato=result_senato.append(pd.DataFrame({"seggi":[4],"Seggio":"plurinominale","partiti":"ESTERO"}))
    result_senato.sort_values(["seggi","Seggio"],ascending=False,inplace=True)

    ### vedi figura
    fig=px.bar(result,title="camera",x="partiti",y="seggi",color="partiti",color_discrete_map=diz_colori,facet_col="Seggio",width=700, height=500)
    fig_senato=px.bar(result_senato,title="Senato",x="partiti",y="seggi",color="partiti",color_discrete_map=diz_colori,facet_col="Seggio",width=700, height=500)
    ### GAUGE
    gauge_data,lista_gauge=compute_gauge_data(result=result,diz=diz_coalizione)
    maggioranza=gauge_data.groupby("coalizione")["seggi"].sum().loc["FDI*LEGA*FI"]
    fig_gauge=create_fig_gauge(maggioranza=maggioranza,lista_gauge=lista_gauge,maggioranza_richiesta=201,totale_posti=400)

    gauge_data_senato,lista_gauge_senato=compute_gauge_data(result=result_senato,diz=diz_coalizione)
    maggioranza=gauge_data_senato.groupby("coalizione")["seggi"].sum().loc["FDI*LEGA*FI"]
    fig_gauge_senato=create_fig_gauge(maggioranza=maggioranza,lista_gauge=lista_gauge_senato,maggioranza_richiesta=101,totale_posti=200,nome_graf="senato")
    ## modifica
    result["parlamento"]="camera"
    result_senato["parlamento"]="senato"
    all_camere=result.append(result_senato)
    all_camere=all_camere.groupby(["parlamento","partiti"],as_index=False)["seggi"].sum()

    all_camere["order"]=all_camere.partiti.apply(lambda x:diz_order[x])
    
    fig_bar=px.bar(all_camere.sort_values("order"), x="parlamento", y="seggi", color_discrete_map=diz_colori,color="partiti", text="partiti")

    da_restituire=[fig,fig_gauge,fig_senato,fig_gauge_senato,fig_bar]

       
    df_camera=tabella_uninom(camera=camera,diz=diz_coalizione)
    df_senato=tabella_uninom(camera=senato,diz=diz_coalizione)




    geo_df_camera=pd.concat([geo_camera.reset_index(drop=True).sort_values("COLLEGIOUNINOMINALE").reset_index(drop=True),df_camera.reset_index().sort_values("COLLEGIOUNINOMINALE").reset_index(drop=True).iloc[:,1:]],axis=1)
    geo_df_senato=pd.concat([geo_senato.reset_index(drop=True).sort_values("COLLEGIOUNINOMINALE").reset_index(drop=True),df_senato.reset_index().sort_values("COLLEGIOUNINOMINALE").reset_index(drop=True).iloc[:,1:]],axis=1)

    geo_df_camera.set_index("COLLEGIOUNINOMINALE",inplace=True)
    geo_df_senato.set_index("COLLEGIOUNINOMINALE",inplace=True)



    mappa_camera = px.choropleth_mapbox(geo_df_camera,
                            geojson=geo_df_camera.geometry,
                            locations=geo_df_camera.index,
                            center={"lat": 41.902782, "lon": 12.496366},
                            color="VINCITORE",
                            mapbox_style="open-street-map",
                            zoom=3,opacity=0.6)
    
    mappa_senato = px.choropleth_mapbox(geo_df_senato,
                            geojson=geo_df_senato.geometry,
                            locations=geo_df_senato.index,
                            center={"lat": 41.902782, "lon": 12.496366},
                            color="VINCITORE",
                            mapbox_style="open-street-map",
                            zoom=3,opacity=0.6)

    mappa_camera_margine = px.choropleth_mapbox(geo_df_camera,
                            geojson=geo_df_camera.geometry,
                            locations=geo_df_camera.index,
                            center={"lat": 41.902782, "lon": 12.496366},
                            color="MARGINE",
                            mapbox_style="open-street-map",
                            zoom=3,opacity=0.8)
    
    mappa_senato_margine = px.choropleth_mapbox(geo_df_senato,
                            geojson=geo_df_senato.geometry,
                            locations=geo_df_senato.index,
                            center={"lat": 41.902782, "lon": 12.496366},
                            color="VINCITORE",
                            mapbox_style="open-street-map",
                            zoom=3,opacity=0.8)



    
    da_restituire.append(dbc.Table.from_dataframe(df=df_camera.reset_index().sort_values("MARGINE"),striped=True, bordered=True, hover=True))
    da_restituire.append(dbc.Table.from_dataframe(df=df_senato.reset_index().sort_values("MARGINE"),striped=True, bordered=True, hover=True))

    da_restituire.append(mappa_camera)
    da_restituire.append(mappa_senato)
    da_restituire.append(mappa_camera_margine)
    da_restituire.append(mappa_senato_margine)

    for party in parties:
        da_restituire.append(cp(party,1))
    ## per il loader
    da_restituire.append(None)
    return da_restituire


    






# @app.callback(dash.dependencies.Output('grafico',"figure"))
# def creagrafico():


#     result=compute_uninom(camera=camera)    
#     fig=px.bar(result,x="partiti",y="seggi",color="partiti",width=1500, height=600)
#     return fig


if __name__ == "__main__":
    app.run_server(debug=True)
    





