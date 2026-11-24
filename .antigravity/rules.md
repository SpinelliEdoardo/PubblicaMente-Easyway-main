# Regole di Progetto - EasyWay (PubblicaMente)

Questo file definisce le istruzioni operative, lo stack tecnologico, lo stile di codice e i vincoli di dominio obbligatori per qualsiasi assistente AI e sviluppatore che lavora sul repository EasyWay.

---

## 1. Istruzioni Operative e Metodo di Lavoro

1. **Rispetto delle decisioni (DECISO vs PROPOSTA)**:
   - Le decisioni marcate come **DECISO** in `REPORT_PROGETTO.md` e `STORICO.md` sono definitive: **non modificarle, non disattenderle e non proporre alternative** a meno di richiesta esplicita dell'utente.
   - Le voci marcate come **PROPOSTA** sono ancora al vaglio: non considerarle definitive.
2. **Sviluppo incrementale (EPCC - Explore, Plan, Code, Commit)**:
   - Lavorare sempre a **piccoli passi modulari** (un livello/passo alla volta).
   - Per ogni passo: formulare la modifica, scrivere il codice con i relativi test unitari in `tests/`, verificare che l'intera suite pytest passi con successo.
3. **Nessuna invenzione di dati (No Hallucinations)**:
   - Non inventare numeri, fermate, soglie, endpoint o policy non presenti nei dataset o nella documentazione. Se un dato manca o non è verificato, dichiararlo chiaramente.
   - Vietato l'uso di dati personali reali: utilizzare esclusivamente dati aperti pubblici (GTT) o dati sintetici dichiarati come tali.
4. **Allineamento della documentazione**:
   - Ogni avanzamento deve essere documentato aggiornando:
     - `STORICO.md`: nuova voce in fondo alla sezione *Diario* e revisione delle *Decisioni in vigore* / *Punti aperti*.
     - `REPORT_PROGETTO.md`: aggiornamento sintetico dello stato, conteggi e fasi completate.
     - `report_progetto_Antigravity.md`: report di progetto dettagliato con anomalie riscontrate, modifiche effettuate e prossimi passi.

---

## 2. Stack Tecnologico e Dipendenze

Tutte le dipendenze devono rimanere allineate con `requirements.txt` (Python 3.12):

| Ambito | Libreria / Versione | Scopo / Note |
|---|---|---|
| **Linguaggio** | Python 3.12 | Ambiente virtuale standard |
| **Manipolazione Dati** | `pandas==3.1.1`, `numpy==2.5.4` | Elaborazione orari, filtri su GTFS e feed |
| **Grafi e Percorsi** | `networkx==3.7` | Modellazione della rete, algoritmi su grafi (Dijkstra) |
| **GTFS Real-time** | `gtfs-realtime-bindings==3.0.0`, `protobuf==7.36.2` | Lettura diretta dei file binari `.bin` |
| **API & Backend** | `fastapi==0.162.5`, `uvicorn==0.54.0`, `pydantic==2.14.3` | Servizi REST (previsto per livello 4+) |
| **Database** | `sqlite3` (built-in Python) | Salvataggio utenti e segnalazioni |
| **Orchestrazione AI** | `langgraph==1.2.16`, `langchain-core==1.6.12`, `langchain-ollama==1.1.0` | Grafo a **nodi fissi** (no agenti autonomi reattivi) |
| **Modello LLM** | Ollama locale: `Qwen3-4B-Instruct-2507` Q4_K_M (2,5 GB) | Ottimizzato per 4 GB VRAM GPU RTX A500 |
| **Testing** | `pytest==9.2.0` | Esecuzione test suite via `pytest.ini` (`pytest -v`) |
| **Frontend** | HTML5 nativo + JavaScript + Leaflet | Pagina web leggera per visualizzazione mappa e percorsi |

---

## 3. Stile del Codice e Convenzioni

1. **Nomenclatura in Italiano**:
   - Nomi di funzioni, variabili, costanti, parametri e file nuovi **devono essere in italiano** (es. `carica_linee_urbane`, `trova_percorsi_diretti`, `orario_in_secondi`, `tratte_medie`).
   - Eccezione ammessa unicamente per metodi, classi e attributi nativi delle librerie di terze parti o parametri del formato standard GTFS (es. `df.merge()`, `trip_id`, `route_id`).
