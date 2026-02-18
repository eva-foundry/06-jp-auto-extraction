#!/usr/bin/env python3
"""
JP Authentication Analysis Tool
===============================

Analyzes JP authentication patterns and session management to diagnose
authentication issues and provide session management recommendations.

Author: JP Automation System
Version: 1.0
Date: 2026-01-23

Usage:
    python scripts/analyze_jp_authentication.py
    python scripts/analyze_jp_authentication.py --clean-sessions
"""

import os
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

def analyze_authentication_history(project_root: Path) -> Dict[str, Any]:
    """Analyze authentication patterns from logs and session files"""
    
    print("[INFO] Analyzing JP authentication patterns...")
    
    # Check for existing session files
    session_dir = project_root / "sessions"
    session_files = []
    
    if session_dir.exists():
        session_files = list(session_dir.rglob("*"))
        print(f"[FOUND] Session directory exists: {session_dir}")
        print(f"[FOUND] {len(session_files)} session-related files:")
        for session_file in session_files:
            relative_path = session_file.relative_to(project_root)
            if session_file.is_file():
                size = session_file.stat().st_size
                modified = datetime.fromtimestamp(session_file.stat().st_mtime)
                print(f"  - {relative_path} ({size} bytes, modified: {modified})")
            else:
                print(f"  - {relative_path}/ (directory)")
    else:
        print("[INFO] No sessions directory found")
    
    # Analyze session metadata if available
    session_metadata_file = session_dir / "jp_browser_session.json"
    session_analysis = {"has_session": False, "session_valid": False, "session_age_hours": 0}
    
    if session_metadata_file.exists():
        try:
            with open(session_metadata_file, 'r') as f:
                session_data = json.load(f)
            
            session_analysis["has_session"] = True
            created_str = session_data.get('created', '1970-01-01')
            created = datetime.fromisoformat(created_str)
            age = datetime.now() - created
            session_analysis["session_age_hours"] = age.total_seconds() / 3600
            session_analysis["session_valid"] = age.total_seconds() < (24 * 3600)  # 24 hours
            
            print(f"[SESSION] Metadata found:")
            print(f"  - Created: {created}")
            print(f"  - Age: {session_analysis['session_age_hours']:.1f} hours")
            print(f"  - Valid: {session_analysis['session_valid']}")
            print(f"  - Status: {session_data.get('status', 'unknown')}")
            
        except Exception as e:
            print(f"[ERROR] Failed to parse session metadata: {e}")
    
    # Check for browser context
    context_dir = session_dir / "browser_context"
    storage_state_file = context_dir / "storage_state.json"
    
    context_analysis = {"has_context": False, "storage_state_exists": False}
    
    if context_dir.exists():
        context_analysis["has_context"] = True
        if storage_state_file.exists():
            context_analysis["storage_state_exists"] = True
            size = storage_state_file.stat().st_size
            print(f"[CONTEXT] Browser storage state found ({size} bytes)")
        else:
            print("[CONTEXT] Context directory exists but no storage state file")
    else:
        print("[CONTEXT] No browser context directory found")
    
    # Analyze logs for authentication patterns
    logs_dir = project_root / "logs"
    log_analysis = {"total_logs": 0, "auth_success_count": 0, "auth_bypass_count": 0, "auth_errors": 0}
    
    if logs_dir.exists():
        log_files = list(logs_dir.glob("jp_execution_*.log"))
        log_analysis["total_logs"] = len(log_files)
        print(f"[LOGS] Found {len(log_files)} execution logs")
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    
                    if "authentication successful" in content or "login successful" in content:
                        log_analysis["auth_success_count"] += 1
                    elif "using existing session" in content or "session verification successful" in content:
                        log_analysis["auth_bypass_count"] += 1
                    elif "authentication failed" in content or "login failed" in content:
                        log_analysis["auth_errors"] += 1
                        
            except Exception as e:
                print(f"[WARNING] Could not analyze log file {log_file}: {e}")
        
        print(f"[ANALYSIS] Authentication patterns from logs:")
        print(f"  - Fresh authentications: {log_analysis['auth_success_count']}")
        print(f"  - Session reuses: {log_analysis['auth_bypass_count']}")  
        print(f"  - Authentication errors: {log_analysis['auth_errors']}")
    else:
        print("[INFO] No logs directory found")
    
    return {
        "session_files": [str(f.relative_to(project_root)) for f in session_files],
        "session_analysis": session_analysis,
        "context_analysis": context_analysis,
        "log_analysis": log_analysis
    }

