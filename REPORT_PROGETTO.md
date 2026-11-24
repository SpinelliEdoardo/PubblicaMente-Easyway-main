# EasyWay - report del progetto (gruppo PubblicaMente)

Questo file descrive lo stato attuale del progetto. È scritto per i componenti del
gruppo e per qualsiasi assistente AI (Claude, Gemini, ChatGPT o altri) a cui viene
dato per lavorare sul progetto. Si aggiorna a ogni passo importante.

- Stato aggiornato al: 24/11/2026
- Fase di lavoro: **Code**. Fatti e committati i passi 1.1 e 1.2 in `dati_gtfs.py`
  (GTFS statico, rete urbana, servizi attivi in una data), il passo 1.3 in
  `dati_realtime.py` (lettura dei `.bin`), il passo 1.4 in entrambi (gestione delle
  insidie), il livello 2 in `rete.py` (grafo delle fermate e percorsi senza cambi),
  l'orologio simulato in `config.py` e il livello 3 in `rete.py` e `dati_realtime.py`
  (cambi a piedi, criteri più veloce, meno cambi, accessibile). Scritto e testato, in
  revisione: livello 4 completo (prossime partenze in `rete.py`, `api.py` con
  FastAPI esteso con `/api/veicoli`, `/api/avvisi` e parametro `criterio`, pagina
  con Leaflet in `frontend/` con veicoli della fotografia e pannello avvisi; 79 test
  passati). Prossimo: attesa del percorso con le partenze vere, poi livello 5, le
  segnalazioni.
- Registro completo delle decisioni e del loro motivo: `STORICO.md`.

## Istruzioni per l'assistente AI che legge questo file

1. Le voci segnate **DECISO** sono scelte del gruppo: non cambiarle e non proporre
   alternative se non lo chiede chi ti sta usando.
2. Le voci segnate **PROPOSTA** non sono ancora approvate: non darle per scontate.
3. Non inventare dati, fonti, link, soglie di rimborso o numeri. Se un'informazione non
   è in questo file o nei dati del progetto, dillo.
4. Vietato usare dati personali reali: solo dati aperti, pubblici o sintetici
   (requisito della traccia). Gli esempi inventati vanno dichiarati come tali.
5. Stile del codice, adottato da tutto il gruppo:
   - Python semplice e leggibile, passo passo;
   - nomi di variabili e funzioni in italiano, tranne i nomi delle librerie e dei
     loro metodi;
   - commenti solo quando spiegano il perché, niente emoji nel codice.
6. Prima di lavorare su un punto, controlla la sezione "Insidie nei dati": contiene
   errori già trovati che è facile ripetere.

## Il progetto in breve

- **Contesto:** esercitazione su una traccia "AI Sprint", area Servizi pubblici. La
  traccia prevede 4 ore, ma per l'esercitazione non c'è limite di tempo.
- **Consegna:** un prototipo funzionante e un pitch di 3 minuti con demo dal vivo.
- **Criteri di valutazione:**

  | Criterio | Peso |
  |---|---|
  | Impatto | 30% |
  | Qualità del prototipo | 30% |
  | Innovazione e uso dell'AI | 20% |
  | Presentazione | 20% |

- **Idea:** EasyWay aiuta chi usa i mezzi pubblici di Torino a scegliere un percorso,
  anche accessibile, e lo ricalcola quando arriva un problema. I problemi arrivano da
  due fonti: gli avvisi ufficiali dell'azienda di trasporto (GTT) e le segnalazioni di
  cittadini e operatori. L'AI legge le segnalazioni scritte in linguaggio libero.
- **Città:** solo Torino. Il nome della traccia, `AI Sprint - ROMA.docx`, non c'entra
  con la città dei dati.

## Flusso dell'app

Schema grafico: `schema_EasyWay_rivisto.png`. Schema originale del gruppo:
`WhatsApp Image 2026-11-19 at 12.19.03.jpeg`.

1. Login/registrazione (da definire; ipotesi: utenti già presenti nel database,
   eventualmente simulati).
