# Storico del progetto PubblicaMente - EasyWay

Registro dei passi fatti e delle decisioni prese. Si aggiorna a ogni sessione di lavoro:
le voci nuove vanno in fondo alla sezione "Diario", le decisioni valide restano nella
sezione "Decisioni in vigore". Se una decisione cambia, si aggiorna la sezione e si
annota il cambio nel diario.

## Contesto

- Gruppo: PubblicaMente. Progetto: EasyWay. Il gruppo lavora a tutte le parti insieme.
- Traccia ufficiale: `AI Sprint - ROMA.docx` (area Servizi pubblici).
  - Criteri: impatto 30%, qualità del prototipo 30%, innovazione e uso dell'AI 20%,
    presentazione 20%.
  - Consegna: prototipo e pitch di 3 minuti con demo dal vivo.
  - Vietati i dati personali reali: solo dati sintetici, aperti o pubblici.
- La traccia prevede 4 ore, ma questa è un'esercitazione: nessun limite di tempo.
- Città: solo Torino (dati GTT), anche se il nome del docx dice "ROMA".

## Dati disponibili

| File | Contenuto |
|---|---|
| `Datasets/gtt_gtfs.zip` | GTFS statico GTT, valido dal 16/11/2026 al 31/01/2027 |
| `Datasets/file_bin/*.bin` | GTFS-Realtime: alerts, vehicle_position, trip_update (fotografia del 18/11/2026, circa 15:50) |
| `Datasets/file_bin/*.bin.txt` | Gli stessi feed decodificati in testo |
| `Datasets/file_bin/*.results.json` | Errori trovati da un validatore GTFS-Realtime |

Licenza dei dati GTT: CC BY-NC 4.0 per GTFS statico, posizione mezzi e passaggi;
CC BY-NC-SA 3.0 per gli alerts (dalle schede del portale incluse nel docx).
Uso non commerciale e citazione di GTT obbligatoria.

## Scheletro del progetto

Fonte: `WhatsApp Image 2026-11-19 at 12.19.03.jpeg` (schema iniziale, può cambiare).
Nello schema i blocchi verdi sono alcune parti di backend, gli altri sono scelte
dell'utente dell'app.

Flusso originale:
- EasyWay -> login/registrazione, poi due rami.
- Ramo percorso: richiesta del percorso -> calcolo del percorso migliore (backend) ->
  visualizzazione dei percorsi -> percorso scelto sulla mappa -> controllo continuo del
  percorso con consiglio di un nuovo percorso in caso di problema segnalato (backend).
- Ramo segnalazione: casi (incidente, lavori, scioperi, guasto dei mezzi, altro da
  specificare) -> salvataggio della segnalazione su db (backend).

Modifiche concordate allo schema (19/11/2026):
- **AI con modello locale**: c'era già nelle intenzioni, mancava nello schema. Punti
  proposti: lettura delle segnalazioni scritte in linguaggio libero (categoria, linea,
  fermata), validazione rispetto ad avvisi ufficiali e dati real-time, spiegazione del
  nuovo percorso.
- **Collegamento tra i rami**: segnalazioni nel db + avvisi ufficiali (feed alerts)
  -> controllo del percorso.
- **Scioperi**: si prendono dal feed ufficiale degli avvisi e restano anche tra i
  casi di segnalazione.
- **Segnalazioni da due ruoli**: cittadino e operatore dell'azienda. Proposta: la
  segnalazione dell'operatore vale come ufficiale, quella del cittadino va validata.
- **Accessibilità**: deve esserci. Criterio "accessibile" nel calcolo del percorso,
  che considera anche gli ascensori metro fuori servizio presi dagli avvisi.
- **Login**: da definire più avanti. Ipotesi: utenti già registrati nel database,
  eventualmente simulati.
- Schema rivisto con queste modifiche: `schema_EasyWay_rivisto.png` (tratteggio,
  di bordo o di freccia = proposta da confermare).

## Decisioni in vigore

