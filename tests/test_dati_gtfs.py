import pytest

import dati_gtfs


@pytest.fixture(scope="module")
def rete():
    # Il caricamento dura 35-70 secondi: si fa una volta sola per tutti i test.
    return dati_gtfs.carica_rete_urbana()


def test_solo_linee_urbane(rete):
    agenzie = set(rete["linee"]["agency_id"])
    assert agenzie == {"U"}


def test_numero_linee_per_tipo(rete):
    linee_per_tipo = rete["linee"]["route_type"].value_counts().to_dict()
    assert linee_per_tipo == {"3": 129, "0": 8, "1": 1}


def test_metro_presente(rete):
    assert "METROU" in set(rete["linee"]["route_id"])


def test_nessuna_corsa_extraurbana_o_turistica(rete):
    tutte_le_linee = dati_gtfs.leggi_file_gtfs("routes.txt")
    filtro_non_urbane = tutte_le_linee["agency_id"] != "U"
    linee_non_urbane = set(tutte_le_linee[filtro_non_urbane]["route_id"])
    linee_delle_corse = set(rete["corse"]["route_id"])
    assert linee_delle_corse.isdisjoint(linee_non_urbane)


def test_conteggi_misurati_il_20_11_2026(rete):
    # Se cambia il file GTFS o il filtro, questo test lo segnala subito.
    assert len(rete["corse"]) == 57332
    assert len(rete["orari"]) == 1705141
    assert len(rete["fermate"]) == 3730


def test_ogni_corsa_ha_i_suoi_orari(rete):
    corse_con_orari = set(rete["orari"]["trip_id"])
    corse_urbane = set(rete["corse"]["trip_id"])
    assert corse_con_orari == corse_urbane


def test_ogni_fermata_degli_orari_esiste(rete):
    fermate_degli_orari = set(rete["orari"]["stop_id"])
    fermate_urbane = set(rete["fermate"]["stop_id"])
    assert fermate_degli_orari == fermate_urbane


def test_nessun_orario_duplicato(rete):
    duplicati = rete["orari"].duplicated(["trip_id", "stop_sequence"]).sum()
    assert duplicati == 0


def test_tipi_delle_colonne_convertite(rete):
    assert rete["orari"]["stop_sequence"].dtype == "int64"
    assert rete["fermate"]["stop_lat"].dtype == "float64"
    assert rete["fermate"]["stop_lon"].dtype == "float64"


def test_fermate_nell_area_di_torino(rete):
    fermate = rete["fermate"]
    assert fermate["stop_lat"].between(44.8, 45.3).all()
    assert fermate["stop_lon"].between(7.4, 7.9).all()


def test_ogni_veicolo_ha_la_sua_categoria():
    veicoli = dati_gtfs.carica_veicoli()
    assert len(veicoli) == 1209
    # Con il merge "left" un veicolo senza categoria avrebbe il nome vuoto (NaN).
    assert veicoli["vehicle_category_name"].notna().all()


def test_fermate_della_metro_con_stazione_madre():
    fermate_con_stazione = dati_gtfs.carica_stazioni_madre()
    stazione_per_fermata = dict(zip(fermate_con_stazione["stop_id"], fermate_con_stazione["nome_stazione"]))
    assert stazione_per_fermata == {
        "3631": "STAZIONE PORTA SUSA",
        "3634": "STAZIONE PORTA NUOVA",
    }
