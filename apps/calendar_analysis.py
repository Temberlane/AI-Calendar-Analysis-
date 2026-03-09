"""
Calendar and Reminder Analysis using LLMs.

This module provides AI-powered analysis of calendar events and reminders:
- Monthly summarization using a fast model
- Long-term trend analysis using a reasoning model

Supports two providers:
- Ollama: Local models (default)
- Claude: Anthropic's Claude API (requires API key)

Requires: Either Ollama running locally, or ANTHROPIC_API_KEY set.
"""

import json
import argparse
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import requests

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


# Provider configuration
PROVIDER_OLLAMA = "ollama"
PROVIDER_CLAUDE = "claude"
DEFAULT_PROVIDER = PROVIDER_OLLAMA

# Ollama API endpoint
OLLAMA_API = "http://localhost:11434/api/generate"

# Ollama model configurations
OLLAMA_SUMMARY_MODEL = "qwen2.5:14b"
OLLAMA_ANALYSIS_MODEL = "qwen3.5:9b"

# Claude model configurations 
CLAUDE_SUMMARY_MODEL = "claude-sonnet-4-20250514"  # Fast model for summaries
CLAUDE_ANALYSIS_MODEL = "claude-sonnet-4-20250514"  # Main model for analysis

# Default model names (set based on provider)
SUMMARY_MODEL = OLLAMA_SUMMARY_MODEL
ANALYSIS_MODEL = OLLAMA_ANALYSIS_MODEL

# Global provider state
_current_provider = DEFAULT_PROVIDER
_anthropic_client = None


def init_provider(provider: str, api_key: Optional[str] = None) -> None:
    """
    Initialize the LLM provider.
    
    Args:
        provider: Either 'ollama' or 'claude'
        api_key: API key for Claude (optional, can use ANTHROPIC_API_KEY env var)
    """
    global _current_provider, _anthropic_client, SUMMARY_MODEL, ANALYSIS_MODEL
    
    _current_provider = provider
    
    if provider == PROVIDER_CLAUDE:
        # Try to import anthropic
        try:
            import anthropic
        except ImportError:
            print("Error: anthropic package not installed. Run: pip install anthropic")
            raise
        
        # Get API key from argument, environment, or .env file
        key = api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("my_key")
        if not key:
            print("Error: No API key provided. Set ANTHROPIC_API_KEY in .env or use --api-key")
            raise ValueError("Missing Anthropic API key")
        
        _anthropic_client = anthropic.Anthropic(api_key=key)
        SUMMARY_MODEL = CLAUDE_SUMMARY_MODEL
        ANALYSIS_MODEL = CLAUDE_ANALYSIS_MODEL
        print(f"Using Claude API (model: {CLAUDE_SUMMARY_MODEL})")
    else:
        SUMMARY_MODEL = OLLAMA_SUMMARY_MODEL
        ANALYSIS_MODEL = OLLAMA_ANALYSIS_MODEL
        print(f"Using Ollama (models: {OLLAMA_SUMMARY_MODEL}, {OLLAMA_ANALYSIS_MODEL})")


