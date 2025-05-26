"""
Cliente para interactuar con Google Cloud Storage (GCS).

Proporciona métodos para subir, descargar y gestionar archivos en GCS.
"""

import asyncio
import io
import logging
import os
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union, BinaryIO

from google.cloud import storage

from clients.base_client import BaseClient, retry_with_backoff
from config.secrets import settings

logger = logging.getLogger(__name__)


class GCSClient(BaseClient):
    """
    Cliente para Google Cloud Storage con patrón Singleton.

    Proporciona métodos para gestionar archivos en GCS de forma asíncrona.
    """

    # Instancia única (patrón Singleton)
    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "GCSClient":
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(GCSClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, bucket_name: Optional[str] = None):
        """
        Inicializa el cliente de Google Cloud Storage.

        Args:
            bucket_name: Nombre del bucket de GCS (opcional, se puede tomar de settings)
        """
        # Evitar reinicialización en el patrón Singleton
        if self._initialized:
            return

        super().__init__(service_name="gcs")
        self.bucket_name = bucket_name or settings.GCS_BUCKET
        self.client = None
        self.bucket = None
        self._initialized = True

    async def initialize(self) -> None:
        """
        Inicializa la conexión con Google Cloud Storage.

        Configura las credenciales y prepara el cliente para su uso.
        """
        if not settings.GOOGLE_APPLICATION_CREDENTIALS:
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS no está configurada en las variables de entorno"
            )

        if not self.bucket_name:
            raise ValueError(
                "Nombre del bucket no especificado. Configure GCS_BUCKET en .env"
            )

        # Inicializar cliente de GCS
        # Esto utilizará las credenciales configuradas en GOOGLE_APPLICATION_CREDENTIALS
        loop = asyncio.get_event_loop()
        self.client = await loop.run_in_executor(None, storage.Client)

        # Obtener referencia al bucket
        self.bucket = await loop.run_in_executor(
            None, self.client.bucket, self.bucket_name
        )

        # Verificar que el bucket existe
        exists = await loop.run_in_executor(None, self.bucket.exists)
        if not exists:
            raise ValueError(f"El bucket {self.bucket_name} no existe")

        logger.info(f"Cliente GCS inicializado con bucket {self.bucket_name}")

    @retry_with_backoff()
    async def upload_file(
        self,
        file_path_or_content: Union[str, bytes, BinaryIO],
        destination_blob_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Sube un archivo a Google Cloud Storage.

        Args:
            file_path_or_content: Ruta al archivo local, bytes o stream de archivo
            destination_blob_name: Nombre del blob en GCS (incluyendo "carpetas")
            content_type: Tipo MIME del contenido (opcional)
            metadata: Metadatos adicionales para el blob (opcional)

        Returns:
            Diccionario con información del blob subido
        """
        if not self.bucket:
            await self.initialize()

        self._record_call("upload_file")

        loop = asyncio.get_event_loop()
        blob = self.bucket.blob(destination_blob_name)

        # Configurar metadatos si se proporcionan
        if metadata:
            blob.metadata = metadata

        # Configurar content_type si se proporciona
        if content_type:
            blob.content_type = content_type

        # Subir el archivo según el tipo de entrada
        if isinstance(file_path_or_content, str) and os.path.isfile(
            file_path_or_content
        ):
            # Es una ruta de archivo
            await loop.run_in_executor(
                None, blob.upload_from_filename, file_path_or_content
            )
        elif isinstance(file_path_or_content, bytes):
            # Es contenido en bytes
            await loop.run_in_executor(
                None, blob.upload_from_string, file_path_or_content
            )
        elif hasattr(file_path_or_content, "read"):
            # Es un stream de archivo
            await loop.run_in_executor(
                None, blob.upload_from_file, file_path_or_content
            )
        else:
            # Es un string (contenido)
            await loop.run_in_executor(
                None, blob.upload_from_string, str(file_path_or_content)
            )

        # Obtener URL pública
        url = blob.public_url

        return {
            "name": blob.name,
            "bucket": blob.bucket.name,
            "size": blob.size,
            "url": url,
            "content_type": blob.content_type,
            "metadata": blob.metadata,
        }

    @retry_with_backoff()
    async def download_file(
        self, blob_name: str, destination_file_path: Optional[str] = None
    ) -> Union[bytes, str]:
        """
        Descarga un archivo de Google Cloud Storage.

        Args:
            blob_name: Nombre del blob en GCS
            destination_file_path: Ruta donde guardar el archivo (opcional)

        Returns:
            Contenido del archivo como bytes si no se especifica destination_file_path,
            o la ruta del archivo descargado si se especifica
        """
        if not self.bucket:
            await self.initialize()

        self._record_call("download_file")

        loop = asyncio.get_event_loop()
        blob = self.bucket.blob(blob_name)

        # Verificar que el blob existe
        exists = await loop.run_in_executor(None, blob.exists)
        if not exists:
            raise FileNotFoundError(
                f"El blob {blob_name} no existe en el bucket {self.bucket_name}"
            )

        if destination_file_path:
            # Descargar a un archivo
            await loop.run_in_executor(
                None, blob.download_to_filename, destination_file_path
            )
            return destination_file_path
        else:
            # Descargar a memoria
            buffer = io.BytesIO()
            await loop.run_in_executor(None, blob.download_to_file, buffer)
            buffer.seek(0)
            return buffer.read()

    @retry_with_backoff()
    async def list_files(
        self, prefix: Optional[str] = None, delimiter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lista archivos en un bucket de GCS.

        Args:
            prefix: Prefijo para filtrar los blobs (opcional)
            delimiter: Delimitador para simular "carpetas" (opcional)

        Returns:
            Lista de diccionarios con información de los blobs
        """
        if not self.bucket:
            await self.initialize()

        self._record_call("list_files")

        loop = asyncio.get_event_loop()
        blobs = await loop.run_in_executor(
            None,
            lambda: list(self.bucket.list_blobs(prefix=prefix, delimiter=delimiter)),
        )

        result = []
        for blob in blobs:
            result.append(
                {
                    "name": blob.name,
                    "size": blob.size,
                    "updated": blob.updated,
                    "content_type": blob.content_type,
                    "url": blob.public_url,
                }
            )

        return result

    @retry_with_backoff()
    async def delete_file(self, blob_name: str) -> bool:
        """
        Elimina un archivo de GCS.

        Args:
            blob_name: Nombre del blob a eliminar

        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        if not self.bucket:
            await self.initialize()

        self._record_call("delete_file")

        loop = asyncio.get_event_loop()
        blob = self.bucket.blob(blob_name)

        # Verificar que el blob existe
        exists = await loop.run_in_executor(None, blob.exists)
        if not exists:
            logger.warning(
                f"El blob {blob_name} no existe en el bucket {self.bucket_name}"
            )
            return False

        # Eliminar el blob
        await loop.run_in_executor(None, blob.delete)
        return True

    @retry_with_backoff()
    async def generate_signed_url(
        self,
        blob_name: str,
        expiration: timedelta = timedelta(hours=1),
        method: str = "GET",
    ) -> str:
        """
        Genera una URL firmada para acceder a un archivo de GCS.

        Args:
            blob_name: Nombre del blob
            expiration: Tiempo de expiración de la URL
            method: Método HTTP permitido (GET, PUT, etc.)

        Returns:
            URL firmada
        """
        if not self.bucket:
            await self.initialize()

        self._record_call("generate_signed_url")

        loop = asyncio.get_event_loop()
        blob = self.bucket.blob(blob_name)

        # Verificar que el blob existe
        exists = await loop.run_in_executor(None, blob.exists)
        if not exists:
            raise FileNotFoundError(
                f"El blob {blob_name} no existe en el bucket {self.bucket_name}"
            )

        # Generar URL firmada
        url = await loop.run_in_executor(
            None,
            lambda: blob.generate_signed_url(
                version="v4", expiration=expiration, method=method
            ),
        )

        return url


# Instancia global para uso en toda la aplicación
gcs_client = GCSClient()
