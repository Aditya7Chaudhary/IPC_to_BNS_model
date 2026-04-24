from database import Session, LegalSection, SectionMapping
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import time
import re


def _section_number_base(num):
    if not num:
        return ""
    match = re.match(r"(\d+)", str(num))
    return match.group(1) if match else str(num)

def create_mappings_optimized():
    """Hybrid mapping using word+char TF-IDF and reciprocal checks."""
    db_session = Session()
    
    print("Fetching sections from database...")
    # Fetch data that was already saved by your scraper script
    ipc_sections = db_session.query(LegalSection).filter_by(code_type='IPC').all()
    bns_sections = db_session.query(LegalSection).filter_by(code_type='BNS').all()
    
    if not ipc_sections or not bns_sections:
        print("Error: Database is empty. Please run your PDF scraper script first.")
        return

    print(f"Found {len(ipc_sections)} IPC sections and {len(bns_sections)} BNS sections.")
    
    # Extract text and titles
    ipc_texts = [sec.full_text for sec in ipc_sections]
    bns_texts = [sec.full_text for sec in bns_sections]
    ipc_titles = [sec.section_title for sec in ipc_sections]
    bns_titles = [sec.section_title for sec in bns_sections]
    
    print("Vectorizing text for instant comparison (hybrid TF-IDF)...")
    start_time = time.time()
    word_vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), min_df=1)
    char_vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=1)

    # Fit vectorizers on all texts so they share the same vocabulary
    all_texts = ipc_texts + bns_texts
    all_titles = ipc_titles + bns_titles
    combined_corpus = all_texts + all_titles
    word_vectorizer.fit(combined_corpus)
    char_vectorizer.fit(combined_corpus)

    ipc_text_word_matrix = word_vectorizer.transform(ipc_texts)
    bns_text_word_matrix = word_vectorizer.transform(bns_texts)
    ipc_title_word_matrix = word_vectorizer.transform(ipc_titles)
    bns_title_word_matrix = word_vectorizer.transform(bns_titles)

    ipc_text_char_matrix = char_vectorizer.transform(ipc_texts)
    bns_text_char_matrix = char_vectorizer.transform(bns_texts)
    ipc_title_char_matrix = char_vectorizer.transform(ipc_titles)
    bns_title_char_matrix = char_vectorizer.transform(bns_titles)

    print("Calculating similarities (word + character n-grams)...")
    text_word_sim = cosine_similarity(ipc_text_word_matrix, bns_text_word_matrix)
    title_word_sim = cosine_similarity(ipc_title_word_matrix, bns_title_word_matrix)
    text_char_sim = cosine_similarity(ipc_text_char_matrix, bns_text_char_matrix)
    title_char_sim = cosine_similarity(ipc_title_char_matrix, bns_title_char_matrix)

    # Heavier weight on semantic title/text word overlap, with char-sim as stabilizer.
    combined_scores = (
        text_word_sim * 0.45
        + title_word_sim * 0.35
        + text_char_sim * 0.15
        + title_char_sim * 0.05
    )

    # Reciprocal-best consistency boosts confidence and reduces false positives.
    reverse_best_idx = np.argmax(combined_scores, axis=0)

    print("Saving best matches to database...")
    mappings_added = 0
    mappings_updated = 0
    low_confidence_count = 0
    
    for i, ipc in enumerate(ipc_sections):
        # Find highest score for this IPC section
        best_bns_idx = np.argmax(combined_scores[i])
        best_score = combined_scores[i][best_bns_idx]
        best_match = bns_sections[best_bns_idx]

        reciprocal = reverse_best_idx[best_bns_idx] == i
        section_num_bonus = 0.08 if _section_number_base(ipc.section_number) == _section_number_base(best_match.section_number) else 0.0
        reciprocal_bonus = 0.07 if reciprocal else 0.0
        calibrated_score = min(0.99, best_score + section_num_bonus + reciprocal_bonus)

        if calibrated_score > 0.33:
            if calibrated_score >= 0.78:
                mapping_type = 'direct'
            elif calibrated_score >= 0.55:
                mapping_type = 'modified'
            else:
                mapping_type = 'needs_review'
                low_confidence_count += 1

            notes = (
                f"hybrid-score={best_score:.2f}, calibrated={calibrated_score:.2f}, "
                f"reciprocal={reciprocal}, number_bonus={section_num_bonus:.2f}"
            )

            existing_mapping = db_session.query(SectionMapping).filter_by(ipc_section_id=ipc.id).first()
            if existing_mapping:
                existing_mapping.bns_section_id = best_match.id
                existing_mapping.confidence = int(calibrated_score * 100)
                existing_mapping.mapping_type = mapping_type
                existing_mapping.notes = notes
                mappings_updated += 1
            else:
                db_session.add(SectionMapping(
                    ipc_section_id=ipc.id,
                    bns_section_id=best_match.id,
                    confidence=int(calibrated_score * 100),
                    mapping_type=mapping_type,
                    notes=notes
                ))
                mappings_added += 1
                
    db_session.commit()
    end_time = time.time()
    print(
        f"Mapping completed! Added {mappings_added}, updated {mappings_updated}, "
        f"needs_review {low_confidence_count} in {end_time - start_time:.2f} seconds."
    )

def print_mappings():
    """Display the created mappings"""
    db_session = Session()
    mappings = db_session.query(
        SectionMapping,
        LegalSection.section_number.label('ipc_num'),
        LegalSection.section_title.label('ipc_title')
    ).join(
        LegalSection, SectionMapping.ipc_section_id == LegalSection.id
    ).all()
    
    # Fetch BNS details separately to avoid complex self-joins for now
    print("\nSample IPC to BNS Mappings:")
    for i, (map_obj, ipc_num, ipc_title) in enumerate(mappings[:20]): # Just print top 20 to avoid terminal spam
        bns_section = db_session.query(LegalSection).filter_by(id=map_obj.bns_section_id).first()
        if bns_section:
            print(f"IPC {ipc_num} ({ipc_title[:30]}...) → BNS {bns_section.section_number} ({bns_section.section_title[:30]}...)")
            print(f"  Type: {map_obj.mapping_type}, Confidence: {map_obj.confidence}%")
            print("-" * 80)

if __name__ == "__main__":
    create_mappings_optimized()
    print_mappings()