1. **Priorità dei dati**

   | Priorità | File |
   |---|---|
   | Essenziale | stops, routes, trips, stop_times, vehicle_position, trip_update, alerts |
   | Alta | vehicles + vehicle_categories (accessibilità dei mezzi in tempo reale); calendar / calendar_dates (prossime partenze di tutti i mezzi dall'orario statico) |
   | Media | shapes, stop_attributes |
   | Da ignorare | fare_*, timetables, trips_booking, agency, feed_info |

2. **Lettura dei feed real-time**: con la libreria `gtfs-realtime-bindings` sui file
   `.bin`, anziché sui dump testuali `*.bin.txt`. Versione 3.0.0, installata il
   20/11/2026 (richiede `protobuf` 7.34 o superiore; nel venv del progetto c'è la 7.36.2).
3. **Calcolo del percorso: la rete come grafo**. Nodi = fermate; archi di viaggio tra
   fermate consecutive di una linea (tempo medio da `stop_times`); archi a piedi tra
   fermate vicine; percorso con l'algoritmo di Dijkstra (`networkx`). Sviluppo per
   livelli: prima solo linee dirette, poi con i cambi, poi i criteri.
   - Limite da dichiarare: usa tempi medi, non l'orario preciso della corsa.
     Correttivo deciso: attesa media pari a metà della frequenza della linea.
   - Applicazione nel livello 2: l'attesa è la metà dell'intervallo medio tra le corse
     utili (vedi "Punti aperti"); Dijkstra serve dal livello 3, con i cambi.
   - Applicazione nel livello 3: i nodi sono di tre tipi e l'attesa è la metà
     dell'intervallo medio tra le corse della stessa sequenza di fermate, a quella
     fermata (vedi decisione 17).
4. **Criteri del percorso, tutti opzionali**: più veloce, meno cambi, accessibile.
5. **Dati della demo**: il ricalcolo del percorso parte dalle segnalazioni degli utenti
   nel db e dagli avvisi ufficiali del feed. Posizioni e ritardi dei mezzi restano
   quelli della fotografia del 18/11 e nell'app vanno presentati come tali, non come
   dati live.
   - **Orologio simulato**: l'app lavora come se fosse il 18/11/2026 alle 15:50,
     l'istante della fotografia, così orari, ritardi, posizioni e avvisi sono
     coerenti. Nel pitch si dichiara che la demo usa la fotografia reale del 18
     novembre.
6. **Mezzi**: solo rete urbana (`agency_id == "U"`): bus urbani, tram e metro. Esclusi
   bus extraurbani e servizi turistici. Né questi né la metro hanno dati real-time
   nella fotografia.
   - **Prossime partenze per tutti i mezzi** dall'orario statico. Per bus e tram si
     aggiunge il ritardo da `trip_update` dove presente; la metro ha solo l'orario
     statico e gli avvisi.
7. **Modello AI**: in locale con Ollama, Qwen3-4B-Instruct-2507 quantizzato Q4_K_M
   (2,5 GB). Motivo: stare nei 4 GB della GPU (NVIDIA RTX A500) del PC su cui girerà
   la demo (dato fornito da PubblicaMente) e avere risposte veloci, come richiesto da
   PubblicaMente. Sui PC senza GPU dedicata il modello gira sulla CPU, più lento: va
   bene per lo sviluppo. Scelta di PubblicaMente: la versione
   `Jadio/Qwen3_4b_instruct_q4km`, ripubblicazione di un utente.
   Proposta di Claude, da decidere nel gruppo: la versione ufficiale con la stessa
   quantizzazione (Q4_K_M, 2,5 GB), `qwen3:4b-instruct-2507-q4_K_M`.
8. **Git e GitHub**: repository privato `PubblicaMente-Easyway` su GitHub, condiviso
   con il gruppo, pubblicato il 20/11/2026. Si fa un commit per ogni passo
   verificato, con il via libera di PubblicaMente.
9. **Interfaccia**: FastAPI + pagina web (come nel project work Salus Levante), con
   mappa Leaflet.
10. **Database**: SQLite.
11. **AI**: LangGraph a nodi fissi, collegato a Ollama. Flusso delle segnalazioni:
    estrazione -> validazione -> salvataggio -> ricalcolo -> spiegazione. Il modello
    lavora solo nei nodi che lo richiedono; il calcolo del percorso resta codice
    Python. Motivo: un agente libero chiama il modello più volte (più lento) e un
    modello da 4B sbaglia più spesso con tanti strumenti.
    - Proposta di Claude, da confermare: se servisse un agente con strumenti, uno
      solo, con 2-3 strumenti al massimo.
12. **Forma del codice**: notebook per esplorare i dati, file `.py` per l'app.
13. **Stile del codice comune** (valido anche per gli assistenti AI usati dai
    componenti): Python semplice e leggibile; nomi di variabili e funzioni in
    italiano, tranne i nomi delle librerie e dei loro metodi; commenti solo quando
    spiegano il perché; niente emoji nel codice; non proporre alternative alle
    decisioni prese se non viene chiesto.
14. **Ambiente Python**: venv del progetto (Python 3.12.1). Le librerie e le loro
    versioni sono in `requirements.txt`, uguale per tutto il gruppo.
15. **Caricamento dei dati**: per ora la rete urbana si rilegge dallo zip a ogni avvio
    (35-70 secondi, secondo quanto è carico il PC). Salvarla in un file veloce
    (Parquet, proposta di Claude) resta un'idea di riserva.
16. **Gestione delle insidie nei dati** (passo 1.4, proposte di Claude approvate da
    PubblicaMente il 21/11/2026):
    - veicoli a (0,0): esclusi dalla mappa;
    - veicoli senza `trip_id`: restano sulla mappa, la posizione è vera anche se la
      corsa non è nota;
    - linea `FLEU`: il veicolo resta, segnato come "linea sconosciuta";
    - avvisi con fine nel 2033-2035: attivi "fino a nuovo avviso"; la regola del periodo
      (inizio <= istante <= fine) li tiene già, senza casi a parte;
    - riferimenti degli avvisi a fermate inesistenti: tolti (sono 93: si contano
      confrontando le righe prima e dopo);
    - stazioni madre della metro: tabella fermata -> stazione madre;
    - feed real-time (completa le correzioni del passo 1.3): si leggono solo le entità
      del tipo atteso e le colonne numeriche restano numeriche anche con un feed vuoto.
17. **Livello 3: cambi e criteri** (proposte di Claude approvate da PubblicaMente il
    23/11/2026):
    - un grafo unico con tre tipi di nodo: "fermata" (si sale, si scende, si parte a
      piedi), "a_piedi" (si arriva camminando: da qui si sale soltanto o si finisce il
      viaggio, così tra due mezzi c'è al massimo una camminata) e "corsa" (una
      fermata dentro una sequenza di fermate, cioè linea, senso e fermate uguali);
    - le sequenze evitano i collegamenti falsi tra varianti della stessa linea;
    - cambi a piedi entro 300 m in linea d'aria, a 1 m/s: valori scelti dal gruppo,
      non dati GTT (GTT non dà `transfers.txt` né `pathways.txt`);
    - criteri: più veloce (predefinito); meno cambi, con 15 minuti di penalità a ogni
      salita (valore scelto dal gruppo); accessibile, che esclude le fermate con
      `wheelchair_boarding` = 2, le corse con `wheelchair_accessible` diverso da 1
      (anche le corse con 0, "dato non noto": scelta prudente) e le fermate senza
      ascensore segnalate dagli avvisi. A bordo si può passare da una fermata esclusa
      senza scendere;
    - fermata senza ascensore: si riconosce perché il suo nome (senza "METRO ")
      compare come parola intera nel testo di un avviso sugli ascensori; tutta la
      fermata è esclusa anche se è fermo un solo ascensore ("Vinzaglio esterno");
    - ricerca con `single_source_dijkstra`; all'arrivo si tiene il migliore tra
      "sceso in fermata" e "arrivato a piedi".
18. **Livello 4: mappa e prossime partenze** (i primi quattro punti decisi da
    PubblicaMente il 23/11/2026; gli ultimi due, proposti da Claude, approvati da
    PubblicaMente il 24/11/2026 dopo la scrittura del codice):
    - partenza e arrivo si scelgono cercando il nome della fermata, con i
      suggerimenti mentre si scrive;
    - prossime partenze: orario statico dopo l'istante simulato più il ritardo del
      feed dove c'è (la metro non ha dati real-time). Il ritardo misurato a una
      fermata vale anche per le successive (regola GTFS-Realtime); se una corsa ha
      misure solo per fermate dopo quella cercata, il mezzo è già passato;
    - mappa: Leaflet e tessere OpenStreetMap da internet (durante la demo serve la
      connessione);
    - la correzione dell'attesa del percorso con le partenze vere è un passo a parte,
      dopo il livello 4;
    - Leaflet alla versione 1.9.4;
    - struttura: `api.py` (FastAPI) carica tutto all'avvio e risponde a `/api/stato`,
      `/api/fermate`, `/api/percorso`, `/api/partenze`; la pagina sta in `frontend/`
      (`index.html`, `stile.css`, `app.js`, senza framework).

## Insidie verificate nei dati

- **Join veicoli-categorie**: in `vehicles.txt` la categoria è scritta `105`, in
  `vehicle_categories.txt` è `105U`. Senza aggiungere la "U" il collegamento trova
  0 veicoli su 1.209; con la "U" li trova tutti.
- **`wheelchair_boarding`** in `stops.txt`: 0 significa "nessuna informazione", non
  "non accessibile" (specifica GTFS). Valori: 3.796 fermate a 1 (accessibile), 3.254
  a 0, 3 a 2 (non accessibile), 2 vuote.
- **`stop_attributes.txt`** contiene solo `stop_id` e `stop_city`: utile per filtrare
  per comune, non contiene dati di accessibilità.
- **vehicle_position**: 15 veicoli con coordinate (0,0) e 44 senza `trip_id`. I due
  gruppi si sovrappongono: 9 veicoli sono in entrambi (confrontando l'id dell'entità
  con il `vehicle.id` senza la "U"). Gestione: decisione 16.
- **vehicle_position**: il veicolo 9483U è assegnato alla linea `FLEU`, che non
  esiste in `routes.txt`. Gestione: decisione 16.
- **alerts**: 93 riferimenti a fermate inesistenti nel GTFS statico, corrispondenti a
  53 `stop_id` distinti (errore E011 del validatore). Gestione: decisione 16.
- **alerts**: 6 avvisi hanno una data di fine molto lontana (tra il 2033 e il 2035).
  Si trattano come "fino a nuovo avviso" (decisione 16). Indizio a favore: tra questi
  c'è l'avviso dell'ascensore di Vinzaglio (dal 18/11/2026 ore 10:00 al 15/10/2035).
  La durata da sola non basta a riconoscerli: metà degli avvisi dura circa un anno.
- **alerts**: alcuni avvisi non citano linee o fermate ma un'intera azienda
  (`agency_id`: U, E, F, T). Sono avvisi generali, come lo sciopero del 20/11: per
  collegarli alla rete urbana va letto anche `agency_id`.
- **trip_update**: nel dump testuale compare un campo non riconosciuto, numero 4,
  dentro `vehicle` (valore 2 in 308 casi, 3 in 121).
- **stop_times.txt** pesa circa 113 MB: conviene filtrarlo prima dell'uso nella demo.
- **Sensi di marcia**: le fermate di bus e tram di solito sono diverse nei due sensi
  (una per lato della strada), quelle della metro sono le stesse. Se il grafo unisce i
  due sensi, un percorso "senza cambi" può arrivare al capolinea e tornare indietro, e
  alla metro i passaggi si contano due volte (attesa dimezzata). Per questo in
  `rete.py` c'è un grafo per linea e senso di marcia (`direction_id`).
- **Varianti di percorso**: 133 coppie linea/senso su 249 hanno corse con percorsi
  diversi (deviazioni, corse limitate) e il grafo della linea le unisce. Un
  collegamento nel grafo non garantisce che una corsa lo faccia: tempo e attesa si
  calcolano sulle sole corse che passano prima dall'origine e poi dalla destinazione.
- **Ascensori della metro**: l'avviso "Situazione aggiornata ascensori metro" è
  collegato a tutte le 23 fermate della metro; quale ascensore è fermo lo dice solo il
  testo ("Vinzaglio esterno"). Usare i collegamenti dell'avviso escluderebbe tutta la
  metro. Gestione: decisione 17.
- **Cambi a piedi**: il GTFS non ha `transfers.txt` né `pathways.txt`, quindi i
  cambi a piedi si calcolano dalle coordinate delle fermate (decisione 17).
- **Accessibilità**: 3.727 fermate urbane su 3.730 hanno `wheelchair_boarding` = 1,
  quindi il dato che distingue davvero è quello delle corse (`wheelchair_accessible`
  = 2 per 10.404 corse su 57.332).
- **Orari dopo mezzanotte**: 47.758 righe di `stop_times.txt` della rete urbana (47.783
  in tutto il file) hanno un orario dalle 24:00:00 in su (massimo "26:55:00"): si
  convertono in secondi a mano, non con le funzioni delle date.
- I collegamenti principali funzionano: i 429 `trip_id` di trip_update esistono tutti
  in `trips.txt`, i 417 veicoli di vehicle_position esistono tutti in `vehicles.txt`.

## Copertura dei dati per tipo di mezzo

Conteggi sulla fotografia del 18/11/2026.

| Mezzo | Linee | Posizioni real-time | Ritardi real-time | Avvisi (riferimenti a linee) |
|---|---|---|---|---|
| Bus urbani | 129 | 329 | 342 | 85 |
| Tram urbani | 8 | 87 | 87 | 5 |
| Metro M1 | 1 | 0 | 0 | 1 |
| Bus extraurbani | 73 | 0 | 0 | 55 |
| Servizi turistici (tra cui la cremagliera di Superga) | 4 | 0 | 0 | 3 |

- La metro non ha dati real-time in questa fotografia. L'assenza è da confermare con un
  secondo scaricamento in un altro orario; la gestione è già decisa (decisione 6).
- 1 veicolo e 7 riferimenti negli avvisi indicano linee che non esistono in
  `routes.txt`.

## Spunti per la demo

Avvisi reali presenti nel feed alerts del 18/11/2026:
- "Situazione aggiornata ascensori metro": fuori servizio Vinzaglio esterno.
- "Sciopero nazionale di 24 ore" previsto venerdì 20 novembre 2026.
- 88 avvisi di deviazione, 18 con causa "lavori".

## Piano

Proposto da Claude e confermato da PubblicaMente il 20/11/2026: livelli, test di ogni
livello e struttura dei file. Le scelte tecniche sono nelle "Decisioni in vigore".

Il codice si scrive a passi piccoli. Per ogni passo: spiegazione, codice e test,
revisione esterna, controllo di PubblicaMente, aggiornamento di storico e report,
commit con il via libera del gruppo.

### Sviluppo a livelli

Ogni livello funziona da solo: se ci si ferma a metà, la demo gira comunque.

| Livello | Cosa si costruisce | Quando è "fatto" (test) |
|---|---|---|
| 1. Dati | Caricamento GTFS della rete urbana; lettura dei `.bin` con `gtfs-realtime-bindings`; join delle categorie con la "U"; gestione delle altre insidie (decisione 16) | I conteggi tornano con quelli di questo storico |
| 2. Grafo, linee dirette | Grafo delle fermate e percorso senza cambi | Su 3-4 coppie di fermate scelte a mano esce la linea giusta |
| 3. Cambi e criteri | Archi a piedi, penalità sui cambi, criterio accessibile | Il percorso accessibile evita la fermata metro con l'ascensore fuori servizio (Vinzaglio) |
| 4. Mappa | Pagina web con Leaflet, percorso disegnato, prossime partenze | Una persona del gruppo usa la pagina senza aiuto |
| 5. Segnalazioni e db | Form cittadino/operatore, salvataggio in SQLite, ricalcolo del percorso | Una segnalazione fa cambiare il percorso |
| 6. AI | Nodi LangGraph con Qwen3 4B: estrazione, validazione, spiegazione (decisione 11) | Su 10 segnalazioni di prova (inventate, dichiarate come tali): JSON valido e campi corretti |
| 7. Pitch | Scaletta di 3 minuti e demo provata | Prova a tempo |

Tra il livello 4 e il livello 5 c'è un passo in più: l'attesa del percorso calcolata
con le prossime partenze vere (decisione 18).

Passi del livello 1:

| Passo | File | Cosa fa |
|---|---|---|
| 1.1 | `dati_gtfs.py` | Lettura dallo zip (senza estrarlo) e filtro sulla rete urbana |
| 1.2 | `dati_gtfs.py` | Servizi attivi in una data (`calendar` + `calendar_dates`) |
| 1.3 | `dati_realtime.py` | Lettura dei `.bin` con `gtfs-realtime-bindings`; test che tutte le 429 corse di trip_update siano attive il 18/11/2026 |
| 1.4 | entrambi | Insidie: categorie con la "U", veicoli a (0,0) e senza `trip_id`, linea `FLEU`, avvisi, stazioni madre |

### Struttura dei file

Ripresa da Salus Levante per le parti che lì esistono (`api.py`, `frontend/`,
`tests/`). Il file della rete si chiama `rete.py` e non `grafo.py`, per non
confonderlo con il grafo di LangGraph. Il flusso AI sta in `flusso_ai.py` e non in
`agenti.py`, perché la decisione 11 usa nodi fissi e non agenti.

```
PubblicaMente/
  Datasets/              dati GTT (esistente)
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
  REPORT_PROGETTO.md     sintesi per il gruppo e per altri assistenti AI
```

## Punti aperti

- Versione del modello: Jadio (scelta attuale) o ufficiale (proposta di Claude). Il
  modello Jadio è stato scaricato e provato sul PC di sviluppo il 20/11/2026; va
  ancora scaricato sul PC della demo.
- `carica_ritardi` per ora non gestisce fermate senza
  `stop_sequence` (darebbero 0), fermate indicate solo con `stop_id`, orari di
  partenza (`departure`) e fermate saltate (`schedule_relationship`). Nel feed del
  18/11 non ce ne sono (verificato in revisione). Il livello 4 non l'ha risolto:
  `prossime_partenze` unisce i ritardi agli orari con `trip_id` e `stop_sequence`. Da
  riprendere se si usano altri feed.
- Attesa alla fermata: nel livello 2 è la metà dell'intervallo medio tra le corse
  utili di tutta la giornata, quindi di pomeriggio può essere diversa da quella vera.
  Da affinare con una fascia oraria intorno all'orologio simulato o con le prossime
  partenze vere.
- Una linea con una sola corsa utile al giorno tra due fermate non ha un'attesa
  stimabile e per ora non compare tra i percorsi diretti.
- Livello 3, attesa per sequenza di fermate: dove passano più varianti della stessa
  linea l'attesa è sovrastimata (il 20 da 1629 a 658 dà un tempo totale più alto del
  livello 2; un test fissa il limite) e 72 delle 519 sequenze, quelle con una sola
  corsa al giorno, non si possono prendere. Stima prudente scelta da
  PubblicaMente: da risolvere con le prossime partenze vere dopo l'istante
  dell'orologio simulato (passo dopo il livello 4, decisione 18).
- Livello 3, fermata senza ascensore: la regola del nome nel testo sbaglia se il
  nome di una fermata è anche una parola comune ("gli ascensori sono fermi" farebbe
  uscire METRO FERMI). Da sostituire con l'estrazione fatta dal modello (livello 6).
- Livello 3, penalità dei cambi: colpisce anche la prima salita, quindi avvantaggia
  di 15 minuti un percorso fatto solo a piedi (al massimo 300 m). Nessun caso reale
  trovato in cui cambi il risultato.
- `stop_attributes.txt`: con il filtro sulla rete urbana non serve più per filtrare
  per comune. Da decidere se tenerlo (per esempio per mostrare il comune della
  fermata) o spostarlo tra i file da ignorare.
- Login: utenti già nel database o da creare.
- Le fonti elencate nella chat con Gemini (nel docx) non sono verificate: controllare
  ogni fonte prima di usarla.
- Livello 4, test di accettazione: una persona del gruppo deve usare la pagina senza
  aiuto. Non ancora fatto.
- Livello 4, memoria: la rete occupa molta RAM. Sul PC di sviluppo (7,3 GB) la suite
  completa è andata in `MemoryError`. La causa principale, la rete costruita due
  volte, è corretta con `tests/conftest.py`; resta il rischio con molti programmi
  aperti. Da verificare sul PC della demo; se serve, leggere da `stop_times.txt` solo
  le colonne utili.
- Livello 4, ricerca delle fermate: mette prima i nomi che iniziano con il testo
  cercato, ma "METRO FERMI" non inizia con "fermi" e può finire più in basso.

## Diario

### 19/11/2026
- Lettura della cartella: traccia, schede dei dataset, GTFS statico e feed real-time.
- Analisi dei dati e verifica dei collegamenti tra i file.
- Concordate da PubblicaMente le priorità dei dati e la libreria per i `.bin`.
- Decisioni di contesto: lavoro di gruppo, modello AI in locale, git più avanti, nessun
  limite di 4 ore, solo Torino.
- Creato questo storico, su richiesta di PubblicaMente.
- Analisi della copertura dei dati per tipo di mezzo; proposto il filtro sulla rete
  urbana.
- Ricevuto lo scheletro del progetto e concordate le modifiche (AI, collegamento tra i
  rami, scioperi dal feed, ruoli cittadino e operatore, accessibilità). Login da
  definire, si può simulare.
- Scelto il calcolo del percorso con la rete come grafo; criteri tutti opzionali.
- Confermati come decisioni: bus, tram e metro come mezzi; attesa media pari a metà
  della frequenza; ascensori fuori servizio nel criterio accessibile; posizioni e
  ritardi dei mezzi presentati come dati del 18/11, non live.
- Decisi: solo rete urbana (bus urbani, tram, metro); per la metro prossime partenze
  dall'orario statico, quindi calendar e calendar_dates passano a priorità alta.
- Creato lo schema rivisto `schema_EasyWay_rivisto.png` da condividere nel gruppo.
- Deciso da PubblicaMente: "Scioperi" resta tra i casi di segnalazione (per esempio
  da operatore), oltre che dal feed ufficiale.
- Deciso da PubblicaMente: chiusa la fase Explore del metodo EPCC, si passa al Plan.
- Deciso da PubblicaMente: modello locale Qwen3-4B-Instruct-2507 Q4_K_M, versione
  `Jadio/Qwen3_4b_instruct_q4km`. Proposta di Claude, da decidere nel gruppo: la
  versione ufficiale `qwen3:4b-instruct-2507-q4_K_M`.
- Deciso da PubblicaMente: FastAPI + pagina web, SQLite, LangGraph con agenti,
  notebook per esplorare e `.py` per l'app.
- Scritta la bozza del piano a livelli, con le proposte di Claude da confermare.
- Precisata la decisione 7: motivazioni attribuite a PubblicaMente, proposta di
  Claude distinta dalla scelta del gruppo.
- Deciso da PubblicaMente: prossime partenze per tutti i mezzi (con ritardo per bus e
  tram), orologio simulato al 18/11/2026 ore 15:50, LangGraph a nodi fissi (cambia
  la decisione 11, che prima diceva "LangGraph con agenti").
- Corretto il riferimento a Salus Levante: lì esistono `api.py`, `frontend/` e
  `tests/`, ma non `db.py` e `config.py`, e non c'è una mappa Leaflet.

### 20/11/2026
- Proposto da Claude nella struttura dei file: `rete.py` al posto di `grafo.py` e
  `flusso_ai.py` al posto di `agenti.py`, per evitare nomi che confondono.
- La regola "un solo agente con 2-3 strumenti" è segnata come proposta di Claude.
- Aggiunti ai punti aperti: gestione dei veicoli a (0,0) e senza `trip_id`, verifica
  delle date di fine lontane negli avvisi.
- Su richiesta di PubblicaMente, creato `REPORT_PROGETTO.md`: sintesi aggiornata del
  progetto per i componenti del gruppo e per gli assistenti AI a cui lo danno, in
  vista della pubblicazione su GitHub.
- Deciso da PubblicaMente: le regole di stile del codice diventano comuni a tutto il
  gruppo (decisione 13).
- Deciso da PubblicaMente: il progetto va su GitHub subito (cambia la decisione 8, che
  diceva "si configura più avanti").
- Primo test del modello: risposta corretta in italiano, ma al 100% sulla CPU, perché
  il PC usato per lo sviluppo non ha una GPU dedicata (solo grafica integrata, 7,3 GB
  di RAM). Deciso da PubblicaMente: la demo girerà sul PC con la RTX A500.
- Precisato che si parla di "ascensori metro" nelle modifiche allo schema (come nel
  report) e, nella decisione 7, che la GPU da 4 GB è quella del PC della demo.
- Preparato il repository git locale con `.gitignore` e `.gitattributes`.
- Pubblicato su GitHub il repository privato `PubblicaMente-Easyway` (primo commit
  `ffad9ff`). Chiusa la fase Commit del primo giro EPCC.
- Deciso da PubblicaMente: piano confermato, si passa alla fase Code a passi piccoli;
  venv del progetto con `requirements.txt` comune (decisione 14).
- Passo 1.1: scritti `dati_gtfs.py`, `tests/test_dati_gtfs.py`, `requirements.txt` e
  `pytest.ini` (i test partono sia con `pytest` sia con `python -m pytest`). Rete
  urbana: 138 linee, 57.332 corse su 60.267, 1.705.141 orari, 3.730 fermate su 7.055.
- Commit del passo 1.1: `f2ab62a`.
- Deciso da PubblicaMente: per ora non si salva la rete filtrata in un file veloce
  (proposta di Claude: Parquet). Il caricamento completo dura 35-70 secondi; l'idea
  resta disponibile se l'attesa diventa un problema.
- Passo 1.2: aggiunte a `dati_gtfs.py` le funzioni `carica_servizi_attivi(data)` e
  `filtra_corse_del_giorno(corse, data)`, con i test in `tests/test_calendario.py`.
  Risultati: il 18/11/2026 sono attivi 125 servizi in tutto il GTFS; sulla rete urbana
  corrispondono a 11.785 corse, e tra queste ci sono tutte le 429 corse del feed
  trip_update; domenica 22/11 le corse sono 6.534. In `calendar_dates.txt` GTT ripete
  come "aggiunta" quasi tutte le date già previste da `calendar.txt`; le eccezioni che
  cambiano davvero qualcosa sulla rete urbana sono 55 rimozioni e 14 aggiunte
  (esempio: l'8/12/2026 il servizio feriale `717657U` è tolto e il festivo `717699U`
  è aggiunto).
- Commit del passo 1.2: `bf2acc1`.
- Passo 1.3: installata `gtfs-realtime-bindings` 3.0.0 (nessun'altra libreria
  cambiata) e aggiunta a `requirements.txt` insieme a `protobuf` 7.36.2. Scritto
  `dati_realtime.py` con cinque funzioni: `leggi_feed`, `carica_posizioni`,
  `carica_ritardi`, `carica_avvisi`, `carica_elementi_degli_avvisi`; test in
  `tests/test_dati_realtime.py`. I dati si leggono così come sono: la pulizia è il
  passo 1.4. Risultati: 417 posizioni, 2.439 righe di ritardi su 429 corse (1.672 con
  il ritardo in secondi, 767 con l'orario previsto), 134 avvisi con 8.854 elementi
  coinvolti. Tutte le 429 corse dei ritardi sono attive il 18/11/2026. Scoperti gli
  avvisi riferiti a un'intera azienda (`agency_id`) e l'indizio sulle date lontane
  (avviso di Vinzaglio).

### 21/11/2026
- Correzioni al passo 1.3 dopo la revisione, approvate da PubblicaMente:
  - colonne rinominate per non confonderle con quelle del GTFS statico:
    `arrival_timestamp` (orario previsto in secondi POSIX; nello statico
    `arrival_time` è un testo "HH:MM:SS") e `vehicle_timestamp` nelle posizioni;
  - inizio e fine degli avvisi letti con `HasField`, così un valore assente resta
    vuoto invece di diventare 0 (cioè il 1970);
  - colonne fisse per ogni tabella, così un feed vuoto dà una tabella vuota ma valida;
  - tre test in più: ogni riga dei ritardi ha esattamente una forma di ritardo; le 47
    righe con ritardo 0 restano 0 e la colonna è di tipo `Int64`; ogni avviso ha
    inizio e fine.
- Suite completa: 27 test passati.
- Commit del passo 1.3: `caab472`.
- Passo 1.4: aggiunte a `dati_gtfs.py` le funzioni `carica_veicoli` (1.209 veicoli,
  tutti con la categoria) e `carica_stazioni_madre` (METRO PORTA SUSA -> STAZIONE
  PORTA SUSA, METRO PORTA NUOVA -> STAZIONE PORTA NUOVA); a `dati_realtime.py`
  `prepara_posizioni_per_la_mappa` (402 posizioni su 417, `FLEU` come linea
  sconosciuta), `filtra_avvisi_attivi` (134 su 134 alle 15:50 del 18/11) e
  `togli_fermate_inesistenti` (93 riferimenti tolti). In tutte le funzioni di lettura
  si tengono solo le entità del tipo atteso (`HasField`). Creato `config.py` con
  l'orologio simulato; l'orario dei feed (14:50 UTC) conferma le 15:50 italiane.
- Chiusi i punti aperti del passo 1.4 (decisione 16).
- Livello 2: scritto `rete.py` con `tests/test_rete.py`. Un grafo per linea e senso di
  marcia sulle corse del 18/11/2026: 249 grafi, 7.971 tratte. `trova_percorsi_diretti`
  dà le linee senza cambi, dalla più veloce. Verificato su tram 4 (Ulivi -> Lauro
  Rossi), bus 2 (Canelli -> Tazzoli), metro (Fermi -> Porta Nuova nei due sensi,
  Bengasi -> Lingotto). Nella prima versione i due sensi di marcia erano uniti:
  corretto prima della revisione (vedi "Sensi di marcia" tra le insidie).
- Correzioni dopo la revisione del codice:
  - approvata da PubblicaMente: il grafo unisce le varianti di una linea, quindi da
    solo può proporre collegamenti che nessuna corsa fa (esempio: il 10 da 2745 a
    2198). Ora `trova_percorsi_diretti` usa il grafo solo per scartare le linee
    impossibili, poi tiene le corse del giorno che passano prima dall'origine e poi
    dalla destinazione, e su quelle calcola tempo, fermate e attesa. Così l'attesa non
    conta più le corse che non arrivano a destinazione (il 20 da 608 a 8833: attesa
    di 187 minuti con 2 corse utili, prima risultava di 14 minuti);
  - basse, applicate direttamente: un avviso senza inizio o senza fine vale "senza
    limite" da quel lato; nelle linee circolari una corsa che passa due volte dalla
    stessa fermata conta una volta sola.
- Aggiunti ai punti aperti, per il livello 2: l'attesa media su tutta la giornata e le
  linee con una sola corsa utile.
- Correzioni dopo la revisione dei documenti: unità e ambito del conteggio degli
  orari dopo mezzanotte; ordine e venv nella sezione "Come eseguire" del report;
  stato "in revisione" nel report finché il passo 1.4 e il livello 2 non sono
  committati; nuova insidia "Varianti di percorso"; punti aperti sull'attesa riferiti
  alle corse utili; tolto il conteggio delle attese, che non si precalcolano più;
  decisione 16 riformulata (riferimenti tolti, punto dei passi 1.3-1.4); nota
  sull'applicazione della decisione 3 nel livello 2.
- Correzione dopo la revisione finale del codice, approvata da PubblicaMente: le
  fermate mostrate sono quelle della corsa con il tempo di viaggio mediano, non della
  prima corsa del giorno (il 35 da 3031 a 3738 mostrava le 40 fermate delle corse
  delle 4 del mattino, mentre 86 corse su 88 ne fanno 10).
- Suite completa: 50 test passati.
- Commit del passo 1.4 e del livello 2: `51cdde2`.

### 23/11/2026
- Stato del report aggiornato: passo 1.4 e livello 2 committati.
- Esplorazione per il livello 3: nel GTFS mancano `transfers.txt` e `pathways.txt`;
  l'avviso degli ascensori è collegato a tutte le 23 fermate della metro, ma solo il
  testo dice quale ascensore è fermo ("Vinzaglio esterno"); 3.727 fermate urbane su
  3.730 risultano accessibili, mentre 10.404 corse su 57.332 hanno
  `wheelchair_accessible` = 2; il 18/11 le corse formano 513 sequenze di fermate
  diverse contando solo le fermate (519 contando anche linea e senso, come nella
  decisione 17).
- Decise da PubblicaMente per il livello 3: nodi per sequenza di fermate; fermata
  senza ascensore riconosciuta dal suo nome nel testo dell'avviso; cambi a piedi entro
  300 m in linea d'aria a 1 m/s; il criterio accessibile esclude le fermate con
  `wheelchair_boarding` = 2, le corse con `wheelchair_accessible` diverso da 1 e le
  fermate senza ascensore segnalate dagli avvisi.
- Livello 3 in `rete.py`: `costruisci_grafo_con_cambi` (21.049 nodi, 76.463 archi il
  18/11, 519 sequenze di fermate contando linea e senso) e `trova_percorso` con i tre
  criteri; in `dati_realtime.py` `trova_fermate_senza_ascensore`, che il 18/11 trova
  solo METRO VINZAGLIO. Test di accettazione superato: dalla fermata bus 3171
  (Vinzaglio) a METRO PORTA NUOVA il percorso più veloce prende la metro a
  Vinzaglio (5,8 minuti), quello accessibile cammina fino a Porta Susa (10,5
  minuti). Una ricerca dura 0,2-0,3 secondi.
- Difetto trovato provando il codice e corretto: senza un limite, Dijkstra metteva in
  fila molte camminate (da 601 a 1256, con meno cambi, 15 tratti a piedi); ora c'è
  il nodo "a_piedi".
- Correzioni dopo la revisione del codice:
  - basse, applicate direttamente: si cammina anche da e verso le 30 fermate senza
    corse il 18/11; la penalità sulla prima salita è dichiarata come limite noto;
  - approvate da PubblicaMente: il nome della fermata si confronta come parola
    intera; l'attesa per sequenza resta (stima prudente) ed è nei punti aperti, con
    un test che fissa il limite.
- Approvate da PubblicaMente dopo la scrittura del codice, perché scelte da Claude
  senza chiedere prima: penalità di 15 minuti a ogni salita per "meno cambi", "più
  veloce" come criterio predefinito, nodo "a_piedi".
- Correzioni dopo la revisione dei documenti: conteggi delle sequenze (513 e 519)
  spiegati; tipi di nodo citati anche nella decisione 3; insidia "Cambi a piedi" a
  parte; frasi più chiare sui valori scelti dal gruppo e sull'esempio di "fermi".
- Seconda revisione del codice: aggiunto il test sulla partenza da una fermata senza
  corse (211).
- Suite completa: 63 test passati.
- Commit del livello 3: `b87c154`.
- Decise da PubblicaMente per il livello 4: ricerca delle fermate per nome;
  partenze dall'orario più il ritardo; correzione dell'attesa in un passo a parte;
  mappa con internet (decisione 18).

### 24/11/2026
- Livello 4 diviso in tre passi: 4.1 prossime partenze in `rete.py`
  (`calcola_ritardi_misurati`, `ritardo_alla_fermata`, `prossime_partenze`); 4.2
  `api.py` con FastAPI; 4.3 pagina in `frontend/` con Leaflet. Aggiunto `httpx` a
  `requirements.txt`, serve al `TestClient` dei test dell'API.
- Verificato sui dati: le 2.439 righe dei ritardi trovano tutte la loro fermata in
  `stop_times`; i ritardi ricavati dagli orari previsti vanno da circa -15 a +13
  minuti, con mediana negativa (molti mezzi in anticipo). Alla fermata 3171
  (Vinzaglio) il primo mezzo è il 68 delle 15:58, previsto alle 15:54.
- Problema di memoria: la suite completa andava in `MemoryError`, perché la rete si
  costruiva due volte (in `api.py` e nei test) e il PC aveva quasi esaurito la
  memoria virtuale. Ora `tests/conftest.py` ha una sola rete per tutti i test, quella
  di `api.py`. Chiusi i programmi pesanti, la suite passa.
- Correzioni dopo la revisione del codice:
  - approvate da PubblicaMente: il ritardo mostrato è la differenza tra i minuti
    dei due orari mostrati (alla 3172 si leggeva "16:28 -> 16:25 (-2 min)"); i nomi
    nei tooltip della mappa sono protetti come nel pannello; gli errori del server
    nei suggerimenti e nelle partenze mostrano un messaggio;
  - basse, applicate direttamente: virgolette protette negli attributi HTML;
    risposte vecchie delle partenze ignorate; messaggio dedicato se partenza e arrivo
    coincidono; ricerca ordinata sulla parte del nome dopo "Fermata NNN - ".
- Approvate da PubblicaMente dopo la scrittura del codice, perché scelte da Claude
  senza chiedere prima: struttura di `api.py` con i quattro endpoint, pagina in
  `frontend/` senza framework, Leaflet 1.9.4.
- Correzioni dopo la revisione dei documenti: attribuzione della decisione 18;
  punti aperti su `carica_ritardi` e sull'attesa non più rimandati al livello 4;
  data del report; nota sul passo in più nel piano; causa del `MemoryError` precisata
  nei punti aperti.
- Suite completa: 76 test passati.
- Estensione Livello 4 (Antigravity, su `api.py`, `frontend/` e `tests/test_api.py`):
  - aggiunti `GET /api/veicoli` (402 posizioni filtrate da `(0,0)`, con `FLEU` etichettata `"linea sconosciuta"`) e `GET /api/avvisi` (avvisi attivi della rete urbana filtrati con `togli_fermate_inesistenti` e dicitura `"Fino a nuovo avviso"` per scadenze 2033-2035);
  - esteso `GET /api/percorso` con il parametro `criterio` (`piu_veloce`, `meno_cambi`, `accessibile`) mantenendo la retrocompatibilità con i flag booleani, e reso opzionale `testo` su `GET /api/fermate` per ottenere l'elenco completo delle 3.730 fermate urbane;
  - aggiornata la pagina `frontend/` con selettore `criterio`, layer dei veicoli della fotografia 18/11/2026 15:50 attivabile da pannello e sezione dedicata agli avvisi attivi della rete urbana;
  - aggiunti 3 test in `tests/test_api.py`. Suite completa eseguita con il venv di `PubblicaMente-Easyway-main_parte1`: 79 test passati in 28,30 s.
