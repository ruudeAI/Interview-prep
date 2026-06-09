"""
utils.py
========
General utility functions for filename sanitization, HTML escaping,
STAR method formatting, and JSON text parsing.
"""

import re
import html
import json

def sanitize_filename(name):
    """Turn an arbitrary string into a safe filename fragment."""
    if not name:
        return "unnamed"
    return re.sub(r'[^\w\-]+', '_', name).strip('_')

def escape_html_for_reportlab(text):
    """Escape special characters using standard html.escape for ReportLab Paragraph compatibility."""
    if not text:
        return ""
    return html.escape(text)

def format_answer_html(answer_text, clr_accent_hex):
    """Escapes raw answer text, bolds STAR labels, handles markdown bold, and formats newlines."""
    escaped = escape_html_for_reportlab(answer_text)
    
    # Bold STAR labels and insert linebreaks
    for label in ("Situation:", "Task:", "Action:", "Result:"):
        escaped = escaped.replace(
            label,
            f'<br/><b><font color="{clr_accent_hex}">{label}</font></b>'
        )
    
    # Safely convert markdown bold (**text**) to ReportLab bold (<b>text</b>)
    escaped = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', escaped)
    
    # Convert newlines to ReportLab linebreaks
    escaped = escaped.replace("\n", "<br/>")
    return escaped

def clean_json_string(raw_str):
    """Strip markdown JSON code block fences if present in the LLM response."""
    if not raw_str:
        return ""
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_str, re.DOTALL)
    if match:
        raw_str = match.group(1)
    return raw_str.strip()

def parse_qa_json(raw_text):
    """Parse JSON array of Q&A objects securely, returning a validated list of dicts.
    
    Expected schema:
    [
        {
            "category": "Technical",
            "question": "...",
            "answer": "...",
            "key_terms": "..."
        }
    ]
    """
    cleaned = clean_json_string(raw_text)
    if not cleaned:
        return []
    
    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of Q&A objects.")
    
    valid_qa = []
    for item in data:
        if not isinstance(item, dict):
            continue
        category = item.get("category", "General")
        question = item.get("question", "")
        answer = item.get("answer", "")
        key_terms = item.get("key_terms", "")
        
        if question and answer:
            valid_qa.append({
                "category": str(category).strip(),
                "question": str(question).strip(),
                "answer": str(answer).strip(),
                "key_terms": str(key_terms).strip()
            })
    return valid_qa
