"""
Mock del módulo supabase para pruebas unitarias.

Este módulo proporciona implementaciones simuladas del cliente de Supabase
para facilitar las pruebas unitarias sin dependencias externas. Permite
simular operaciones CRUD y almacenar datos temporalmente en memoria.

Características principales:
- Modo Mock: Permite simular operaciones sin conectarse a una base de datos real.
- Almacenamiento en Memoria: Utiliza diccionarios y listas para datos temporales.
- Métodos Síncronos y Asíncronos: Compatible con diferentes partes del código.

Clases:
    Client: Mock del cliente de Supabase.
    Client.Table: Mock de una tabla de Supabase.

Funciones:
    create_client: Crea un mock del cliente de Supabase.
"""

from unittest.mock import MagicMock
import uuid
from datetime import datetime


class Client:
    """Mock del cliente de Supabase.

    Esta clase simula el comportamiento del cliente de Supabase para pruebas unitarias,
    proporcionando implementaciones simuladas de los métodos principales que se utilizan
    en la aplicación. Almacena datos temporalmente en memoria utilizando diccionarios
    y listas.

    Atributos:
        is_mock (bool): Indica si el cliente está en modo mock (True) o real (False).
        _mock_users (dict): Diccionario para almacenar usuarios simulados.
        _mock_conversations (list): Lista para almacenar mensajes de conversación.
        _mock_tables (dict): Diccionario para almacenar tablas simuladas.

    Métodos síncronos:
        table: Retorna un mock de tabla.
        get_or_create_user_by_api_key: Obtiene o crea un usuario por su API key.
        log_conversation_message: Registra un mensaje de conversación.
        get_conversation_history: Obtiene el historial de conversación de un usuario.

    Métodos asíncronos:
        query: Simula consultas a tablas con filtros y paginación.
        insert: Simula la inserción de datos en tablas.
        update: Simula la actualización de datos en tablas.
        delete: Simula la eliminación de datos en tablas.
    """

    def __init__(self, *args, **kwargs):
        """Inicializa el mock del cliente de Supabase.

        Configura las estructuras de datos internas para almacenar información
        simulada durante las pruebas unitarias.

        Args:
            *args: Argumentos posicionales que se pasan al constructor real.
            **kwargs: Argumentos con nombre que se pasan al constructor real.
        """
        self.args = args
        self.kwargs = kwargs
        self.data = {}
        self.auth = MagicMock()
        self.table = self.Table
        self.is_mock = True
        self._mock_users = {}
        self._mock_conversations = []
        self._mock_tables = {"conversation_states": {}}

    def table(self, name):
        """Retorna un mock de tabla de Supabase.

        Este método simula el comportamiento del método `table` del cliente
        real de Supabase, permitiendo acceder a tablas simuladas.

        Args:
            name (str): Nombre de la tabla a acceder.

        Returns:
            Table: Instancia de la clase Table que simula una tabla de Supabase.
        """
        return self.Table(name)

    class Table:
        """Mock de una tabla de Supabase.

        Esta clase interna simula el comportamiento de una tabla de Supabase,
        proporcionando métodos para realizar operaciones CRUD simuladas.

        Atributos:
            name (str): Nombre de la tabla simulada.
            data (dict): Diccionario para almacenar datos temporales.

        Métodos:
            select: Simula una selección de columnas.
            eq: Simula una condición de igualdad.
            execute: Simula la ejecución de una consulta.
            insert: Simula la inserción de datos.
            update: Simula la actualización de datos.
            delete: Simula la eliminación de datos.
        """

        def __init__(self, name):
            """Inicializa el mock con el nombre de la tabla.

            Args:
                name (str): Nombre de la tabla simulada.
            """
            self.name = name
            self.data = {}

        def select(self, *args, **kwargs):
            """Simula una selección de columnas en una tabla.

            Args:
                *args: Columnas a seleccionar.
                **kwargs: Argumentos adicionales para la selección.

            Returns:
                self: Retorna la instancia actual para encadenar métodos.
            """
            return self

        def eq(self, column, value):
            """Simula una condición de igualdad en una consulta.

            Args:
                column (str): Nombre de la columna para la condición.
                value: Valor a comparar.

            Returns:
                self: Retorna la instancia actual para encadenar métodos.
            """
            return self

        def execute(self):
            """Simula la ejecución de una consulta.

            Returns:
                dict: Diccionario con los resultados de la consulta y posible error.
            """
            return {"data": [], "error": None}

        def insert(self, data):
            """Simula la inserción de datos en una tabla.

            Args:
                data (dict): Datos a insertar en la tabla.

            Returns:
                dict: Diccionario con los datos insertados y posible error.
            """
            return {"data": data, "error": None}

        def update(self, data):
            """Simula la actualización de datos en una tabla.

            Args:
                data (dict): Datos actualizados.

            Returns:
                dict: Diccionario con los datos actualizados y posible error.
            """
            return {"data": data, "error": None}

        def delete(self):
            """Simula la eliminación de datos de una tabla.

            Returns:
                dict: Diccionario con resultado de la eliminación y posible error.
            """
            return {"data": [], "error": None}