2. **Ramo percorso:** richiesta del percorso con criteri opzionali -> calcolo del
   percorso migliore -> visualizzazione dei percorsi e delle prossime partenze ->
   percorso scelto sulla mappa -> controllo continuo: se arriva un problema, nuovo
   percorso.
3. **Ramo segnalazione:** chi segnala (cittadino o operatore dell'azienda) -> caso
   (incidente, lavori, scioperi, guasto dei mezzi, altro) -> salvataggio nel database.
4. Le segnalazioni salvate e gli avvisi ufficiali alimentano il controllo continuo del
   percorso.

## Decisioni in vigore

| Tema | Decisione | Stato |
|---|---|---|
| Mezzi | Solo rete urbana GTT (`agency_id == "U"`): bus urbani, tram, metro. Esclusi extraurbani e servizi turistici | DECISO |
| Calcolo del percorso | Rete come grafo: nodi = fermate, archi = tratte tra fermate consecutive (tempo medio da `stop_times`) e tratti a piedi tra fermate vicine; algoritmo di Dijkstra con `networkx`. Dal livello 3 i nodi sono di tre tipi (riga "Cambi e criteri"). Limite da dichiarare: usa tempi medi, non l'orario preciso della corsa | DECISO |
| Ordine di sviluppo del percorso | Prima solo linee dirette, poi i cambi, poi i criteri | DECISO |
| Tempo di attesa | Attesa media alla fermata = metà della frequenza della linea. Nel livello 2: metà dell'intervallo medio tra le corse utili; nel livello 3: tra le corse della stessa sequenza di fermate (vedi "Punti aperti") | DECISO |
| Criteri del percorso | Più veloce, meno cambi, accessibile: tutti opzionali | DECISO |
| Accessibilità | Il criterio accessibile considera anche gli ascensori metro fuori servizio presi dagli avvisi | DECISO |
| Prossime partenze | Per tutti i mezzi dall'orario statico; per bus e tram si aggiunge il ritardo real-time dove c'è | DECISO |
| Orologio simulato | L'app lavora come se fosse il 18/11/2026 alle 15:50, l'istante dei dati real-time disponibili | DECISO |
| Dati real-time | Posizioni e ritardi sono una fotografia del 18/11/2026: si presentano come tali, non come dati live | DECISO |
| Interfaccia | Backend FastAPI + pagina web con mappa Leaflet | DECISO |
| Database | SQLite | DECISO |
| AI | LangGraph a nodi fissi: estrazione -> validazione -> salvataggio -> ricalcolo -> spiegazione. Il modello lavora solo nei nodi che lo richiedono; il percorso lo calcola codice Python | DECISO |
| Modello AI | Locale con Ollama: Qwen3-4B-Instruct-2507 quantizzato Q4_K_M (2,5 GB), versione `Jadio/Qwen3_4b_instruct_q4km` | DECISO |
| Lettura feed real-time | Libreria `gtfs-realtime-bindings` 3.0.0 sui file `.bin`, in `dati_realtime.py`; i dati si leggono così come sono, la pulizia è un passo a parte | DECISO |
| Forma del codice | Notebook per esplorare i dati, file `.py` per l'app | DECISO |
| Scioperi | Arrivano dal feed ufficiale degli avvisi e restano anche tra i casi di segnalazione | DECISO |
| Git e GitHub | Repository privato `PubblicaMente-Easyway`, condiviso con il gruppo; un commit per ogni passo verificato | DECISO |
| Ambiente Python | Python 3.12; librerie e versioni in `requirements.txt`, uguale per tutti | DECISO |
| Caricamento dei dati | Per ora la rete si rilegge dallo zip a ogni avvio (35-70 secondi); salvarla in un file veloce (Parquet, proposta di Claude) resta un'idea di riserva | DECISO |
| Insidie nei dati | Veicoli a (0,0) esclusi dalla mappa; veicoli senza `trip_id` tenuti; linea `FLEU` mostrata come "linea sconosciuta"; avvisi con fine nel 2033-2035 attivi "fino a nuovo avviso"; riferimenti a fermate inesistenti tolti (93); tabella fermata -> stazione madre per la metro | DECISO |
| Cambi e criteri (livello 3) | Grafo unico con tre tipi di nodo: fermata, a_piedi (dopo una camminata si sale soltanto o si finisce il viaggio) e corsa (fermata dentro una sequenza di fermate); cambi a piedi entro 300 m in linea d'aria a 1 m/s; meno cambi = 15 minuti di penalità a ogni salita; accessibile = niente fermate con `wheelchair_boarding` 2, niente corse con `wheelchair_accessible` diverso da 1, niente fermate senza ascensore (nome della fermata nel testo dell'avviso). 300 m, 1 m/s e 15 minuti sono valori scelti dal gruppo, non dati GTT | DECISO |
| Mappa e partenze (livello 4) | Fermate scelte cercando il nome; prossime partenze = orario statico + ritardo del feed dove c'è (il ritardo misurato vale anche per le fermate successive); Leaflet 1.9.4 e tessere OpenStreetMap (serve internet alla demo); l'attesa del percorso con le partenze vere è un passo a parte | DECISO |
| Nodi con il modello | Estrazione dal testo libero (categoria, linea, fermata), validazione rispetto ad avvisi e dati real-time, spiegazione del nuovo percorso | PROPOSTA |
| Versione del modello | Usare la versione ufficiale `qwen3:4b-instruct-2507-q4_K_M` (stessa quantizzazione) | PROPOSTA |
| Validazione segnalazioni | Segnalazione dell'operatore = ufficiale; quella del cittadino va validata | PROPOSTA |
| Agente con strumenti | Se servisse, uno solo, con 2-3 strumenti al massimo | PROPOSTA |

