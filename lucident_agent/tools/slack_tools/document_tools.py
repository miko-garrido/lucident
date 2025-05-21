"""
Slack document-related tools module.

This module provides functions for detecting, listing, getting information, and downloading
document content from Slack conversations.
"""

import logging
import os
import requests
import tempfile
import io
from typing import Dict, Any, List, Optional, Tuple
from slack_sdk.errors import SlackApiError
from .client import get_slack_client
from .message_tools import get_slack_channel_history, get_slack_thread_replies

# Import PDF processing library
import PyPDF2

# Import OCR libraries
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_extraction_capability(file_type: str, mime_type: str) -> Tuple[bool, str, bool]:
    """
    Check if we have capability to extract text from a file based on its type.
    
    Returns a tuple containing:
    - is_supported: Boolean indicating if we support extraction
    - method: The method of extraction ('standard', 'ocr', 'none')
    - needs_ocr: Boolean indicating if OCR might be needed
    """
    file_type = file_type.lower() if file_type else ""
    mime_type = mime_type.lower() if mime_type else ""
    
    # Text-based formats that we can directly extract
    text_formats = {
        "txt": "standard", 
        "md": "standard", 
        "markdown": "standard",
        "html": "standard", 
        "htm": "standard",
        "xml": "standard", 
        "json": "standard",
        "csv": "standard",
        "rtf": "standard"
    }
    
    # Formats that require specific libraries
    pdf_formats = {"pdf"}
    doc_formats = {"doc", "docx", "odt"}
    spreadsheet_formats = {"xls", "xlsx", "ods"}
    
    # Image formats that need OCR
    image_formats = {"png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"}
    
    # Check by file extension first
    if file_type in text_formats:
        return True, text_formats[file_type], False
    
    # Check by mime type for text
    if "text/" in mime_type:
        return True, "standard", False
    
    # Check PDF
    if file_type in pdf_formats or "application/pdf" in mime_type:
        return True, "pdf", True  # PDFs may need OCR if scanned
    
    # Check Office documents
    if file_type in doc_formats or "document" in mime_type:
        return False, "none", False  # Not supported yet
    
    # Check spreadsheets
    if file_type in spreadsheet_formats:
        return False, "none", False  # Not supported yet
    
    # Check images
    if file_type in image_formats or "image/" in mime_type:
        return True, "ocr", True
    
    # Default case - unknown or unsupported type
    return False, "none", False

def detect_files_in_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect files in a list of Slack messages.

    Args:
        messages (List[Dict[str, Any]]): List of raw Slack message objects (each message is a dict as returned by the Slack API)

    Returns:
        List[Dict[str, Any]]: List of file objects found in the messages
    """
    files = []
    
    for message in messages:
        # Check if the message contains files
        if "files" in message and message["files"]:
            for file in message["files"]:
                # Add message timestamp to file for reference
                file["message_ts"] = message.get("ts", "")
                files.append(file)
    
    return files

def get_file_info(file_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a file in Slack.
    
    Args:
        file_id: The ID of the file to get information for
        
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'file': File object with details if successful
        - 'error': Error message if unsuccessful
    """
    client = get_slack_client()
    response = client.files_info(file=file_id)
    if not response["ok"]:
        return {
            "success": False,
            "error": f"API error: {response.get('error', 'Unknown error')}"
        }
    return {
        "success": True,
        "file": response["file"]
    }

