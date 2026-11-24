import pytest

import config
import rete as modulo_rete

# Coppie di fermate scelte dagli orari reali del 18/11/2026 (corse 28521187U del 4
# e 28519467U del 2) e dalle fermate della metro.
ULIVI = "2456"
LAURO_ROSSI = "1516"
CANELLI = "670"
TAZZOLI = "483"
METRO_FERMI = "3619"
METRO_PORTA_NUOVA = "3634"
METRO_BENGASI = "8648"
METRO_LINGOTTO = "3640"
SOFIA_CAPOLINEA = "3532"
# Coppie trovate in revisione: linee con varianti di percorso.
LINEA_10_DA = "2745"
LINEA_10_A = "2198"
LINEA_20_DA = "608"
LINEA_20_A = "8833"
LINEA_35_DA = "3031"
LINEA_35_A = "3738"


def test_orario_dopo_mezzanotte():
    assert modulo_rete.orario_in_secondi("25:10:00") == 25 * 3600 + 10 * 60


def test_dimensioni_della_rete(rete):
    # Valori misurati il 21/11/2026 sulle corse del 18/11/2026.
    numero_tratte = 0
    for grafo in rete["grafi_per_linea"].values():
        numero_tratte = numero_tratte + grafo.number_of_edges()
    assert len(rete["grafi_per_linea"]) == 249
    assert numero_tratte == 7971


def test_tram_4(rete):
    percorsi = modulo_rete.trova_percorsi_diretti(rete, ULIVI, LAURO_ROSSI)
    assert percorsi[0]["route_id"] == "4U"
    assert len(percorsi[0]["fermate"]) == 9


def test_bus_2(rete):
    percorsi = modulo_rete.trova_percorsi_diretti(rete, CANELLI, TAZZOLI)
    assert percorsi[0]["route_id"] == "2U"


def test_metro_nei_due_sensi(rete):
    andata = modulo_rete.trova_percorsi_diretti(rete, METRO_FERMI, METRO_PORTA_NUOVA)
    ritorno = modulo_rete.trova_percorsi_diretti(rete, METRO_PORTA_NUOVA, METRO_FERMI)
    assert andata[0]["route_id"] == "METROU"
    assert ritorno[0]["route_id"] == "METROU"
    assert andata[0]["fermate"][0] == METRO_FERMI
    assert andata[0]["fermate"][-1] == METRO_PORTA_NUOVA
    assert len(andata[0]["fermate"]) == 15


def test_metro_tratto_breve(rete):
    percorsi = modulo_rete.trova_percorsi_diretti(rete, METRO_BENGASI, METRO_LINGOTTO)
    assert percorsi[0]["route_id"] == "METROU"
    assert len(percorsi[0]["fermate"]) == 3


def test_attesa_metro_realistica(rete):
    percorsi = modulo_rete.trova_percorsi_diretti(rete, METRO_FERMI, METRO_PORTA_NUOVA)
    attesa_in_minuti = percorsi[0]["attesa"] / 60
    # Se i due sensi di marcia si mescolassero, i passaggi conterebbero doppio e l'attesa si dimezzerebbe.
    assert 1.5 < attesa_in_minuti < 5


def test_nessun_giro_al_capolinea(rete):
    # Nel verso opposto la fermata di partenza è quella dall'altro lato della strada:
    # senza cambi l'unico modo sarebbe arrivare al capolinea e tornare indietro.
    assert modulo_rete.trova_percorsi_diretti(rete, LAURO_ROSSI, ULIVI) == []


def test_nessuna_linea_diretta(rete):
    assert modulo_rete.trova_percorsi_diretti(rete, METRO_FERMI, SOFIA_CAPOLINEA) == []


def test_stessa_fermata(rete):
    assert modulo_rete.trova_percorsi_diretti(rete, METRO_FERMI, METRO_FERMI) == []


def test_percorsi_ordinati_e_tempi_coerenti(rete):
    percorsi = modulo_rete.trova_percorsi_diretti(rete, ULIVI, LAURO_ROSSI)
    tempi_totali = [percorso["tempo_totale"] for percorso in percorsi]
    assert tempi_totali == sorted(tempi_totali)
    for percorso in percorsi:
        assert percorso["tempo_totale"] == percorso["attesa"] + percorso["tempo_viaggio"]


def test_nessun_percorso_tra_varianti_diverse(rete):
    # Nel grafo del 10 le due fermate sono collegate, ma stanno su varianti diverse:
    # nessuna corsa del 18/11 passa da entrambe.
    assert modulo_rete.trova_percorsi_diretti(rete, LINEA_10_DA, LINEA_10_A) == []


