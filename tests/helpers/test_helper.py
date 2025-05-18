
# Helper para pruebas

import os
import asyncio
from pathlib import Path

# Configurar modo mock
os.environ["MOCK_MODE"] = "True"
os.environ["MOCK_VERTEX_AI"] = "True"
os.environ["MOCK_A2A"] = "True"
os.environ["ENV"] = "test"

def get_new_event_loop():
    # Obtiene un nuevo bucle de eventos
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop

def run_async(coro):
    # Ejecuta una corutina de forma síncrona
    loop = get_new_event_loop()
    return loop.run_until_complete(coro)