def download_file_content(file_url: str, file_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Download a file from Slack and return its content.
    
    Args:
        file_url: The private URL of the file to download
        file_name: Optional name to save the file as (temp file used if not provided)
        
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'file_path': Path to the downloaded file
        - 'content': Text content of the file (if text-based)
        - 'error': Error message if unsuccessful
    """
    client = get_slack_client()
    headers = {"Authorization": f"Bearer {client.token}"}
    # Download the file with authentication
    response = requests.get(file_url, headers=headers)
    if response.status_code != 200:
        return {
            "success": False,
            "error": f"Failed to download file: HTTP {response.status_code}"
        }
    # Determine if this is likely a text file based on content
    is_text = True
    content = None
    try:
        content = response.text
        # Check if this might be binary data by looking for null bytes
        if "\x00" in content or len(content) > 1000000:  # Don't try to return huge text files
            is_text = False
            content = None
    except UnicodeDecodeError:
        is_text = False
        content = None
    # Save the file
    if file_name:
        file_path = file_name
    else:
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"slack_file_{os.urandom(4).hex()}")
    with open(file_path, 'wb') as f:
        f.write(response.content)
    return {
        "success": True,
        "file_path": file_path,
        "content": content if is_text else "Binary content (not displayed)",
        "is_text": is_text,
        "raw_content": response.content  # Include raw content for further processing
    }

def extract_pdf_text(pdf_content) -> str:
    """
    Extract text from PDF content.
    
    Args:
        pdf_content: Raw PDF content in bytes
        
    Returns:
        Extracted text as string
    """
    text = []
    # Create a PDF file reader object
    pdf_file = io.BytesIO(pdf_content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    # Extract text from each page
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        page_text = page.extract_text()
        if page_text:
            text.append(f"--- Page {page_num + 1} ---\n{page_text}")
        else:
            text.append(f"--- Page {page_num + 1} ---\n[No extractable text on this page]")
    # If no text was extracted, PDF might be scanned or image-based
    if not any(text) or all("[No extractable text on this page]" in page for page in text):
        return "This PDF appears to contain scanned images or non-extractable text. OCR processing would be required to extract text."
    return "\n\n".join(text)

def perform_ocr_on_pdf(pdf_content) -> str:
    """
    Perform OCR on PDF content to extract text from scanned documents.
    
    Args:
        pdf_content: Raw PDF content in bytes
        
    Returns:
        Extracted text as string
    """
    # Convert PDF to images
    images = convert_from_bytes(pdf_content)
    # Perform OCR on each page
    text = []
    for i, image in enumerate(images):
        page_text = pytesseract.image_to_string(image)
        if page_text.strip():
            text.append(f"--- Page {i + 1} (OCR) ---\n{page_text}")
        else:
            text.append(f"--- Page {i + 1} (OCR) ---\n[No text detected via OCR]")
    if not any(text) or all("[No text detected via OCR]" in page for page in text):
        return "OCR processing was unable to extract text from this document. The document may be complex or low quality."
    return "\n\n".join(text)

def extract_image_text(image_content) -> str:
    """
    Perform OCR on image content to extract text.
    
    Args:
        image_content: Raw image content in bytes
        
    Returns:
        Extracted text as string
    """
    image = Image.open(io.BytesIO(image_content))
    text = pytesseract.image_to_string(image)
    if not text.strip():
        return "No text detected in this image via OCR. The image may not contain text or the text is not recognizable."
    return text

def list_files_in_channel(channel: str, limit: int = 100) -> Dict[str, Any]:
    """
    List all files shared in a Slack channel.
    
    Args:
        channel: The channel name or ID to get files from
        limit: The maximum number of messages to check (default: 100)
        
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'files': List of files found in the channel
        - 'error': Error message if unsuccessful
    """
    # Get channel history
    history_response = get_slack_channel_history(channel, limit)
    
    if not history_response["success"]:
        return {
            "success": False,
            "error": history_response["error"]
        }
    
    # Extract files from raw messages
    files = detect_files_in_messages(history_response["raw_messages"])
    
    # Enhance files with extraction capability info
    for file in files:
        file_type = file.get("filetype", "").lower()
        mime_type = file.get("mimetype", "").lower()
        supported, method, needs_ocr = check_extraction_capability(file_type, mime_type)
        file["text_extractable"] = supported
        file["extraction_method"] = method
        file["may_need_ocr"] = needs_ocr
    
    return {
        "success": True,
        "channel": history_response["channel"],
        "channel_name": history_response.get("channel_name"),
        "files": files
    }

def list_files_in_thread(channel: str, thread_ts: str, limit: int = 100) -> Dict[str, Any]:
    """
    List all files shared in a Slack thread.
    
    Args:
        channel: The channel name or ID where the thread exists
        thread_ts: The timestamp of the parent message
        limit: The maximum number of replies to check (default: 100)
        
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'files': List of files found in the thread
        - 'error': Error message if unsuccessful
    """
    # Get thread replies
    replies_response = get_slack_thread_replies(channel, thread_ts, limit)
    
    if not replies_response["success"]:
        return {
            "success": False,
            "error": replies_response["error"]
        }
    
    # Extract files from raw messages
    files = detect_files_in_messages(replies_response["raw_replies"])
    
    # Enhance files with extraction capability info
    for file in files:
        file_type = file.get("filetype", "").lower()
        mime_type = file.get("mimetype", "").lower()
        supported, method, needs_ocr = check_extraction_capability(file_type, mime_type)
        file["text_extractable"] = supported
        file["extraction_method"] = method
        file["may_need_ocr"] = needs_ocr
    
    return {
        "success": True,
        "channel": replies_response["channel"],
        "thread_ts": replies_response["thread_ts"],
        "files": files
    }

def get_document_text(file_id: str, use_ocr: bool = True) -> Dict[str, Any]:
    """
    Get the text content of a document in Slack.
    
    Args:
        file_id: The ID of the file to get text content for
        use_ocr: Whether to attempt OCR for scanned documents
        
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'content': Text content of the file if successful
        - 'file_info': Information about the file
        - 'error': Error message if unsuccessful
    """
    # First get file info to get the download URL
    file_info_response = get_file_info(file_id)
    
    if not file_info_response["success"]:
        return {
            "success": False,
            "error": file_info_response["error"]
        }
    
    file_info = file_info_response["file"]
    file_name = file_info.get("name", "")
    file_type = file_info.get("filetype", "").lower()
    mime_type = file_info.get("mimetype", "").lower()
    
    # Check extraction capability
    is_supported, method, needs_ocr = check_extraction_capability(file_type, mime_type)
    
    if not is_supported:
        return {
            "success": False,
            "error": f"Unsupported file type for text extraction: {file_type}",
            "file_info": file_info,
            "available_methods": "None"
        }
    
    # If OCR is needed but not enabled, inform the user
    if needs_ocr and not use_ocr:
        return {
            "success": False,
            "error": f"This {file_type} file likely requires OCR processing which is currently disabled. Enable OCR to extract text.",
            "file_info": file_info,
            "available_methods": method,
            "ocr_required": True
        }
    
    # Get the download URL
    download_url = file_info.get("url_private", "")
    
    if not download_url:
        return {
            "success": False,
            "error": "No download URL available for this file",
            "file_info": file_info
        }
    
    # Download the file content
    download_response = download_file_content(download_url)
    
    if not download_response["success"]:
        return {
            "success": False,
            "error": download_response["error"],
            "file_info": file_info
        }
    
    raw_content = download_response.get("raw_content")
    if not raw_content:
        return {
            "success": False,
            "error": "Failed to retrieve file content",
            "file_info": file_info
        }
    
    # Handle different file types according to their extraction method
    if method == "pdf":
        # Handle PDF files specifically
        # Try normal PDF text extraction first
        pdf_text = extract_pdf_text(raw_content)
        
        # If the PDF appears to be scanned and OCR is enabled, try OCR
        if "scanned images or non-extractable text" in pdf_text and use_ocr:
            logger.info(f"Attempting OCR on PDF file: {file_name}")
            ocr_text = perform_ocr_on_pdf(raw_content)
            
            return {
                "success": True,
                "content": ocr_text,
                "file_info": file_info,
                "file_path": download_response.get("file_path"),
                "file_type": "pdf",
                "extraction_method": "ocr"
            }
        
        return {
            "success": True,
            "content": pdf_text,
            "file_info": file_info,
            "file_path": download_response.get("file_path"),
            "file_type": "pdf",
            "extraction_method": "standard"
        }
    
    elif method == "ocr":
        # Handle image files with OCR
        logger.info(f"Attempting OCR on image file: {file_name}")
        ocr_text = extract_image_text(raw_content)
        
        return {
            "success": True,
            "content": ocr_text,
            "file_info": file_info,
            "file_path": download_response.get("file_path"),
            "file_type": file_type,
            "extraction_method": "ocr"
        }
    
    elif method == "standard":
        # For standard text-based files
        if not download_response.get("is_text", False):
            return {
                "success": False,
                "error": f"Unable to extract text from this {file_type} file. The file may contain non-textual content or encoding issues.",
                "file_info": file_info,
                "file_path": download_response.get("file_path")
            }
        
        return {
            "success": True,
            "content": download_response["content"],
            "file_info": file_info,
            "file_path": download_response.get("file_path"),
            "file_type": file_type,
            "extraction_method": "standard"
        }
    
    # Default case if we got here somehow
    return {
        "success": False,
        "error": f"Unknown extraction method: {method}",
        "file_info": file_info,
        "file_path": download_response.get("file_path", "")
    } 