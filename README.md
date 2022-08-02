# dati_simulatore_elettorale
data repository per il simulatore elettorale accessibile qui https://simulatorelezioni.herokuapp.com/

Il codice sorgente del simulatore può essere trovato ![qui](https://github.com/gabrielepinto/dati_simulatore_elettorale/blob/main/app.py)

i dati sottostanti al simulatore possono essere scaricati da  ![camera](https://github.com/gabrielepinto/dati_simulatore_elettorale/blob/main/camera_bilanciato.csv) e ![senato](https://github.com/gabrielepinto/dati_simulatore_elettorale/blob/main/camera_bilanciato.csv).

Gli shapefile dei seggi unininominali per camera e senato si trovanno sotto la cartella ![COLLEGI_ELETTORALI_NUOVI](https://github.com/gabrielepinto/dati_simulatore_elettorale/tree/main/COLLEGI_ELETTORALI_NUOVI)

La distribuzione territoriale dei voti per i partiti è calcolata pesando il risultato delle elezioni politiche del 2018 e può essere visualizzata ![qui](https://raw.githubusercontent.com/gabrielepinto/dati_simulatore_elettorale/main/distribuzione_territoriale.PNG).
Per il partito AZIONE/EUROPA+ è stata utilizzata la distribuzione del 2018 di EUROPA+ (forte nelle grandi città e debole in provincia). Per Italia Viva si è ipotizzata una distribuzione in cui il risultato in toscana è 3 volte la media e nel Lazio è 2 volte la media nazionale. Per i restanti partiti per cui non si hanno informazioni o ipotesi "credibili" (IPF, ITALEXIT e ALTRI) abbiamo randomizzato la distribuzione residua ("a caso").