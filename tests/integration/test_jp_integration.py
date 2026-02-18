#!/usr/bin/env python3
"""
Integration tests for JP Automation
Tests end-to-end functionality with mock server and controlled scenarios
"""

import pytest
import tempfile
import csv
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add scripts directory to path for imports  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from run_jp_batch import run_batch, InputValidationError


class TestEndToEndIntegration:
    """Test complete batch processing workflow"""
    
    def create_test_input(self, questions_data):
        """Helper to create test input CSV"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
        writer = csv.DictWriter(temp_file, fieldnames=['question_id', 'question'])
        writer.writeheader()
        for row in questions_data:
            writer.writerow(row)
        temp_file.close()
        return Path(temp_file.name)
    
    def test_batch_input_validation_failure(self):
        """Test that batch processing fails gracefully on invalid input"""
        # Create invalid input (duplicate IDs)
        invalid_data = [
            {'question_id': 'q001', 'question': 'First question'},
            {'question_id': 'q001', 'question': 'Duplicate question'}  # Duplicate ID
        ]
        input_path = self.create_test_input(invalid_data)
        output_path = Path(tempfile.mktemp(suffix='.csv'))
        
        try:
            with pytest.raises(InputValidationError) as exc_info:
                run_batch(input_path, output_path, headless=True)
            
            assert "Duplicate question_ids" in str(exc_info.value)
            assert not output_path.exists()  # Output should not be created
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()
    
    def test_batch_creates_output_structure(self):
        """Test that batch processing creates expected output files and directories"""
        valid_data = [
            {'question_id': 'q001', 'question': 'Test question one'},
            {'question_id': 'q002', 'question': 'Test question two'}
        ]
        input_path = self.create_test_input(valid_data)
        output_path = Path(tempfile.mktemp(suffix='.csv'))
        
        # Mock the browser automation parts to avoid actual browser launch
        with patch('run_jp_batch.sync_playwright') as mock_playwright:
            mock_browser = MagicMock()
            mock_page = MagicMock()
            mock_context = MagicMock()
            
            # Setup mock chain
            mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page
            
            # Mock successful question processing
            with patch('run_jp_batch.process_question') as mock_process:
                mock_process.return_value = (
                    "Test answer text with citations 2023 SST 1234",
                    ["2023 SST 1234"], 
                    "success", 
                    ""
                )
                
                try:
                    run_batch(input_path, output_path, headless=True)
                    
                    # Check output CSV was created
                    assert output_path.exists()
                    
                    # Check JSON output was created
                    json_path = output_path.with_suffix('.json')
                    assert json_path.exists()
                    
                    # Verify CSV structure
                    with open(output_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                        
                        assert len(rows) == 2
                        expected_columns = ['question_id', 'question', 'answer_text', 'citations', 'timestamp', 'status', 'error']
                        assert list(reader.fieldnames) == expected_columns
                        
                        # Check first row content
                        assert rows[0]['question_id'] == 'q001'
                        assert rows[0]['status'] == 'success'
                        assert rows[0]['citations'] == '2023 SST 1234'
                    
                    # Verify JSON structure
                    with open(json_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                        assert len(json_data) == 2
                        assert json_data[0]['question_id'] == 'q001'
                        assert json_data[0]['status'] == 'success'
                        
                finally:
                    # Cleanup
                    input_path.unlink()
                    if output_path.exists():
                        output_path.unlink()
                    if json_path.exists():
                        json_path.unlink()
    
    def test_batch_handles_processing_failures(self):
        """Test that batch continues processing even when individual questions fail"""
        valid_data = [
            {'question_id': 'q001', 'question': 'Good question'},
            {'question_id': 'q002', 'question': 'Failing question'},  
            {'question_id': 'q003', 'question': 'Another good question'}
        ]
        input_path = self.create_test_input(valid_data)
        output_path = Path(tempfile.mktemp(suffix='.csv'))
        
        # Mock browser automation
        with patch('run_jp_batch.sync_playwright') as mock_playwright:
            mock_browser = MagicMock()
            mock_page = MagicMock()
            mock_context = MagicMock()
            
            mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page
            
            # Mock mixed success/failure results
            def mock_process_side_effect(page, question_id, question):
                if question_id == 'q002':
                    return ("", [], "error", "Simulated processing error")
                else:
                    return (f"Answer for {question_id}", [f"citation_{question_id}"], "success", "")
            
            with patch('run_jp_batch.process_question', side_effect=mock_process_side_effect):
                try:
                    run_batch(input_path, output_path, headless=True)
                    
                    # Verify all questions were processed despite failure
                    with open(output_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                        
                        assert len(rows) == 3
                        
                        # Check success cases
                        success_rows = [r for r in rows if r['status'] == 'success']
                        assert len(success_rows) == 2
                        
                        # Check failure case
                        error_rows = [r for r in rows if r['status'] == 'error']
                        assert len(error_rows) == 1
                        assert error_rows[0]['question_id'] == 'q002'
                        assert "Simulated processing error" in error_rows[0]['error']
                        
                finally:
                    # Cleanup
                    input_path.unlink()
                    if output_path.exists():
                        output_path.unlink()
                    json_path = output_path.with_suffix('.json')
                    if json_path.exists():
                        json_path.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])