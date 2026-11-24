import re
from pathlib import Path

import pandas as pd
from google.transit import gtfs_realtime_pb2

CARTELLA_FEED = Path(__file__).parent / "Datasets" / "file_bin"

# Le colonne fisse servono anche quando un feed è vuoto (es. di notte):
# la tabella resta vuota ma con le colonne giuste.
COLONNE_POSIZIONI = ["vehicle_id", "trip_id", "route_id", "latitude", "longitude", "vehicle_timestamp"]
COLONNE_RITARDI = ["trip_id", "start_date", "vehicle_id", "stop_sequence", "arrival_delay", "arrival_timestamp"]
COLONNE_AVVISI = ["alert_id", "header_text", "description_text", "url", "cause", "effect", "active_start", "active_end"]
COLONNE_ELEMENTI_AVVISI = ["alert_id", "agency_id", "route_id", "stop_id", "trip_id"]


def leggi_feed(nome_file):
    percorso_feed = CARTELLA_FEED / nome_file
    feed = gtfs_realtime_pb2.FeedMessage()
    with open(percorso_feed, "rb") as file_feed:
        feed.ParseFromString(file_feed.read())
    return feed


def carica_posizioni():
    # Le colonne seguono i nomi GTFS per i join con dati_gtfs; dove un nome GTFS-RT
    # coinciderebbe con una colonna statica di significato diverso, si usa un nome distinto.
    feed = leggi_feed("vehicle_position.bin")
    righe = []
    for entita in feed.entity:
        # Un feed può mescolare tipi di entità: si tengono solo quelle del tipo atteso.
        if not entita.HasField("vehicle"):
            continue
        posizione_veicolo = entita.vehicle
        righe.append({
            "vehicle_id": posizione_veicolo.vehicle.id,
            "trip_id": posizione_veicolo.trip.trip_id,
            "route_id": posizione_veicolo.trip.route_id,
            "latitude": posizione_veicolo.position.latitude,
            "longitude": posizione_veicolo.position.longitude,
            "vehicle_timestamp": posizione_veicolo.timestamp,
        })
    posizioni = pd.DataFrame(righe, columns=COLONNE_POSIZIONI)
    # Senza conversione, con un feed vuoto queste colonne non sarebbero numeriche.
    posizioni["latitude"] = posizioni["latitude"].astype(float)
    posizioni["longitude"] = posizioni["longitude"].astype(float)
    posizioni["vehicle_timestamp"] = posizioni["vehicle_timestamp"].astype("Int64")
    return posizioni


def carica_ritardi():
    feed = leggi_feed("trip_update.bin")
    righe = []
    for entita in feed.entity:
        if not entita.HasField("trip_update"):
            continue
        aggiornamento_corsa = entita.trip_update
        for aggiornamento_fermata in aggiornamento_corsa.stop_time_update:
            arrivo = aggiornamento_fermata.arrival
            # Il feed dà o il ritardo in secondi o l'orario previsto: dove manca resta vuoto.
            # HasField distingue un ritardo 0 vero da un ritardo assente.
            ritardo = None
            if arrivo.HasField("delay"):
                ritardo = arrivo.delay
            orario_previsto = None
            if arrivo.HasField("time"):
                orario_previsto = arrivo.time
            righe.append({
                "trip_id": aggiornamento_corsa.trip.trip_id,
                "start_date": aggiornamento_corsa.trip.start_date,
                "vehicle_id": aggiornamento_corsa.vehicle.id,
                "stop_sequence": aggiornamento_fermata.stop_sequence,
                "arrival_delay": ritardo,
                "arrival_timestamp": orario_previsto,
            })
    ritardi = pd.DataFrame(righe, columns=COLONNE_RITARDI)
    # Int64 (con la I maiuscola) è un intero che ammette valori vuoti senza diventare decimale.
    ritardi["arrival_delay"] = ritardi["arrival_delay"].astype("Int64")
    ritardi["arrival_timestamp"] = ritardi["arrival_timestamp"].astype("Int64")
    return ritardi


def primo_testo(testo_tradotto):
    if len(testo_tradotto.translation) == 0:
        return ""
    return testo_tradotto.translation[0].text


def carica_avvisi():
    feed = leggi_feed("alerts.bin")
    righe = []
    for entita in feed.entity:
        if not entita.HasField("alert"):
            continue
        avviso = entita.alert
        inizio = None
        fine = None
        if len(avviso.active_period) > 0:
            periodo = avviso.active_period[0]
            # Senza HasField un inizio o una fine assenti varrebbero 0, cioè il 1970.
            if periodo.HasField("start"):
                inizio = periodo.start
            if periodo.HasField("end"):
                fine = periodo.end
        righe.append({
            "alert_id": entita.id,
            "header_text": primo_testo(avviso.header_text),
            "description_text": primo_testo(avviso.description_text),
            "url": primo_testo(avviso.url),
            "cause": gtfs_realtime_pb2.Alert.Cause.Name(avviso.cause),
            "effect": gtfs_realtime_pb2.Alert.Effect.Name(avviso.effect),
            "active_start": inizio,
            "active_end": fine,
        })
    avvisi = pd.DataFrame(righe, columns=COLONNE_AVVISI)
    avvisi["active_start"] = avvisi["active_start"].astype("Int64")
    avvisi["active_end"] = avvisi["active_end"].astype("Int64")
    return avvisi


