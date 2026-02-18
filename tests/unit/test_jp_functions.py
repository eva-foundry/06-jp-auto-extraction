#!/usr/bin/env python3
"""
Unit tests for JP Automation core functions
Tests citation extraction, input validation, and text stabilization logic
"""

import pytest
import tempfile
import csv
from pathlib import Path
from unittest.mock import Mock, MagicMock
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from run_jp_batch import (
    extract_citations, 
    validate_input_csv, 
    InputValidationError,
    StabilizationTimeoutError
)


class TestCitationExtraction:
    """Test citation extraction from various text formats"""
    
    def test_extract_citations_neutral_format(self):
        """Test extraction of neutral citations like '2023 SST 2068'"""
        text = """
        In the case of 2023 SST 2068, the tribunal found that...
        Also see 2022 SST 1234 for similar reasoning.
        Another case is 2024 SST 9999.
        """
        citations = extract_citations(text)
        
        expected = ['2023 SST 2068', '2022 SST 1234', '2024 SST 9999']
        assert citations == expected
    
    def test_extract_citations_pdf_format(self):
        """Test extraction of PDF filenames"""
        text = """
        Please refer to case_123.pdf for details.
        Also see document-456.pdf and final_report.pdf.
        The file test.PDF should also be detected.
        """
        citations = extract_citations(text)
        
        expected = ['case_123.pdf', 'document-456.pdf', 'final_report.pdf', 'test.PDF']
        assert citations == expected
    
    def test_extract_citations_link_format(self):
        """Test extraction of Link: references"""
        text = """
        Some text here.
        Link: https://example.com/case/12345
        More text.
        Link: https://tribunal.gc.ca/sst-tss/decisions/12345
        """
        citations = extract_citations(text)
        
        expected = [
            'Link: https://example.com/case/12345',
            'Link: https://tribunal.gc.ca/sst-tss/decisions/12345'
        ]
        assert citations == expected
    
    def test_extract_citations_mixed_formats(self):
        """Test extraction of mixed citation types"""
        text = """
        In 2023 SST 2068, the tribunal examined case_doc.pdf.
        Link: https://example.com/cases/2023-sst-2068
        Reference to another_file.pdf was made.
        See also 2022 SST 5678.
        Link: https://tribunal.gc.ca/decisions/5678
        """
        citations = extract_citations(text)
        
        expected = [
            '2023 SST 2068',
            'case_doc.pdf', 
            'Link: https://example.com/cases/2023-sst-2068',
            'another_file.pdf',
            '2022 SST 5678',
            'Link: https://tribunal.gc.ca/decisions/5678'
        ]
        assert citations == expected
    
    def test_extract_citations_deduplication(self):
        """Test that duplicate citations are removed while preserving order"""
        text = """
        First mention of 2023 SST 2068.
        Reference to test.pdf file.
        Another mention of 2023 SST 2068.
        Second reference to test.pdf.
        """
        citations = extract_citations(text)
        
        expected = ['2023 SST 2068', 'test.pdf']
        assert citations == expected
    
    def test_extract_citations_empty_text(self):
        """Test extraction from empty or whitespace-only text"""
        assert extract_citations("") == []
        assert extract_citations("   \\n\\t   ") == []
    
    def test_extract_citations_no_matches(self):
        """Test extraction from text with no citations"""
        text = "This is just regular text with no citations or references."
        assert extract_citations(text) == []