2. **Semplicità e leggibilità**:
   - Codice procedurale o funzionale chiaro, "passo passo", senza eccessivi livelli di astrazione o metaprogrammazione non necessaria.
3. **Commenti mirati**:
   - Commentare solo quando necessario per spiegare il **perché** di una logica, un limite di business o un'insidia specifica del dataset.
4. **Niente Emoji**:
   - **Vietato inserire emoji nel codice sorgente**, nei commenti di codice o nelle stringhe di log/stampa interne.
5. **Tipizzazione e robustezza colonne**:
   - Per colonne numeriche che ammettono valori nulli, usare esplicitamente `Int64` (per non convertire interi con NaN in float, distinguendo il valore `0` da `assente/None`).
   - Gestire sempre il caso di feed real-time vuoto garantendo schema e tipi colonna stabili.
   - Orari GTFS oltre mezzanotte (es. `25:10:00`): convertire sempre in secondi assoluti tramite funzione ad hoc, senza usare parsing datetime standard.

---

## 4. Vincoli di Dominio e Insidie nei Dati (GTFS GTT)

Ogni modifica al codice deve rispettare le seguenti regole convalidate:

1. **Ambito di trasporto (Solo rete urbana)**:
   - Filtrare rigorosamente su `agency_id == "U"`: bus urbani, tram e metro M1.
   - Escludere bus extraurbani e linee turistiche (es. cremagliera di Superga).
2. **Orologio simulato**:
   - L'applicazione opera con riferimento temporale fissato in `config.py` al **18/11/2026 alle 15:50 (UTC+1)**. Non usare `datetime.now()` per valutare la validità dei dati o dei ritardi.
3. **Accessibilità**:
   - Nelle fermate GTFS, `wheelchair_boarding == 0` indica "nessuna informazione", non "non accessibile" (il valore non accessibile è `2`).
   - Il criterio accessibile deve escludere le fermate della metro con ascensori guasti identificate dagli avvisi (es. ascensore esterno stazione Vinzaglio M1).
4. **Join Categorie Veicoli**:
   - In `vehicles.txt` il campo categoria è scritto senza agenzia (es. `105`), mentre in `vehicle_categories.txt` è `105U`. Aggiungere sempre `"U"` (`+ AGENZIA_URBANA`) prima del join.
5. **Coordinate nulle e veicoli senza corsa**:
   - Escludere dalla mappa le coordinate `(0.0, 0.0)`.
   - Mantenere i veicoli privi di `trip_id`: la posizione è veritiera anche se la corsa non è identificata.
   - La linea `FLEU` non esiste a catalogo: deve essere etichettata come "linea sconosciuta".
6. **Avvisi e fermate inesistenti**:
   - Escludere dagli avvisi i riferimenti a `stop_id` non presenti in `stops.txt` (usando `togli_fermate_inesistenti`), preservando gli avvisi generali a livello di intera azienda (`agency_id`).
   - Gli avvisi con termine tra il 2033 e il 2035 vanno considerati validi "fino a nuovo avviso".
7. **Sensi di marcia e varianti di linea**:
   - Separare rigorosamente i grafi per coppia `(route_id, direction_id)`: non mescolare i due sensi di marcia.
   - Prima di restituire un percorso diretto, verificare che esistano corse utili nel giorno che tocchino sia origine che destinazione con `stop_sequence` crescente.
   - Per mostrare l'elenco fermate della linea, usare la corsa dal tempo di percorrenza **mediano/tipico** (non la prima corsa della giornata).
8. **Calcolo Attesa**:
   - Il tempo di attesa medio è calcolato come metà dell'intervallo medio tra le corse utili.
9. **Architettura AI (LangGraph a Nodi Fissi)**:
   - Il flusso LangGraph deve impiegare nodi fissi sequenziali: `estrazione` $\rightarrow$ `validazione` $\rightarrow$ `salvataggio` $\rightarrow$ `ricalcolo` $\rightarrow$ `spiegazione`.
   - Il calcolo dei percorsi rimane in puro codice Python; il modello LLM interviene solo dove serve comprensione o generazione di linguaggio naturale.
