#!/usr/bin/env python3
"""
JP Project Runner - Professional Automation Wrapper
===================================================

Reusable project automation wrapper that handles:
- Working directory detection and navigation
- Environment variable configuration
- Parameter validation and help
- Professional error messaging
- Cross-platform compatibility

This wrapper pattern can be applied to other projects by adapting the
script paths and parameter mappings.

Usage:
    python jp_project_runner.py input/questions.csv output/jp_answers.csv
    python jp_project_runner.py input/questions.csv output/jp_answers.csv --headed
    python jp_project_runner.py input/questions.csv output/jp_answers.csv --limit 5
    python jp_project_runner.py --help

Author: JP Automation System
Version: 1.0 (Professional Wrapper)
Date: 2026-01-23
"""

import os
import sys
import argparse
from pathlib import Path
import subprocess
from typing import Optional, List

# Set UTF-8 encoding for Windows compatibility
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

class JPProjectRunner:
    """Professional project wrapper for automated execution"""
    
    def __init__(self):
        self.project_root = self.find_project_root()
        self.main_script = "scripts/jp_automation_main.py"
        
    def find_project_root(self) -> Path:
        """Auto-detect project root directory"""
        current = Path.cwd()
        
        # Look for project indicators in current and parent directories
        indicators = [
            "scripts/jp_automation_main.py",
            "input/questions.csv",
            "ACCEPTANCE.md"
        ]
        
        # Check current directory first
        for indicator in indicators:
            if (current / indicator).exists():
                return current
                
        # Check if we're in a subdirectory of the project
        for parent in current.parents:
            for indicator in indicators:
                if (parent / indicator).exists():
                    return parent
        
        # If not found, assume current directory
        return current
    
    def validate_environment(self) -> tuple[bool, str]:
        """Validate project environment and dependencies"""
        # Check main script exists
        main_script_path = self.project_root / self.main_script
        if not main_script_path.exists():
            return False, f"Main script not found: {main_script_path}"
        
        # Check input directory exists
        input_dir = self.project_root / "input"
        if not input_dir.exists():
            return False, f"Input directory not found: {input_dir}"
        
        # Check if Python has required modules
        try:
            import pandas
            import asyncio
        except ImportError as e:
            return False, f"Required Python module missing: {e}"
        
        return True, "Environment validation successful"
    
    def validate_csv_file(self, csv_path: Path) -> tuple[bool, str]:
        """Validate CSV file format and structure"""
        if not csv_path.exists():
            return False, f"Input CSV file not found: {csv_path}"
        
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            
            # Check required columns
            required_cols = ["question_id", "question"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                return False, f"Missing required columns: {missing_cols}"
            
            # Check for empty questions
            if df['question'].isnull().any():
                return False, "CSV contains empty question fields"
            
            return True, f"CSV validation successful: {len(df)} questions loaded"
            
        except Exception as e:
            return False, f"CSV parsing error: {str(e)}\nEnsure questions with commas are properly quoted: \"question,with,commas\""
    
    def build_command(self, input_file: str, output_file: str, **kwargs) -> List[str]:
        """Build command line arguments for main script"""
        cmd = [
            sys.executable,
            str(self.project_root / self.main_script),
            "--input", input_file,
            "--output", output_file
        ]
        
        # Add optional parameters
        if kwargs.get('headed'):
            cmd.append('--headed')
        if kwargs.get('limit'):
            cmd.extend(['--limit', str(kwargs['limit'])])
        if kwargs.get('connect'):
            cmd.append('--connect')
        
        return cmd
    
    def execute_with_encoding(self, cmd: List[str]) -> int:
        """Execute command with proper encoding environment"""
        # Set environment for Windows compatibility
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # Change to project root directory
        original_cwd = os.getcwd()
        os.chdir(self.project_root)
        
        try:
            # Execute command
            print(f"[INFO] Executing from: {self.project_root}")
            print(f"[INFO] Command: {' '.join(cmd)}")
            print(f"[INFO] Encoding: UTF-8")
            print("-" * 60)
            
            result = subprocess.run(cmd, env=env)
            return result.returncode
            
        finally:
            # Restore original directory
            os.chdir(original_cwd)
    
    def run(self, args: argparse.Namespace) -> int:
        """Main execution function"""
        try:
            # Validate environment
            valid, message = self.validate_environment()
            if not valid:
                print(f"[ERROR] Environment validation failed: {message}")
                return 1
            
            print(f"[PASS] {message}")
            
            # Validate CSV input file
            input_path = self.project_root / args.input_file
            valid, message = self.validate_csv_file(input_path)
            if not valid:
                print(f"[ERROR] CSV validation failed: {message}")
                return 1
                
            print(f"[PASS] {message}")
            
            # Build and execute command
            cmd = self.build_command(
                args.input_file,
                args.output_file,
                headed=args.headed,
                limit=args.limit,
                connect=args.connect
            )
            
            return self.execute_with_encoding(cmd)
            
        except KeyboardInterrupt:
            print("\n[INFO] Execution interrupted by user")
            return 1
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            return 1


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="JP Project Runner - Professional automation wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python jp_project_runner.py input/questions.csv output/jp_answers.csv
  python jp_project_runner.py input/questions.csv output/jp_answers.csv --headed
  python jp_project_runner.py input/questions.csv output/jp_answers.csv --limit 5 --connect

CSV Format Requirements:
  - Required columns: question_id, question
  - UTF-8 encoding recommended
  - Questions with commas must be quoted: "question,with,commas"
  - Use validation: python -c "import pandas as pd; pd.read_csv('input/questions.csv')"

For full script options: python scripts/jp_automation_main.py --help
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Input CSV file path (relative to project root)'
    )
    parser.add_argument(
        'output_file', 
        help='Output CSV file path (relative to project root)'
    )
    parser.add_argument(
        '--headed',
        action='store_true',
        help='Show browser window (for debugging)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Process only first N questions (for testing)'
    )
    parser.add_argument(
        '--connect',
        action='store_true',
        help='Connect to existing browser instance'
    )
    
    args = parser.parse_args()
    
    # Create runner and execute
    runner = JPProjectRunner()
    return runner.run(args)


if __name__ == "__main__":
    sys.exit(main())