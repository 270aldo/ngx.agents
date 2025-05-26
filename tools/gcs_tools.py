"""
Habilidades para interactuar con Google Cloud Storage (GCS).

Este módulo implementa skills que permiten subir, descargar y gestionar
archivos en Google Cloud Storage.
"""

import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from clients.gcs_client import gcs_client
from core.skill import Skill, skill_registry


class GCSUploadInput(BaseModel):
    """Esquema de entrada para la skill de subida de archivos a GCS."""

    file_path: Optional[str] = Field(None, description="Ruta al archivo local a subir")
    file_content: Optional[str] = Field(
        None, description="Contenido del archivo a subir (alternativa a file_path)"
    )
    destination_path: str = Field(
        ..., description="Ruta de destino en GCS (incluyendo nombre de archivo)"
    )
    content_type: Optional[str] = Field(None, description="Tipo MIME del contenido")
    metadata: Optional[Dict[str, str]] = Field(
        None, description="Metadatos adicionales para el archivo"
    )


class GCSUploadOutput(BaseModel):
    """Esquema de salida para la skill de subida de archivos a GCS."""

    url: str = Field(..., description="URL del archivo subido")
    size: int = Field(..., description="Tamaño del archivo en bytes")
    path: str = Field(..., description="Ruta completa en GCS")
    bucket: str = Field(..., description="Nombre del bucket")


class GCSUploadSkill(Skill):
    """
    Skill para subir archivos a Google Cloud Storage.

    Permite subir archivos locales o contenido en memoria a GCS.
    """

    def __init__(self):
        """Inicializa la skill de subida a GCS."""
        super().__init__(
            name="gcs_upload",
            description="Sube archivos a Google Cloud Storage",
            version="1.0.0",
            input_schema=GCSUploadInput,
            output_schema=GCSUploadOutput,
            categories=["storage", "files", "cloud"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la subida de archivos a GCS.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Información del archivo subido
        """
        # Extraer parámetros
        file_path = input_data.get("file_path")
        file_content = input_data.get("file_content")
        destination_path = input_data["destination_path"]
        content_type = input_data.get("content_type")
        metadata = input_data.get("metadata", {})

        # Verificar que se proporciona al menos una fuente de datos
        if not file_path and not file_content:
            raise ValueError("Debe proporcionar file_path o file_content")

        # Determinar el contenido a subir
        if file_path:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"El archivo {file_path} no existe")
            content_to_upload = file_path
        else:
            content_to_upload = file_content

        # Inferir content_type si no se proporciona
        if not content_type and file_path:
            import mimetypes

            content_type, _ = mimetypes.guess_type(file_path)

        # Subir archivo
        result = await gcs_client.upload_file(
            file_path_or_content=content_to_upload,
            destination_blob_name=destination_path,
            content_type=content_type,
            metadata=metadata,
        )

        # Construir resultado
        return {
            "url": result["url"],
            "size": result["size"],
            "path": result["name"],
            "bucket": result["bucket"],
        }


class GCSDownloadInput(BaseModel):
    """Esquema de entrada para la skill de descarga de archivos de GCS."""

    gcs_path: str = Field(..., description="Ruta del archivo en GCS")
    local_path: Optional[str] = Field(
        None, description="Ruta local donde guardar el archivo (opcional)"
    )
    as_text: bool = Field(
        False, description="Si es True, devuelve el contenido como texto"
    )


class GCSDownloadOutput(BaseModel):
    """Esquema de salida para la skill de descarga de archivos de GCS."""

    local_path: Optional[str] = Field(
        None, description="Ruta local donde se guardó el archivo"
    )
    content: Optional[str] = Field(
        None, description="Contenido del archivo (si as_text=True)"
    )
    size: int = Field(..., description="Tamaño del archivo en bytes")


class GCSDownloadSkill(Skill):
    """
    Skill para descargar archivos de Google Cloud Storage.

    Permite descargar archivos de GCS a disco local o a memoria.
    """

    def __init__(self):
        """Inicializa la skill de descarga de GCS."""
        super().__init__(
            name="gcs_download",
            description="Descarga archivos de Google Cloud Storage",
            version="1.0.0",
            input_schema=GCSDownloadInput,
            output_schema=GCSDownloadOutput,
            categories=["storage", "files", "cloud"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la descarga de archivos de GCS.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Información del archivo descargado
        """
        # Extraer parámetros
        gcs_path = input_data["gcs_path"]
        local_path = input_data.get("local_path")
        as_text = input_data.get("as_text", False)

        # Descargar archivo
        result = await gcs_client.download_file(
            blob_name=gcs_path, destination_file_path=local_path
        )

        # Construir resultado
        if local_path:
            # Se descargó a un archivo
            return {
                "local_path": local_path,
                "content": None,
                "size": os.path.getsize(local_path),
            }
        else:
            # Se descargó a memoria
            content = result
            if as_text and isinstance(content, bytes):
                content = content.decode("utf-8")

            return {
                "local_path": None,
                "content": content if as_text else None,
                "size": len(content),
            }


class GCSListFilesInput(BaseModel):
    """Esquema de entrada para la skill de listar archivos en GCS."""

    prefix: Optional[str] = Field(None, description="Prefijo para filtrar archivos")
    delimiter: Optional[str] = Field(
        "/", description="Delimitador para simular carpetas"
    )


class GCSListFilesOutput(BaseModel):
    """Esquema de salida para la skill de listar archivos en GCS."""

    files: List[Dict[str, Any]] = Field(..., description="Lista de archivos")
    count: int = Field(..., description="Número de archivos encontrados")


class GCSListFilesSkill(Skill):
    """
    Skill para listar archivos en Google Cloud Storage.

    Permite obtener una lista de archivos en un bucket de GCS.
    """

    def __init__(self):
        """Inicializa la skill de listar archivos en GCS."""
        super().__init__(
            name="gcs_list_files",
            description="Lista archivos en Google Cloud Storage",
            version="1.0.0",
            input_schema=GCSListFilesInput,
            output_schema=GCSListFilesOutput,
            categories=["storage", "files", "cloud"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el listado de archivos en GCS.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Lista de archivos encontrados
        """
        # Extraer parámetros
        prefix = input_data.get("prefix")
        delimiter = input_data.get("delimiter", "/")

        # Listar archivos
        files = await gcs_client.list_files(prefix=prefix, delimiter=delimiter)

        # Construir resultado
        return {"files": files, "count": len(files)}


# Registrar las skills
skill_registry.register_skill(GCSUploadSkill())
skill_registry.register_skill(GCSDownloadSkill())
skill_registry.register_skill(GCSListFilesSkill())
