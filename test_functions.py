#!/usr/bin/env python3
"""
Comprehensive test script for all functions in the reportr codebase
"""

import sys
import os
import json
import argparse
from datetime import datetime

from features.progress_report.progress_report import create_progress_report
from functions.git_history import get_commit_diffs_by_file, get_git_history


# Add the functions directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "functions"))
sys.path.append(os.path.join(os.path.dirname(__file__), "features/progress_report"))


def test_get_commit_diffs_by_file():
    """Test the get_commit_diffs_by_file function"""
    print("\n" + "=" * 60)
    print("TESTING: get_commit_diffs_by_file")
    print("=" * 60)

    # Run the function
    diffs = get_commit_diffs_by_file(".", "064118de")

    if diffs:
        print(f"✅ SUCCESS! Found diffs for {len(diffs)} files")

        # Show file list
        print("\nFiles changed:")
        for i, file_path in enumerate(diffs.keys(), 1):
            print(f"  {i}. {file_path}")

        # Show sample diff
        if diffs:
            first_file = list(diffs.keys())[0]
            print(f"\nSample diff for '{first_file}':")
            print("-" * 40)
            diff_content = diffs[first_file]
            if len(diff_content) > 500:
                print(diff_content[:500] + "\n... (truncated)")
            else:
                print(diff_content)

        return diffs
    else:
        print("❌ FAILED: Could not get commit diffs")
        return None


def main():
    test_get_commit_diffs_by_file()


if __name__ == "__main__":
    main()
