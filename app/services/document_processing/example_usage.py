"""
Example usage of the PDF processor for academic documents.

This module demonstrates how to use the comprehensive PDF processing
capabilities for extracting text, figures, tables, citations, and metadata.
"""

import asyncio
from pathlib import Path
from uuid import uuid4

from app.services.document_processing.processors.pdf_processor import PDFProcessor
from app.domain.schemas.document_processing import (
    ProcessingRequest,
    DocumentType,
)


async def process_academic_pdf_example():
    """Example of processing an academic PDF document."""
    
    # Initialize the PDF processor
    config = {
        'max_file_size_mb': 50,
        'max_pages': 100,
        'image_dpi': 150,
        'enable_ocr': False,
        'max_workers': 2,
    }
    
    processor = PDFProcessor(config)
    
    # Example PDF file path (replace with actual path)
    pdf_path = "/path/to/academic_paper.pdf"
    
    if not Path(pdf_path).exists():
        print(f"Example PDF not found at {pdf_path}")
        print("Please provide a valid PDF path to test the processor.")
        return
    
    # Create processing request
    request = ProcessingRequest(
        document_id=uuid4(),
        file_path=pdf_path,
        document_type=DocumentType.PDF,
        extract_text=True,
        extract_figures=True,
        extract_tables=True,
        extract_citations=True,
        extract_references=True,
        extract_metadata=True,
        preserve_layout=True,
        multi_column_handling=True,
    )
    
    try:
        print(f"Processing PDF: {pdf_path}")
        print("=" * 50)
        
        # Process the document
        result = await processor.process(request)
        
        # Display results
        print(f"Status: {result.status}")
        print(f"Processing time: {result.processing_time:.2f} seconds")
        print()
        
        # Metadata
        if result.metadata:
            print("METADATA:")
            print(f"  Title: {result.metadata.title}")
            print(f"  Authors: {', '.join(result.metadata.authors)}")
            print(f"  Year: {result.metadata.year}")
            print(f"  DOI: {result.metadata.doi}")
            print()
        
        # Text elements
        print(f"TEXT ELEMENTS: {len([e for e in result.elements if e.element_type == 'text'])}")
        text_elements = [e for e in result.elements if e.element_type == 'text'][:5]
        for i, element in enumerate(text_elements):
            print(f"  {i+1}. {element.content[:100]}...")
        print()
        
        # Figures
        print(f"FIGURES: {len(result.figures)}")
        for i, figure in enumerate(result.figures[:3]):
            print(f"  {i+1}. {figure.content}")
            if figure.caption:
                print(f"      Caption: {figure.caption}")
        print()
        
        # Tables
        print(f"TABLES: {len(result.tables)}")
        for i, table in enumerate(result.tables[:3]):
            print(f"  {i+1}. {table.content}")
            if table.headers:
                print(f"      Headers: {', '.join(table.headers)}")
            print(f"      Rows: {len(table.rows)}")
        print()
        
        # Citations
        print(f"CITATIONS: {len(result.citations)}")
        for i, citation in enumerate(result.citations[:5]):
            print(f"  {i+1}. {citation.content}")
            if citation.authors:
                print(f"      Authors: {', '.join(citation.authors)}")
            if citation.year:
                print(f"      Year: {citation.year}")
        print()
        
        # References
        print(f"REFERENCES: {len(result.references)}")
        for i, reference in enumerate(result.references[:3]):
            print(f"  {i+1}. {reference.content[:150]}...")
            if reference.title:
                print(f"      Title: {reference.title}")
            if reference.journal:
                print(f"      Journal: {reference.journal}")
        print()
        
        # Layout information
        print(f"LAYOUT INFO: {len(result.layout_info)} pages")
        for i, layout in enumerate(result.layout_info[:3]):
            print(f"  Page {i+1}: {layout.columns} columns, "
                  f"{len(layout.text_regions)} text regions, "
                  f"{len(layout.figure_regions)} figure regions")
        print()
        
        # Document structure
        print(f"DOCUMENT SECTIONS: {len(result.sections)}")
        for section in result.sections[:5]:
            print(f"  {section.title} (Level {section.level})")
            print(f"    Elements: {len(section.elements)}")
            if section.subsections:
                print(f"    Subsections: {len(section.subsections)}")
        
        # Warnings
        if result.warnings:
            print("\nWARNINGS:")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        print("=" * 50)
        print("Processing completed successfully!")
        
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")


async def validate_pdf_example():
    """Example of validating a PDF document."""
    
    processor = PDFProcessor()
    pdf_path = "/path/to/academic_paper.pdf"
    
    try:
        is_valid = await processor.validate_document(pdf_path)
        print(f"PDF validation result: {is_valid}")
        
        # Check processor capabilities
        capabilities = processor.capabilities
        print("\nProcessor capabilities:")
        for name, capability in capabilities.items():
            status = "✓" if capability.supported else "✗"
            print(f"  {status} {capability.name}: {capability.description}")
            
    except Exception as e:
        print(f"Validation error: {str(e)}")


async def extract_metadata_only_example():
    """Example of extracting only metadata from a PDF."""
    
    processor = PDFProcessor()
    pdf_path = "/path/to/academic_paper.pdf"
    
    try:
        metadata = await processor.extract_metadata(pdf_path)
        
        print("METADATA EXTRACTION:")
        print(f"  Title: {metadata.title}")
        print(f"  Authors: {metadata.authors}")
        print(f"  Subject: {metadata.subject}")
        print(f"  Creation Date: {metadata.creation_date}")
        print(f"  Keywords: {metadata.keywords}")
        print(f"  DOI: {metadata.doi}")
        
    except Exception as e:
        print(f"Metadata extraction error: {str(e)}")


async def text_extraction_example():
    """Example of extracting text with layout preservation."""
    
    processor = PDFProcessor()
    pdf_path = "/path/to/academic_paper.pdf"
    
    try:
        # Extract text with layout preservation
        text_elements = await processor.extract_text(pdf_path, preserve_layout=True)
        
        print(f"EXTRACTED TEXT ELEMENTS: {len(text_elements)}")
        
        # Show elements with their positions
        for i, element in enumerate(text_elements[:10]):
            print(f"\nElement {i+1}:")
            print(f"  Content: {element.content[:100]}...")
            if element.bbox:
                print(f"  Position: ({element.bbox.x0:.1f}, {element.bbox.y0:.1f}) "
                      f"to ({element.bbox.x1:.1f}, {element.bbox.y1:.1f})")
                print(f"  Page: {element.bbox.page}")
            if element.style:
                print(f"  Font: {element.style.font_name}, Size: {element.style.font_size}")
            if element.reading_order is not None:
                print(f"  Reading order: {element.reading_order}")
            if element.column_index is not None:
                print(f"  Column: {element.column_index}")
        
    except Exception as e:
        print(f"Text extraction error: {str(e)}")


if __name__ == "__main__":
    """Run examples."""
    print("PDF Processor Examples")
    print("=" * 50)
    
    # Run the main processing example
    asyncio.run(process_academic_pdf_example())
    
    print("\n" + "=" * 50)
    print("Additional Examples:")
    
    # Run other examples
    # asyncio.run(validate_pdf_example())
    # asyncio.run(extract_metadata_only_example()) 
    # asyncio.run(text_extraction_example())