def carica_elementi_degli_avvisi():
    # Un avviso può riguardare molte linee e fermate: una riga per ogni elemento coinvolto.
    feed = leggi_feed("alerts.bin")
    righe = []
    for entita in feed.entity:
        if not entita.HasField("alert"):
            continue
        for elemento in entita.alert.informed_entity:
            # agency_id da solo indica un avviso per tutta l'azienda (es. uno sciopero).
            righe.append({
                "alert_id": entita.id,
                "agency_id": elemento.agency_id,
                "route_id": elemento.route_id,
                "stop_id": elemento.stop_id,
                "trip_id": elemento.trip.trip_id,
            })
    return pd.DataFrame(righe, columns=COLONNE_ELEMENTI_AVVISI)


def prepara_posizioni_per_la_mappa(posizioni, linee_urbane):
    # (0,0) è un punto nell'oceano Atlantico: il veicolo non ha una posizione vera.
    senza_posizione = (posizioni["latitude"] == 0) & (posizioni["longitude"] == 0)
    posizioni_mappa = posizioni[~senza_posizione].copy()
    # I veicoli senza trip_id restano: la posizione è vera anche se la corsa non è nota.
    # Una linea che non esiste nel GTFS (es. FLEU) si mostra come "linea sconosciuta".
    posizioni_mappa["linea_conosciuta"] = posizioni_mappa["route_id"].isin(linee_urbane["route_id"])
    return posizioni_mappa.reset_index(drop=True)


def filtra_avvisi_attivi(avvisi, istante):
    # istante è un datetime con fuso orario; il feed usa i secondi dal 1/1/1970 (UTC).
    # Le fini nel 2033-2035 non hanno bisogno di casi a parte: sono avvisi attivi
    # "fino a nuovo avviso" e la regola del periodo li tiene già.
    # Un inizio o una fine assenti vogliono dire "senza limite" da quel lato.
    secondi = int(istante.timestamp())
    iniziato = avvisi["active_start"].isna() | (avvisi["active_start"] <= secondi)
    non_finito = avvisi["active_end"].isna() | (avvisi["active_end"] >= secondi)
    return avvisi[iniziato & non_finito].reset_index(drop=True)


def togli_fermate_inesistenti(elementi_degli_avvisi, codici_fermate):
    # codici_fermate sono tutti gli stop_id di stops.txt. Alcuni avvisi citano fermate
    # che non esistono nel GTFS statico: non si possono collegare alla rete, quindi si tolgono.
    # Le righe senza stop_id (avvisi su una linea o su tutta l'azienda) restano.
    fermata_inesistente = (elementi_degli_avvisi["stop_id"] != "") & ~elementi_degli_avvisi["stop_id"].isin(codici_fermate)
    return elementi_degli_avvisi[~fermata_inesistente].reset_index(drop=True)


def trova_fermate_senza_ascensore(avvisi_attivi, elementi_degli_avvisi, fermate):
    # L'avviso degli ascensori è collegato a tutte le fermate della metro: quella con
    # l'ascensore fermo si riconosce perché il suo nome compare nel testo dell'avviso.
    # Si confrontano parole intere, così "carducci" non si trova dentro "carduccini".
    # Limite noto, fino al livello 6 (estrazione fatta dal modello): un testo come
    # "gli ascensori sono fermi" farebbe uscire anche METRO FERMI.
    avvisi_ascensori = avvisi_attivi[avvisi_attivi["header_text"].str.contains("ascensor", case=False)]
    fermate_senza_ascensore = []
    for avviso in avvisi_ascensori.itertuples():
        testo = avviso.description_text.lower()
        dell_avviso = elementi_degli_avvisi[(elementi_degli_avvisi["alert_id"] == avviso.alert_id) & (elementi_degli_avvisi["stop_id"] != "")]
        con_nome = dell_avviso.merge(fermate[["stop_id", "stop_name"]], on="stop_id")
        for fermata in con_nome.itertuples():
            nome_breve = fermata.stop_name.lower().replace("metro ", "")
            nome_come_parola = r"\b" + re.escape(nome_breve) + r"\b"
            if re.search(nome_come_parola, testo) and fermata.stop_id not in fermate_senza_ascensore:
                fermate_senza_ascensore.append(fermata.stop_id)
    return fermate_senza_ascensore


if __name__ == "__main__":
    import config
    import dati_gtfs

    posizioni = carica_posizioni()
    avvisi = carica_avvisi()
    elementi_degli_avvisi = carica_elementi_degli_avvisi()
    print("posizioni", len(posizioni), "righe")
    print("ritardi", len(carica_ritardi()), "righe")
    print("avvisi", len(avvisi), "righe")
    print("elementi degli avvisi", len(elementi_degli_avvisi), "righe")

    linee_urbane = dati_gtfs.carica_linee_urbane()
    print("posizioni per la mappa", len(prepara_posizioni_per_la_mappa(posizioni, linee_urbane)), "righe")
    print("avvisi attivi", len(filtra_avvisi_attivi(avvisi, config.ISTANTE_SIMULATO)), "righe")
    codici_fermate = dati_gtfs.leggi_file_gtfs("stops.txt")["stop_id"]
    elementi_validi = togli_fermate_inesistenti(elementi_degli_avvisi, codici_fermate)
    print("elementi tolti per fermate inesistenti", len(elementi_degli_avvisi) - len(elementi_validi))