**Perché nodi fissi e non agenti liberi:** un agente libero chiama il modello più volte
(più lento) e un modello da 4B sbaglia più spesso quando deve scegliere tra tanti
strumenti. Il modello è piccolo per stare nei 4 GB della scheda video (NVIDIA RTX
A500) del PC su cui girerà la demo e rispondere in fretta. Sui PC senza GPU dedicata
gira sulla CPU: più lento, ma va bene per sviluppare.

## Dati

Cartella `Datasets/`. Fonte: open data GTT (Gruppo Torinese Trasporti).

| File | Contenuto |
|---|---|
| `gtt_gtfs.zip` | Orari statici in formato GTFS (CSV dentro uno zip), validi dal 16/11/2026 al 31/01/2027 |
| `file_bin/alerts.bin` | Avvisi ufficiali in tempo reale (formato GTFS-Realtime, binario) |
| `file_bin/vehicle_position.bin` | Posizione dei mezzi |
| `file_bin/trip_update.bin` | Ritardi delle corse |
| `file_bin/*.bin.txt` | Gli stessi feed in testo leggibile, solo per consultazione |
| `file_bin/*.results.json` | Errori trovati da un validatore GTFS-Realtime |

I tre `.bin` sono una sola fotografia del 18/11/2026, circa alle 15:50.

**Licenze:** CC BY-NC 4.0 per GTFS statico, posizioni e ritardi; CC BY-NC-SA 3.0 per
gli avvisi. Uso non commerciale e citazione di GTT obbligatoria.

**Priorità dei file:**

| Priorità | File |
|---|---|
| Essenziale | stops, routes, trips, stop_times, vehicle_position, trip_update, alerts |
| Alta | vehicles + vehicle_categories (mezzi accessibili); calendar / calendar_dates (prossime partenze) |
| Media | shapes, stop_attributes |
| Da ignorare | fare_*, timetables, trips_booking, agency, feed_info |