class TestInputValidation:
    """Test CSV input validation functionality"""
    
    def create_test_csv(self, data, headers=['question_id', 'question']):
        """Helper to create temporary CSV files for testing"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
        writer = csv.DictWriter(temp_file, fieldnames=headers)
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        temp_file.close()
        return Path(temp_file.name)
    
    def test_validate_input_csv_valid_file(self):
        """Test validation of a properly formatted CSV"""
        data = [
            {'question_id': 'q001', 'question': 'What is the law on antedates?'},
            {'question_id': 'q002', 'question': 'Show me vacation pay cases.'}
        ]
        csv_path = self.create_test_csv(data)
        
        try:
            errors = validate_input_csv(csv_path)
            assert errors == []
        finally:
            csv_path.unlink()  # Clean up
    
    def test_validate_input_csv_missing_columns(self):
        """Test validation with missing required columns"""
        data = [{'id': 'q001', 'text': 'Some question'}]
        csv_path = self.create_test_csv(data, headers=['id', 'text'])
        
        try:
            errors = validate_input_csv(csv_path)
            assert len(errors) == 1
            assert "Missing required columns" in errors[0]
            assert "question_id" in errors[0] and "question" in errors[0]
        finally:
            csv_path.unlink()
    
    def test_validate_input_csv_duplicate_ids(self):
        """Test validation with duplicate question_ids"""
        data = [
            {'question_id': 'q001', 'question': 'First question'},
            {'question_id': 'q002', 'question': 'Second question'},
            {'question_id': 'q001', 'question': 'Duplicate ID question'}
        ]
        csv_path = self.create_test_csv(data)
        
        try:
            errors = validate_input_csv(csv_path)
            assert len(errors) == 1
            assert "Duplicate question_ids" in errors[0]
            assert "q001" in errors[0]
        finally:
            csv_path.unlink()
    
    def test_validate_input_csv_empty_fields(self):
        """Test validation with empty required fields"""
        data = [
            {'question_id': '', 'question': 'Question without ID'},
            {'question_id': 'q002', 'question': ''},
            {'question_id': '  ', 'question': '   '},  # Whitespace only
        ]
        csv_path = self.create_test_csv(data)
        
        try:
            errors = validate_input_csv(csv_path)
            assert len(errors) >= 2  # Should catch empty ID and empty question
            error_text = ' '.join(errors)
            assert "Empty question_id" in error_text
            assert "Empty question" in error_text
        finally:
            csv_path.unlink()
    
    def test_validate_input_csv_question_too_long(self):
        """Test validation with overly long questions"""
        long_question = "A" * 1001  # Over 1000 char limit
        data = [
            {'question_id': 'q001', 'question': long_question}
        ]
        csv_path = self.create_test_csv(data)
        
        try:
            errors = validate_input_csv(csv_path)
            assert len(errors) == 1
            assert "Question too long" in errors[0]
            assert "1001 chars" in errors[0]
        finally:
            csv_path.unlink()
    
    def test_validate_input_csv_empty_file(self):
        """Test validation with CSV file containing no data rows"""
        csv_path = self.create_test_csv([])  # Empty data
        
        try:
            errors = validate_input_csv(csv_path)
            assert len(errors) == 1
            assert "no data rows" in errors[0]
        finally:
            csv_path.unlink()
    
    def test_validate_input_csv_file_not_found(self):
        """Test validation with non-existent file"""
        fake_path = Path("/nonexistent/file.csv")
        errors = validate_input_csv(fake_path)
        
        assert len(errors) == 1
        assert "not found" in errors[0]
    
    def test_validate_input_csv_encoding_error(self):
        """Test validation with improperly encoded file"""
        # Create a file with invalid UTF-8 encoding
        temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False)
        temp_file.write(b'\\xff\\xfe\\x00\\x00')  # Invalid UTF-8 bytes
        temp_file.close()
        
        try:
            errors = validate_input_csv(Path(temp_file.name))
            assert len(errors) >= 1
            # Should catch encoding error or CSV parsing error
            error_text = ' '.join(errors)
            assert ("encoding" in error_text.lower() or 
                   "reading CSV" in error_text)
        finally:
            Path(temp_file.name).unlink()


class TestStabilizationTimeout:
    """Test custom exception handling"""
    
    def test_stabilization_timeout_error_creation(self):
        """Test that StabilizationTimeoutError can be created and caught"""
        with pytest.raises(StabilizationTimeoutError) as exc_info:
            raise StabilizationTimeoutError("Test timeout message")
        
        assert "Test timeout message" in str(exc_info.value)
    
    def test_input_validation_error_creation(self):
        """Test that InputValidationError can be created and caught"""
        with pytest.raises(InputValidationError) as exc_info:
            raise InputValidationError("Test validation message")
        
        assert "Test validation message" in str(exc_info.value)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])