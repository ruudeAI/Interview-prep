"""
doc_loader.py
=============
Module to handle loading and extracting text from Word (.docx) documents,
providing robust error handling for missing or malformed files.
"""

import os
import docx

def load_docx(filepath):
    """Extract all paragraph text from a .docx file.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is empty or cannot be read as a document.
    """
    if not filepath:
        raise ValueError("No file path specified.")
        
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"The file '{filepath}' could not be found. Please check the file path.")
        
    try:
        doc = docx.Document(filepath)
    except Exception as e:
        raise ValueError(f"Failed to read '{filepath}' as a valid Word (.docx) document. Details: {e}")
        
    text_lines = [p.text for p in doc.paragraphs if p.text.strip()]
    
    if not text_lines:
        raise ValueError(f"The document '{filepath}' is empty or contains no readable text paragraphs.")
        
    return "\n".join(text_lines)
