# Document Processing with Vertex AI Document AI

This module provides a comprehensive set of tools for document processing using Google Cloud's Vertex AI Document AI. It enables capabilities such as document classification, text extraction, entity extraction, form processing, and more.

## Components

The document processing module consists of the following components:

### 1. Base Document Client (`document_client.py`)

A robust client for Vertex AI Document AI that provides:
- Document processing with various processor types
- Text extraction
- Document classification
- Form processing
- Batch processing capabilities
- Comprehensive error handling with circuit breaker pattern
- Detailed telemetry for monitoring performance
- Mock mode for development and testing

### 2. Entity Extractor Client (`entity_extractor_client.py`)

A specialized client for entity extraction that provides:
- General entity extraction
- Specialized extraction for different document types:
  - Personal information
  - Business information
  - Medical information
  - Invoice information
  - ID document information
- Entity organization by type
- Confidence scoring for extracted entities

### 3. Classifier Client (`classifier_client.py`)

A specialized client for document classification that provides:
- Document type classification with confidence scores
- Processor selection based on document type
- Batch classification capabilities
- Classification-based document processing

### 4. Document Processor (`core/document_processor.py`)

A central processor that integrates all document processing capabilities:
- Unified interface for all document operations
- Automatic document type detection
- Intelligent processor selection
- Comprehensive document analysis
- Support for various input formats (bytes, file paths, file objects)
- MIME type detection

### 5. Document Adapter (`infrastructure/adapters/document_adapter.py`)

An adapter that provides a simplified interface for other system components:
- Singleton pattern for global access
- High-level methods for common document operations
- Context-based parameter passing
- Comprehensive error handling and telemetry
- Lazy initialization

## Usage

### Basic Usage

```python
from infrastructure.adapters.document_adapter import document_adapter

# Initialize the adapter
await document_adapter.initialize()

# Process a document
result = await document_adapter.process_document(
    "path/to/document.pdf",
    {
        "auto_classify": True  # Automatically classify the document
    }
)

# Extract text from a document
result = await document_adapter.extract_text(
    "path/to/document.pdf"
)

# Classify a document
result = await document_adapter.classify_document(
    "path/to/document.pdf"
)

# Extract entities from a document
result = await document_adapter.extract_entities(
    "path/to/document.pdf",
    {
        "document_type": "invoice",
        "entity_types": ["supplier_name", "total_amount"]
    }
)

# Process a form
result = await document_adapter.process_form(
    "path/to/form.pdf"
)

# Analyze a document (comprehensive analysis)
result = await document_adapter.analyze_document(
    "path/to/document.pdf"
)
```

### Advanced Usage

```python
# Extract specific information based on document type
result = await document_adapter.extract_invoice_information(
    "path/to/invoice.pdf"
)

result = await document_adapter.extract_id_document_information(
    "path/to/id.pdf"
)

result = await document_adapter.extract_personal_information(
    "path/to/document.pdf"
)

# Batch processing
results = await document_adapter.batch_process_documents(
    [
        ("path/to/document1.pdf", {"mime_type": "application/pdf"}),
        ("path/to/document2.jpg", {"mime_type": "image/jpeg"}),
        ("path/to/document3.pdf", {"mime_type": "application/pdf"})
    ],
    {
        "auto_classify": True
    }
)

# Get available processors
processors = await document_adapter.get_available_processors()

# Get statistics
stats = await document_adapter.get_stats()
```

## Configuration

The document processing components can be configured through environment variables:

- `GOOGLE_CLOUD_PROJECT`: Google Cloud project ID
- `DOCUMENT_AI_LOCATION`: Location of Document AI processors (default: "us")
- `DOCUMENT_AI_PROCESSOR_ID`: Default processor ID
- `DOCUMENT_AI_TIMEOUT`: Timeout for Document AI operations (default: 60 seconds)
- `DOCUMENT_AI_OCR_PROCESSOR_ID`: Processor ID for OCR operations
- `DOCUMENT_AI_CLASSIFIER_PROCESSOR_ID`: Processor ID for classification operations
- `DOCUMENT_AI_ENTITY_PROCESSOR_ID`: Processor ID for entity extraction operations
- `DOCUMENT_AI_FORM_PROCESSOR_ID`: Processor ID for form processing operations
- `DOCUMENT_AI_INVOICE_PROCESSOR_ID`: Processor ID for invoice processing
- `DOCUMENT_AI_RECEIPT_PROCESSOR_ID`: Processor ID for receipt processing
- `DOCUMENT_AI_ID_PROCESSOR_ID`: Processor ID for ID document processing
- `DOCUMENT_AI_MEDICAL_PROCESSOR_ID`: Processor ID for medical document processing
- `DOCUMENT_AI_TAX_PROCESSOR_ID`: Processor ID for tax document processing

## Testing

The document processing module includes a comprehensive test script:

```bash
python scripts/test_document_processing.py --help
```

This script provides various commands for testing different document processing capabilities:

- `process`: Process a document
- `extract_text`: Extract text from a document
- `classify`: Classify a document
- `extract_entities`: Extract entities from a document
- `process_form`: Process a form
- `extract_personal`: Extract personal information
- `extract_business`: Extract business information
- `extract_medical`: Extract medical information
- `extract_invoice`: Extract invoice information
- `extract_id`: Extract ID document information
- `analyze`: Analyze a document
- `batch`: Process multiple documents in batch
- `processors`: Get available processors
- `stats`: Get statistics

Example:

```bash
# Process a document with auto-classification
python scripts/test_document_processing.py process path/to/document.pdf

# Extract text from a document
python scripts/test_document_processing.py extract_text path/to/document.pdf

# Classify a document
python scripts/test_document_processing.py classify path/to/document.pdf

# Process multiple documents in batch
python scripts/test_document_processing.py batch path/to/document1.pdf path/to/document2.pdf

# Use mock mode for testing without actual API calls
python scripts/test_document_processing.py --mock process path/to/document.pdf
```

## Example

A complete example of using the document processing capabilities is available in:

```bash
python examples/document_processing_example.py
```

This example demonstrates various document processing operations in mock mode.

## Integration with Other Components

The document processing module is designed to integrate seamlessly with other components of the system:

- **Intent Analyzer**: Can use document processing to extract intents from documents
- **Agents**: Can use document processing for domain-specific document analysis
- **Orchestrator**: Can route document processing requests to appropriate agents
- **State Manager**: Can store document processing results for later use

## Error Handling

All document processing components include comprehensive error handling:

- Circuit breaker pattern to prevent cascading failures
- Detailed error messages with context
- Fallback to mock mode when appropriate
- Telemetry for monitoring errors and performance

## Performance Considerations

- Use batch processing for multiple documents when possible
- Consider caching results for frequently processed documents
- Use the appropriate processor for each document type
- Monitor performance using the telemetry data
