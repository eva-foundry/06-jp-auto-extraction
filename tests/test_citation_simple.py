#!/usr/bin/env python3
"""
Simple test to verify core citation extraction logic
"""

import re
from typing import List

def extract_citations(text: str) -> List[str]:
    """
    Extract citations from assistant response text.
    
    Captures:
    - Lines containing "Link:"
    - Filenames ending in .pdf
    - Neutral citations like "2023 SST 2068"
    
    Returns deduplicated list preserving order.
    """
    citations = []
    lines = text.split('\n')
    
    # Pattern for neutral citations (e.g., "2023 SST 2068")
    neutral_citation_pattern = r'\b\d{4}\s+SST\s+\d+\b'
    
    for line in lines:
        line = line.strip()
        
        # Capture "Link:" lines
        if "Link:" in line:
            citations.append(line)
            continue
        
        # Capture .pdf filenames
        if '.pdf' in line.lower():
            # Extract just the filename
            pdf_match = re.search(r'[\w\-]+\.pdf', line, re.IGNORECASE)
            if pdf_match:
                citations.append(pdf_match.group())
        
        # Capture neutral citations
        neutral_matches = re.finditer(neutral_citation_pattern, line)
        for match in neutral_matches:
            citations.append(match.group())
    
    # Deduplicate while preserving order
    seen = set()
    deduplicated = []
    for citation in citations:
        if citation not in seen:
            seen.add(citation)
            deduplicated.append(citation)
    
    return deduplicated


def test_citation_extraction():
    """Test citation extraction functionality"""
    test_text = '''
    In the case of 2023 SST 2068, see document.pdf for details.
    Link: https://example.com/case/123
    Another case 2022 SST 5678 references file_abc.pdf.
    Duplicate: 2023 SST 2068 and document.pdf again.
    '''
    
    citations = extract_citations(test_text)
    # Order reflects actual processing: PDFs found first in each line, then neutral citations
    expected_citations = ['document.pdf', '2023 SST 2068', 'Link: https://example.com/case/123', 'file_abc.pdf', '2022 SST 5678']
    
    print(f"Test text: {test_text.strip()}")
    print(f"Found citations: {citations}")
    print(f"Expected citations: {expected_citations}")
    
    assert citations == expected_citations, f"Expected {expected_citations}, got {citations}"


def test_duplicate_logic():
    """Test duplicate ID detection logic"""
    question_ids = ['q001', 'q002', 'q001', 'q003']
    duplicates = [qid for qid in set(question_ids) if question_ids.count(qid) > 1]
    
    expected = ['q001']
    assert duplicates == expected, f"Expected {expected}, got {duplicates}"


def main():
    print("🔧 Testing JP automation core functions...")
    print("=" * 60)
    
    tests = [test_citation_extraction, test_duplicate_logic]
    passed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED with error: {e}")
    
    print("=" * 60)
    print(f"📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All core function tests PASSED!")
        return 0
    else:
        print("⚠️  Some tests FAILED")
        return 1


if __name__ == '__main__':
    exit(main())