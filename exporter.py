"""
Data export module for calendar and reminder data.

This module handles exporting CalendarData to various formats,
primarily JSON files organized by calendar/list and month.
"""

import datetime
import json
from pathlib import Path
from typing import Optional

from models import CalendarData, CalendarEvent, Reminder


def sanitize_name(name: str) -> str:
    """Sanitize a name for use as a directory/filename."""
    return "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name).strip()


def get_month_year_key(dt: datetime.datetime) -> str:
    """Get month-year string in format 'Month_Year' e.g. 'March_2026'."""
    return dt.strftime("%B_%Y")


class DataExporter:
    """
    Exports calendar and reminder data to various formats.
    """
    
    def __init__(self, data: CalendarData):
        """
        Initialize the exporter with calendar data.
        
        Args:
            data: CalendarData object containing events and reminders
        """
        self.data = data
    
    def export_to_json(self, base_dir: str = ".") -> None:
        """
        Export all calendar and reminder data to JSON files.
        
        Structure:
        - cal_data/calendars.json
        - cal_data/events.json
        - cal_data/Calendars/<Month>_<Year>.json (all events aggregated by month)
        - reminder_data/reminder_lists.json
        - reminder_data/reminders_content.json
        - reminder_data/Reminders/<Month>_<Year>.json (all reminders aggregated by month)
        
        Args:
            base_dir: Base directory for output (default: current directory)
        """
        base_path = Path(base_dir)
        cal_dir = base_path / "cal_data"
        reminder_dir = base_path / "reminder_data"
        
        cal_dir.mkdir(parents=True, exist_ok=True)
        reminder_dir.mkdir(parents=True, exist_ok=True)
        
        self._export_calendar_data(cal_dir)
        self._export_reminder_data(reminder_dir)
        
        print(f"\n✓ Export complete!")
        print(f"  Calendar data: {cal_dir.absolute()}")
        print(f"  Reminder data: {reminder_dir.absolute()}")
    
    def _export_calendar_data(self, cal_dir: Path) -> None:
        """Export all calendar-related data."""
        print("\nExporting calendar data...")
        
        # Export calendars list
        calendars_file = cal_dir / "calendars.json"
        with open(calendars_file, 'w', encoding='utf-8') as f:
            json.dump(self.data.calendars, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved {len(self.data.calendars)} calendars to {calendars_file}")
        
        # Export all events in a single file
        all_events_file = cal_dir / "events.json"
        all_events = [e.to_dict() for e in self.data.events]
        with open(all_events_file, 'w', encoding='utf-8') as f:
            json.dump(all_events, f, indent=2, ensure_ascii=False)
        
        # Group events by month/year (aggregated across all calendars)
        events_by_month = {}
        for event in self.data.events:
            if event.start_date:
                month_year = get_month_year_key(event.start_date)
            else:
                month_year = "No_Date"
            
            if month_year not in events_by_month:
                events_by_month[month_year] = []
            
            events_by_month[month_year].append(event.to_dict())
        
        # Write events organized by month in Calendars subdirectory
        calendars_subdir = cal_dir / "Calendars"
        calendars_subdir.mkdir(parents=True, exist_ok=True)
        
        for month_year, events in events_by_month.items():
            events.sort(key=lambda e: e['start_date'] or '')
            event_file = calendars_subdir / f"{month_year}.json"
            with open(event_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Saved {len(self.data.events)} events across {len(events_by_month)} monthly snapshots in Calendars/")
    
    def _export_reminder_data(self, reminder_dir: Path) -> None:
        """Export all reminder-related data."""
        print("\nExporting reminder data...")
        
        # Export reminder lists
        lists_file = reminder_dir / "reminder_lists.json"
        with open(lists_file, 'w', encoding='utf-8') as f:
            json.dump(self.data.reminder_lists, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved {len(self.data.reminder_lists)} reminder lists to {lists_file}")
        
        # Export all reminders content
        all_reminders_file = reminder_dir / "reminders_content.json"
        all_reminders = [r.to_dict() for r in self.data.reminders]
        with open(all_reminders_file, 'w', encoding='utf-8') as f:
            json.dump(all_reminders, f, indent=2, ensure_ascii=False)
        
        # Group reminders by month/year (aggregated across all lists)
        reminders_by_month = {}
        for reminder in self.data.reminders:
            if reminder.due_date:
                month_year = get_month_year_key(reminder.due_date)
            elif reminder.completion_date:
                month_year = get_month_year_key(reminder.completion_date)
            else:
                month_year = "No_Date"
            
            if month_year not in reminders_by_month:
                reminders_by_month[month_year] = []
            
            reminders_by_month[month_year].append(reminder.to_dict())
        
        # Write reminders organized by month in Reminders subdirectory
        reminders_subdir = reminder_dir / "Reminders"
        reminders_subdir.mkdir(parents=True, exist_ok=True)
        
        for month_year, reminders in reminders_by_month.items():
            reminders.sort(key=lambda r: r['due_date'] or r['completion_date'] or '')
            reminder_file = reminders_subdir / f"{month_year}.json"
            with open(reminder_file, 'w', encoding='utf-8') as f:
                json.dump(reminders, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Saved {len(self.data.reminders)} reminders across {len(reminders_by_month)} monthly snapshots in Reminders/")
        
        # Export incomplete reminders separately
        incomplete = [r.to_dict() for r in self.data.get_incomplete_reminders()]
        incomplete_file = reminder_dir / "reminders_incomplete.json"
        with open(incomplete_file, 'w', encoding='utf-8') as f:
            json.dump(incomplete, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved {len(incomplete)} incomplete reminders to {incomplete_file}")
    
    def export_events_by_date_range(
        self,
        output_file: str,
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None
    ) -> None:
        """
        Export events within a specific date range to a single JSON file.
        
        Args:
            output_file: Path to the output JSON file
            start_date: Start of date range (inclusive), None for no lower bound
            end_date: End of date range (inclusive), None for no upper bound
        """
        filtered_events = []
        for event in self.data.events:
            if event.start_date is None:
                continue
            if start_date and event.start_date < start_date:
                continue
            if end_date and event.start_date > end_date:
                continue
            filtered_events.append(event.to_dict())
        
        filtered_events.sort(key=lambda e: e['start_date'] or '')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_events, f, indent=2, ensure_ascii=False)
        
        print(f"Exported {len(filtered_events)} events to {output_file}")
    
    def export_reminders_by_list(self, list_name: str, output_file: str) -> None:
        """
        Export all reminders from a specific list to a JSON file.
        
        Args:
            list_name: Name of the reminder list
            output_file: Path to the output JSON file
        """
        filtered_reminders = [
            r.to_dict() for r in self.data.reminders
            if r.list_name.lower() == list_name.lower()
        ]
        
        filtered_reminders.sort(key=lambda r: r['due_date'] or r['completion_date'] or '')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_reminders, f, indent=2, ensure_ascii=False)
        
        print(f"Exported {len(filtered_reminders)} reminders to {output_file}")
