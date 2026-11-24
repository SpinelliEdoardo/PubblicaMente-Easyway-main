from datetime import datetime

import networkx as nx
import numpy as np
import pandas as pd

import config
import dati_gtfs


def orario_in_secondi(orario):
    # Gli orari GTFS possono superare le 24: "25:10:00" è l'1:10 della notte dopo.
    ore, minuti, secondi = orario.split(":")
    return int(ore) * 3600 + int(minuti) * 60 + int(secondi)


def prepara_orari_del_giorno(rete_urbana, data):
    corse_del_giorno = dati_gtfs.filtra_corse_del_giorno(rete_urbana["corse"], data)
    filtro_del_giorno = rete_urbana["orari"]["trip_id"].isin(corse_del_giorno["trip_id"])
    orari = rete_urbana["orari"][filtro_del_giorno]
    colonne_corse = ["trip_id", "route_id", "direction_id", "wheelchair_accessible", "trip_headsign"]
    orari = orari.merge(corse_del_giorno[colonne_corse], on="trip_id")
    orari["arrivo"] = orari["arrival_time"].apply(orario_in_secondi)
    orari["partenza"] = orari["departure_time"].apply(orario_in_secondi)
    orari = orari.sort_values(["trip_id", "stop_sequence"]).reset_index(drop=True)
    return orari


def calcola_tratte(orari):
    # Per ogni corsa, la riga successiva è la fermata dopo: insieme formano una tratta.
    # L'ultima fermata di ogni corsa non ha una fermata dopo e non diventa una tratta.
    fermata_dopo = orari.groupby("trip_id").shift(-1)
    tratte = pd.DataFrame({
        "route_id": orari["route_id"],
        "direction_id": orari["direction_id"],
        "da_fermata": orari["stop_id"],
        "a_fermata": fermata_dopo["stop_id"],
        "tempo": fermata_dopo["arrivo"] - orari["partenza"],
    })
    tratte = tratte.dropna(subset=["a_fermata"])
    return tratte.reset_index(drop=True)


def costruisci_grafi_per_linea(tratte):
    # Un grafo per linea e senso di marcia: un percorso dentro un solo grafo è senza cambi
    # e non può girare al capolinea per tornare indietro sulla stessa linea.
    # La stessa tratta è percorsa da molte corse: si tiene il tempo medio.
    tratte_medie = tratte.groupby(["route_id", "direction_id", "da_fermata", "a_fermata"], as_index=False)["tempo"].mean()
    grafi_per_linea = {}
    for (codice_linea, senso_di_marcia), tratte_della_linea in tratte_medie.groupby(["route_id", "direction_id"]):
        grafo = nx.DiGraph()
        for tratta in tratte_della_linea.itertuples():
            grafo.add_edge(tratta.da_fermata, tratta.a_fermata, tempo=tratta.tempo)
        grafi_per_linea[(codice_linea, senso_di_marcia)] = grafo
    return grafi_per_linea


def costruisci_rete(data):
    rete_urbana = dati_gtfs.carica_rete_urbana()
    orari = prepara_orari_del_giorno(rete_urbana, data)
    tratte = calcola_tratte(orari)
    rete = {
        "linee": rete_urbana["linee"],
        "fermate": rete_urbana["fermate"],
        "orari": orari,
        "grafi_per_linea": costruisci_grafi_per_linea(tratte),
        "grafo_con_cambi": costruisci_grafo_con_cambi(orari, rete_urbana["fermate"]),
    }
    return rete


def trova_corse_utili(orari, codice_linea, senso_di_marcia, origine, destinazione):
    # Le corse del giorno che passano prima dall'origine e poi dalla destinazione.
    # Serve perché il grafo unisce le varianti della linea (deviazioni, corse limitate):
    # nel grafo un collegamento può esistere anche se nessuna corsa lo fa davvero.
    della_linea = orari[(orari["route_id"] == codice_linea) & (orari["direction_id"] == senso_di_marcia)]
    partenze = della_linea[della_linea["stop_id"] == origine][["trip_id", "stop_sequence", "partenza"]]
    arrivi = della_linea[della_linea["stop_id"] == destinazione][["trip_id", "stop_sequence", "arrivo"]]
    coppie = partenze.merge(arrivi, on="trip_id", suffixes=("_origine", "_destinazione"))
    coppie = coppie[coppie["stop_sequence_origine"] < coppie["stop_sequence_destinazione"]].copy()
    coppie["tempo"] = coppie["arrivo"] - coppie["partenza"]
    # Nelle linee circolari una corsa può passare due volte da una fermata: si tiene il tratto più breve.
    coppie = coppie.sort_values("tempo").drop_duplicates("trip_id")
    return coppie.sort_values("partenza").reset_index(drop=True)


