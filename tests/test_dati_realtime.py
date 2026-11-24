from datetime import date, datetime

import pytest
from google.transit import gtfs_realtime_pb2

import config
import dati_gtfs
import dati_realtime

DATA_FOTOGRAFIA = date(2026, 11, 18)


@pytest.fixture(scope="module")
def avvisi():
    return dati_realtime.carica_avvisi()


@pytest.fixture(scope="module")
def elementi_degli_avvisi():
    return dati_realtime.carica_elementi_degli_avvisi()


@pytest.fixture(scope="module")
def ritardi():
    return dati_realtime.carica_ritardi()


@pytest.fixture(scope="module")
def posizioni():
    return dati_realtime.carica_posizioni()


def test_numero_di_righe_dei_feed(avvisi, ritardi, posizioni):
    assert len(avvisi) == 134
    assert len(posizioni) == 417
    assert ritardi["trip_id"].nunique() == 429
    assert len(ritardi) == 2439


def test_ritardi_in_due_forme(ritardi):
    assert ritardi["arrival_delay"].notna().sum() == 1672
    assert ritardi["arrival_timestamp"].notna().sum() == 767


def test_ogni_riga_ha_una_sola_forma_di_ritardo(ritardi):
    ha_ritardo = ritardi["arrival_delay"].notna()
    ha_orario = ritardi["arrival_timestamp"].notna()
    # ^ è lo "o esclusivo": vero quando esattamente una delle due condizioni è vera.
    assert (ha_ritardo ^ ha_orario).all()


def test_ritardo_zero_non_si_perde(ritardi):
    assert ritardi["arrival_delay"].dtype == "Int64"
    assert (ritardi["arrival_delay"] == 0).sum() == 47


def test_tutte_le_corse_dei_ritardi_sono_attive_il_18_11(ritardi):
    linee_urbane = dati_gtfs.carica_linee_urbane()
    corse_urbane = dati_gtfs.carica_corse_urbane(linee_urbane)
    corse_del_giorno = dati_gtfs.filtra_corse_del_giorno(corse_urbane, DATA_FOTOGRAFIA)
    corse_dei_ritardi = set(ritardi["trip_id"])
    assert corse_dei_ritardi <= set(corse_del_giorno["trip_id"])


def test_avviso_ascensore_vinzaglio(avvisi):
    filtro_ascensori = avvisi["header_text"].str.contains("ascensori metro")
    avviso_ascensori = avvisi[filtro_ascensori]
    assert len(avviso_ascensori) == 1
    assert "Vinzaglio" in avviso_ascensori["description_text"].iloc[0]


def test_avviso_sciopero_con_accenti(avvisi):
    filtro_sciopero = avvisi["header_text"].str.contains("Sciopero nazionale")
    avviso_sciopero = avvisi[filtro_sciopero]
    assert len(avviso_sciopero) == 1
    assert "Venerdì 20 Novembre 2026" in avviso_sciopero["description_text"].iloc[0]


def test_sciopero_riguarda_la_rete_urbana(avvisi, elementi_degli_avvisi):
    filtro_sciopero = avvisi["header_text"].str.contains("Sciopero nazionale")
    codice_sciopero = avvisi[filtro_sciopero]["alert_id"].iloc[0]
    elementi_sciopero = elementi_degli_avvisi[elementi_degli_avvisi["alert_id"] == codice_sciopero]
    assert "U" in set(elementi_sciopero["agency_id"])


def test_periodo_degli_avvisi_sempre_presente(avvisi):
    assert avvisi["active_start"].notna().all()
    assert avvisi["active_end"].notna().all()


def test_cause_ed_effetti_leggibili(avvisi):
    effetti = avvisi["effect"].value_counts().to_dict()
    cause = avvisi["cause"].value_counts().to_dict()
    assert effetti["DETOUR"] == 88
    assert cause["CONSTRUCTION"] == 18


def test_posizioni_lette_senza_pulizia(posizioni):
    # La gestione di questi casi è il passo 1.4: qui si controlla solo la lettura.
    assert (posizioni["latitude"] == 0).sum() == 15
    assert (posizioni["trip_id"] == "").sum() == 44


def test_posizioni_per_la_mappa(posizioni):
    linee_urbane = dati_gtfs.carica_linee_urbane()
    posizioni_mappa = dati_realtime.prepara_posizioni_per_la_mappa(posizioni, linee_urbane)
    assert len(posizioni_mappa) == 417 - 15
    assert ((posizioni_mappa["latitude"] == 0) & (posizioni_mappa["longitude"] == 0)).sum() == 0
    # Dei 44 veicoli senza trip_id, 9 sono anche a (0,0): ne restano 35.
    assert (posizioni_mappa["trip_id"] == "").sum() == 35
    linee_sconosciute = posizioni_mappa[~posizioni_mappa["linea_conosciuta"]]
    assert list(linee_sconosciute["route_id"]) == ["FLEU"]


