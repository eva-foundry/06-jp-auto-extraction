#!/usr/bin/env python3
"""
JP Automation - Cleanup Script
==============================

Professional cleanup script to archive redundant files and organize
the project according to professional standards.

Author: JP Automation System  
Version: 1.0
Date: 2026-01-23
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Set UTF-8 encoding for Windows compatibility
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

from jp_naming_system import get_timestamp

# Files to archive (redundant/legacy)
REDUNDANT_FILES = [
    "README.md",                    # Replace with README_PROFESSIONAL.md  
    "README-UPDATED.md",           # Merged into professional README
    "SESSION_GUIDE.md",            # Content moved to professional README
    "PLAN.md",                     # Replaced by IMPLEMENTATION_PLAN.md
    "COMPLETED_PROJECT.md",        # Content merged into README
    "ARTIFACT-LOCATIONS.md"        # Content integrated into README
]

# Scripts to archive (legacy versions)
LEGACY_SCRIPTS = [
    "scripts/run_jp_batch.py",     # Replaced by jp_automation_main.py
    "scripts/run_jp_aggressive.py" # Legacy version
]

# Files to keep as-is (core project files)
KEEP_FILES = [
    "README_PROFESSIONAL.md",      # New comprehensive README
    "ACCEPTANCE.md",               # Core acceptance criteria  
    "IMPLEMENTATION_PLAN.md",      # Transformation blueprint
    "PROFESSIONAL_TRANSFORMATION_STANDARD.md",  # Standards template
    "coding_standards.md",         # Professional standards
    "scripts/jp_automation_main.py",      # Professional main script
    "scripts/jp_naming_system.py",        # Professional utilities
    "scripts/jp_exceptions.py",           # Professional error handling  
    "scripts/jp_acceptance_tester.py",    # Automated validation
    "scripts/jp_evidence_collector.py",  # Evidence collection
]


class JPCleanupManager:
    """Professional cleanup and archival system
    
    Systematically archives redundant files while preserving
    important historical versions and maintaining audit trails.
    """
    
    def __init__(self, project_dir: Path):
        """Initialize cleanup manager
        
        Args:
            project_dir: Project root directory
        """
        self.project_dir = Path(project_dir)
        self.timestamp = get_timestamp()
        
        # Create archive directory
        self.archive_dir = self.project_dir / "archive" / f"pre_professional_{self.timestamp}"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Cleanup report
        self.cleanup_report = {
            "timestamp": datetime.now().isoformat(),
            "archived_files": [],
            "kept_files": [],
            "cleanup_summary": {}
        }
    
    def execute_cleanup(self) -> Dict[str, Any]:
        """Execute comprehensive cleanup process
        
        Returns:
            Detailed cleanup report
        """
        print(f"[INFO] Starting professional cleanup - Archive: {self.archive_dir}")
        
        # Archive redundant documentation
        self._archive_redundant_documentation()
        
        # Archive legacy scripts  
        self._archive_legacy_scripts()
        
        # Rename professional README to standard name
        self._finalize_documentation()
        
        # Generate cleanup report
        self._generate_cleanup_report()
        
        print(f"[INFO] Cleanup completed - See archive at: {self.archive_dir}")
        return self.cleanup_report
    
    def _archive_redundant_documentation(self):
        """Archive redundant documentation files"""
        print("[INFO] Archiving redundant documentation files...")
        
        for file_name in REDUNDANT_FILES:
            file_path = self.project_dir / file_name
            
            if file_path.exists():
                # Create archive path  
                archive_path = self.archive_dir / file_name
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy to archive
                shutil.copy2(file_path, archive_path)
                
                # Remove original
                file_path.unlink()
                
                self.cleanup_report["archived_files"].append({
                    "original": str(file_path),
                    "archived_to": str(archive_path),
                    "type": "redundant_documentation"
                })
                
                print(f"  [ARCHIVED] {file_name}")
    
    def _archive_legacy_scripts(self):
        """Archive legacy script files"""
        print("[INFO] Archiving legacy scripts...")
        
        for script_path in LEGACY_SCRIPTS:
            full_path = self.project_dir / script_path
            
            if full_path.exists():
                # Create archive path
                archive_path = self.archive_dir / script_path  
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy to archive
                shutil.copy2(full_path, archive_path)
                
                # Remove original
                full_path.unlink()
                
                self.cleanup_report["archived_files"].append({
                    "original": str(full_path),
                    "archived_to": str(archive_path),
                    "type": "legacy_script"
                })
                
                print(f"  [ARCHIVED] {script_path}")
    
    def _finalize_documentation(self):
        """Rename professional README to standard README.md"""
        print("[INFO] Finalizing documentation structure...")
        
        professional_readme = self.project_dir / "README_PROFESSIONAL.md"
        standard_readme = self.project_dir / "README.md"
        
        if professional_readme.exists():
            # Rename professional README to standard name
            shutil.move(professional_readme, standard_readme)
            
            self.cleanup_report["kept_files"].append({
                "file": str(standard_readme),
                "action": "renamed_from_README_PROFESSIONAL.md",
                "type": "primary_documentation"
            })
            
            print(f"  [RENAMED] README_PROFESSIONAL.md -> README.md")
    
    def _generate_cleanup_report(self):
        """Generate comprehensive cleanup report"""
        
        # Count files by type
        archived_by_type = {}
        for item in self.cleanup_report["archived_files"]:
            file_type = item["type"]
            archived_by_type[file_type] = archived_by_type.get(file_type, 0) + 1
        
        # Verify kept files still exist
        for keep_file in KEEP_FILES:
            file_path = self.project_dir / keep_file
            if file_path.exists():
                self.cleanup_report["kept_files"].append({
                    "file": str(file_path),
                    "action": "verified_exists", 
                    "type": "professional_component"
                })
        
        # Summary statistics
        self.cleanup_report["cleanup_summary"] = {
            "total_archived": len(self.cleanup_report["archived_files"]),
            "total_kept": len(self.cleanup_report["kept_files"]),
            "archived_by_type": archived_by_type,
            "archive_directory": str(self.archive_dir),
            "cleanup_complete": True
        }
    
    def save_cleanup_report(self) -> Path:
        """Save cleanup report to file
        
        Returns:
            Path to saved report file
        """
        import json
        
        report_path = self.project_dir / f"cleanup_report_{self.timestamp}.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.cleanup_report, f, indent=2)
        
        return report_path


def main():
    """Main cleanup execution"""
    
    # Get project directory
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    
    print(f"JP Automation Professional Cleanup")
    print(f"Project Directory: {project_dir}")
    print(f"Timestamp: {get_timestamp()}")
    print()
    
    # Execute cleanup
    cleanup_manager = JPCleanupManager(project_dir)
    report = cleanup_manager.execute_cleanup()
    
    # Save report
    report_path = cleanup_manager.save_cleanup_report()
    
    # Print summary
    summary = report["cleanup_summary"]
    print()
    print("[CLEANUP SUMMARY]")
    print(f"Files Archived: {summary['total_archived']}")
    print(f"Files Kept: {summary['total_kept']}")
    print(f"Archive Location: {summary['archive_directory']}")
    print(f"Report Saved: {report_path}")
    print()
    
    print("[ARCHIVED BY TYPE]")
    for file_type, count in summary["archived_by_type"].items():
        print(f"  {file_type}: {count} files")
    
    print()
    print("[SUCCESS] Professional cleanup completed!")
    print(f"The project now follows professional standards with clean structure.")
    print(f"All legacy files have been safely archived to: {summary['archive_directory']}")


if __name__ == "__main__":
    main()