def fermate_della_corsa(orari, corsa_utile):
    della_corsa = orari[orari["trip_id"] == corsa_utile["trip_id"]]
    dopo_origine = della_corsa["stop_sequence"] >= corsa_utile["stop_sequence_origine"]
    prima_della_destinazione = della_corsa["stop_sequence"] <= corsa_utile["stop_sequence_destinazione"]
    return list(della_corsa[dopo_origine & prima_della_destinazione]["stop_id"])


def trova_percorsi_diretti(rete, origine, destinazione):
    # Restituisce tutte le linee che vanno da origine a destinazione senza cambi,
    # dalla più veloce alla più lenta. Lista vuota se non ce n'è nessuna.
    percorsi = []
    if origine == destinazione:
        return percorsi
    for (codice_linea, senso_di_marcia), grafo in rete["grafi_per_linea"].items():
        # Il grafo scarta subito le linee che non possono collegare le due fermate.
        if origine not in grafo or destinazione not in grafo:
            continue
        if not nx.has_path(grafo, origine, destinazione):
            continue
        corse_utili = trova_corse_utili(rete["orari"], codice_linea, senso_di_marcia, origine, destinazione)
        # Con meno di due corse utili non c'è un intervallo da cui stimare l'attesa.
        if len(corse_utili) < 2:
            continue
        # Attesa media = metà dell'intervallo medio tra due corse utili.
        # Semplificazione del livello 2: media su tutta la giornata.
        intervallo_medio = (corse_utili["partenza"].max() - corse_utili["partenza"].min()) / (len(corse_utili) - 1)
        attesa = intervallo_medio / 2
        tempo_viaggio = corse_utili["tempo"].mean()
        # Le fermate da mostrare sono quelle della corsa dal tempo mediano, la più tipica:
        # la prima corsa del giorno può essere una variante con un giro più lungo.
        ordinate_per_tempo = corse_utili.sort_values("tempo").reset_index(drop=True)
        corsa_tipica = ordinate_per_tempo.iloc[len(ordinate_per_tempo) // 2]
        percorsi.append({
            "route_id": codice_linea,
            "direction_id": senso_di_marcia,
            "fermate": fermate_della_corsa(rete["orari"], corsa_tipica),
            "corse_utili": len(corse_utili),
            "attesa": attesa,
            "tempo_viaggio": tempo_viaggio,
            "tempo_totale": attesa + tempo_viaggio,
        })
    percorsi.sort(key=lambda percorso: percorso["tempo_totale"])
    return percorsi


# Livello 3: valori scelti dal gruppo, non dati GTT.
RAGGIO_A_PIEDI_METRI = 300
VELOCITA_A_PIEDI = 1.0
PENALITA_CAMBIO_SECONDI = 900
RAGGIO_TERRA_METRI = 6371000


def distanza_in_metri(lat_1, lon_1, lat_2, lon_2):
    # Formula dell'emisenoverso: distanza in linea d'aria sulla sfera terrestre.
    lat_1, lon_1, lat_2, lon_2 = np.radians(lat_1), np.radians(lon_1), np.radians(lat_2), np.radians(lon_2)
    termine = np.sin((lat_2 - lat_1) / 2) ** 2 + np.cos(lat_1) * np.cos(lat_2) * np.sin((lon_2 - lon_1) / 2) ** 2
    return 2 * RAGGIO_TERRA_METRI * np.arcsin(np.sqrt(termine))


def aggiungi_sequenze(orari):
    # Corse con la stessa linea, lo stesso senso e le stesse fermate formano una sequenza.
    orari = orari.copy()
    fermate_per_corsa = orari.groupby("trip_id")["stop_id"].apply(lambda fermate: "-".join(fermate))
    chiavi = orari.groupby("trip_id")[["route_id", "direction_id"]].first()
    chiavi["fermate"] = fermate_per_corsa
    chiavi["id_sequenza"] = chiavi["route_id"] + "|" + chiavi["direction_id"] + "|" + chiavi["fermate"]
    orari = orari.merge(chiavi[["id_sequenza"]], left_on="trip_id", right_index=True)
    # La posizione distingue le due fermate uguali di una linea circolare.
    orari["posizione"] = orari.groupby("trip_id").cumcount()
    return orari


def calcola_attese(orari):
    # Attesa = metà dell'intervallo medio tra le corse della sequenza a quella fermata.
    # Con meno di due corse l'attesa non si può stimare e resta vuota (NaN).
    passaggi = orari.groupby(["id_sequenza", "posizione"])["partenza"].agg(["min", "max", "count"])
    attese = (passaggi["max"] - passaggi["min"]) / (passaggi["count"] - 1) / 2
    attese[passaggi["count"] < 2] = np.nan
    return attese


def calcola_archi_a_piedi(fermate):
    latitudini = fermate["stop_lat"].astype(float).to_numpy()
    longitudini = fermate["stop_lon"].astype(float).to_numpy()
    codici = list(fermate["stop_id"])
    archi = []
    for i in range(len(codici)):
        distanze = distanza_in_metri(latitudini[i], longitudini[i], latitudini, longitudini)
        for j in np.where(distanze <= RAGGIO_A_PIEDI_METRI)[0]:
            if i != j:
                archi.append((codici[i], codici[j], distanze[j] / VELOCITA_A_PIEDI))
    return archi


def costruisci_grafo_con_cambi(orari, fermate):
    # Nodi "fermata": dove si sale, si scende e si parte a piedi.
    # Nodi "a_piedi": si arriva in una fermata camminando; da qui si sale soltanto, così
    # tra due mezzi c'è al massimo una camminata e non una catena di camminate.
    # Nodi "corsa": una fermata dentro una sequenza; si passa da uno all'altro viaggiando.
    orari = aggiungi_sequenze(orari)
    grafo = nx.DiGraph()

    fermata_dopo = orari.groupby("trip_id").shift(-1)
    viaggi = pd.DataFrame({
        "id_sequenza": orari["id_sequenza"],
        "posizione": orari["posizione"],
        "tempo": fermata_dopo["arrivo"] - orari["partenza"],
    }).dropna(subset=["tempo"])
    tempi_medi = viaggi.groupby(["id_sequenza", "posizione"])["tempo"].mean()
    for (id_sequenza, posizione), tempo in tempi_medi.items():
        grafo.add_edge(("corsa", id_sequenza, posizione), ("corsa", id_sequenza, posizione + 1), tipo="viaggio", tempo=tempo)

    attese = calcola_attese(orari)
    attese_accessibili = calcola_attese(orari[orari["wheelchair_accessible"] == "1"])
    passaggi = orari.drop_duplicates(["id_sequenza", "posizione"])
    for passaggio in passaggi.itertuples():
        nodo_fermata = ("fermata", passaggio.stop_id)
        nodo_corsa = ("corsa", passaggio.id_sequenza, passaggio.posizione)
        grafo.add_node(nodo_corsa, stop_id=passaggio.stop_id)
        chiave = (passaggio.id_sequenza, passaggio.posizione)
        attesa = attese[chiave]
        attesa_accessibile = attese_accessibili.get(chiave, np.nan)
        for nodo_di_salita in (nodo_fermata, ("a_piedi", passaggio.stop_id)):
            grafo.add_edge(nodo_di_salita, nodo_corsa, tipo="salita", route_id=passaggio.route_id,
                           attesa=attesa, attesa_accessibile=attesa_accessibile)
        grafo.add_edge(nodo_corsa, nodo_fermata, tipo="discesa", tempo=0)

    # Si cammina anche da e verso le fermate senza corse in quel giorno: da lì si può
    # comunque raggiungere a piedi una fermata servita vicina.
    for da_fermata, a_fermata, tempo in calcola_archi_a_piedi(fermate):
        grafo.add_edge(("fermata", da_fermata), ("a_piedi", a_fermata), tipo="a_piedi", tempo=tempo)
    return grafo


def ricostruisci_tratti(grafo, nodi, accessibile):
    tratti = []
    for nodo_da, nodo_a in zip(nodi[:-1], nodi[1:]):
        arco = grafo.edges[nodo_da, nodo_a]
        if arco["tipo"] == "a_piedi":
            tratti.append({"tipo": "a_piedi", "fermate": [nodo_da[1], nodo_a[1]], "tempo": arco["tempo"]})
        elif arco["tipo"] == "salita":
            attesa = arco["attesa_accessibile"] if accessibile else arco["attesa"]
            tratti.append({"tipo": "mezzo", "route_id": arco["route_id"], "fermate": [nodo_da[1]],
                           "attesa": attesa, "tempo": 0})
        elif arco["tipo"] == "viaggio":
            tratti[-1]["fermate"].append(grafo.nodes[nodo_a]["stop_id"])
            tratti[-1]["tempo"] = tratti[-1]["tempo"] + arco["tempo"]
    return tratti


def trova_percorso(rete, origine, destinazione, meno_cambi=False, accessibile=False, fermate_senza_ascensore=()):
    # Restituisce il percorso migliore secondo i criteri scelti, oppure None.
    if origine == destinazione:
        return None
    grafo = rete["grafo_con_cambi"]
    fermate_escluse = set()
    if accessibile:
        non_accessibili = rete["fermate"][rete["fermate"]["wheelchair_boarding"] == "2"]["stop_id"]
        fermate_escluse = set(non_accessibili) | set(fermate_senza_ascensore)
    # La penalità colpisce ogni salita, anche la prima: tra percorsi con i mezzi è uguale per
    # tutti, ma avvantaggia un percorso fatto solo a piedi (limite noto, al massimo 300 m).
    penalita = PENALITA_CAMBIO_SECONDI if meno_cambi else 0

    def peso(nodo_da, nodo_a, arco):
        # Restituire None vuol dire "questo arco non si può usare".
        for nodo in (nodo_da, nodo_a):
            if nodo[0] != "corsa" and nodo[1] in fermate_escluse:
                return None
        if arco["tipo"] == "salita":
            attesa = arco["attesa_accessibile"] if accessibile else arco["attesa"]
            if pd.isna(attesa):
                return None
            return attesa + penalita
        return arco["tempo"]

    if ("fermata", origine) not in grafo:
        return None
    costi, cammini = nx.single_source_dijkstra(grafo, ("fermata", origine), weight=peso)
    # Alla destinazione si arriva scendendo da un mezzo oppure a piedi: si tiene il meno costoso.
    arrivi = [nodo for nodo in (("fermata", destinazione), ("a_piedi", destinazione)) if nodo in costi]
    if not arrivi:
        return None
    arrivo_migliore = min(arrivi, key=lambda nodo: costi[nodo])
    nodi = cammini[arrivo_migliore]

    tratti = ricostruisci_tratti(grafo, nodi, accessibile)
    tratti_in_mezzo = [tratto for tratto in tratti if tratto["tipo"] == "mezzo"]
    attesa = sum(tratto["attesa"] for tratto in tratti_in_mezzo)
    tempo_in_movimento = sum(tratto["tempo"] for tratto in tratti)
    return {
        "tratti": tratti,
        "cambi": max(len(tratti_in_mezzo) - 1, 0),
        "attesa": attesa,
        "tempo_totale": attesa + tempo_in_movimento,
    }


# Livello 4: prossime partenze.
# Una corsa partita fino a 30 minuti prima può essere ancora in arrivo, se è in ritardo.
FINESTRA_RITARDO_SECONDI = 1800


def secondi_dalla_mezzanotte(istante):
    return istante.hour * 3600 + istante.minute * 60 + istante.second


def secondi_in_orario(secondi):
    # 25:10 diventa 01:10: nella pagina si mostra l'ora dell'orologio.
    ore = (secondi // 3600) % 24
    minuti = (secondi % 3600) // 60
    return f"{ore:02d}:{minuti:02d}"


def calcola_ritardi_misurati(orari, ritardi, data):
    # Il feed dà il ritardo in due forme: in secondi, oppure come orario previsto (POSIX).
    # Nel secondo caso il ritardo è l'orario previsto meno quello programmato.
    mezzanotte = datetime(data.year, data.month, data.day, tzinfo=config.ORA_ITALIANA)
    mezzanotte_posix = int(mezzanotte.timestamp())
    misurati = ritardi.merge(orari[["trip_id", "stop_sequence", "arrivo"]], on=["trip_id", "stop_sequence"])
    dal_orario_previsto = misurati["arrival_timestamp"] - mezzanotte_posix - misurati["arrivo"]
    misurati["ritardo"] = misurati["arrival_delay"].fillna(dal_orario_previsto)
    return misurati[["trip_id", "stop_sequence", "ritardo"]]


def ritardo_alla_fermata(ritardi_della_corsa, sequenza_fermata):
    # Restituisce il ritardo in secondi, None se la corsa non ha dati in tempo reale,
    # oppure "passata" se le misure riguardano solo fermate dopo questa.
    if len(ritardi_della_corsa) == 0:
        return None
    misure_prima = ritardi_della_corsa[ritardi_della_corsa["stop_sequence"] <= sequenza_fermata]
    if len(misure_prima) == 0:
        return "passata"
    # Regola GTFS-Realtime: il ritardo misurato vale anche per le fermate successive.
    ultima_misura = misure_prima.sort_values("stop_sequence").iloc[-1]
    return int(ultima_misura["ritardo"])


def prossime_partenze(rete, ritardi_misurati, fermata, istante, quante=5):
    adesso = secondi_dalla_mezzanotte(istante)
    orari = rete["orari"]
    ultima_fermata = orari.groupby("trip_id")["stop_sequence"].transform("max")
    # Al capolinea di arrivo una corsa non parte: si tolgono quelle righe.
    della_fermata = orari[(orari["stop_id"] == fermata) & (orari["stop_sequence"] < ultima_fermata)]
    candidate = della_fermata[della_fermata["partenza"] >= adesso - FINESTRA_RITARDO_SECONDI]
    nomi_linee = rete["linee"].set_index("route_id")["route_short_name"]

    partenze = []
    for corsa in candidate.itertuples():
        ritardi_della_corsa = ritardi_misurati[ritardi_misurati["trip_id"] == corsa.trip_id]
        ritardo = ritardo_alla_fermata(ritardi_della_corsa, corsa.stop_sequence)
        if ritardo == "passata":
            continue
        prevista = corsa.partenza if ritardo is None else corsa.partenza + ritardo
        if prevista < adesso:
            continue
        partenze.append({
            "route_id": corsa.route_id,
            "linea": nomi_linee[corsa.route_id],
            "destinazione": corsa.trip_headsign,
            "programmata": secondi_in_orario(corsa.partenza),
            "prevista": secondi_in_orario(prevista),
            "secondi_previsti": prevista,
            # Differenza tra i minuti mostrati, così orario e ritardo tornano sempre tra loro.
            "ritardo_minuti": None if ritardo is None else int(prevista // 60 - corsa.partenza // 60),
            "tempo_reale": ritardo is not None,
        })
    partenze.sort(key=lambda partenza: partenza["secondi_previsti"])
    return partenze[:quante]


if __name__ == "__main__":
    rete = costruisci_rete(config.DATA_SIMULATA)
    numero_tratte = 0
    for grafo in rete["grafi_per_linea"].values():
        numero_tratte = numero_tratte + grafo.number_of_edges()
    print("grafi (linea e senso di marcia)", len(rete["grafi_per_linea"]))
    print("tratte", numero_tratte)
    grafo_con_cambi = rete["grafo_con_cambi"]
    print("grafo con i cambi: nodi", grafo_con_cambi.number_of_nodes(), "archi", grafo_con_cambi.number_of_edges())
