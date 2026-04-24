import requests
from PyPDF2 import PdfReader
from io import BytesIO
from database import Session, LegalSection
from datetime import datetime
import re
import time

def download_pdf_to_text(url):
    """Download PDF and extract text"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        with BytesIO(response.content) as pdf_file:
            reader = PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error downloading PDF: {str(e)}")
        return None

def parse_ipc_text(text):
    """Extract sections from IPC PDF text"""
    sections = []
    current_section = None
    
    # IPC typically has patterns like "1. Title" or "Section 1:"
    for line in text.split('\n'):
        line = line.strip()
        section_match = re.match(r'^(?:Section\s*)?(\d+[A-Z]*)[\.\:\s]*(.*)', line)
        if section_match:
            if current_section:
                sections.append(current_section)
            section_num = section_match.group(1)
            title = section_match.group(2).strip()
            current_section = (section_num, title, "")
        elif current_section:
            num, title, content = current_section
            current_section = (num, title, content + "\n" + line)
    
    if current_section:
        sections.append(current_section)
    
    return sections

def parse_bns_text(text):
    """Extract sections from BNS PDF text"""
    sections = []
    current_section = None
    
    # BNS uses slightly different formatting
    for line in text.split('\n'):
        line = line.strip()
        section_match = re.match(r'^(\d+[A-Z]*)[\.\:\-\s]*(.*)', line)
        if section_match:
            if current_section:
                sections.append(current_section)
            section_num = section_match.group(1)
            title = section_match.group(2).strip()
            current_section = (section_num, title, "")
        elif current_section:
            num, title, content = current_section
            current_section = (num, title, content + "\n" + line)
    
    if current_section:
        sections.append(current_section)
    
    return sections

def scrape_via_pdf():
    """Main scraping function using PDF downloads"""
    session = Session()
    
    # PDF download URLs (these are official and stable)
    pdf_urls = [
        ("IPC", "https://www.indiacode.nic.in/bitstream/123456789/15289/1/ipc_act.pdf"),
        ("BNS", "https://www.mha.gov.in/sites/default/files/250883_english_01042024.pdf")
    ]
    
    for code_type, url in pdf_urls:
        try:
            print(f"Downloading {code_type} PDF from {url}")
            pdf_text = download_pdf_to_text(url)
            
            if not pdf_text:
                print(f"Failed to get PDF content for {code_type}")
                continue
                
            if code_type == "IPC":
                sections = parse_ipc_text(pdf_text)
            else:
                sections = parse_bns_text(pdf_text)
            
            if not sections:
                print(f"Warning: No sections found in {code_type} PDF")
                continue
                
            # Store in database
            for section_num, title, text in sections:
                legal_section = LegalSection(
                    code_type=code_type,
                    section_number=section_num,
                    section_title=title,
                    full_text=text,
                    effective_date=datetime(1860, 1, 1).date() if code_type == "IPC" else datetime(2024, 7, 1).date()
                )
                session.add(legal_section)
                print(f"Added {code_type} Section {section_num}")
            
            session.commit()
            time.sleep(5)  # Be polite with delays
            
        except Exception as e:
            print(f"Error processing {code_type}: {str(e)}")
            session.rollback()

if __name__ == "__main__":
    scrape_via_pdf()