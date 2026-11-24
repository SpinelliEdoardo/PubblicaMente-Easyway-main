from datetime import datetime, timedelta, timezone

# Orologio simulato: la demo si ferma all'istante della fotografia dei feed real-time,
# così orari, ritardi e avvisi raccontano lo stesso momento.
# A novembre Torino è all'ora solare, cioè UTC+1.
ORA_ITALIANA = timezone(timedelta(hours=1))
ISTANTE_SIMULATO = datetime(2026, 11, 18, 15, 50, tzinfo=ORA_ITALIANA)
DATA_SIMULATA = ISTANTE_SIMULATO.date()
