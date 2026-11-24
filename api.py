from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
import dati_gtfs
import dati_realtime
import rete as modulo_rete

CARTELLA_FRONTEND = Path(__file__).parent / "frontend"
MASSIMO_RISULTATI_RICERCA = 10
CRITERI_AMMESSI = {"piu_veloce", "meno_cambi", "accessibile"}

# Tutto si carica una volta all'avvio (35-70 secondi): la rete del giorno simulato e i
# dati real-time della fotografia del 18/11/2026.
rete = modulo_rete.costruisci_rete(config.DATA_SIMULATA)
ritardi_misurati = modulo_rete.calcola_ritardi_misurati(rete["orari"], dati_realtime.carica_ritardi(), config.DATA_SIMULATA)
avvisi_attivi = dati_realtime.filtra_avvisi_attivi(dati_realtime.carica_avvisi(), config.ISTANTE_SIMULATO)
codici_fermate_statiche = set(dati_gtfs.leggi_file_gtfs("stops.txt")["stop_id"])
elementi_degli_avvisi = dati_realtime.togli_fermate_inesistenti(
    dati_realtime.carica_elementi_degli_avvisi(),
    codici_fermate_statiche,
)
fermate_senza_ascensore = dati_realtime.trova_fermate_senza_ascensore(avvisi_attivi, elementi_degli_avvisi, rete["fermate"])
posizioni_veicoli = dati_realtime.prepara_posizioni_per_la_mappa(dati_realtime.carica_posizioni(), rete["linee"])
fermate_per_codice = rete["fermate"].set_index("stop_id")
nomi_linee = rete["linee"].set_index("route_id")["route_short_name"]

app = FastAPI(title="EasyWay")


def descrivi_fermata(codice):
    fermata = fermate_per_codice.loc[codice]
    return {
        "stop_id": codice,
        "nome": fermata["stop_name"],
        "lat": float(fermata["stop_lat"]),
        "lon": float(fermata["stop_lon"]),
    }


def controlla_fermata(codice):
    if codice not in fermate_per_codice.index:
        raise HTTPException(status_code=404, detail=f"Fermata {codice} non trovata")


def formatta_fine_avviso(fine_posix):
    if fine_posix is None or str(fine_posix) == "<NA>":
        return "Fino a nuovo avviso"
    istante_fine = datetime.fromtimestamp(int(fine_posix), tz=config.ORA_ITALIANA)
    # Gli avvisi con scadenza 2033-2035 nei dati GTT indicano validita indeterminata.
    if 2033 <= istante_fine.year <= 2035:
        return "Fino a nuovo avviso"
    return istante_fine.strftime("%d/%m/%Y %H:%M")


@app.get("/api/stato")
def stato():
    nomi_senza_ascensore = [fermate_per_codice.loc[codice, "stop_name"] for codice in fermate_senza_ascensore]
    return {
        "istante_simulato": config.ISTANTE_SIMULATO.strftime("%d/%m/%Y %H:%M"),
        "fermate_senza_ascensore": nomi_senza_ascensore,
    }


@app.get("/api/fermate")
def cerca_fermate(testo: str | None = None):
    if testo is None:
        return [descrivi_fermata(codice) for codice in rete["fermate"]["stop_id"]]
    testo = testo.strip()
    if len(testo) < 2:
        return []
    nomi = rete["fermate"]["stop_name"]
    trovate = rete["fermate"][nomi.str.contains(testo, case=False, regex=False)].copy()
    # Quasi tutti i nomi iniziano con "Fermata NNN - ": si ordina sulla parte dopo il
    # trattino, mettendo prima i nomi che iniziano con il testo cercato.
    # n=1: si taglia solo al primo trattino ("Fermata 243 - DUOMO - MUSEI REALI").
    trovate["nome_breve"] = trovate["stop_name"].str.split(" - ", n=1).str[-1]
    trovate["inizia_col_testo"] = trovate["nome_breve"].str.lower().str.startswith(testo.lower())
    trovate = trovate.sort_values(["inizia_col_testo", "nome_breve"], ascending=[False, True])
    trovate = trovate.head(MASSIMO_RISULTATI_RICERCA)
    return [descrivi_fermata(codice) for codice in trovate["stop_id"]]


