import zipfile
from pathlib import Path

import pandas as pd

CARTELLA_PROGETTO = Path(__file__).parent
PERCORSO_ZIP_GTFS = CARTELLA_PROGETTO / "Datasets" / "gtt_gtfs.zip"
AGENZIA_URBANA = "U"
RIGHE_PER_BLOCCO = 500_000
COLONNE_ORARI = ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"]
NOMI_GIORNI = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
SERVIZIO_AGGIUNTO = "1"
SERVIZIO_TOLTO = "2"


def leggi_file_gtfs(nome_file):
    # I codici GTFS sono etichette (es. "0U"): letti come testo, i join non sbagliano.
    with zipfile.ZipFile(PERCORSO_ZIP_GTFS) as archivio:
        with archivio.open(nome_file) as file_gtfs:
            tabella = pd.read_csv(
                file_gtfs,
                dtype=str,
                keep_default_na=False,
                encoding="utf-8-sig",
            )
    return tabella


def carica_linee_urbane():
    linee = leggi_file_gtfs("routes.txt")
    linee_urbane = linee[linee["agency_id"] == AGENZIA_URBANA]
    return linee_urbane.reset_index(drop=True)


def carica_corse_urbane(linee_urbane):
    corse = leggi_file_gtfs("trips.txt")
    filtro_urbane = corse["route_id"].isin(linee_urbane["route_id"])
    corse_urbane = corse[filtro_urbane]
    return corse_urbane.reset_index(drop=True)


def carica_orari_urbani(corse_urbane):
    # stop_times.txt pesa circa 113 MB: si legge a blocchi per non riempire la RAM.
    codici_corse_urbane = set(corse_urbane["trip_id"])
    blocchi_urbani = []

    with zipfile.ZipFile(PERCORSO_ZIP_GTFS) as archivio:
        with archivio.open("stop_times.txt") as file_orari:
            lettore_a_blocchi = pd.read_csv(
                file_orari,
                dtype=str,
                keep_default_na=False,
                encoding="utf-8-sig",
                usecols=COLONNE_ORARI,
                chunksize=RIGHE_PER_BLOCCO,
            )
            for blocco in lettore_a_blocchi:
                filtro_urbane = blocco["trip_id"].isin(codici_corse_urbane)
                blocchi_urbani.append(blocco[filtro_urbane])

    orari_urbani = pd.concat(blocchi_urbani, ignore_index=True)
    orari_urbani["stop_sequence"] = orari_urbani["stop_sequence"].astype(int)
    return orari_urbani


def carica_fermate_urbane(orari_urbani):
    fermate = leggi_file_gtfs("stops.txt")
    filtro_urbane = fermate["stop_id"].isin(orari_urbani["stop_id"])
    fermate_urbane = fermate[filtro_urbane].reset_index(drop=True)
    fermate_urbane["stop_lat"] = fermate_urbane["stop_lat"].astype(float)
    fermate_urbane["stop_lon"] = fermate_urbane["stop_lon"].astype(float)
    return fermate_urbane


def carica_servizi_attivi(data):
    # data è un oggetto date di Python (es. date(2026, 11, 18)), non una stringa.
    # Nel GTFS le date sono testo "AAAAMMGG": in questo formato l'ordine
    # alfabetico coincide con quello cronologico, quindi <= e >= funzionano.
    data_gtfs = data.strftime("%Y%m%d")
    giorno_della_settimana = NOMI_GIORNI[data.weekday()]

    calendario = leggi_file_gtfs("calendar.txt")
    nel_periodo = (calendario["start_date"] <= data_gtfs) & (calendario["end_date"] >= data_gtfs)
    nel_giorno = calendario[giorno_della_settimana] == "1"
    servizi_attivi = set(calendario[nel_periodo & nel_giorno]["service_id"])

    eccezioni = leggi_file_gtfs("calendar_dates.txt")
    eccezioni_del_giorno = eccezioni[eccezioni["date"] == data_gtfs]
    filtro_aggiunti = eccezioni_del_giorno["exception_type"] == SERVIZIO_AGGIUNTO
    filtro_tolti = eccezioni_del_giorno["exception_type"] == SERVIZIO_TOLTO
    servizi_aggiunti = set(eccezioni_del_giorno[filtro_aggiunti]["service_id"])
    servizi_tolti = set(eccezioni_del_giorno[filtro_tolti]["service_id"])

    servizi_attivi = servizi_attivi | servizi_aggiunti
    servizi_attivi = servizi_attivi - servizi_tolti
    return servizi_attivi


def filtra_corse_del_giorno(corse, data):
    servizi_attivi = carica_servizi_attivi(data)
    filtro_del_giorno = corse["service_id"].isin(servizi_attivi)
    corse_del_giorno = corse[filtro_del_giorno]
    return corse_del_giorno.reset_index(drop=True)


def carica_veicoli():
    veicoli = leggi_file_gtfs("vehicles.txt")
    categorie = leggi_file_gtfs("vehicle_categories.txt")
    # In vehicles.txt la categoria è scritta "105", in vehicle_categories.txt "105U":
    # senza aggiungere la "U" il collegamento non trova nessun veicolo.
    veicoli["vehicle_category_id"] = veicoli["vehicle_category_id"] + AGENZIA_URBANA
    colonne_categorie = ["vehicle_category_id", "vehicle_category_name", "wheelchair_boarding"]
    veicoli_con_categoria = veicoli.merge(categorie[colonne_categorie], on="vehicle_category_id", how="left")
    return veicoli_con_categoria


def carica_stazioni_madre():
    # Le stazioni madre (location_type 1) non compaiono negli orari: servono per
    # collegare un avviso o una segnalazione sulla stazione intera alle sue fermate.
    fermate = leggi_file_gtfs("stops.txt")
    fermate_figlie = fermate[fermate["parent_station"] != ""]
    stazioni = fermate[fermate["location_type"] == "1"]
    stazioni = stazioni[["stop_id", "stop_name"]]
    stazioni = stazioni.rename(columns={"stop_id": "parent_station", "stop_name": "nome_stazione"})
    fermate_con_stazione = fermate_figlie[["stop_id", "stop_name", "parent_station"]].merge(stazioni, on="parent_station")
    return fermate_con_stazione.reset_index(drop=True)


def carica_rete_urbana():
    linee = carica_linee_urbane()
    corse = carica_corse_urbane(linee)
    orari = carica_orari_urbani(corse)
    fermate = carica_fermate_urbane(orari)

    rete = {
        "linee": linee,
        "corse": corse,
        "orari": orari,
        "fermate": fermate,
    }
    return rete


if __name__ == "__main__":
    rete_urbana = carica_rete_urbana()
    for nome_tabella, tabella in rete_urbana.items():
        print(nome_tabella, len(tabella), "righe")
    print("veicoli", len(carica_veicoli()), "righe")
    print("fermate con stazione madre", len(carica_stazioni_madre()), "righe")
