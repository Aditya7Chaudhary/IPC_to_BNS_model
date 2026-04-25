from sqlalchemy import create_engine, Column, Integer, String, Text, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

class LegalSection(Base):
    __tablename__ = 'legal_sections'
    
    id = Column(Integer, primary_key=True)
    code_type = Column(String(10))  # 'IPC' or 'BNS'
    section_number = Column(String(20))
    section_title = Column(String(255))
    full_text = Column(Text)
    keywords = Column(Text)
    effective_date = Column(Date)
    repeal_date = Column(Date, nullable=True)

class SectionMapping(Base):
    __tablename__ = 'section_mappings'
    
    id = Column(Integer, primary_key=True)
    ipc_section_id = Column(Integer, ForeignKey('legal_sections.id'))
    bns_section_id = Column(Integer, ForeignKey('legal_sections.id'))
    confidence = Column(Integer)  # 0-100
    mapping_type = Column(String(20))  # 'direct', 'modified', etc.
    notes = Column(Text)

# Initialize DB
engine = create_engine('sqlite:///legal_mappings.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)