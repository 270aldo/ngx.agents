"""
Document processing module for Vertex AI Document AI.

This module provides clients and utilities for document processing using
Google Cloud's Vertex AI Document AI.
"""

from clients.vertex_ai.document.document_client import DocumentClient
from clients.vertex_ai.document.entity_extractor_client import EntityExtractorClient
from clients.vertex_ai.document.classifier_client import ClassifierClient

__all__ = [
    'DocumentClient',
    'EntityExtractorClient',
    'ClassifierClient',
]
