#!/usr/bin/env python3
"""
Test input validation with the actual questions.csv file
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Mock the logger to avoid dependency
class MockLogger:
    def debug(self, msg): pass
    def info(self, msg): print(f"INFO: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")  
    def error(self, msg): print(f"ERROR: {msg}")

# Import validation function without playwright dependencies
def test_real_questions_csv():
    """Test validation with the actual questions.csv file"""
    
    # Create minimal validation function inline to avoid import issues
    import csv
    from pathlib import Path
    
    def validate_input_csv(csv_path):
        errors = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Check required columns exist
                required_columns = ['question_id', 'question']
                missing_columns = [col for col in required_columns if col not in reader.fieldnames]
                if missing_columns:
                    errors.append(f"Missing required columns: {', '.join(missing_columns)}")
                    return errors
                
                rows = list(reader)
                
                # Check for duplicate question_ids
                question_ids = [row['question_id'] for row in rows]
                duplicates = [qid for qid in set(question_ids) if question_ids.count(qid) > 1]
                if duplicates:
                    errors.append(f"Duplicate question_ids found: {', '.join(duplicates)}")
                
                # Check for empty or invalid questions
                for i, row in enumerate(rows, 2):
                    qid = row['question_id'].strip()
                    question = row['question'].strip()
                    
                    if not qid:
                        errors.append(f"Row {i}: Empty question_id")
                    
                    if not question:
                        errors.append(f"Row {i}: Empty question")
                    elif len(question) > 1000:
                        errors.append(f"Row {i}: Question too long ({len(question)} chars, max 1000)")
                    
                if not rows:
                    errors.append("CSV file contains no data rows")
                    
        except UnicodeDecodeError:
            errors.append("File encoding error - ensure CSV is UTF-8 encoded")
        except FileNotFoundError:
            errors.append(f"Input file not found: {csv_path}")
        except Exception as e:
            errors.append(f"Error reading CSV file: {str(e)}")
        
        return errors
    
    # Test with actual questions file
    questions_path = Path("input/questions.csv")
    
    if not questions_path.exists():
        print("❌ questions.csv not found at input/questions.csv")
        return False
    
    print(f"🔍 Validating {questions_path}")
    errors = validate_input_csv(questions_path)
    
    if errors:
        print("❌ Validation FAILED:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("✅ Input validation PASSED")
        
        # Show some stats  
        with open(questions_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            print(f"  - {len(rows)} questions loaded")
            print(f"  - Question IDs: {rows[0]['question_id']} to {rows[-1]['question_id']}")
            avg_length = sum(len(row['question']) for row in rows) / len(rows)
            print(f"  - Average question length: {avg_length:.1f} characters")
        
        return True


if __name__ == '__main__':
    success = test_real_questions_csv()
    if success:
        print("\n🎉 All validation tests PASSED!")
        exit(0)
    else:
        print("\n⚠️ Validation tests FAILED!")
        exit(1)