def test_avvisi_attivi_alla_fotografia(avvisi):
    avvisi_attivi = dati_realtime.filtra_avvisi_attivi(avvisi, config.ISTANTE_SIMULATO)
    assert len(avvisi_attivi) == 134
    # Vinzaglio finisce nel 2035: resta attivo come avviso "fino a nuovo avviso".
    assert avvisi_attivi["description_text"].str.contains("Vinzaglio").any()


def test_avviso_non_ancora_iniziato(avvisi):
    # L'avviso di Vinzaglio inizia il 18/11/2026 alle 10:00: alle 9:00 non è ancora attivo.
    prima_dell_inizio = datetime(2026, 11, 18, 9, 0, tzinfo=config.ORA_ITALIANA)
    avvisi_attivi = dati_realtime.filtra_avvisi_attivi(avvisi, prima_dell_inizio)
    assert not avvisi_attivi["description_text"].str.contains("Vinzaglio").any()


def test_fermate_inesistenti_tolte(elementi_degli_avvisi):
    codici_fermate = dati_gtfs.leggi_file_gtfs("stops.txt")["stop_id"]
    elementi_validi = dati_realtime.togli_fermate_inesistenti(elementi_degli_avvisi, codici_fermate)
    assert len(elementi_degli_avvisi) - len(elementi_validi) == 93
    con_fermata = elementi_validi[elementi_validi["stop_id"] != ""]
    assert con_fermata["stop_id"].isin(codici_fermate).all()
    # Gli avvisi su tutta l'azienda (senza stop_id) non vanno persi.
    solo_azienda = (elementi_validi["agency_id"] != "") & (elementi_validi["route_id"] == "") & (elementi_validi["stop_id"] == "")
    assert solo_azienda.sum() == 12


def test_feed_vuoto_mantiene_colonne_e_tipi(monkeypatch):
    # Si simula un feed vuoto (es. di notte) sostituendo la lettura del file.
    monkeypatch.setattr(dati_realtime, "leggi_feed", lambda nome_file: gtfs_realtime_pb2.FeedMessage())
    posizioni_vuote = dati_realtime.carica_posizioni()
    assert len(posizioni_vuote) == 0
    assert list(posizioni_vuote.columns) == dati_realtime.COLONNE_POSIZIONI
    assert posizioni_vuote["latitude"].dtype == "float64"
    assert len(dati_realtime.carica_avvisi()) == 0


def test_avviso_senza_fine_resta_attivo():
    # Tabella di prova inventata: nel feed del 18/11 ogni avviso ha inizio e fine.
    futuro = 10**10
    avvisi_di_prova = dati_realtime.pd.DataFrame({
        "alert_id": ["senza_fine", "finito", "senza_inizio", "non_iniziato"],
        "active_start": dati_realtime.pd.array([0, 0, None, futuro], dtype="Int64"),
        "active_end": dati_realtime.pd.array([None, 1, futuro, None], dtype="Int64"),
    })
    avvisi_attivi = dati_realtime.filtra_avvisi_attivi(avvisi_di_prova, config.ISTANTE_SIMULATO)
    assert list(avvisi_attivi["alert_id"]) == ["senza_fine", "senza_inizio"]


def test_fermata_senza_ascensore_dal_testo(avvisi, elementi_degli_avvisi):
    # L'avviso è collegato a tutte le 23 fermate della metro, ma il testo cita solo Vinzaglio.
    avvisi_attivi = dati_realtime.filtra_avvisi_attivi(avvisi, config.ISTANTE_SIMULATO)
    fermate = dati_gtfs.leggi_file_gtfs("stops.txt")
    assert dati_realtime.trova_fermate_senza_ascensore(avvisi_attivi, elementi_degli_avvisi, fermate) == ["3632"]


def test_nome_della_fermata_come_parola_intera():
    # Avviso e fermate inventati per la prova: "carduccini" non deve far uscire Carducci.
    avvisi_di_prova = dati_realtime.pd.DataFrame({
        "alert_id": ["prova"],
        "header_text": ["Situazione ascensori metro"],
        "description_text": ["Fuori servizio: Marconi. Lavori in piazza Carduccini."],
    })
    elementi_di_prova = dati_realtime.pd.DataFrame({"alert_id": ["prova", "prova"], "stop_id": ["3635", "3638"]})
    fermate_di_prova = dati_realtime.pd.DataFrame({"stop_id": ["3635", "3638"], "stop_name": ["METRO MARCONI", "METRO CARDUCCI"]})
    assert dati_realtime.trova_fermate_senza_ascensore(avvisi_di_prova, elementi_di_prova, fermate_di_prova) == ["3635"]