def test_attesa_sulle_sole_corse_utili(rete):
    # Il 20 passa spesso da 608, ma solo 2 corse arrivano fino a 8833:
    # l'attesa va calcolata su quelle 2, non su tutte le partenze.
    percorsi = modulo_rete.trova_percorsi_diretti(rete, LINEA_20_DA, LINEA_20_A)
    assert percorsi[0]["route_id"] == "20U"
    assert percorsi[0]["corse_utili"] == 2
    assert percorsi[0]["attesa"] / 60 > 60


def test_fermate_dalla_partenza_all_arrivo(rete):
    for origine, destinazione in [(ULIVI, LAURO_ROSSI), (CANELLI, TAZZOLI), (METRO_BENGASI, METRO_LINGOTTO)]:
        for percorso in modulo_rete.trova_percorsi_diretti(rete, origine, destinazione):
            assert percorso["fermate"][0] == origine
            assert percorso["fermate"][-1] == destinazione


def test_fermate_della_corsa_tipica(rete):
    # Sul 35 da 3031 a 3738 le 2 corse delle 4 del mattino fanno 40 fermate, le altre 86 ne fanno 10:
    # si mostrano le fermate della corsa dal tempo mediano, non quelle della prima corsa.
    percorsi = modulo_rete.trova_percorsi_diretti(rete, LINEA_35_DA, LINEA_35_A)
    percorso_35 = [percorso for percorso in percorsi if percorso["route_id"] == "35U"][0]
    assert percorso_35["corse_utili"] == 88
    assert len(percorso_35["fermate"]) == 10


BUS_VINZAGLIO = "3171"
METRO_VINZAGLIO = "3632"
METRO_PORTA_SUSA = "3631"


def linee_del_percorso(percorso):
    return [tratto["route_id"] for tratto in percorso["tratti"] if tratto["tipo"] == "mezzo"]


def fermate_di_salita_e_discesa(percorso):
    fermate = set()
    for tratto in percorso["tratti"]:
        fermate.add(tratto["fermate"][0])
        fermate.add(tratto["fermate"][-1])
    return fermate


def test_distanza_in_metri():
    # Un grado di latitudine misura circa 111 km.
    assert round(modulo_rete.distanza_in_metri(45.0, 7.0, 46.0, 7.0)) == 111195


def test_percorso_con_un_cambio(rete):
    percorso = modulo_rete.trova_percorso(rete, METRO_FERMI, SOFIA_CAPOLINEA)
    assert percorso["cambi"] == 1
    assert linee_del_percorso(percorso) == ["METROU", "2U"]


def test_percorso_diretto_uguale_al_livello_2(rete):
    percorso = modulo_rete.trova_percorso(rete, ULIVI, LAURO_ROSSI)
    assert percorso["cambi"] == 0
    assert linee_del_percorso(percorso) == ["4U"]
    assert len(percorso["tratti"][0]["fermate"]) == 9


def test_variante_raggiunta_a_piedi(rete):
    # Nessuna corsa del 10 va da 2745 a 2198 (livello 2): si cammina fino a 2746.
    percorso = modulo_rete.trova_percorso(rete, LINEA_10_DA, LINEA_10_A)
    assert percorso["tratti"][0]["tipo"] == "a_piedi"
    assert percorso["tratti"][0]["fermate"] == [LINEA_10_DA, "2746"]
    assert linee_del_percorso(percorso) == ["10U"]


def test_stessa_fermata_nessun_percorso(rete):
    assert modulo_rete.trova_percorso(rete, ULIVI, ULIVI) is None


def test_mai_due_camminate_di_fila(rete):
    # Prima della correzione, senza cambi, qui si camminava per 15 tratti di fila.
    for meno_cambi in (False, True):
        percorso = modulo_rete.trova_percorso(rete, "601", "1256", meno_cambi=meno_cambi)
        tipi = [tratto["tipo"] for tratto in percorso["tratti"]]
        for tipo, tipo_dopo in zip(tipi[:-1], tipi[1:]):
            assert not (tipo == "a_piedi" and tipo_dopo == "a_piedi")


def test_meno_cambi(rete):
    veloce = modulo_rete.trova_percorso(rete, "861", "756")
    con_meno_cambi = modulo_rete.trova_percorso(rete, "861", "756", meno_cambi=True)
    assert con_meno_cambi["cambi"] < veloce["cambi"]
    assert con_meno_cambi["tempo_totale"] >= veloce["tempo_totale"]


def test_accessibile_evita_vinzaglio(rete):
    # Test di accettazione del livello 3: l'ascensore esterno di Vinzaglio è fuori servizio.
    veloce = modulo_rete.trova_percorso(rete, BUS_VINZAGLIO, METRO_PORTA_NUOVA)
    assert METRO_VINZAGLIO in fermate_di_salita_e_discesa(veloce)
    accessibile = modulo_rete.trova_percorso(rete, BUS_VINZAGLIO, METRO_PORTA_NUOVA, accessibile=True,
                                             fermate_senza_ascensore=[METRO_VINZAGLIO])
    assert METRO_VINZAGLIO not in fermate_di_salita_e_discesa(accessibile)
    assert METRO_PORTA_SUSA in fermate_di_salita_e_discesa(accessibile)
    assert accessibile["tempo_totale"] > veloce["tempo_totale"]


