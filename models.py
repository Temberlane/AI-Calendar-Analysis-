"""
Data models for Apple Calendar and Reminders.

This module defines the core data structures used throughout the application.
"""

import datetime
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ReminderPriority(Enum):
    """Priority levels for reminders."""
    NONE = 0
    HIGH = 1
    MEDIUM = 5
    LOW = 9


@dataclass
class CalendarEvent:
    """Represents a calendar event."""
    title: str
    start_date: Optional[datetime.datetime]
    end_date: Optional[datetime.datetime]
    location: Optional[str]
    notes: Optional[str]
    calendar_name: str
    is_all_day: bool
    event_id: str
    url: Optional[str] = None
    attendees: list = field(default_factory=list)
    recurrence_rules: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert CalendarEvent to dictionary."""
        return {
            'title': self.title,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'location': self.location,
            'notes': self.notes,
            'calendar_name': self.calendar_name,
            'is_all_day': self.is_all_day,
            'event_id': self.event_id,
            'url': self.url,
            'attendees': self.attendees,
            'recurrence_rules': self.recurrence_rules,
        }


@dataclass
class Reminder:
    """Represents a reminder item."""
    title: str
    notes: Optional[str]
    due_date: Optional[datetime.datetime]
    completion_date: Optional[datetime.datetime]
    is_completed: bool
    priority: ReminderPriority
    list_name: str
    reminder_id: str
    location: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert Reminder to dictionary."""
        return {
            'title': self.title,
            'notes': self.notes,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            'is_completed': self.is_completed,
            'priority': self.priority.name,
            'list_name': self.list_name,
            'reminder_id': self.reminder_id,
            'location': self.location,
            'url': self.url,
        }


@dataclass
class CalendarData:
    """Container for all calendar and reminder data."""
    calendars: list = field(default_factory=list)
    events: list = field(default_factory=list)
    reminder_lists: list = field(default_factory=list)
    reminders: list = field(default_factory=list)

    def get_upcoming_events(self, days: int = 7) -> list:
        """Get events in the next N days."""
        now = datetime.datetime.now()
        cutoff = now + datetime.timedelta(days=days)
        upcoming = [e for e in self.events if e.start_date and now <= e.start_date <= cutoff]
        upcoming.sort(key=lambda x: x.start_date)
        return upcoming

    def get_incomplete_reminders(self) -> list:
        """Get all incomplete reminders."""
        return [r for r in self.reminders if not r.is_completed]

    def get_completed_reminders(self) -> list:
        """Get all completed reminders."""
        return [r for r in self.reminders if r.is_completed]