def create_client(url, key, **kwargs):
    """Crea un mock del cliente de Supabase.

    Esta función simula el comportamiento de la función `create_client` del
    módulo supabase, permitiendo crear una instancia del cliente simulado.

    Args:
        url (str): URL de la instancia de Supabase.
        key (str): Clave de API de Supabase.
        **kwargs: Argumentos adicionales para la configuración del cliente.

    Returns:
        Client: Instancia del cliente simulado de Supabase.
    """
    return Client(url, key, **kwargs)


# Implementación de métodos para las pruebas de persistencia


# Definir una función para get_or_create_user_by_api_key para evitar problemas de sintaxis
def _get_or_create_user_by_api_key(self, api_key):
    """Obtiene o crea un usuario por su API key."""
    # Buscar usuario existente por API key
    for user_id, user in self._mock_users.items():
        if user.get("api_key") == api_key:
            return user

    # Crear nuevo usuario
    user_id = str(uuid.uuid4())
    user = {"id": user_id, "api_key": api_key, "created_at": datetime.now().isoformat()}
    self._mock_users[user_id] = user
    return user


# Asignar la función al cliente
setattr(Client, "get_or_create_user_by_api_key", _get_or_create_user_by_api_key)


# Definir una función para log_conversation_message para evitar problemas de sintaxis
def _log_conversation_message(self, user_id, role, message):
    """Registra un mensaje de conversación."""
    self._mock_conversations.append(
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "role": role,
            "message": message,
            "created_at": datetime.now().isoformat(),
        }
    )
    return True


# Asignar la función al cliente
setattr(Client, "log_conversation_message", _log_conversation_message)


# Definir una función para get_conversation_history para evitar problemas de sintaxis
def _get_conversation_history(self, user_id, limit=None, offset=0):
    """Obtiene el historial de conversación de un usuario."""
    # Filtrar mensajes por usuario
    messages = [msg for msg in self._mock_conversations if msg["user_id"] == user_id]

    # Aplicar paginación
    if limit is not None:
        return messages[offset : offset + limit]
    else:
        return messages[offset:]


# Asignar la función al cliente
setattr(Client, "get_conversation_history", _get_conversation_history)