def test_accessibile_da_fermata_senza_ascensore(rete):
    percorso = modulo_rete.trova_percorso(rete, METRO_VINZAGLIO, METRO_LINGOTTO, accessibile=True,
                                          fermate_senza_ascensore=[METRO_VINZAGLIO])
    assert percorso is None


def test_limite_attesa_per_sequenza(rete):
    # Limite noto del livello 3: l'attesa si calcola sulla sola sequenza di fermate, quindi
    # sulle linee con varianti è più alta di quella del livello 2 (qui il 20 da 1629 a 658).
    # Se questo test fallisce, il limite è stato risolto: aggiornare i punti aperti.
    diretto = modulo_rete.trova_percorsi_diretti(rete, "1629", "658")[0]
    con_cambi = modulo_rete.trova_percorso(rete, "1629", "658")
    assert diretto["route_id"] == "20U"
    assert con_cambi["tempo_totale"] > diretto["tempo_totale"]


def test_partenza_da_fermata_senza_corse(rete):
    # La fermata 211 non ha corse il 18/11: si raggiunge a piedi una fermata servita vicina.
    percorso = modulo_rete.trova_percorso(rete, "211", "658")
    assert percorso is not None
    assert percorso["tratti"][0]["tipo"] == "a_piedi"


@pytest.fixture(scope="module")
def ritardi_misurati(rete):
    # api.py li ha già calcolati all'avvio (la fixture rete lo importa): si riusano.
    import api
    return api.ritardi_misurati


def test_orario_mostrato_dopo_mezzanotte():
    assert modulo_rete.secondi_in_orario(25 * 3600 + 10 * 60) == "01:10"


def test_ritardo_alla_fermata():
    # Misure inventate per la prova: la corsa ha ritardi alle fermate 5 (60 s) e 8 (120 s).
    misure = modulo_rete.pd.DataFrame({"stop_sequence": [5, 8], "ritardo": [60, 120]})
    assert modulo_rete.ritardo_alla_fermata(misure.iloc[0:0], 3) is None
    assert modulo_rete.ritardo_alla_fermata(misure, 3) == "passata"
    assert modulo_rete.ritardo_alla_fermata(misure, 6) == 60
    assert modulo_rete.ritardo_alla_fermata(misure, 10) == 120


def test_ritardi_misurati_tutti_calcolati(ritardi_misurati):
    # Le 2.439 righe del feed hanno tutte una fermata in stop_times e un ritardo.
    assert len(ritardi_misurati) == 2439
    assert ritardi_misurati["ritardo"].notna().all()


def test_prossime_partenze_a_vinzaglio(rete, ritardi_misurati):
    partenze = modulo_rete.prossime_partenze(rete, ritardi_misurati, BUS_VINZAGLIO, config.ISTANTE_SIMULATO)
    adesso = modulo_rete.secondi_dalla_mezzanotte(config.ISTANTE_SIMULATO)
    assert len(partenze) == 5
    secondi = [partenza["secondi_previsti"] for partenza in partenze]
    assert secondi == sorted(secondi)
    assert min(secondi) >= adesso
    # Il 68 delle 15:58 è in anticipo di 4 minuti: è il primo a passare.
    assert (partenze[0]["linea"], partenze[0]["programmata"], partenze[0]["prevista"]) == ("68", "15:58", "15:54")
    assert partenze[0]["tempo_reale"]


def test_metro_senza_tempo_reale(rete, ritardi_misurati):
    partenze = modulo_rete.prossime_partenze(rete, ritardi_misurati, METRO_PORTA_NUOVA, config.ISTANTE_SIMULATO)
    assert len(partenze) == 5
    assert not any(partenza["tempo_reale"] for partenza in partenze)


def test_ritardo_mostrato_uguale_alla_differenza_degli_orari(rete, ritardi_misurati):
    # Prima della correzione alla 3172 si leggeva "16:28 -> 16:25 (-2 min)".
    def in_minuti(orario):
        ore, minuti = orario.split(":")
        return int(ore) * 60 + int(minuti)

    controllate = 0
    for fermata in [BUS_VINZAGLIO, "3172", LAURO_ROSSI]:
        partenze = modulo_rete.prossime_partenze(rete, ritardi_misurati, fermata, config.ISTANTE_SIMULATO, quante=20)
        for partenza in partenze:
            if partenza["tempo_reale"]:
                differenza = in_minuti(partenza["prevista"]) - in_minuti(partenza["programmata"])
                assert partenza["ritardo_minuti"] == differenza
                controllate = controllate + 1
    # Senza partenze in tempo reale il test passerebbe senza controllare niente.
    assert controllate > 0
