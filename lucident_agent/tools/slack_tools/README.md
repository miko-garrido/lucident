# Slack Tools for Lucident

This module provides functionality for the Lucident agent to interact with Slack workspaces.

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

### Document Processing Capabilities
- Fully supported formats (text extraction): Plain text, Markdown, HTML, XML, JSON, CSV, PDF
- OCR support: Images (PNG, JPG, GIF, etc.) and scanned PDFs
- Not yet supported: Office documents, Spreadsheets

### Document Processing Requirements
- PDF processing: `pip install PyPDF2`
- OCR: `pip install pytesseract Pillow pdf2image`
- External dependencies:
  - Tesseract OCR engine
  - Poppler (for PDF to image conversion) 