def check_playwright_session_storage(project_root: Path):
    """Check for Playwright session storage in common locations"""
    
    # Common Playwright session locations
    session_locations = [
        project_root / "playwright_sessions",
        project_root / "browser_sessions", 
        project_root / ".playwright",
        Path.home() / ".playwright"
    ]
    
    print("\n[INFO] Checking Playwright session storage locations...")
    
    found_any = False
    for location in session_locations:
        if location.exists():
            found_any = True
            print(f"[FOUND] Session directory: {location}")
            
            # List contents (limit to first 10 items)
            try:
                contents = list(location.rglob("*"))[:10]
                for item in contents:
                    relative = item.relative_to(location)
                    item_type = "dir" if item.is_dir() else "file"
                    print(f"  - {relative} ({item_type})")
                
                total_items = len(list(location.rglob("*")))
                if total_items > 10:
                    print(f"  ... and {total_items - 10} more items")
                    
            except Exception as e:
                print(f"  [ERROR] Could not list contents: {e}")
        else:
            print(f"[NOT FOUND] {location}")
    
    if not found_any:
        print("[INFO] No Playwright session storage directories found")

def generate_recommendations(analysis_result: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on authentication analysis"""
    
    recommendations = []
    
    session_analysis = analysis_result["session_analysis"]
    context_analysis = analysis_result["context_analysis"]
    log_analysis = analysis_result["log_analysis"]
    
    # Session-related recommendations
    if not session_analysis["has_session"]:
        recommendations.append(
            "No session found - first run will require manual authentication in browser window"
        )
    elif not session_analysis["session_valid"]:
        recommendations.append(
            f"Session expired ({session_analysis['session_age_hours']:.1f} hours old) - "
            "will require re-authentication"
        )
    elif not context_analysis["storage_state_exists"]:
        recommendations.append(
            "Session metadata exists but browser context missing - may need fresh authentication"
        )
    else:
        recommendations.append(
            f"Valid session found ({session_analysis['session_age_hours']:.1f} hours old) - "
            "should work without re-authentication"
        )
    
    # Error pattern recommendations
    if log_analysis["auth_errors"] > 0:
        recommendations.append(
            f"Found {log_analysis['auth_errors']} authentication errors in logs - "
            "check network connectivity and Microsoft credentials"
        )
    
    if log_analysis["auth_bypass_count"] == 0 and log_analysis["total_logs"] > 0:
        recommendations.append(
            "No session reuse detected in logs - session persistence may not be working properly"
        )
    
    # Success pattern analysis
    if log_analysis["auth_success_count"] > 0 and log_analysis["auth_bypass_count"] > 0:
        recommendations.append(
            "Session management appears to be working correctly - "
            f"{log_analysis['auth_bypass_count']} successful session reuses detected"
        )
    
    return recommendations

def clean_sessions(project_root: Path, confirm: bool = False):
    """Clean up all session data"""
    
    session_dir = project_root / "sessions"
    
    if not session_dir.exists():
        print("[INFO] No sessions directory to clean")
        return
    
    if not confirm:
        print(f"[WARNING] This will delete all session data in: {session_dir}")
        response = input("Are you sure? (y/N): ").strip().lower()
        if response != 'y':
            print("[INFO] Session cleanup cancelled")
            return
    
    try:
        shutil.rmtree(session_dir)
        print(f"[SUCCESS] Sessions directory deleted: {session_dir}")
        print("[INFO] Next run will require fresh authentication")
        
    except Exception as e:
        print(f"[ERROR] Failed to clean sessions: {e}")

def main():
    """Main entry point for authentication analysis"""
    
    parser = argparse.ArgumentParser(
        description="Analyze JP authentication patterns and session management"
    )
    parser.add_argument(
        "--clean-sessions",
        action="store_true",
        help="Clean up all saved sessions (forces fresh authentication)"
    )
    parser.add_argument(
        "--project-root",
        help="Project root directory (default: auto-detect)"
    )
    
    args = parser.parse_args()
    
    # Determine project root
    if args.project_root:
        project_root = Path(args.project_root)
    else:
        # Auto-detect project root
        current = Path(__file__).parent
        while current != current.parent:
            if (current / "input" / "questions.csv").exists():
                project_root = current
                break
            current = current.parent
        else:
            project_root = Path.cwd()
    
    print("=" * 80)
    print("JP AUTHENTICATION ANALYSIS")
    print("=" * 80)
    print(f"Project root: {project_root}")
    print(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Handle session cleanup if requested
    if args.clean_sessions:
        clean_sessions(project_root)
        print()
        return
    
    try:
        # Run authentication analysis
        analysis_result = analyze_authentication_history(project_root)
        
        # Check Playwright storage
        check_playwright_session_storage(project_root)
        
        # Generate recommendations
        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        
        recommendations = generate_recommendations(analysis_result)
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
        else:
            print("No specific recommendations - system appears properly configured")
        
        print("\n" + "=" * 80)
        print("TROUBLESHOOTING COMMANDS")
        print("=" * 80)
        print("Clean sessions (force fresh auth): python scripts/analyze_jp_authentication.py --clean-sessions")
        print("Check session files: ls -la sessions/")
        print("Run with fresh auth: rm -rf sessions/ && python scripts/jp_automation_main.py ...")
        
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"[ERROR] Analysis failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())