@app.get("/api/percorso")
def percorso(
    origine: str,
    destinazione: str,
    criterio: str | None = None,
    meno_cambi: bool = False,
    accessibile: bool = False,
):
    controlla_fermata(origine)
    controlla_fermata(destinazione)
    if criterio is not None:
        if criterio not in CRITERI_AMMESSI:
            raise HTTPException(status_code=422, detail=f"Criterio non valido: {criterio}")
        meno_cambi = criterio == "meno_cambi"
        accessibile = criterio == "accessibile"
    trovato = modulo_rete.trova_percorso(rete, origine, destinazione, meno_cambi=meno_cambi, accessibile=accessibile,
                                         fermate_senza_ascensore=fermate_senza_ascensore)
    if trovato is None:
        return {"trovato": False}
    tratti = []
    for tratto in trovato["tratti"]:
        descritto = {
            "tipo": tratto["tipo"],
            "fermate": [descrivi_fermata(codice) for codice in tratto["fermate"]],
            "minuti": round(float(tratto["tempo"]) / 60, 1),
        }
        if tratto["tipo"] == "mezzo":
            descritto["linea"] = nomi_linee[tratto["route_id"]]
            descritto["attesa_minuti"] = round(float(tratto["attesa"]) / 60, 1)
        tratti.append(descritto)
    return {
        "trovato": True,
        "tratti": tratti,
        "cambi": trovato["cambi"],
        "attesa_minuti": round(float(trovato["attesa"]) / 60, 1),
        "totale_minuti": round(float(trovato["tempo_totale"]) / 60, 1),
    }


@app.get("/api/partenze")
def partenze(fermata: str):
    controlla_fermata(fermata)
    trovate = modulo_rete.prossime_partenze(rete, ritardi_misurati, fermata, config.ISTANTE_SIMULATO)
    risposta = []
    for partenza in trovate:
        risposta.append({
            "linea": partenza["linea"],
            "destinazione": partenza["destinazione"],
            "programmata": partenza["programmata"],
            "prevista": partenza["prevista"],
            "ritardo_minuti": partenza["ritardo_minuti"],
            "tempo_reale": partenza["tempo_reale"],
        })
    return risposta


@app.get("/api/veicoli")
def veicoli(linea: str | None = None):
    filtro_linea = linea.strip().lower() if linea else None
    risposta = []
    for veicolo in posizioni_veicoli.itertuples():
        nome_linea = nomi_linee[veicolo.route_id] if veicolo.linea_conosciuta else "linea sconosciuta"
        if filtro_linea and nome_linea.lower() != filtro_linea and veicolo.route_id.lower() != filtro_linea:
            continue
        orario = None
        if veicolo.vehicle_timestamp is not None and str(veicolo.vehicle_timestamp) != "<NA>":
            orario = datetime.fromtimestamp(int(veicolo.vehicle_timestamp), tz=config.ORA_ITALIANA).strftime("%H:%M:%S")
        risposta.append({
            "vehicle_id": veicolo.vehicle_id,
            "trip_id": veicolo.trip_id,
            "route_id": veicolo.route_id,
            "linea": nome_linea,
            "linea_conosciuta": bool(veicolo.linea_conosciuta),
            "lat": float(veicolo.latitude),
            "lon": float(veicolo.longitude),
            "orario": orario,
        })
    return risposta


@app.get("/api/avvisi")
def avvisi():
    linee_urbane_set = set(nomi_linee.index)
    fermate_urbane_set = set(fermate_per_codice.index)
    elementi_urbani = elementi_degli_avvisi[
        (elementi_degli_avvisi["agency_id"] == dati_gtfs.AGENZIA_URBANA)
        | elementi_degli_avvisi["route_id"].isin(linee_urbane_set)
        | elementi_degli_avvisi["stop_id"].isin(fermate_urbane_set)
    ]
    raggruppati = elementi_urbani.groupby("alert_id")
    risposta = []
    for avviso in avvisi_attivi.itertuples():
        if avviso.alert_id not in raggruppati.groups:
            continue
        gruppo = raggruppati.get_group(avviso.alert_id)
        linee_coinvolte = sorted({
            nomi_linee[codice] for codice in gruppo["route_id"] if codice in linee_urbane_set
        })
        azienda_intera = bool((gruppo["agency_id"] == dati_gtfs.AGENZIA_URBANA).any())
        fine_testo = formatta_fine_avviso(avviso.active_end)
        risposta.append({
            "alert_id": avviso.alert_id,
            "titolo": avviso.header_text,
            "descrizione": avviso.description_text,
            "causa": avviso.cause,
            "effetto": avviso.effect,
            "linee": linee_coinvolte,
            "azienda_intera": azienda_intera,
            "fine": fine_testo,
        })
    return risposta


@app.get("/")
def pagina():
    return FileResponse(CARTELLA_FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=CARTELLA_FRONTEND), name="static")
