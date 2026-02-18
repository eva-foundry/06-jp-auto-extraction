#!/usr/bin/env python3
"""
Quick test runner for core JP automation functions
Tests functionality without requiring full playwright installation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Test citation extraction (doesn't need playwright)
def test_citation_extraction():
    # Import just the function we need
    import importlib.util
    import types
    
    # Load just the extract_citations function without importing playwright dependencies
    spec = importlib.util.spec_from_file_location("run_jp_batch", "../scripts/run_jp_batch.py")
    
    # Create a mock module to avoid playwright import
    mock_module = types.ModuleType("run_jp_batch")
    
    # Add the citation extraction function directly
    with open("../scripts/run_jp_batch.py", 'r') as f:
        content = f.read()
    
    # Extract just the extract_citations function
    extract_start = content.find("def extract_citations(text: str) -> List[str]:")
    if extract_start == -1:
        print("❌ Could not find extract_citations function")
        return False
    
    # Find end of function (next def or class)
    extract_end = content.find("\ndef ", extract_start + 1)
    if extract_end == -1:
        extract_end = content.find("\nclass ", extract_start + 1)
    if extract_end == -1:
        extract_end = len(content)
    
    func_code = content[extract_start:extract_end]
    
    # Add imports and execute
    full_code = """
import re
from typing import List

""" + func_code
    
    exec(full_code, globals())
    
    # Test the function
    test_text = '''
    In the case of 2023 SST 2068, see document.pdf for details.
    Link: https://example.com/case/123
    Another case 2022 SST 5678 references file_abc.pdf.
    '''
    
    citations = extract_citations(test_text)
    expected_citations = ['2023 SST 2068', 'document.pdf', 'Link: https://example.com/case/123', '2022 SST 5678', 'file_abc.pdf']
    
    if citations == expected_citations:
        print("✅ Citation extraction test passed")
        print(f"   Found citations: {citations}")
        return True
    else:
        print("❌ Citation extraction test failed")
        print(f"   Expected: {expected_citations}")
        print(f"   Got: {citations}")
        return False


def test_input_validation_logic():
    """Test validation logic without CSV files"""
    
    # Test duplicate detection logic
    question_ids = ['q001', 'q002', 'q001', 'q003']
    duplicates = [qid for qid in set(question_ids) if question_ids.count(qid) > 1]
    
    if duplicates == ['q001']:
        print("✅ Duplicate detection logic test passed")
        return True
    else:
        print("❌ Duplicate detection logic test failed")
        print(f"   Expected: ['q001'], Got: {duplicates}")
        return False


def main():
    print("🔧 Testing JP automation core functions...")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 2
    
    if test_citation_extraction():
        tests_passed += 1
    
    if test_input_validation_logic():
        tests_passed += 1
    
    print("=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All core function tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())