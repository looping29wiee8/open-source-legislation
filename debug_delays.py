#!/usr/bin/env python3
"""
🔍 DELAY DEBUGGING UTILITY

This script searches for ALL potential delay sources in the codebase
to ensure no hidden delays are affecting scraper performance.

Usage: python debug_delays.py
"""

import os
import re
from pathlib import Path

def find_delay_sources(root_dir: str = "src"):
    """Find all potential delay sources in the codebase."""
    
    delay_patterns = [
        (r'time\.sleep\s*\([^)]+\)', "time.sleep() call"),
        (r'delay_seconds?\s*[=:]\s*[0-9.]+', "delay_seconds setting"),
        (r'delay_time\s*[=:]\s*[^0]', "delay_time variable"),
        (r'wait\s*=\s*wait_', "tenacity wait configuration"),
        (r'WebDriverWait\([^)]*[0-9]+', "Selenium wait"),
        (r'implicitly_wait\([^)]*[0-9]+', "Selenium implicit wait"),
        (r'threading\.Timer\([^)]*[0-9]+', "Threading timer"),
        (r'asyncio\.sleep\([^)]+\)', "asyncio.sleep() call"),
        (r'rate.*limit', "Rate limiting references"),
        (r'throttle', "Throttling references"),
    ]
    
    print("🔍 COMPREHENSIVE DELAY SOURCE SEARCH")
    print("=" * 50)
    
    total_files_checked = 0
    files_with_delays = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Skip common non-code directories
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.pytest_cache', 'node_modules'}]
        
        for file in files:
            if file.endswith('.py'):
                total_files_checked += 1
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    file_has_delays = False
                    
                    for pattern, description in delay_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            if not file_has_delays:
                                print(f"\n📁 {file_path}")
                                files_with_delays += 1
                                file_has_delays = True
                            
                            # Find line number
                            line_num = content[:match.start()].count('\n') + 1
                            line_content = content.split('\n')[line_num - 1].strip()
                            
                            print(f"  ⏰ Line {line_num}: {description}")
                            print(f"     Code: {line_content}")
                            
                except Exception as e:
                    print(f"❌ Error reading {file_path}: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 SUMMARY:")
    print(f"   Total Python files checked: {total_files_checked}")
    print(f"   Files with potential delays: {files_with_delays}")
    
    if files_with_delays == 0:
        print("✅ NO DELAY SOURCES FOUND - Maximum performance achieved!")
    else:
        print("⚠️  DELAY SOURCES FOUND - Review above for performance impact")

if __name__ == "__main__":
    find_delay_sources()