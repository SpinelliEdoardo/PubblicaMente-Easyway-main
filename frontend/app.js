const CENTRO_TORINO = [45.0703, 7.6869];

const mappa = L.map("mappa").setView(CENTRO_TORINO, 13);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(mappa);

const livelloPercorso = L.layerGroup().addTo(mappa);
const livelloVeicoli = L.layerGroup().addTo(mappa);
const fermateScelte = { partenza: null, arrivo: null };
let fermataDellePartenze = null;

function testoSicuro(testo) {
  // I nomi arrivano dai dati: si trasformano in testo semplice prima di metterli nella pagina.
  // Anche le virgolette, perché il testo può finire dentro un attributo HTML.
  const contenitore = document.createElement("span");
  contenitore.textContent = testo;
  return contenitore.innerHTML.replaceAll('"', "&quot;");
}

async function chiediAlServer(indirizzo) {
  const risposta = await fetch(indirizzo);
  if (!risposta.ok) {
    throw new Error("Errore del server: " + risposta.status);
  }
  return risposta.json();
}

async function mostraOrologio() {
  const stato = await chiediAlServer("/api/stato");
  let testo = "Orologio simulato: " + stato.istante_simulato + " (fotografia reale dei dati GTT, non dati live)";
  if (stato.fermate_senza_ascensore.length > 0) {
    testo += " - Ascensore fuori servizio: " + stato.fermate_senza_ascensore.join(", ");
  }
  document.getElementById("orologio").textContent = testo;
}

function preparaRicerca(ruolo) {
  const casella = document.getElementById(ruolo);
  const elenco = document.getElementById("suggerimenti-" + ruolo);

  casella.addEventListener("input", async function () {
    fermateScelte[ruolo] = null;
    aggiornaPulsante();
    const testo = casella.value.trim();
    if (testo.length < 2) {
      elenco.innerHTML = "";
      return;
    }
    let fermate;
    try {
      fermate = await chiediAlServer("/api/fermate?testo=" + encodeURIComponent(testo));
    } catch (errore) {
      elenco.innerHTML = "<li>Ricerca non disponibile: " + testoSicuro(errore.message) + "</li>";
      return;
    }
    // Se nel frattempo il testo è cambiato, questi risultati sono vecchi.
    if (casella.value.trim() !== testo) {
      return;
    }
    elenco.innerHTML = "";
    for (const fermata of fermate) {
      const voce = document.createElement("li");
      voce.textContent = fermata.nome + " (" + fermata.stop_id + ")";
      voce.addEventListener("click", function () {
        fermateScelte[ruolo] = fermata;
        casella.value = fermata.nome;
        elenco.innerHTML = "";
        mappa.setView([fermata.lat, fermata.lon], 16);
        aggiornaPulsante();
      });
      elenco.appendChild(voce);
    }
  });
}

function aggiornaPulsante() {
  const pronto = fermateScelte.partenza !== null && fermateScelte.arrivo !== null;
  document.getElementById("calcola").disabled = !pronto;
}

async function calcolaPercorso() {
  const risultato = document.getElementById("risultato");
  document.getElementById("partenze").innerHTML = "";
  fermataDellePartenze = null;
  if (fermateScelte.partenza.stop_id === fermateScelte.arrivo.stop_id) {
    risultato.innerHTML = '<p class="avviso">Partenza e arrivo sono la stessa fermata.</p>';
    livelloPercorso.clearLayers();
    return;
  }
  risultato.textContent = "Calcolo in corso...";
  const parametri = new URLSearchParams({
    origine: fermateScelte.partenza.stop_id,
    destinazione: fermateScelte.arrivo.stop_id,
    criterio: document.getElementById("criterio").value,
  });
  const percorso = await chiediAlServer("/api/percorso?" + parametri.toString());
  livelloPercorso.clearLayers();
  if (!percorso.trovato) {
    risultato.innerHTML = '<p class="avviso">Nessun percorso trovato con questi criteri.</p>';
    return;
  }
  mostraPercorsoNelPannello(percorso);
  disegnaPercorso(percorso);
}

function mostraPercorsoNelPannello(percorso) {
  let html = '<p class="riepilogo">Totale circa ' + Math.round(percorso.totale_minuti) + " minuti, "
    + percorso.cambi + (percorso.cambi === 1 ? " cambio" : " cambi") + "</p>";
  for (const tratto of percorso.tratti) {
    const prima = tratto.fermate[0];
    const ultima = tratto.fermate[tratto.fermate.length - 1];
    html += '<div class="tratto">';
    if (tratto.tipo === "a_piedi") {
      html += "A piedi fino a " + testoSicuro(ultima.nome)
        + '<div class="dettaglio">circa ' + Math.max(1, Math.round(tratto.minuti)) + " minuti</div>";
    } else {
      html += '<span class="linea">' + testoSicuro(tratto.linea) + "</span> da "
        + '<span class="fermata-cliccabile" data-fermata="' + testoSicuro(prima.stop_id) + '">'
        + testoSicuro(prima.nome) + "</span> a " + testoSicuro(ultima.nome)
        + '<div class="dettaglio">attesa media circa ' + Math.round(tratto.attesa_minuti) + " minuti, "
        + (tratto.fermate.length - 1) + " fermate, circa " + Math.round(tratto.minuti) + " minuti a bordo</div>";
    }
    html += "</div>";
  }
  html += '<p class="dettaglio">I tempi sono medie della giornata. Clicca una fermata di salita per le prossime partenze.</p>';
  const risultato = document.getElementById("risultato");
  risultato.innerHTML = html;
  for (const elemento of risultato.querySelectorAll(".fermata-cliccabile")) {
    elemento.addEventListener("click", function () {
      mostraPartenze(elemento.dataset.fermata, elemento.textContent);
    });
  }
}

