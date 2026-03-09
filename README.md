# AI-Calendar-Analysis-

A Python application that accesses Apple Calendar and Reminders data for AI-powered analysis and actionable insights.

## Features

- 📅 **Calendar Access**: Fetches all calendars and events via EventKit
- ✅ **Reminders Access**: Fetches all reminder lists and items
- 🔒 **Privacy-First**: Requests proper macOS permissions before accessing data
- 📊 **Structured Data**: Parses everything into typed Python dataclasses for easy analysis
- 🤖 **Multi-Provider AI**: Supports both local Ollama models and Claude API

## Requirements

- macOS (uses native EventKit framework)
- Python 3.8+
- PyObjC framework
- Either: Ollama installed locally, or an Anthropic API key

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

### Export Calendar Data

```bash
python calendar_reminders_app.py
```

On first run, macOS will prompt you to grant access to Calendar and Reminders. You may need to:

1. Go to **System Settings > Privacy & Security > Calendars** and allow Terminal/your IDE
2. Go to **System Settings > Privacy & Security > Reminders** and allow Terminal/your IDE

### Run AI Analysis

#### Using Ollama (default, local):

```bash
python CALENDER_ANALYSIS.py
```

#### Using Claude API:

```bash
# Option 1: Set environment variable
export ANTHROPIC_API_KEY="your-api-key-here"
python CALENDER_ANALYSIS.py --provider claude

# Option 2: Pass API key directly
python CALENDER_ANALYSIS.py --provider claude --api-key "your-api-key-here"
```

#### Full Options:

```bash
python CALENDER_ANALYSIS.py --help

# Examples:
python CALENDER_ANALYSIS.py --provider claude -s  # Skip regenerating summaries
python CALENDER_ANALYSIS.py -p claude --summary-model claude-3-haiku-20240307  # Use different model
```

## Data Structure

The application loads data into these structures:

### CalendarEvent

- `title`, `start_date`, `end_date`
- `location`, `notes`, `calendar_name`
- `is_all_day`, `attendees`, `recurrence_rules`

### Reminder

- `title`, `notes`, `due_date`
- `is_completed`, `completion_date`
- `priority`, `list_name`

## Programmatic Usage

```python
from calendar_reminders_app import AppleDataAccessor

# Initialize and request access
accessor = AppleDataAccessor()
accessor.request_calendar_access()
accessor.request_reminder_access()

# Fetch all data
data = accessor.fetch_all(days_back=365, days_forward=365)

# Access parsed data
for event in data.events:
    print(f"{event.title} on {event.start_date}")

for reminder in data.reminders:
    if not reminder.is_completed:
        print(f"TODO: {reminder.title}")
```

## Privacy Note

This application only reads your calendar and reminder data locally. No data is transmitted externally.