**Copertura real-time nella fotografia:** bus urbani 329 posizioni e 342 ritardi; tram
87 e 87; la metro non ha dati real-time e si gestisce con orario statico e avvisi
(l'assenza è da confermare con un secondo scaricamento in un altro orario).

**Collegamenti verificati:** i 429 `trip_id` di trip_update esistono tutti in
`trips.txt`; i 417 veicoli di vehicle_position esistono tutti in `vehicles.txt`.

## Insidie nei dati (già verificate)

- **Join veicoli-categorie:** in `vehicles.txt` la categoria è `105`, in
  `vehicle_categories.txt` è `105U`. Senza aggiungere la "U" il collegamento trova 0
  veicoli su 1.209; con la "U" li trova tutti.
- **`wheelchair_boarding` = 0** nelle fermate significa "nessuna informazione", non
  "non accessibile". Il valore "non accessibile" è 2.
- **vehicle_position:** 15 veicoli hanno coordinate (0,0) e 44 non hanno `trip_id`
  (9 sono in entrambi i gruppi); il veicolo 9483U è assegnato alla linea `FLEU`, che
  non esiste. Gestione: riga "Insidie nei dati" delle decisioni;
  `prepara_posizioni_per_la_mappa` lascia 402 posizioni su 417.
- **trip_update:** nel dump testuale compare un campo non riconosciuto, numero 4,
  dentro `vehicle` (valore 2 in 308 casi, 3 in 121).
- **alerts:** 93 riferimenti a fermate che non esistono nel GTFS statico (53 fermate
  distinte), tolti da `togli_fermate_inesistenti`; 6 avvisi hanno una data di fine
  tra il 2033 e il 2035, tra cui quello dell'ascensore di Vinzaglio: si trattano come
  attivi "fino a nuovo avviso". Alle 15:50 del 18/11 sono attivi tutti i 134 avvisi.
- **Sensi di marcia:** le fermate di bus e tram di solito sono diverse nei due sensi,
  quelle della metro sono le stesse. Il grafo va diviso per linea e senso di marcia
  (`direction_id`): unendo i sensi, un percorso "senza cambi" può girare al capolinea
  e alla metro l'attesa esce dimezzata.
- **Varianti di percorso:** molte linee hanno corse che fanno percorsi diversi
  (deviazioni, corse limitate), e il grafo della linea le unisce. Un collegamento nel
  grafo quindi non basta: `trova_percorsi_diretti` tiene solo le corse che passano
  davvero prima dall'origine e poi dalla destinazione, e su quelle calcola tempo e
  attesa (esempio: il 20 da 608 a 8833 ha solo 2 corse utili il 18/11).
- **Ascensori della metro:** l'avviso sugli ascensori è collegato a tutte le 23
  fermate della metro; quale ascensore è fermo lo dice solo il testo ("Vinzaglio
  esterno"). Gestione: riga "Cambi e criteri" delle decisioni.
- **Accessibilità:** quasi tutte le fermate urbane risultano accessibili (3.727 su
  3.730); il dato che distingue è quello delle corse (`wheelchair_accessible` = 2 per
  10.404 corse su 57.332).
- **Cambi a piedi:** il GTFS non ha `transfers.txt` né `pathways.txt`: i cambi a
  piedi si calcolano dalle coordinate delle fermate.
- **Orari dopo mezzanotte:** 47.758 righe di `stop_times.txt` della rete urbana hanno
  un orario dalle 24:00:00 in su (fino a "26:55:00"): si convertono in secondi a mano.
- **alerts riferiti a un'intera azienda:** alcuni avvisi, come lo sciopero del 20/11,
  non citano linee o fermate ma solo `agency_id` (U, E, F, T). Per collegarli alla
  rete urbana va letto anche `agency_id`.
- **trip_update:** il ritardo arriva in due forme: il campo `arrival.delay` del feed,
  colonna `arrival_delay` (secondi, 1.672 righe), oppure il campo `arrival.time`,
  colonna `arrival_timestamp` (orario previsto in secondi POSIX, 767 righe). Mai
  entrambi e mai nessuno nella stessa riga. Attenzione: `arrival_time` di
  `stop_times.txt` è un'altra cosa, l'orario programmato come testo "HH:MM:SS". Per
  lo stesso motivo l'orario delle posizioni si chiama `vehicle_timestamp`.
- **Ritardo 0:** 47 righe (coppie corsa-fermata) hanno un ritardo di 0 secondi, cioè
  in orario. Non va confuso con "ritardo assente": per questo le colonne usano il
  tipo `Int64`, che ammette celle vuote.
- **stop_times.txt** pesa circa 113 MB: conviene filtrarlo sulla rete urbana prima
  dell'uso.
- **`stop_attributes.txt`** contiene solo il comune della fermata, non dati di
  accessibilità.
- **Calendario:** per sapere quali corse circolano in una data servono sia
  `calendar.txt` sia le eccezioni di `calendar_dates.txt` (tipo 1 aggiunge, tipo 2
  toglie). GTT ripete come "aggiunta" quasi tutte le date già previste, ma alcune
  eccezioni cambiano davvero il servizio (per esempio l'8/12/2026). La funzione
  `filtra_corse_del_giorno` applica entrambe le regole: il 18/11/2026 dà 11.785
  corse urbane.

## Spunti per la demo

Avvisi reali presenti nel feed alerts del 18/11/2026:
- "Situazione aggiornata ascensori metro": fuori servizio Vinzaglio esterno (fermata
  della metro M1).
- "Sciopero nazionale di 24 ore" previsto venerdì 20 novembre 2026.
- 88 avvisi di deviazione, 18 con causa "lavori".

## Piano di sviluppo (DECISO)

Il codice si scrive a passi piccoli: per ogni passo codice e test, revisione, controllo
del gruppo, commit. Il livello 1 è diviso in quattro passi: 1.1 lettura del GTFS
statico e filtro sulla rete urbana; 1.2 servizi attivi in una data; 1.3 lettura dei
`.bin`, con il controllo che tutte le 429 corse di trip_update risultino attive il
18/11/2026; 1.4 gestione delle insidie.

| Livello | Cosa si costruisce | Quando è "fatto" |
|---|---|---|
| 1. Dati | Caricamento GTFS della rete urbana, lettura dei `.bin`, gestione delle insidie | I conteggi tornano con quelli delle sezioni "Dati" e "Insidie nei dati" |
| 2. Linee dirette | Grafo delle fermate e percorso senza cambi | Su 3-4 coppie di fermate esce la linea giusta |
| 3. Cambi e criteri | Tratti a piedi, penalità sui cambi, criterio accessibile | Il percorso accessibile evita la fermata metro Vinzaglio, con l'ascensore fuori servizio |
| 4. Mappa | Pagina web con Leaflet, percorso disegnato, prossime partenze | Una persona del gruppo la usa senza aiuto |
| 5. Segnalazioni | Form cittadino/operatore, salvataggio in SQLite, ricalcolo | Una segnalazione fa cambiare il percorso |
| 6. AI | Nodi LangGraph: estrazione, validazione, spiegazione | Su 10 segnalazioni di prova inventate: JSON valido e campi corretti |
| 7. Pitch | Scaletta di 3 minuti e demo provata | Prova a tempo |

Tra il livello 4 e il livello 5 c'è un passo in più: l'attesa del percorso calcolata
con le prossime partenze vere (riga "Mappa e partenze").

Struttura dei file prevista (DECISO):

```
PubblicaMente/
  Datasets/              dati GTT
  notebook/              esplorazione dei dati
  config.py              collegamento al modello, orologio simulato
  dati_gtfs.py           GTFS statico, filtro rete urbana
  dati_realtime.py       lettura dei .bin
  rete.py                grafo delle fermate, percorsi, criteri
  db.py                  SQLite: utenti, segnalazioni
  flusso_ai.py           grafo LangGraph a nodi fissi
  api.py                 FastAPI
  frontend/              pagina web con Leaflet
  tests/                 test per ogni livello
  requirements.txt
  STORICO.md
  REPORT_PROGETTO.md
```

## Punti aperti

- Login: utenti già nel database o da creare.
- `stop_attributes.txt`: tenerlo o ignorarlo.
- Versione del modello (vedi PROPOSTA sopra).
- Scaricare il modello sul PC della demo e verificare 100% GPU con `ollama ps`.
- `carica_ritardi` non gestisce ancora fermate senza `stop_sequence`, fermate indicate
  solo con `stop_id`, orari di partenza e fermate saltate (assenti nel feed del
  18/11). Il livello 4 non l'ha risolto: da riprendere se si usano altri feed.
- Attesa alla fermata: nel livello 2 è la metà dell'intervallo medio tra le corse
  utili di tutta la giornata; da affinare con una fascia oraria intorno all'orologio
  simulato. Una linea con una sola corsa utile al giorno tra due fermate per ora non
  compare tra i percorsi diretti.
- Livello 3: l'attesa per sequenza di fermate è sovrastimata dove passano più varianti
  della stessa linea, e 72 delle 519 sequenze (una sola corsa al giorno) non si possono
  prendere (da risolvere con le prossime partenze vere, passo dopo il livello 4). La
  regola del nome nel testo sbaglia con nomi che sono anche parole comuni (esempio
  ipotetico: "fermi" farebbe escludere METRO FERMI): da sostituire con il modello
  (livello 6). La penalità dei cambi colpisce anche la prima salita.
- Livello 4: manca il test di accettazione (una persona del gruppo usa la pagina
  senza aiuto). La rete occupa molta memoria: sul PC di sviluppo (7,3 GB) la suite è
  andata in `MemoryError`; la causa principale (rete costruita due volte) è corretta
  con `tests/conftest.py`, resta il rischio con molti programmi aperti. Da verificare
  sul PC della demo.
- Le fonti elencate nella chat con Gemini dentro il docx della traccia non sono
  verificate: controllarle prima di usarle.

## Come eseguire il codice e i test

Dalla cartella del progetto, nel venv del progetto (Python 3.12, con le librerie di
`requirements.txt`: `pip install -r requirements.txt`):

```
python dati_gtfs.py
python dati_realtime.py
python rete.py
pytest -v
```

`dati_gtfs.py` stampa le righe caricate della rete urbana (138 linee, 57.332 corse,
1.705.141 orari, 3.730 fermate), poi 1.209 veicoli e 2 fermate con stazione madre. Il
caricamento dura 35-70 secondi, secondo quanto è carico il PC, perché legge dallo zip
anche gli orari, circa 113 MB.

`dati_realtime.py` stampa le righe lette dai feed del 18/11/2026: 417 posizioni,
2.439 righe di ritardi, 134 avvisi, 8.854 elementi degli avvisi; poi i risultati della
pulizia: 402 posizioni per la mappa, 134 avvisi attivi, 93 riferimenti a fermate
inesistenti tolti.

`rete.py` costruisce la rete del 18/11/2026: 249 grafi (linea e senso di marcia),
7.971 tratte, poi il grafo con i cambi (21.049 nodi, 76.463 archi). Rilegge lo zip,
quindi dura come `dati_gtfs.py`.

Per la pagina web, sempre dalla cartella del progetto:

```
python -m uvicorn api:app --port 8000
```

Dopo il caricamento (35-70 secondi) la pagina è su `http://127.0.0.1:8000`. Serve
internet per Leaflet e per la mappa di sfondo. Con poca RAM conviene chiudere prima
i programmi pesanti, come i browser con molte schede.

Il file `pytest.ini` dice a pytest dove trovare i moduli e i test, quindi i test
partono anche dal pannello Test di VS Code.

## Come preparare il modello

Serve Ollama installato. Nel terminale:

```
ollama pull Jadio/Qwen3_4b_instruct_q4km
ollama run Jadio/Qwen3_4b_instruct_q4km "Rispondi in una riga: che cos'è una fermata del tram?"
ollama ps
```

In `ollama ps`, sul PC della demo (NVIDIA RTX A500) la colonna `PROCESSOR` dovrebbe
mostrare 100% GPU: se il modello è diviso tra CPU e GPU, le risposte sono più lente.
Sui PC senza GPU dedicata mostra 100% CPU, ed è normale.

## Glossario

- **GTFS:** formato standard degli orari del trasporto pubblico (fermate, linee,
  corse, orari).
- **GTFS-Realtime:** versione in tempo reale (posizioni, ritardi, avvisi), in formato
  binario protobuf.
- **Grafo:** insieme di nodi collegati da archi con un peso; qui i nodi sono le
  fermate e il peso è il tempo.
- **Dijkstra:** algoritmo che trova il percorso di peso minimo in un grafo.
- **LangGraph:** libreria per costruire flussi di passi (nodi) che usano un modello AI.
- **Ollama:** programma per far girare modelli AI in locale.
- **Quantizzazione Q4_K_M:** compressione del modello che lo rende più piccolo e
  veloce, con una piccola perdita di precisione.
