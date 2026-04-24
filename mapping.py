import spacy
from database import Session, LegalSection, SectionMapping

nlp = spacy.load("en_core_web_lg")

def basic_similarity_mapping():
    """Simple cosine similarity based mapping"""
    session = Session()
    
    # Get all IPC and BNS sections
    ipc_sections = session.query(LegalSection).filter_by(code_type='IPC').all()
    bns_sections = session.query(LegalSection).filter_by(code_type='BNS').all()
    
    for ipc in ipc_sections:
        ipc_doc = nlp(ipc.full_text)
        best_match = None
        best_score = 0
        
        for bns in bns_sections:
            bns_doc = nlp(bns.full_text)
            similarity = ipc_doc.similarity(bns_doc)
            
            if similarity > best_score:
                best_score = similarity
                best_match = bns
        
        if best_match and best_score > 0.7:  # Threshold
            mapping = SectionMapping(
                ipc_section_id=ipc.id,
                bns_section_id=best_match.id,
                confidence=int(best_score * 100),
                mapping_type='direct' if best_score > 0.85 else 'modified'
            )
            session.add(mapping)
    
    session.commit()