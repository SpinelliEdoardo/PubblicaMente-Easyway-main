from datetime import date

import pytest

import dati_gtfs

DATA_FOTOGRAFIA = date(2026, 11, 18)
DOMENICA_DOPO = date(2026, 11, 22)
IMMACOLATA = date(2026, 12, 8)


@pytest.fixture(scope="module")
def corse_urbane():
    # Senza stop_times il caricamento dura pochi secondi.
    linee_urbane = dati_gtfs.carica_linee_urbane()
    return dati_gtfs.carica_corse_urbane(linee_urbane)


def test_corse_del_giorno_della_fotografia(corse_urbane):
    corse_del_giorno = dati_gtfs.filtra_corse_del_giorno(corse_urbane, DATA_FOTOGRAFIA)
    assert len(corse_del_giorno) == 11785


def test_la_domenica_ci_sono_meno_corse(corse_urbane):
    corse_mercoledi = dati_gtfs.filtra_corse_del_giorno(corse_urbane, DATA_FOTOGRAFIA)
    corse_domenica = dati_gtfs.filtra_corse_del_giorno(corse_urbane, DOMENICA_DOPO)
    assert len(corse_domenica) == 6534
    assert len(corse_domenica) < len(corse_mercoledi)


def test_corse_del_real_time_attive_nel_giorno(corse_urbane):
    # Corse presenti nel feed trip_update del 18/11/2026 (start_date 20261118).
    corse_del_giorno = dati_gtfs.filtra_corse_del_giorno(corse_urbane, DATA_FOTOGRAFIA)
    codici_attivi = set(corse_del_giorno["trip_id"])
    assert "28519050U" in codici_attivi
    assert "28522040U" in codici_attivi


def test_eccezione_toglie_il_servizio_feriale():
    servizi = dati_gtfs.carica_servizi_attivi(IMMACOLATA)
    assert "717657U" not in servizi


def test_eccezione_aggiunge_il_servizio_festivo():
    servizi = dati_gtfs.carica_servizi_attivi(IMMACOLATA)
    assert "717699U" in servizi


def test_nessun_servizio_fuori_dal_periodo_del_gtfs():
    servizi = dati_gtfs.carica_servizi_attivi(date(2027, 3, 1))
    assert servizi == set()
