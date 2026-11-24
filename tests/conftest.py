import pytest


@pytest.fixture(scope="session")
def rete():
    # La rete si costruisce in 35-70 secondi e occupa molta memoria: tutti i test usano
    # la stessa, quella che api.py carica all'avvio. Con due reti in memoria, su un PC
    # da 8 GB la suite completa finiva con MemoryError.
    import api
    return api.rete