function disegnaPercorso(percorso) {
  const tuttiIPunti = [];
  for (const tratto of percorso.tratti) {
    const punti = tratto.fermate.map(function (fermata) {
      return [fermata.lat, fermata.lon];
    });
    tuttiIPunti.push(...punti);
    const stile = tratto.tipo === "a_piedi"
      ? { color: "#5b6475", weight: 4, dashArray: "6 8" }
      : { color: "#1f5fbf", weight: 6 };
    L.polyline(punti, stile).addTo(livelloPercorso);
    const salita = tratto.fermate[0];
    const segnaposto = L.circleMarker([salita.lat, salita.lon], { radius: 7, color: "#c8102e", fillOpacity: 1 });
    // Leaflet inserisce il testo del tooltip come HTML: va protetto come nel pannello.
    segnaposto.bindTooltip(testoSicuro(salita.nome));
    segnaposto.on("click", function () {
      mostraPartenze(salita.stop_id, salita.nome);
    });
    segnaposto.addTo(livelloPercorso);
  }
  const arrivo = percorso.tratti[percorso.tratti.length - 1].fermate.slice(-1)[0];
  L.circleMarker([arrivo.lat, arrivo.lon], { radius: 8, color: "#1d2330", fillOpacity: 1 })
    .bindTooltip("Arrivo: " + testoSicuro(arrivo.nome))
    .addTo(livelloPercorso);
  mappa.fitBounds(tuttiIPunti, { padding: [40, 40] });
}

async function mostraPartenze(codiceFermata, nomeFermata) {
  const contenitore = document.getElementById("partenze");
  contenitore.textContent = "Caricamento delle partenze...";
  fermataDellePartenze = codiceFermata;
  let partenze;
  try {
    partenze = await chiediAlServer("/api/partenze?fermata=" + encodeURIComponent(codiceFermata));
  } catch (errore) {
    if (fermataDellePartenze === codiceFermata) {
      contenitore.textContent = "Partenze non disponibili: " + errore.message;
    }
    return;
  }
  // Se nel frattempo è stata cliccata un'altra fermata, questa risposta è vecchia.
  if (fermataDellePartenze !== codiceFermata) {
    return;
  }
  let html = "<h3>Prossime partenze da " + testoSicuro(nomeFermata) + "</h3>";
  if (partenze.length === 0) {
    html += "<p>Nessuna partenza nelle prossime ore.</p>";
  } else {
    html += "<table><tr><th>Linea</th><th>Direzione</th><th>Orario</th><th>Previsto</th></tr>";
    for (const partenza of partenze) {
      let previsto = "solo orario";
      if (partenza.tempo_reale) {
        const segno = partenza.ritardo_minuti > 0 ? "+" : "";
        previsto = partenza.prevista + " (" + segno + partenza.ritardo_minuti + " min)";
      }
      html += "<tr><td>" + testoSicuro(partenza.linea) + "</td><td>" + testoSicuro(partenza.destinazione)
        + "</td><td>" + partenza.programmata + "</td><td>" + previsto + "</td></tr>";
    }
    html += "</table>";
  }
  contenitore.innerHTML = html;
}

async function mostraVeicoli() {
  livelloVeicoli.clearLayers();
  if (!document.getElementById("mostra-veicoli").checked) {
    return;
  }
  const veicoli = await chiediAlServer("/api/veicoli");
  for (const veicolo of veicoli) {
    const etichetta = "Linea " + veicolo.linea + " (veicolo " + veicolo.vehicle_id + ")";
    const segnaposto = L.circleMarker([veicolo.lat, veicolo.lon], {
      radius: 4,
      color: veicolo.linea_conosciuta ? "#0f766e" : "#9a3412",
      fillOpacity: 0.75,
      weight: 1,
    });
    segnaposto.bindTooltip(testoSicuro(etichetta));
    segnaposto.addTo(livelloVeicoli);
  }
}

async function mostraAvvisi() {
  const contenitore = document.getElementById("avvisi");
  const elenco = await chiediAlServer("/api/avvisi");
  if (elenco.length === 0) {
    contenitore.textContent = "Nessun avviso attivo sulla rete urbana.";
    return;
  }
  let html = '<p class="meta-avviso">Avvisi attivi nella fotografia del 18/11/2026: ' + elenco.length + "</p>";
  for (const avviso of elenco) {
    const ambito = avviso.azienda_intera
      ? "intera rete urbana"
      : (avviso.linee.length > 0 ? "linee: " + avviso.linee.join(", ") : "fermate specifiche");
    html += '<div class="scheda-avviso">'
      + "<strong>" + testoSicuro(avviso.titolo || "Avviso GTT") + "</strong>"
      + '<div class="meta-avviso">' + testoSicuro(ambito) + " - fino a: " + testoSicuro(avviso.fine) + "</div>"
      + "<div>" + testoSicuro(avviso.descrizione) + "</div>"
      + "</div>";
  }
  contenitore.innerHTML = html;
}

preparaRicerca("partenza");
preparaRicerca("arrivo");
document.getElementById("calcola").addEventListener("click", function () {
  calcolaPercorso().catch(function (errore) {
    document.getElementById("risultato").textContent = errore.message;
  });
});
document.getElementById("mostra-veicoli").addEventListener("change", function () {
  mostraVeicoli().catch(function (errore) {
    document.getElementById("risultato").textContent = errore.message;
  });
});
mostraOrologio().catch(function (errore) {
  document.getElementById("orologio").textContent = errore.message;
});
mostraVeicoli().catch(function (errore) {
  document.getElementById("risultato").textContent = errore.message;
});
mostraAvvisi().catch(function (errore) {
  document.getElementById("avvisi").textContent = "Avvisi non disponibili: " + errore.message;
});
