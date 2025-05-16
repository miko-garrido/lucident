# Slack Tools for Lucident Agent

This package provides modular tools for interacting with Slack APIs, enabling the Lucident agent to communicate and perform various operations within Slack workspaces.

## Features

### Message Operations
- Send messages to channels
- Update existing messages
- Get channel message history
- Get thread replies

### User Operations
- Get bot user ID and information
- List workspace users

### Channel Operations
- List available channels
- Get channel ID from name or ID

### Document Processing
- Detect and list files shared in channels or threads
- Get detailed file information
- Read and extract text from various document types
- Process PDFs with OCR capabilities for scanned documents
- Extract text from images using OCR

## Document Processing Capabilities

The document processing tools support the following file types:

### Fully Supported (Text Extraction)
- Plain text files (`.txt`)
- Markdown (`.md`, `.markdown`)
- HTML (`.html`, `.htm`)
- XML (`.xml`)
- JSON (`.json`)
- CSV (`.csv`)
- PDF (`.pdf`) - with OCR support for scanned documents

### OCR Support
- Images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.webp`)
- Scanned PDFs

### Not Yet Supported
- Office documents (`.doc`, `.docx`, `.odt`)
- Spreadsheets (`.xls`, `.xlsx`, `.ods`)

## Requirements for Document Processing

To use the full document processing capabilities, the following dependencies need to be installed:

1. **For PDF processing:**
   ```
   pip install PyPDF2
   ```

2. **For OCR (Optical Character Recognition):**
   ```
   pip install pytesseract Pillow pdf2image
   ```

3. **External Dependencies:**
   - Tesseract OCR engine:
     ```
     brew install tesseract tesseract-lang  # macOS
     apt-get install tesseract-ocr          # Linux/Ubuntu
     ```
   - Poppler (for PDF to image conversion):
     ```
     brew install poppler  # macOS
     apt-get install poppler-utils  # Linux/Ubuntu
     ```

## Usage Examples

### List Files in a Channel
```python
from lucident_agent.tools.slack_tools import list_files_in_channel

# Get all files in a channel
files_response = list_files_in_channel(channel="general")

if files_response["success"]:
    for file in files_response["files"]:
        print(f"File: {file.get('name')} ({file.get('filetype')})")
        print(f"  Can extract text: {file.get('text_extractable')}")
        print(f"  Extraction method: {file.get('extraction_method')}")
        print(f"  May need OCR: {file.get('may_need_ocr')}")
```

### Get Document Text
```python
from lucident_agent.tools.slack_tools import get_document_text

# Extract text from a PDF file
document_response = get_document_text(file_id="F12345678", use_ocr=True)

if document_response["success"]:
    print(f"Extraction method: {document_response.get('extraction_method')}")
    print(f"Content:\n{document_response.get('content')}")
else:
    print(f"Error: {document_response.get('error')}") 