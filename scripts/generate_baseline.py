#!/usr/bin/env python3
"""
Baseline Evidence Generation Script for JP Automation

Generates reference dataset by running a subset of questions against live JP UI
for manual validation and regression testing baseline.

Usage:
    python generate_baseline.py --input input/questions.csv --count 5 --output evidence/baseline/
"""

import argparse
import csv
import json
import hashlib
from datetime import datetime
from pathlib import Path
import logging
import sys
import os

# Add scripts directory for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from run_jp_batch import run_batch

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def select_baseline_questions(input_csv: Path, count: int) -> Path:
    """
    Select a subset of questions for baseline generation.
    Prioritizes questions with diverse content and stable expectations.
    """
    logger.info(f"Selecting {count} questions from {input_csv}")
    
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        all_questions = list(reader)
    
    if len(all_questions) <= count:
        selected = all_questions
    else:
        # Select evenly distributed questions across the dataset
        step = len(all_questions) // count
        selected = [all_questions[i * step] for i in range(count)]
    
    # Create temporary file with selected questions
    baseline_input = Path("temp_baseline_questions.csv")
    with open(baseline_input, 'w', newline='', encoding='utf-8') as f:
        if selected:
            fieldnames = selected[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(selected)
    
    logger.info(f"Selected questions: {[q['question_id'] for q in selected]}")
    return baseline_input


def generate_content_fingerprints(results_csv: Path) -> dict:
    """
    Generate content fingerprints for baseline comparison.
    Returns dict with question_id -> fingerprint mapping.
    """
    fingerprints = {}
    
    with open(results_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['status'] == 'success':
                # Create fingerprint from answer text and citations
                content = f"{row['answer_text']}|{row['citations']}"
                fingerprint = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
                fingerprints[row['question_id']] = fingerprint
    
    return fingerprints


def create_baseline_package(output_dir: Path, input_file: Path, results_csv: Path):
    """
    Create comprehensive baseline evidence package.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_dir = output_dir / f"baseline_{timestamp}"
    package_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Creating baseline package in {package_dir}")
    
    # Copy input questions
    input_snapshot = package_dir / "baseline_questions.csv"
    input_snapshot.write_text(input_file.read_text(encoding='utf-8'), encoding='utf-8')
    
    # Copy results
    results_snapshot = package_dir / "baseline_results.csv"
    results_snapshot.write_text(results_csv.read_text(encoding='utf-8'), encoding='utf-8')
    
    # Generate JSON version
    with open(results_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        results_data = list(reader)
    
    json_results = package_dir / "baseline_results.json"
    with open(json_results, 'w', encoding='utf-8') as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)
    
    # Generate content fingerprints
    fingerprints = generate_content_fingerprints(results_csv)
    fingerprints_file = package_dir / "content_fingerprints.json"
    with open(fingerprints_file, 'w', encoding='utf-8') as f:
        json.dump(fingerprints, f, indent=2)
    
    # Generate metadata
    metadata = {
        "generation_timestamp": datetime.now().isoformat(),
        "total_questions": len(results_data),
        "successful_questions": len([r for r in results_data if r['status'] == 'success']),
        "failed_questions": len([r for r in results_data if r['status'] != 'success']),
        "baseline_version": "1.0",
        "purpose": "Manual validation and regression testing baseline",
        "validation_required": True,
        "fingerprint_algorithm": "SHA256 truncated to 16 chars"
    }
    
    metadata_file = package_dir / "baseline_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    # Create validation checklist
    checklist = package_dir / "VALIDATION_CHECKLIST.md"
    checklist_content = f"""# Baseline Validation Checklist

## Generated: {metadata['generation_timestamp']}

## Manual Validation Required

For each question in `baseline_results.csv`, verify:

### Legal Accuracy Review
- [ ] Answer content is factually correct
- [ ] Citations are accurate and complete  
- [ ] No hallucinated or incorrect case references
- [ ] Legal reasoning follows established principles

### Technical Quality Review  
- [ ] All citations properly extracted (no missing PDFs/neutral citations)
- [ ] Text formatting is clean (no HTML artifacts)
- [ ] Response completeness (no truncated answers)
- [ ] Consistent citation format

### Questions to Validate:
{chr(10).join([f"- [ ] **{row['question_id']}**: {row['question'][:80]}{'...' if len(row['question']) > 80 else ''}" for row in results_data if row['status'] == 'success'])}

### Failed Questions to Investigate:
{chr(10).join([f"- [ ] **{row['question_id']}**: {row['error']}" for row in results_data if row['status'] != 'success']) or "None"}

## Sign-off
- [ ] Legal analyst review completed: ________________ (Date/Signature)
- [ ] Technical review completed: ________________ (Date/Signature)
- [ ] Approved for regression baseline: ________________ (Date/Signature)

## Notes
_Add any validation notes or exceptions here_

"""
    checklist.write_text(checklist_content, encoding='utf-8')
    
    logger.info(f"✓ Baseline package created: {package_dir}")
    logger.info(f"✓ Files generated:")
    for file in package_dir.iterdir():
        logger.info(f"  - {file.name}")
    
    return package_dir


def main():
    parser = argparse.ArgumentParser(
        description="Generate baseline evidence for JP automation validation"
    )
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Input CSV file with all questions'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=5,
        help='Number of questions to include in baseline (default: 5)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('evidence/baseline'),
        help='Output directory for baseline package (default: evidence/baseline)'
    )
    parser.add_argument(
        '--headed',
        action='store_true',
        help='Run in headed mode (show browser window)'
    )
    
    args = parser.parse_args()
    
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return 1
    
    try:
        # Select subset of questions
        baseline_input = select_baseline_questions(args.input, args.count)
        
        # Generate temporary output file
        temp_output = Path("temp_baseline_results.csv")
        
        logger.info("Starting baseline generation...")
        logger.info("⚠️  Manual validation will be required after generation")
        
        # Run batch processing
        run_batch(baseline_input, temp_output, headless=not args.headed)
        
        # Create baseline package
        package_dir = create_baseline_package(args.output, baseline_input, temp_output)
        
        # Cleanup temporary files
        baseline_input.unlink()
        temp_output.unlink()
        temp_json = temp_output.with_suffix('.json')
        if temp_json.exists():
            temp_json.unlink()
        
        logger.info("🎯 Baseline generation completed successfully")
        logger.info(f"📁 Package location: {package_dir}")
        logger.info("📋 Next steps:")
        logger.info("   1. Review VALIDATION_CHECKLIST.md")
        logger.info("   2. Perform manual legal accuracy validation")
        logger.info("   3. Sign off on baseline for regression testing")
        
        return 0
        
    except Exception as e:
        logger.error(f"Baseline generation failed: {e}")
        
        # Cleanup on failure
        temp_files = ["temp_baseline_questions.csv", "temp_baseline_results.csv", "temp_baseline_results.json"]
        for temp_file in temp_files:
            temp_path = Path(temp_file)
            if temp_path.exists():
                temp_path.unlink()
        
        return 1


if __name__ == '__main__':
    sys.exit(main())