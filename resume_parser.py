import requests
import tempfile
import os
import re
from pdfminer.high_level import extract_text
from docx import Document

def download_file(url: str) -> str:
    response = requests.get(url)
    response.raise_for_status()

    suffix = os.path.splitext(url)[-1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(response.content)
    tmp.close()
    return tmp.name

def extract_text_from_file(path: str) -> str:
    if path.endswith(".pdf"):
        return extract_text(path)
    elif path.endswith(".docx"):
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        raise ValueError("Unsupported resume format")

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def parse_resume_from_url(url: str) -> str:
    local_path = download_file(url)
    raw = extract_text_from_file(local_path)
    return clean_text(raw)
#
# def parse_resume_from_url(url: str) -> str:
#     local_path = download_file(url)
#     raw = extract_text_from_file(local_path)
#
#     print("\n========== RAW EXTRACTED TEXT ==========\n")
#     print(raw)
#     print("\n========== END RAW TEXT ==========\n")
#
#     cleaned = clean_text(raw)
#
#     print("\n========== CLEANED TEXT ==========\n")
#     print(cleaned)
#     print("\n========== END CLEANED TEXT ==========\n")
#
#     return cleaned