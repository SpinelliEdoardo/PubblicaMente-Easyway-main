import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def cliente(rete):
    # La fixture rete (conftest.py) importa api, che carica tutto all'avvio.
    import api
    return TestClient(api.app)


def test_pagina_principale(cliente):
    risposta = cliente.get("/")
    assert risposta.status_code == 200
    assert "EasyWay" in risposta.text
    assert cliente.get("/static/app.js").status_code == 200
    assert cliente.get("/static/stile.css").status_code == 200


def test_stato_con_orologio_e_ascensore(cliente):
    stato = cliente.get("/api/stato").json()
    assert stato["istante_simulato"] == "18/11/2026 15:50"
    assert stato["fermate_senza_ascensore"] == ["METRO VINZAGLIO"]


def test_ricerca_fermate(cliente):
    fermate = cliente.get("/api/fermate", params={"testo": "vinzaglio"}).json()
    codici = [fermata["stop_id"] for fermata in fermate]
    assert set(codici) == {"3171", "3172", "3632"}
    assert cliente.get("/api/fermate", params={"testo": "v"}).json() == []


def test_percorso_accessibile_evita_vinzaglio(cliente):
    parametri = {"origine": "3171", "destinazione": "3634", "accessibile": True}
    percorso = cliente.get("/api/percorso", params=parametri).json()
    assert percorso["trovato"]
    fermate_usate = [fermata["stop_id"] for tratto in percorso["tratti"] for fermata in tratto["fermate"]]
    assert fermate_usate[0] == "3171"
    assert fermate_usate[-1] == "3634"
    # A bordo si passa da Vinzaglio senza scendere: non deve essere né salita né discesa.
    for tratto in percorso["tratti"]:
        assert tratto["fermate"][0]["stop_id"] != "3632"
        assert tratto["fermate"][-1]["stop_id"] != "3632"


def test_percorso_non_trovato(cliente):
    parametri = {"origine": "3632", "destinazione": "3640", "accessibile": True}
    assert cliente.get("/api/percorso", params=parametri).json() == {"trovato": False}


def test_fermata_inesistente(cliente):
    risposta = cliente.get("/api/percorso", params={"origine": "zzz", "destinazione": "3634"})
    assert risposta.status_code == 404


def test_partenze(cliente):
    partenze = cliente.get("/api/partenze", params={"fermata": "3171"}).json()
    assert len(partenze) == 5
    assert partenze[0]["linea"] == "68"
    assert partenze[0]["prevista"] == "15:54"


def test_elenco_completo_fermate_e_criterio(cliente):
    tutte = cliente.get("/api/fermate").json()
    assert len(tutte) == 3730
    assert {"stop_id", "nome", "lat", "lon"}.issubset(tutte[0].keys())

    percorso_veloce = cliente.get(
        "/api/percorso",
        params={"origine": "3171", "destinazione": "3634", "criterio": "piu_veloce"},
    ).json()
    assert percorso_veloce["trovato"]

    percorso_accessibile = cliente.get(
        "/api/percorso",
        params={"origine": "3171", "destinazione": "3634", "criterio": "accessibile"},
    ).json()
    assert percorso_accessibile["trovato"]
    for tratto in percorso_accessibile["tratti"]:
        assert tratto["fermate"][0]["stop_id"] != "3632"
        assert tratto["fermate"][-1]["stop_id"] != "3632"

    errore = cliente.get(
        "/api/percorso",
        params={"origine": "3171", "destinazione": "3634", "criterio": "inventato"},
    )
    assert errore.status_code == 422


def test_veicoli_per_mappa(cliente):
    risposta = cliente.get("/api/veicoli")
    assert risposta.status_code == 200
    veicoli = risposta.json()
    assert len(veicoli) == 402
    assert all(not (v["lat"] == 0.0 and v["lon"] == 0.0) for v in veicoli)
    fleu = [v for v in veicoli if v["route_id"] == "FLEU"]
    assert len(fleu) == 1
    assert fleu[0]["linea"] == "linea sconosciuta"
    assert not fleu[0]["linea_conosciuta"]


def test_avvisi_urbani(cliente):
    risposta = cliente.get("/api/avvisi")
    assert risposta.status_code == 200
    avvisi = risposta.json()
    assert len(avvisi) > 0
    titoli = [a["titolo"] for a in avvisi]
    assert any("ascensor" in titolo.lower() for titolo in titoli)
    assert any(a["azienda_intera"] for a in avvisi)
    assert any(a["fine"] == "Fino a nuovo avviso" for a in avvisi)