# Métodos asíncronos para StateManager
async def query(
    self, table_name, select="*", filters=None, order=None, limit=None, offset=None
):
    """Simula una consulta a una tabla en Supabase.

    Este método asíncrono simula el comportamiento del método `query` del cliente
    real de Supabase, permitiendo realizar consultas con filtros, ordenamiento y
    paginación sin necesidad de conectarse a una base de datos real.

    Args:
        table_name (str): Nombre de la tabla a consultar.
        select (str, opcional): Columnas a seleccionar. Por defecto "*".
        filters (dict, opcional): Diccionario con filtros (columna: valor).
        order (str, opcional): Columna y dirección para ordenar.
        limit (int, opcional): Número máximo de resultados.
        offset (int, opcional): Número de resultados a saltar.

    Returns:
        list: Lista de registros que coinciden con la consulta.
    """
    if table_name not in self._mock_tables:
        self._mock_tables[table_name] = {}

    result = []
    for id, item in self._mock_tables[table_name].items():
        if filters:
            match = True
            for key, value in filters.items():
                if key not in item or item[key] != value:
                    match = False
                    break
            if match:
                result.append(item)
        else:
            result.append(item)

    if order:
        # Implementación simplificada de ordenamiento
        pass

    if offset is not None:
        result = result[offset:]

    if limit is not None:
        result = result[:limit]

    return result


async def insert(self, table_name, data, upsert=False):
    """Simula la inserción de datos en una tabla de Supabase.

    Este método asíncrono simula el comportamiento del método `insert` del cliente
    real de Supabase, permitiendo insertar datos en una tabla simulada en memoria.

    Args:
        table_name (str): Nombre de la tabla donde insertar los datos.
        data (dict o list): Datos a insertar. Puede ser un diccionario o una lista de diccionarios.
        upsert (bool, opcional): Si es True, actualiza registros existentes. Por defecto False.

    Returns:
        list: Lista de registros insertados.
    """
    if table_name not in self._mock_tables:
        self._mock_tables[table_name] = {}

    if isinstance(data, list):
        result = []
        for item in data:
            if "id" not in item:
                item["id"] = str(uuid.uuid4())
            self._mock_tables[table_name][item["id"]] = item
            result.append(item)
        return result
    else:
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        self._mock_tables[table_name][data["id"]] = data
        return [data]


async def update(self, table_name, data, filters):
    """Simula la actualización de datos en una tabla de Supabase.

    Este método asíncrono simula el comportamiento del método `update` del cliente
    real de Supabase, permitiendo actualizar datos en una tabla simulada en memoria.

    Args:
        table_name (str): Nombre de la tabla donde actualizar los datos.
        data (dict): Diccionario con los datos a actualizar.
        filters (dict): Diccionario con filtros para identificar registros a actualizar.

    Returns:
        list: Lista de registros actualizados.
    """
    if table_name not in self._mock_tables:
        self._mock_tables[table_name] = {}

    result = []
    for id, item in self._mock_tables[table_name].items():
        match = True
        for key, value in filters.items():
            if key not in item or item[key] != value:
                match = False
                break
        if match:
            updated_item = {**item, **data}
            self._mock_tables[table_name][id] = updated_item
            result.append(updated_item)

    return result


async def delete(self, table_name, filters):
    """Simula la eliminación de datos en una tabla de Supabase.

    Este método asíncrono simula el comportamiento del método `delete` del cliente
    real de Supabase, permitiendo eliminar datos de una tabla simulada en memoria.

    Args:
        table_name (str): Nombre de la tabla donde eliminar los datos.
        filters (dict): Diccionario con filtros para identificar registros a eliminar.

    Returns:
        list: Lista de registros eliminados.
    """
    if table_name not in self._mock_tables:
        return []

    result = []
    ids_to_delete = []

    for id, item in self._mock_tables[table_name].items():
        match = True
        for key, value in filters.items():
            if key not in item or item[key] != value:
                match = False
                break
        if match:
            ids_to_delete.append(id)
            result.append(item)

    for id in ids_to_delete:
        del self._mock_tables[table_name][id]

    return result


# Asignar métodos asíncronos a la clase Client
setattr(Client, "query", query)
setattr(Client, "insert", insert)
setattr(Client, "update", update)
setattr(Client, "delete", delete)

# Exportar las clases y funciones
__all__ = ["create_client", "Client"]
