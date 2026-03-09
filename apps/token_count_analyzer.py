#!/usr/bin/env python3
"""
Token Analysis Script
Estimates token counts for JSON files in data/cal_data and data/reminder_data directories.
"""

import os
import json
from pathlib import Path

# Try to use tiktoken for accurate counts, fall back to approximation
try:
    import tiktoken
    ENCODER = tiktoken.encoding_for_model("gpt-4")
    USE_TIKTOKEN = True
except ImportError:
    USE_TIKTOKEN = False
    ENCODER = None


def estimate_tokens(text: str) -> int:
    """Estimate token count for a string."""
    if USE_TIKTOKEN:
        return len(ENCODER.encode(text))
    # Approximation: ~4 characters per token for English/JSON
    return len(text) // 4


def analyze_directory(directory: Path) -> dict:
    """Analyze all JSON files in a directory recursively."""
    results = {
        "files": [],
        "total_tokens": 0,
        "total_chars": 0,
        "total_files": 0
    }
    
    if not directory.exists():
        return results
    
    for json_file in sorted(directory.rglob("*.json")):
        try:
            content = json_file.read_text(encoding="utf-8")
            char_count = len(content)
            token_count = estimate_tokens(content)
            
            results["files"].append({
                "path": str(json_file.relative_to(directory.parent)),
                "chars": char_count,
                "tokens": token_count
            })
            results["total_tokens"] += token_count
            results["total_chars"] += char_count
            results["total_files"] += 1
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
    
    return results


def format_number(n: int) -> str:
    """Format large numbers with commas."""
    return f"{n:,}"


def main():
    # Project root is parent of apps/
    base_path = Path(__file__).parent.parent / "data"
    
    print("=" * 60)
    print("TOKEN ANALYSIS REPORT")
    print("=" * 60)
    print(f"Method: {'tiktoken (accurate)' if USE_TIKTOKEN else 'char/4 approximation'}")
    print()
    
    directories = ["cal_data", "reminder_data"]
    grand_total_tokens = 0
    grand_total_chars = 0
    grand_total_files = 0
    
    for dir_name in directories:
        dir_path = base_path / dir_name
        print(f"\n{'─' * 60}")
        print(f"📁 {dir_name.upper()}")
        print(f"{'─' * 60}")
        
        results = analyze_directory(dir_path)
        
        if results["total_files"] == 0:
            print("  No JSON files found.")
            continue
        
        # Group by subdirectory
        by_subdir = {}
        for f in results["files"]:
            parts = Path(f["path"]).parts
            subdir = parts[1] if len(parts) > 2 else "(root)"
            if subdir not in by_subdir:
                by_subdir[subdir] = {"files": [], "tokens": 0, "chars": 0}
            by_subdir[subdir]["files"].append(f)
            by_subdir[subdir]["tokens"] += f["tokens"]
            by_subdir[subdir]["chars"] += f["chars"]
        
        for subdir, data in sorted(by_subdir.items()):
            print(f"\n  📂 {subdir}")
            print(f"     Files: {len(data['files'])}")
            print(f"     Chars: {format_number(data['chars'])}")
            print(f"     Tokens: {format_number(data['tokens'])}")
            
            # Show individual files if few, or top 5 by size
            files_to_show = sorted(data["files"], key=lambda x: x["tokens"], reverse=True)
            if len(files_to_show) <= 5:
                for f in files_to_show:
                    name = Path(f["path"]).name
                    print(f"       • {name}: {format_number(f['tokens'])} tokens")
            else:
                print(f"     Top 5 by size:")
                for f in files_to_show[:5]:
                    name = Path(f["path"]).name
                    print(f"       • {name}: {format_number(f['tokens'])} tokens")
        
        print(f"\n  {'─' * 40}")
        print(f"  SUBTOTAL: {format_number(results['total_tokens'])} tokens ({results['total_files']} files)")
        
        grand_total_tokens += results["total_tokens"]
        grand_total_chars += results["total_chars"]
        grand_total_files += results["total_files"]
    
    print(f"\n{'=' * 60}")
    print("GRAND TOTAL")
    print(f"{'=' * 60}")
    print(f"  Files:  {grand_total_files}")
    print(f"  Chars:  {format_number(grand_total_chars)}")
    print(f"  Tokens: {format_number(grand_total_tokens)}")
    print()
    
    # Cost estimates (approximate, based on GPT-4 pricing)
    print("Estimated API costs (GPT-4 pricing):")
    input_cost = grand_total_tokens * 0.00003  # $0.03 per 1K tokens
    print(f"  As input:  ${input_cost:.4f}")
    print()


if __name__ == "__main__":
    main()