def ollama_generate(prompt: str, model: str, stream: bool = False) -> str:
    """
    Generate text using Ollama API.
    
    Args:
        prompt: The prompt to send to the model
        model: Model name (e.g., 'qwen2.5:14b')
        stream: Whether to stream the response
        
    Returns:
        Generated text response
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream
    }
    
    try:
        response = requests.post(OLLAMA_API, json=payload, timeout=300)
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to Ollama. Make sure it's running (ollama serve)")
        raise
    except requests.exceptions.Timeout:
        print("Error: Request timed out. The model may be too slow or not loaded.")
        raise


def claude_generate(prompt: str, model: str) -> str:
    """
    Generate text using Claude API.
    
    Args:
        prompt: The prompt to send to Claude
        model: Model name (e.g., 'claude-sonnet-4-20250514')
        
    Returns:
        Generated text response
    """
    if _anthropic_client is None:
        raise RuntimeError("Claude client not initialized. Call init_provider first.")
    
    try:
        message = _anthropic_client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    except Exception as e:
        print(f"Error calling Claude API: {e}")
        raise


def generate_text(prompt: str, model: str) -> str:
    """
    Generate text using the configured provider.
    
    Args:
        prompt: The prompt to send to the model
        model: Model name (provider-specific)
        
    Returns:
        Generated text response
    """
    if _current_provider == PROVIDER_CLAUDE:
        return claude_generate(prompt, model)
    else:
        return ollama_generate(prompt, model)


def load_monthly_data(base_dir: str = ".") -> dict:
    """
    Load all monthly JSON files from Calendars and Reminders directories.
    
    Returns:
        Dictionary with structure:
        {
            'calendars': {'Month_Year': [events...]},
            'reminders': {'Month_Year': [reminders...]}
        }
    """
    base_path = Path(base_dir)
    cal_dir = base_path / "data" / "cal_data" / "Calendars"
    reminder_dir = base_path / "data" / "reminder_data" / "Reminders"
    
    data = {
        'calendars': {},
        'reminders': {}
    }
    
    # Load calendar data
    if cal_dir.exists():
        for json_file in sorted(cal_dir.glob("*.json")):
            month_year = json_file.stem
            with open(json_file, 'r', encoding='utf-8') as f:
                data['calendars'][month_year] = json.load(f)
    
    # Load reminder data
    if reminder_dir.exists():
        for json_file in sorted(reminder_dir.glob("*.json")):
            month_year = json_file.stem
            with open(json_file, 'r', encoding='utf-8') as f:
                data['reminders'][month_year] = json.load(f)
    
    return data


def format_events_for_prompt(events: list) -> str:
    """Format a list of calendar events into a readable string."""
    if not events:
        return "No events."
    
    lines = []
    for e in events:
        date_str = e.get('start_date', 'No date')[:10] if e.get('start_date') else 'No date'
        title = e.get('title', 'Untitled')
        calendar = e.get('calendar_name', 'Unknown')
        location = e.get('location', '')
        line = f"- [{date_str}] {title} ({calendar})"
        if location:
            line += f" @ {location}"
        lines.append(line)
    
    return "\n".join(lines)


def format_reminders_for_prompt(reminders: list) -> str:
    """Format a list of reminders into a readable string."""
    if not reminders:
        return "No reminders."
    
    lines = []
    for r in reminders:
        date_str = r.get('due_date', 'No date')[:10] if r.get('due_date') else 'No date'
        title = r.get('title', 'Untitled')
        list_name = r.get('list_name', 'Unknown')
        status = "✓" if r.get('is_completed') else "○"
        priority = r.get('priority', 'NONE')
        line = f"- {status} [{date_str}] {title} ({list_name})"
        if priority != 'NONE':
            line += f" [Priority: {priority}]"
        lines.append(line)
    
    return "\n".join(lines)


def summarize_month(month_year: str, events: list, reminders: list, model: str = SUMMARY_MODEL) -> str:
    """
    Generate a summary for a single month using the fast model.
    
    Args:
        month_year: Month identifier (e.g., 'March_2026')
        events: List of calendar events for the month
        reminders: List of reminders for the month
        model: Model to use for summarization
        
    Returns:
        AI-generated summary of the month
    """
    month_name = month_year.replace("_", " ")
    
    events_text = format_events_for_prompt(events)
    reminders_text = format_reminders_for_prompt(reminders)
    
    # Statistics
    total_events = len(events)
    total_reminders = len(reminders)
    completed_reminders = sum(1 for r in reminders if r.get('is_completed'))
    
    prompt = f"""Analyze the following calendar events and reminders for {month_name}.

## Calendar Events ({total_events} total):
{events_text}

## Reminders ({total_reminders} total, {completed_reminders} completed):
{reminders_text}

Provide a concise summary (3-5 sentences) covering:
1. Main activities and themes for the month
2. Key events or deadlines
3. Task completion rate and productivity observations
4. Notable patterns (busy periods, types of activities)

Summary:"""

    print(f"  Summarizing {month_name}...")
    summary = generate_text(prompt, model)
    return summary.strip()


def analyze_long_term(summaries: dict, model: str = ANALYSIS_MODEL) -> str:
    """
    Perform long-term analysis across all monthly summaries.
    
    Args:
        summaries: Dictionary of {month_year: summary_text}
        model: Model to use for analysis
        
    Returns:
        AI-generated long-term analysis
    """
    # Sort summaries chronologically
    def parse_month_year(key: str):
        try:
            return datetime.strptime(key, "%B_%Y")
        except ValueError:
            return datetime.min
    
    sorted_months = sorted(summaries.keys(), key=parse_month_year)
    
    summaries_text = "\n\n".join([
        f"### {month.replace('_', ' ')}\n{summaries[month]}"
        for month in sorted_months
    ])
    
    prompt = f"""You are analyzing a person's calendar and task history across multiple months.

Below are monthly summaries spanning their schedule and tasks:

{summaries_text}

Provide a comprehensive long-term analysis covering:

1. **Activity Patterns**: What recurring themes or activities appear across months?
2. **Productivity Trends**: How has task completion and workload changed over time?
3. **Life Areas**: What areas of life are represented (work, education, personal, health, social)?
4. **Seasonal Patterns**: Are there seasonal or cyclical patterns in activities?
5. **Recommendations**: Based on the patterns, suggest improvements for time management or work-life balance.
6. **Notable Observations**: Any interesting insights about habits, priorities, or changes over time.

