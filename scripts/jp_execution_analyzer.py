#!/usr/bin/env python3
"""
JP Execution Analysis Tool
==========================

Analyzes JP automation execution logs, screenshots, and output to assess 
timeout vs retries vs response quality patterns and provide optimization recommendations.

Author: JP Automation System
Version: 1.0
Date: 2026-01-23

Usage:
    python jp_execution_analyzer.py
    python jp_execution_analyzer.py --session-id jp_session_20260123_085555
"""

import os
import json
import re
import glob
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import argparse


class JPExecutionAnalyzer:
    """Analyzes JP execution artifacts to identify improvement opportunities"""
    
    def __init__(self, project_root: Optional[str] = None):
        """Initialize analyzer with project root detection"""
        if project_root is None:
            # Auto-detect project root
            current = Path(__file__).parent
            while current != current.parent:
                if (current / "input" / "questions.csv").exists():
                    project_root = current
                    break
                current = current.parent
        
        if not project_root:
            project_root = Path.cwd()
            
        self.project_root = Path(project_root)
        self.logs_dir = self.project_root / "logs"
        self.debug_dir = self.project_root / "debug"
        self.output_dir = self.project_root / "output"
        
        # Ensure directories exist
        self.logs_dir.mkdir(exist_ok=True)
        self.debug_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
    def find_latest_session(self) -> Optional[str]:
        """Find the most recent execution session"""
        log_files = list(self.logs_dir.glob("jp_execution_*.log"))
        if not log_files:
            print("[ERROR] No log files found in", self.logs_dir)
            return None
            
        latest_log = max(log_files, key=os.path.getmtime)
        session_id = latest_log.stem.replace("jp_execution_", "")
        print(f"[INFO] Found latest session: {session_id}")
        return session_id
    
    def analyze_logs(self, session_id: str) -> Dict[str, Any]:
        """Analyze log file for timeout/retry patterns"""
        log_file = self.logs_dir / f"jp_execution_{session_id}.log"
        if not log_file.exists():
            print(f"[ERROR] Log file not found: {log_file}")
            return {}
            
        analysis = {
            "timeouts": [],
            "retries": [],
            "errors": [],
            "completion_times": [],
            "phase_transitions": [],
            "quality_issues": []
        }
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line_lower = line.lower()
                    
                    # Detect timeouts
                    if any(term in line_lower for term in ["timeout", "timed out"]):
                        analysis["timeouts"].append({
                            "line": line_num,
                            "content": line.strip(),
                            "timestamp": self._extract_timestamp(line)
                        })
                    
                    # Detect retries
                    if any(term in line_lower for term in ["retry", "retrying", "attempt"]):
                        analysis["retries"].append({
                            "line": line_num,
                            "content": line.strip(),
                            "timestamp": self._extract_timestamp(line)
                        })
                    
                    # Detect errors
                    if any(term in line_lower for term in ["[error]", "exception", "failed"]):
                        analysis["errors"].append({
                            "line": line_num,
                            "content": line.strip(),
                            "timestamp": self._extract_timestamp(line)
                        })
                    
                    # Detect phase transitions
                    if any(phase in line_lower for phase in [
                        "thinking", "search agent", "document analysis", "summary agent",
                        "phase transition"
                    ]):
                        analysis["phase_transitions"].append({
                            "line": line_num,
                            "content": line.strip(),
                            "timestamp": self._extract_timestamp(line)
                        })
                    
                    # Detect quality issues
                    if any(issue in line_lower for issue in [
                        "no citations", "incomplete response", "quality_score: 0",
                        "empty response", "premature capture"
                    ]):
                        analysis["quality_issues"].append({
                            "line": line_num,
                            "content": line.strip(),
                            "timestamp": self._extract_timestamp(line)
                        })
                        
        except Exception as e:
            print(f"[ERROR] Failed to analyze log file: {e}")
            
        return analysis
    
    def analyze_screenshots(self, session_id: str) -> Dict[str, Any]:
        """Analyze screenshots for response quality indicators"""
        screenshot_dir = self.debug_dir / "screenshots"
        if not screenshot_dir.exists():
            screenshot_dir = self.debug_dir  # Fallback to main debug dir
            
        screenshots = list(screenshot_dir.glob(f"*{session_id}*.png"))
        
        analysis = {
            "total_screenshots": len(screenshots),
            "response_states": [],
            "completion_indicators": [],
            "timeout_captures": [],
            "error_captures": []
        }
        
        for screenshot in screenshots:
            filename = screenshot.name.lower()
            
            # Analyze filename for state information
            if "thinking" in filename:
                analysis["response_states"].append("thinking_phase")
            elif "search_agent" in filename:
                analysis["response_states"].append("search_phase")
            elif "document_analysis" in filename:
                analysis["response_states"].append("analysis_phase")
            elif "summary" in filename:
                analysis["response_states"].append("summary_phase")
            elif "complete" in filename:
                analysis["completion_indicators"].append(filename)
            elif "timeout" in filename:
                analysis["timeout_captures"].append(filename)
            elif "error" in filename:
                analysis["error_captures"].append(filename)
        
        return analysis
    
    def analyze_output_quality(self, session_id: str) -> Dict[str, Any]:
        """Analyze output files for response quality metrics"""
        # Find output files matching session
        csv_files = list(self.output_dir.glob(f"*{session_id}*.csv"))
        if not csv_files:
            # Fallback: find most recent CSV file
            csv_files = list(self.output_dir.glob("jp_answers_*.csv"))
        
        if not csv_files:
            print("[ERROR] No output CSV files found")
            return {}
        
        latest_csv = max(csv_files, key=os.path.getmtime)
        print(f"[INFO] Analyzing output file: {latest_csv.name}")
        
        try:
            df = pd.read_csv(latest_csv)
            
            analysis = {
                "total_questions": len(df),
                "successful_responses": 0,
                "case_citations_found": 0,
                "decision_statements": 0,
                "empty_responses": 0,
                "timeout_responses": 0,
                "average_response_length": 0,
                "processing_times": [],
                "quality_scores": [],
                "citation_rates": []
            }
            
            total_length = 0
            
            for _, row in df.iterrows():
                response = str(row.get('answer_text', ''))
                citations = str(row.get('citations', ''))
                
                # Response quality analysis
                if len(response) < 50:
                    analysis["empty_responses"] += 1
                elif any(indicator in response.lower() for indicator in ["thinking", "search agent", "timeout"]):
                    if len(response) < 200:
                        analysis["timeout_responses"] += 1
                    else:
                        analysis["successful_responses"] += 1
                else:
                    analysis["successful_responses"] += 1
                
                # Citation analysis using enhanced patterns
                citation_patterns = [
                    r'\\b20\\d{2}\\s+(FC|SST|FCA)\\s+\\d+\\b',
                    r'\\b\\d{4}\\s+CanLII\\s+\\d+\\b',
                    r'\\bA-\\d+-\\d+\\b',
                    r'\\bGE-\\d+-\\d+\\b'
                ]
                
                citations_found = 0
                full_text = response + " " + citations
                
                for pattern in citation_patterns:
                    matches = re.findall(pattern, full_text, re.IGNORECASE)
                    citations_found += len(matches)
                
                if citations_found > 0:
                    analysis["case_citations_found"] += 1
                    analysis["citation_rates"].append(citations_found)
                
                # Decision statement detection
                if re.search(r'decision:\\s*[^\\n]{20,}', response, re.IGNORECASE):
                    analysis["decision_statements"] += 1
                
                # Processing time analysis
                if 'processing_time_seconds' in df.columns:
                    proc_time = row.get('processing_time_seconds', 0)
                    if proc_time > 0:
                        analysis["processing_times"].append(float(proc_time))
                
                # Quality score analysis (if available from enhanced version)
                if 'quality_score' in df.columns:
                    quality_score = row.get('quality_score', 0)
                    analysis["quality_scores"].append(float(quality_score))
                
                total_length += len(response)
            
            analysis["average_response_length"] = total_length / len(df) if len(df) > 0 else 0
            
            return analysis
            
        except Exception as e:
            print(f"[ERROR] Failed to analyze output: {e}")
            return {}
    
    def generate_recommendations(self, log_analysis: Dict, screenshot_analysis: Dict, output_analysis: Dict) -> List[Dict]:
        """Generate improvement recommendations based on analysis"""
        recommendations = []
        
        # Timeout analysis
        timeout_count = len(log_analysis.get("timeouts", []))
        if timeout_count > 0:
            severity = "HIGH" if timeout_count > 3 else "MEDIUM"
            recommendations.append({
                "category": "TIMEOUT_OPTIMIZATION",
                "priority": severity,
                "issue": f"Found {timeout_count} timeout events",
                "recommendation": "Implement phase-aware adaptive timeouts (60s-300s based on JP processing phase)",
                "code_change": "Update PHASE_TIMEOUTS configuration and use enhanced _wait_for_response_completion()",
                "estimated_improvement": f"Reduce timeouts by {min(80, timeout_count * 15)}%"
            })
        
        # Retry pattern analysis
        retry_count = len(log_analysis.get("retries", []))
        if retry_count > 5:
            recommendations.append({
                "category": "RETRY_STRATEGY",
                "priority": "MEDIUM",
                "issue": f"Excessive retries detected: {retry_count}",
                "recommendation": "Implement exponential backoff with jitter (2s, 4s, 8s intervals)",
                "code_change": "Add backoff strategy to question processing retry loop",
                "estimated_improvement": "Reduce system load and improve success rate on retries"
            })
        
        # Response quality analysis
        total_q = output_analysis.get("total_questions", 1)
        success_q = output_analysis.get("successful_responses", 0)
        success_rate = success_q / total_q if total_q > 0 else 0
        
        if success_rate < 0.8:
            recommendations.append({
                "category": "RESPONSE_QUALITY",
                "priority": "HIGH", 
                "issue": f"Low success rate: {success_rate:.1%} ({success_q}/{total_q})",
                "recommendation": "Improve completion detection with multi-criteria validation (citations + stability + quality indicators)",
                "code_change": "Implement enhanced _is_response_complete_enhanced() with scoring system",
                "estimated_improvement": f"Increase success rate to 90%+ (target: {int(total_q * 0.9)} successful)"
            })
        
        # Case citation extraction
        citation_q = output_analysis.get("case_citations_found", 0)
        citation_rate = citation_q / total_q if total_q > 0 else 0
        
        if citation_rate < 0.6:
            recommendations.append({
                "category": "CITATION_EXTRACTION",
                "priority": "HIGH" if citation_rate < 0.4 else "MEDIUM",
                "issue": f"Low case citation rate: {citation_rate:.1%} ({citation_q}/{total_q})",
                "recommendation": "Add post-processing citation extraction using regex patterns for legal references",
                "code_change": "Implement CITATION_PATTERNS matching in _extract_response_data_enhanced()",
                "estimated_improvement": f"Increase citation detection to 75%+ (target: {int(total_q * 0.75)} with citations)"
            })
        
        # Processing time analysis
        if output_analysis.get("processing_times"):
            avg_time = sum(output_analysis["processing_times"]) / len(output_analysis["processing_times"])
            if avg_time > 240:  # 4 minutes
                recommendations.append({
                    "category": "PERFORMANCE_OPTIMIZATION",
                    "priority": "MEDIUM",
                    "issue": f"High average processing time: {avg_time:.1f} seconds",
                    "recommendation": "Optimize polling intervals and implement early completion detection",
                    "code_change": "Tune POLL_INTERVAL_SECONDS and add content change detection",
                    "estimated_improvement": f"Reduce processing time by 20-30% (target: {avg_time * 0.75:.1f}s avg)"
                })
        
        # Empty/timeout response analysis
        empty_count = output_analysis.get("empty_responses", 0) + output_analysis.get("timeout_responses", 0)
        if empty_count > 0:
            empty_rate = empty_count / total_q
            recommendations.append({
                "category": "COMPLETION_DETECTION",
                "priority": "HIGH" if empty_rate > 0.2 else "MEDIUM",
                "issue": f"Empty/premature responses: {empty_count} ({empty_rate:.1%})",
                "recommendation": "Enhance completion detection with phase-aware waiting and content validation",
                "code_change": "Use enhanced phase detection and require minimum completion criteria",
                "estimated_improvement": f"Eliminate 80% of premature captures (reduce to {int(empty_count * 0.2)})"
            })
        
        return recommendations
    
    def _extract_timestamp(self, log_line: str) -> Optional[str]:
        """Extract timestamp from log line"""
        # Look for ISO timestamp pattern
        timestamp_pattern = r'(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2})'
        match = re.search(timestamp_pattern, log_line)
        if match:
            return match.group(1)
        
        # Fallback: look for date-time pattern
        timestamp_pattern = r'(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2})'
        match = re.search(timestamp_pattern, log_line)
        return match.group(1) if match else None
    
    def run_full_analysis(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Run complete analysis and generate report"""
        print("\\n" + "="*80)
        print("JP EXECUTION ANALYSIS TOOL")
        print("="*80)
        print(f"Project root: {self.project_root}")
        print(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not session_id:
            session_id = self.find_latest_session()
            if not session_id:
                print("[ERROR] No execution sessions found")
                return {}
        
        print(f"\\n[INFO] Analyzing session: {session_id}")
        
        # Run analyses
        print("[INFO] Analyzing logs...")
        log_analysis = self.analyze_logs(session_id)
        
        print("[INFO] Analyzing screenshots...")
        screenshot_analysis = self.analyze_screenshots(session_id)
        
        print("[INFO] Analyzing output quality...")
        output_analysis = self.analyze_output_quality(session_id)
        
        # Generate recommendations
        print("[INFO] Generating recommendations...")
        recommendations = self.generate_recommendations(log_analysis, screenshot_analysis, output_analysis)
        
        # Print report
        self._print_analysis_report(session_id, log_analysis, screenshot_analysis, output_analysis, recommendations)
        
        return {
            "session_id": session_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "log_analysis": log_analysis,
            "screenshot_analysis": screenshot_analysis,
            "output_analysis": output_analysis,
            "recommendations": recommendations
        }
    
    def _print_analysis_report(self, session_id: str, log_analysis: Dict, screenshot_analysis: Dict, 
                             output_analysis: Dict, recommendations: List[Dict]):
        """Print formatted analysis report"""
        print("\\n" + "="*80)
        print(f"EXECUTION ANALYSIS REPORT - Session: {session_id}")
        print("="*80)
        
        # Log Analysis Summary
        print("\\n[LOG ANALYSIS]")
        print(f"  Timeouts detected: {len(log_analysis.get('timeouts', []))}")
        print(f"  Retries detected: {len(log_analysis.get('retries', []))}")
        print(f"  Errors detected: {len(log_analysis.get('errors', []))}")
        print(f"  Phase transitions: {len(log_analysis.get('phase_transitions', []))}")
        print(f"  Quality issues: {len(log_analysis.get('quality_issues', []))}")
        
        # Screenshot Analysis
        print("\\n[SCREENSHOT ANALYSIS]")
        print(f"  Total screenshots: {screenshot_analysis.get('total_screenshots', 0)}")
        print(f"  Response states captured: {len(screenshot_analysis.get('response_states', []))}")
        print(f"  Completion indicators: {len(screenshot_analysis.get('completion_indicators', []))}")
        print(f"  Timeout captures: {len(screenshot_analysis.get('timeout_captures', []))}")
        print(f"  Error captures: {len(screenshot_analysis.get('error_captures', []))}")
        
        # Output Quality Analysis  
        print("\\n[OUTPUT QUALITY ANALYSIS]")
        total_q = output_analysis.get('total_questions', 0)
        success_q = output_analysis.get('successful_responses', 0)
        citations = output_analysis.get('case_citations_found', 0)
        
        if total_q > 0:
            print(f"  Total questions processed: {total_q}")
            print(f"  Successful responses: {success_q} ({success_q/total_q:.1%})")
            print(f"  Case citations found: {citations} ({citations/total_q:.1%})")
            print(f"  Decision statements: {output_analysis.get('decision_statements', 0)} ({output_analysis.get('decision_statements', 0)/total_q:.1%})")
            print(f"  Empty responses: {output_analysis.get('empty_responses', 0)}")
            print(f"  Timeout responses: {output_analysis.get('timeout_responses', 0)}")
            print(f"  Average response length: {output_analysis.get('average_response_length', 0):.0f} chars")
            
            if output_analysis.get('processing_times'):
                times = output_analysis['processing_times']
                avg_time = sum(times) / len(times)
                max_time = max(times)
                print(f"  Average processing time: {avg_time:.1f} seconds")
                print(f"  Maximum processing time: {max_time:.1f} seconds")
        else:
            print("  No output data available for analysis")
        
        # Recommendations
        print(f"\\n[RECOMMENDATIONS] ({len(recommendations)} items)")
        if not recommendations:
            print("  No specific recommendations - system appears to be performing well!")
        else:
            for i, rec in enumerate(recommendations, 1):
                print(f"\\n  {i}. [{rec['priority']}] {rec['category']}")
                print(f"     Issue: {rec['issue']}")
                print(f"     Fix: {rec['recommendation']}")
                print(f"     Code: {rec['code_change']}")
                if 'estimated_improvement' in rec:
                    print(f"     Impact: {rec['estimated_improvement']}")
        
        print("\\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)


def main():
    """Main entry point for JP execution analyzer"""
    parser = argparse.ArgumentParser(
        description="Analyze JP automation execution for optimization opportunities"
    )
    parser.add_argument(
        "--session-id", 
        help="Specific session ID to analyze (default: latest session)"
    )
    parser.add_argument(
        "--project-root",
        help="Project root directory (default: auto-detect)"
    )
    
    args = parser.parse_args()
    
    try:
        analyzer = JPExecutionAnalyzer(args.project_root)
        result = analyzer.run_full_analysis(args.session_id)
        
        # Optionally save analysis results
        if result:
            analysis_file = analyzer.project_root / "logs" / f"analysis_{result['session_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, default=str)
            print(f"\\nAnalysis results saved to: {analysis_file.name}")
        
    except Exception as e:
        print(f"[ERROR] Analysis failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())