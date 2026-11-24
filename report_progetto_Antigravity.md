# Report di Progetto - EasyWay (PubblicaMente)
*Documento di sintesi tecnica e stato avanzamento a cura di Antigravity*

- **Data aggiornamento**: 24/11/2026
- **Stato completamento**: **Livello 4 completato e verificato** (79/79 test passati in 28,30 s)
- **Riferimento orologio simulato**: 18/11/2026 ore 15:50 (UTC+1)

---

## 1. Stato e Decisioni Rispettate

Prima di intervenire sul Livello 4 sono stati verificati i vincoli di [.antigravity/rules.md](file:///c:/Users/spine/OneDrive/Desktop/PubblicaMente-Easyway-main/.antigravity/rules.md), [REPORT_PROGETTO.md](file:///c:/Users/spine/OneDrive/Desktop/PubblicaMente-Easyway-main/REPORT_PROGETTO.md) e [STORICO.md](file:///c:/Users/spine/OneDrive/Desktop/PubblicaMente-Easyway-main/STORICO.md):

1. Nel repository erano già presenti [api.py](file:///c:/Users/spine/OneDrive/Desktop/PubblicaMente-Easyway-main/api.py), `frontend/` (`index.html`, `stile.css`, `app.js`) e [tests/test_api.py](file:///c:/Users/spine/OneDrive/Desktop/PubblicaMente-Easyway-main/tests/test_api.py) con [tests/conftest.py](file:///c:/Users/spine/OneDrive/Desktop/PubblicaMente-Easyway-main/tests/conftest.py) (che condivide una sola istanza di `rete` in memoria per evitare `MemoryError` su PC con 8 GB di RAM).
2. Per rispettare le decisioni marcate **DECISO** (`api.py`, nomi in italiano, Leaflet 1.9.4, niente emoji nel codice, orologio simulato al 18/11/2026 15:50, immagine statica dichiarata come fotografia reale), si è estesa la base esistente senza duplicare il caricamento della rete.

---

## 2. Modifiche Effettuate nel Dettaglio (Livello 4)

### A. Backend FastAPI ([api.py](file:///c:/Users/spine/OneDrive/Desktop/PubblicaMente-Easyway-main/api.py))
- **`GET /api/fermate`**: reso opzionale il parametro `testo`. Con `testo` valorizzato mantiene la ricerca ordinata (massimo 10 risultati, `[]` sotto 2 caratteri); senza `testo` restituisce tutte le 3.730 fermate urbane con coordinate `lat`/`lon`.
- **`GET /api/percorso`**: aggiunto il parametro `criterio` (`piu_veloce`, `meno_cambi`, `accessibile`) con validazione (422 su valori non ammessi), mantenendo la retrocompatibilità con i flag booleani `meno_cambi` e `accessibile`.
- **`GET /api/veicoli`**: espone le 402 posizioni filtrate tramite `dati_realtime.prepara_posizioni_per_la_mappa` (esclusi `(0.0, 0.0)`, inclusi i veicoli senza `trip_id`, linea `FLEU` etichettata `"linea sconosciuta"`), con filtro opzionale per `linea`.
- **`GET /api/avvisi`**: espone gli avvisi attivi alle 15:50 del 18/11/2026 pertinenti alla rete urbana (`agency_id == "U"`, linee o fermate urbane), puliti con `dati_realtime.togli_fermate_inesistenti` rispetto a `stops.txt`. Le scadenze tra il 2033 e il 2035 vengono rese come `"Fino a nuovo avviso"`.

### B. Frontend Leaflet ([index.html](file:///c:/Users/spine/OneDrive/Desktop/PubblicaMente-Easyway-main/frontend/index.html), [stile.css](file:///c:/Users/spine/OneDrive/Desktop/PubblicaMente-Easyway-main/frontend/stile.css), [app.js](file:///c:/Users/spine/OneDrive/Desktop/PubblicaMente-Easyway-main/frontend/app.js))
- Sostituite le checkbox dei criteri con il selettore `<select id="criterio">` (`piu_veloce`, `meno_cambi`, `accessibile`).
- Aggiunto layer mappa per i veicoli della fotografia del 18/11/2026 15:50 con checkbox di attivazione `#mostra-veicoli` e tooltip sicuri (`testoSicuro`).
- Aggiunta nel pannello laterale la sezione `#sezione-avvisi` con il conteggio e l'elenco degli avvisi urbani attivi.
- Mantenuti disegno differenziato delle tratte (`mezzo` blu continuo vs `a_piedi` grigio tratteggiato) e tabella delle prossime partenze al clic su fermate e marker.

### C. Verifica e Test ([tests/test_api.py](file:///c:/Users/spine/OneDrive/Desktop/PubblicaMente-Easyway-main/tests/test_api.py))
- Aggiunti 3 nuovi test API:
  - `test_elenco_completo_fermate_e_criterio`: verifica le 3.730 fermate, i criteri `piu_veloce` e `accessibile` (esclusione `3632` Vinzaglio) e l'errore `422` su criterio non valido.
  - `test_veicoli_per_mappa`: verifica 402 posizioni, assenza di `(0.0, 0.0)` e gestione di `FLEU` come `"linea sconosciuta"`.
  - `test_avvisi_urbani`: verifica la presenza degli avvisi urbani attivi, incluso ascensore Vinzaglio, avviso aziendale (`azienda_intera`) e scadenza `"Fino a nuovo avviso"`.
- **Nota ambiente**: nella cartella corrente non è presente `.venv`; la suite completa è stata eseguita con il Python dell'ambiente virtuale di `PubblicaMente-Easyway-main_parte1`.
- **Risultato**: **79 test passati su 79 in 28,30 secondi**.

---

## 3. Schema Pronto per la Prossima Sessione (Livelli 5 e 6)

> Nota preliminare da Piano di Sviluppo: prima o in parallelo al Livello 5 resta previsto il passo intermedio di allineamento dell'attesa del percorso alle prossime partenze reali in `rete.py`, e la creazione della `.venv` locale con `pip install -r requirements.txt` nella root corrente.

### Schema Livello 5 — Segnalazioni, SQLite (`db.py`) e Ricalcolo

1. **Modulo `db.py` (`sqlite3`)**:
   - Tabelle:
     - `utenti(id INTEGER PRIMARY KEY, nome TEXT, ruolo TEXT CHECK(ruolo IN ('cittadino', 'operatore')))` — pre-popolata con utenti demo sintetici (nessun dato personale reale).
     - `segnalazioni(id INTEGER PRIMARY KEY, utente_id INTEGER, ruolo TEXT, categoria TEXT, linea TEXT, stop_id TEXT, descrizione TEXT, creata_il TEXT, validata INTEGER, stato TEXT)` dove `categoria` in `('incidente', 'lavori', 'sciopero', 'guasto_mezzi', 'altro')`.
   - Funzioni in italiano: `inizializza_db(percorso_db)`, `salva_segnalazione(...)`, `elenca_segnalazioni_attive(...)`, `aggiorna_stato_segnalazione(...)`.
   - Regola validazione per ruolo: le segnalazioni da `operatore` nascono già validate (`validata = 1`); quelle da `cittadino` restano in attesa di validazione (Livello 6 o conferma esplicita) prima di bloccare linee/fermate.
2. **Estensione `rete.py` e `api.py`**:
   - Aggiungere filtro dinamico su `trova_percorso(...)` (es. `linee_escluse=()`, `fermate_escluse=()`), così le segnalazioni validate e gli avvisi critici possono escludere temporaneamente linee o fermate colpite e produrre un percorso alternativo.
   - Endpoint FastAPI in `api.py`:
     - `GET /api/segnalazioni` (elenco segnalazioni salvate)
     - `POST /api/segnalazioni` (invio segnalazione da cittadino/operatore, salvataggio in `db.py` e ritorno stato)
     - `POST /api/percorso/ricalcola` (o parametro su `/api/percorso` che controlla se il percorso attivo tocca linee/fermate segnalate e restituisce `modificato`, `motivo` e `nuovo_percorso`).
3. **Frontend (`frontend/`)**:
   - Form segnalazione (ruolo cittadino/operatore, categoria, testo libero/linea/fermata) + pannello controllo percorso con notifica automatica di ricalcolo quando una nuova segnalazione validata impatta il tragitto scelto.
4. **Test (`tests/test_db.py` + `tests/test_api.py`)**:
   - Database temporaneo (`tmp_path`) in SQLite, salvataggio cittadino vs operatore, verifica che una segnalazione validata su una linea/fermata del percorso causi il ricalcolo di un itinerario alternativo.

### Schema Livello 6 — Orchestrazione AI con LangGraph a Nodi Fissi (`flusso_ai.py`)

1. **Configurazione LLM locale (`config.py`)**:
   - Collegamento a Ollama (`langchain-ollama`) con modello `Qwen3-4B-Instruct-2507` quantizzato Q4_K_M (`Jadio/Qwen3_4b_instruct_q4km` o `qwen3:4b-instruct-2507-q4_K_M` su GPU RTX A500 4 GB), `temperature=0` per output JSON deterministico.
2. **Grafo LangGraph a nodi fissi (`flusso_ai.py`)**:
   - Stato tipizzato `StatoSegnalazione` (`TypedDict`) con campi: `testo_originale`, `ruolo`, `categoria`, `linea`, `nome_fermata`, `stop_id`, `validata`, `motivo_validazione`, `percorso_precedente`, `percorso_ricalcolato`, `spiegazione`.
   - Sequenza lineare obbligatoria a 5 nodi fissi (nessun agente autonomo reattivo):
     1. `estrazione` (LLM): estrae JSON strutturato (`categoria`, `linea`, `fermata`, `effetto`) dal testo libero della segnalazione (e può essere riusato anche per l'estrazione delle fermate dagli avvisi ascensori al posto della regola testuale semplice).
     2. `validazione` (Python + LLM solo per supporto semantico): verifica corrispondenza di `linea` e `fermata` contro il GTFS urbano, incrocia con avvisi attivi e ritardi/posizioni real-time; per `operatore` valida direttamente, per `cittadino` assegna esito motivato.
     3. `salvataggio` (Python): persiste la segnalazione validata/non validata in SQLite tramite `db.py`.
     4. `ricalcolo` (puro codice Python via `rete.py`): se la segnalazione è validata e impatta il percorso corrente, ricalcola l'itinerario alternativo con `trova_percorso`.
     5. `spiegazione` (LLM): genera una spiegazione breve, chiara e fedele ai soli dati calcolati (zero dati inventati) sul perché il percorso è stato modificato o confermato.
3. **Integrazione API e Test (`tests/test_flusso_ai.py`)**:
   - Collegare `POST /api/segnalazioni` all'esecuzione di `flusso_ai.py` (con fallback sicuro se Ollama non è raggiungibile durante i test offline).
   - Test su almeno **10 segnalazioni sintetiche di prova** (dichiarate come tali), verificando schema JSON valido, campi coerenti, separazione dei nodi fissi e spiegazione coerente con i dati di `rete.py` tramite mock deterministico del modello nei test automatici + test manuale con Ollama attivo.
