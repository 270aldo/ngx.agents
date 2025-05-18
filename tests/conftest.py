
# Configuración global para pytest

import os
import pytest
import asyncio

# Configurar modo mock
os.environ["MOCK_MODE"] = "True"
os.environ["MOCK_VERTEX_AI"] = "True"
os.environ["MOCK_A2A"] = "True"
os.environ["ENV"] = "test"

@pytest.fixture(scope="session")
def event_loop():
    # Crear un nuevo bucle de eventos para cada sesión de prueba
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
