#!/usr/bin/env python3
"""
Apple Calendar and Reminders Access Application

This application requests access to Apple Calendar and Reminders,
then parses all information into memory for analysis.

Modules:
    - utils/models.py: Data classes (CalendarEvent, Reminder, CalendarData)
    - utils/accessor.py: EventKit access and data fetching
    - utils/exporter.py: JSON export functionality
"""

import datetime
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.models import CalendarData
from utils.accessor import AppleDataAccessor, is_eventkit_available
from utils.exporter import DataExporter


def print_summary(data: CalendarData) -> None:
    """Print a summary of all fetched data."""
    print("\n" + "=" * 60)
    print("CALENDAR & REMINDERS SUMMARY")
    print("=" * 60)
    
    print(f"\n📅 Calendars ({len(data.calendars)}):")
    for cal in data.calendars:
        print(f"   • {cal['title']}")
    
    print(f"\n📆 Events ({len(data.events)}):")
    upcoming = data.get_upcoming_events(days=7)
    
    if upcoming:
        print("   Upcoming (next 7 days):")
        for event in upcoming[:10]:
            date_str = event.start_date.strftime("%m/%d %H:%M") if event.start_date else "No date"
            print(f"   • [{date_str}] {event.title} ({event.calendar_name})")
        if len(upcoming) > 10:
            print(f"   ... and {len(upcoming) - 10} more")
    
    print(f"\n📋 Reminder Lists ({len(data.reminder_lists)}):")
    for rlist in data.reminder_lists:
        print(f"   • {rlist['title']}")
    
    print(f"\n✓ Reminders ({len(data.reminders)}):")
    incomplete = data.get_incomplete_reminders()
    completed = data.get_completed_reminders()
    
    print(f"   Incomplete: {len(incomplete)}")
    for reminder in incomplete[:10]:
        due_str = reminder.due_date.strftime("%m/%d") if reminder.due_date else "No due date"
        print(f"   • [{due_str}] {reminder.title} ({reminder.list_name})")
    if len(incomplete) > 10:
        print(f"   ... and {len(incomplete) - 10} more")
    
    print(f"   Completed: {len(completed)}")
    
    print("\n" + "=" * 60)


def main():
    """Main entry point for the application."""
    print("=" * 60)
    print("Apple Calendar & Reminders Access Application")
    print("=" * 60)
    print()
    
    if not is_eventkit_available():
        print("ERROR: PyObjC EventKit framework is not installed.")
        print("Please install it with:")
        print("  pip install pyobjc-framework-EventKit pyobjc-framework-Cocoa")
        return None
    
    # Create accessor
    accessor = AppleDataAccessor()
    
    # Request access to both services
    calendar_access = accessor.request_calendar_access()
    reminder_access = accessor.request_reminder_access()
    
    if not calendar_access and not reminder_access:
        print("\nNo access granted. Please grant access in System Settings > Privacy & Security.")
        print("You may need to add Terminal (or your Python IDE) to the allowed apps.")
        return None
    
    print("\nFetching data...")
    
    # Fetch all data (10 years back, 1 year forward)
    data = accessor.fetch_all(
        days_back=3650,
        days_forward=365,
        include_completed_reminders=True
    )
    
    # Print summary
    print_summary(data)
    
    # The data is now available in memory
    print("\n✓ All data is now loaded into memory!")
    print(f"  • {len(data.calendars)} calendars")
    print(f"  • {len(data.events)} events")
    print(f"  • {len(data.reminder_lists)} reminder lists")
    print(f"  • {len(data.reminders)} reminders")
    
    # Export to JSON - export to data/ directory
    project_root = Path(__file__).parent.parent.absolute()
    data_dir = project_root / "data"
    exporter = DataExporter(data)
    exporter.export_to_json(str(data_dir))
    
    return accessor


if __name__ == "__main__":
    accessor = main()

