import re
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from database import Session, LegalSection, SectionMapping
from pydantic import BaseModel

app = FastAPI()

LEGAL_STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "of", "to", "in", "on", "with",
    "section", "legal", "law", "under", "against", "about", "regarding",
    "is", "are", "can", "what", "which", "when", "how", "action", "actions",
    "act", "acts", "file", "case", "matter", "please", "tell", "me", "i",
    "my", "we", "our", "you", "your"
}


def extract_query_keywords(query: str) -> List[str]:
    """Extract meaningful tokens from a natural language legal query."""
    tokens = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", query.lower())
    filtered = [tok for tok in tokens if tok not in LEGAL_STOPWORDS]

    # Keep ordering stable while de-duplicating.
    seen = set()
    unique = []
    for token in filtered:
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return unique[:8]


def score_section(section: LegalSection, keywords: List[str], raw_query: str) -> Dict[str, object]:
    """Simple weighted lexical scorer for retrieval ranking."""
    title = (section.section_title or "").lower()
    text = (section.full_text or "").lower()
    number = (section.section_number or "").lower()
    query_lower = raw_query.lower()

    score = 0.0
    matched = []

    if query_lower and query_lower in title:
        score += 18.0
    if query_lower and query_lower in text:
        score += 12.0
    if query_lower and query_lower == number:
        score += 30.0

    for kw in keywords:
        kw_score = 0.0
        if kw in title:
            kw_score += 10.0
        if kw in text:
            kw_score += 4.0
        if kw == number:
            kw_score += 20.0
        if kw_score > 0:
            matched.append(kw)
            score += kw_score

    return {"score": score, "matched_keywords": matched}


def resolve_mappings_for_section(session, section: LegalSection, limit: int = 3) -> List[dict]:
    """Return best mappings for either IPC or BNS section."""
    if section.code_type == "IPC":
        mappings = session.query(SectionMapping).filter_by(ipc_section_id=section.id).order_by(SectionMapping.confidence.desc()).all()
        direction = "IPC->BNS"
    else:
        mappings = session.query(SectionMapping).filter_by(bns_section_id=section.id).order_by(SectionMapping.confidence.desc()).all()
        direction = "BNS->IPC"

    output = []
    for mapping in mappings[:limit]:
        counterpart_id = mapping.bns_section_id if section.code_type == "IPC" else mapping.ipc_section_id
        counterpart = session.query(LegalSection).get(counterpart_id)
        if not counterpart:
            continue
        output.append({
            "direction": direction,
            "confidence": mapping.confidence,
            "mapping_type": mapping.mapping_type,
            "counterpart_section": {
                "code_type": counterpart.code_type,
                "section_number": counterpart.section_number,
                "section_title": counterpart.section_title
            }
        })
    return output

class SectionResponse(BaseModel):
    id: int
    code_type: str
    section_number: str
    section_title: str
    full_text: str

class MappingResponse(BaseModel):
    ipc_section: SectionResponse
    bns_section: SectionResponse
    confidence: int
    mapping_type: str

class LegalActionResult(BaseModel):
    section: SectionResponse
    matched_keywords: List[str]
    relevance_score: float
    mappings: List[dict]

class LegalActionResponse(BaseModel):
    query: str
    extracted_keywords: List[str]
    results: List[LegalActionResult]

@app.get("/search")
def search_sections(q: str, code_type: Optional[str] = None):
    """Search sections with keyword expansion and ranking."""
    session = Session()
    keywords = extract_query_keywords(q)
    db_query = session.query(LegalSection).filter(
        LegalSection.full_text.contains(q) |
        LegalSection.section_title.contains(q) |
        LegalSection.section_number.contains(q)
    )

    for kw in keywords:
        db_query = db_query.union(
            session.query(LegalSection).filter(
                LegalSection.full_text.contains(kw) |
                LegalSection.section_title.contains(kw)
            )
        )

    if code_type and code_type.lower() in ['ipc', 'bns']:
        db_query = db_query.filter(LegalSection.code_type == code_type.upper())

    raw_results = db_query.limit(100).all()

    scored = []
    for section in raw_results:
        data = score_section(section, keywords, q)
        if data["score"] > 0:
            scored.append((section, data))

    scored.sort(key=lambda x: x[1]["score"], reverse=True)
    top_results = scored[:50]
    return [SectionResponse(
        id=item[0].id,
        code_type=item[0].code_type,
        section_number=item[0].section_number,
        section_title=item[0].section_title,
        full_text=item[0].full_text
    ) for item in top_results]

@app.get("/mappings/{ipc_section}")
def get_mappings(ipc_section: str):
    """Get BNS mappings for an IPC section"""
    session = Session()
    ipc = session.query(LegalSection).filter_by(
        code_type='IPC',
        section_number=ipc_section
    ).first()
    
    if not ipc:
        raise HTTPException(status_code=404, detail="IPC section not found")
    
    mappings = session.query(SectionMapping).filter_by(
        ipc_section_id=ipc.id
    ).all()
    
    response = []
    for m in mappings:
        bns = session.query(LegalSection).get(m.bns_section_id)
        if not bns:
            continue
        response.append(MappingResponse(
            ipc_section=SectionResponse(
                id=ipc.id,
                code_type=ipc.code_type,
                section_number=ipc.section_number,
                section_title=ipc.section_title,
                full_text=ipc.full_text
            ),
            bns_section=SectionResponse(
                id=bns.id,
                code_type=bns.code_type,
                section_number=bns.section_number,
                section_title=bns.section_title,
                full_text=bns.full_text
            ),
            confidence=m.confidence,
            mapping_type=m.mapping_type
        ))
    
    return response


@app.get("/legal-action", response_model=LegalActionResponse)
def legal_action_search(q: str, code_type: Optional[str] = None, limit: int = 10):
    """
    Query by legal action in plain language.
    Automatically extracts keywords and returns ranked clauses with mappings.
    """
    session = Session()
    keywords = extract_query_keywords(q)
    if not keywords:
        keywords = [q.lower().strip()]

    db_query = session.query(LegalSection)
    if code_type and code_type.lower() in ["ipc", "bns"]:
        db_query = db_query.filter(LegalSection.code_type == code_type.upper())

    candidates = db_query.limit(4000).all()
    scored_results = []
    for section in candidates:
        score_info = score_section(section, keywords, q)
        if score_info["score"] <= 0:
            continue
        scored_results.append((section, score_info))

    scored_results.sort(key=lambda x: x[1]["score"], reverse=True)
    final = []
    for section, score_info in scored_results[:max(1, min(limit, 25))]:
        final.append(LegalActionResult(
            section=SectionResponse(
                id=section.id,
                code_type=section.code_type,
                section_number=section.section_number,
                section_title=section.section_title,
                full_text=section.full_text
            ),
            matched_keywords=score_info["matched_keywords"],
            relevance_score=round(float(score_info["score"]), 2),
            mappings=resolve_mappings_for_section(session, section, limit=3)
        ))

    return LegalActionResponse(
        query=q,
        extracted_keywords=keywords,
        results=final
    )