Analysis:"""

    print("\nPerforming long-term analysis...")
    analysis = generate_text(prompt, model)
    return analysis.strip()


def run_analysis(
    base_dir: str = ".",
    output_dir: Optional[str] = None,
    skip_summaries: bool = False,
    summary_model: Optional[str] = None,
    analysis_model: Optional[str] = None,
    provider: str = DEFAULT_PROVIDER,
    api_key: Optional[str] = None
) -> None:
    """
    Run the full calendar analysis pipeline.
    
    Args:
        base_dir: Base directory containing data/cal_data and data/reminder_data
        output_dir: Directory to save analysis results (default: base_dir/analysis)
        skip_summaries: If True, load existing summaries instead of regenerating
        summary_model: Model to use for monthly summaries
        analysis_model: Model to use for long-term analysis
        provider: LLM provider ('ollama' or 'claude')
        api_key: API key for Claude (optional, can use env var)
    """
    print("=" * 60)
    print("CALENDAR & REMINDER ANALYSIS")
    print("=" * 60)
    
    # Initialize provider
    init_provider(provider, api_key)
    
    # Use provided models or fall back to defaults (which are set by init_provider)
    if summary_model is None:
        summary_model = SUMMARY_MODEL
    if analysis_model is None:
        analysis_model = ANALYSIS_MODEL
    
    # Setup output directory
    output_path = Path(output_dir) if output_dir else Path(base_dir) / "analysis"
    output_path.mkdir(parents=True, exist_ok=True)
    summaries_file = output_path / "monthly_summaries.json"
    
    summaries = {}
    
    if skip_summaries and summaries_file.exists():
        print("\nLoading existing summaries...")
        with open(summaries_file, 'r', encoding='utf-8') as f:
            summaries = json.load(f)
        print(f"  Loaded {len(summaries)} monthly summaries")
    else:
        # Load all monthly data
        print("\nLoading monthly data...")
        data = load_monthly_data(base_dir)
        
        # Get all unique months
        all_months = set(data['calendars'].keys()) | set(data['reminders'].keys())
        print(f"  Found {len(all_months)} months to analyze")
        
        # Generate summaries for each month
        print(f"\nGenerating monthly summaries using {summary_model}...")
        
        for month_year in sorted(all_months):
            events = data['calendars'].get(month_year, [])
            reminders = data['reminders'].get(month_year, [])
            
            if not events and not reminders:
                continue
            
            summary = summarize_month(month_year, events, reminders, model=summary_model)
            summaries[month_year] = summary
        
        # Save summaries
        with open(summaries_file, 'w', encoding='utf-8') as f:
            json.dump(summaries, f, indent=2, ensure_ascii=False)
        print(f"\n  ✓ Saved summaries to {summaries_file}")
    
    # Perform long-term analysis
    print(f"\nRunning long-term analysis using {analysis_model}...")
    long_term_analysis = analyze_long_term(summaries, model=analysis_model)
    
    # Save long-term analysis
    analysis_file = output_path / "long_term_analysis.md"
    with open(analysis_file, 'w', encoding='utf-8') as f:
        f.write("# Long-Term Calendar & Task Analysis\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(f"*Analysis Model: {analysis_model}*\n\n")
        f.write("---\n\n")
        f.write(long_term_analysis)
    
    print(f"  ✓ Saved long-term analysis to {analysis_file}")
    
    # Also save a combined report
    report_file = output_path / "full_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# Calendar & Reminder Analysis Report\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(f"*Summary Model: {summary_model}*\n")
        f.write(f"*Analysis Model: {analysis_model}*\n\n")
        f.write("---\n\n")
        
        f.write("## Monthly Summaries\n\n")
        for month_year in sorted(summaries.keys(), 
                                  key=lambda x: datetime.strptime(x, "%B_%Y") if x != "No_Date" else datetime.min):
            f.write(f"### {month_year.replace('_', ' ')}\n\n")
            f.write(summaries[month_year] + "\n\n")
        
        f.write("---\n\n")
        f.write("## Long-Term Analysis\n\n")
        f.write(long_term_analysis)
    
    print(f"  ✓ Saved full report to {report_file}")
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze calendar and reminder data using LLMs (Ollama or Claude)"
    )
    parser.add_argument(
        "--dir", "-d",
        default=".",
        help="Base directory containing data/ folder with cal_data and reminder_data (default: current directory)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output directory for analysis results (default: <dir>/analysis)"
    )
    parser.add_argument(
        "--skip-summaries", "-s",
        action="store_true",
        help="Skip regenerating monthly summaries, use existing ones"
    )
    parser.add_argument(
        "--summary-model",
        default=None,
        help="Model for monthly summaries (default: depends on provider)"
    )
    parser.add_argument(
        "--analysis-model",
        default=None,
        help="Model for long-term analysis (default: depends on provider)"
    )
    parser.add_argument(
        "--provider", "-p",
        choices=[PROVIDER_OLLAMA, PROVIDER_CLAUDE],
        default=DEFAULT_PROVIDER,
        help=f"LLM provider to use: 'ollama' or 'claude' (default: {DEFAULT_PROVIDER})"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key for Claude (or set ANTHROPIC_API_KEY env var)"
    )
    
    args = parser.parse_args()
    
    run_analysis(
        base_dir=args.dir,
        output_dir=args.output,
        skip_summaries=args.skip_summaries,
        summary_model=args.summary_model,
        analysis_model=args.analysis_model,
        provider=args.provider,
        api_key=args.api_key
    )


if __name__ == "__main__":
    main()
