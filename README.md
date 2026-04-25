# IPCtoBNSMapping

## Install core packages
`pip install fastapi uvicorn sqlalchemy beautifulsoup4 requests pdfminer.six spacy scrapy scikit-learn pypdf2`

## Setup and run
1. `python database.py`
2. `python ingest.py`
3. `python mapping_creator.py`
4. `uvicorn api:app --reload`
5. `streamlit run ui.py`

## New capabilities
- Legal-action retrieval endpoint: `GET /legal-action?q=<query>&code_type=IPC|BNS`
- Automatic keyword extraction from natural language queries.
- Ranked clauses with relevance score + matched keywords.
- IPC<->BNS counterpart mappings included with each result.
- Improved mapping confidence via hybrid TF-IDF (word + char n-grams), reciprocal-best boost, and `needs_review` tag for low-confidence pairs.
