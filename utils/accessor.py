"""
Apple EventKit accessor module.

This module handles all interactions with Apple's EventKit framework
for fetching calendar events and reminders.
"""

import datetime
import threading
from typing import Optional

from utils.models import CalendarEvent, Reminder, CalendarData, ReminderPriority

# EventKit imports via PyObjC
try:
    import EventKit
    from Foundation import NSDate
    EVENTKIT_AVAILABLE = True
except ImportError:
    EVENTKIT_AVAILABLE = False
    print("Warning: PyObjC EventKit not available. Install with: pip install pyobjc-framework-EventKit")


class AppleDataAccessor:
    """
    Handles access to Apple Calendar and Reminders via EventKit.
    """
    
    def __init__(self):
        if not EVENTKIT_AVAILABLE:
            raise RuntimeError("EventKit is not available. Please install pyobjc-framework-EventKit")
        
        self.event_store = EventKit.EKEventStore.alloc().init()
        self.data = CalendarData()
        self._calendar_access_granted = False
        self._reminder_access_granted = False
    
    def request_calendar_access(self) -> bool:
        """Request access to calendars. Returns True if granted."""
        print("Requesting Calendar access...")
        
        semaphore = threading.Semaphore(0)
        access_granted = [False]
        
        def completion_handler(granted, error):
            access_granted[0] = granted
            if error:
                print(f"Calendar access error: {error}")
            semaphore.release()
        
        # Request full access to events (macOS 14+) or fallback to legacy
        try:
            self.event_store.requestFullAccessToEventsWithCompletion_(completion_handler)
        except AttributeError:
            self.event_store.requestAccessToEntityType_completion_(
                EventKit.EKEntityTypeEvent,
                completion_handler
            )
        
        semaphore.acquire()
        self._calendar_access_granted = access_granted[0]
        
        if self._calendar_access_granted:
            print("✓ Calendar access granted")
        else:
            print("✗ Calendar access denied")
        
        return self._calendar_access_granted
    
    def request_reminder_access(self) -> bool:
        """Request access to reminders. Returns True if granted."""
        print("Requesting Reminders access...")
        
        semaphore = threading.Semaphore(0)
        access_granted = [False]
        
        def completion_handler(granted, error):
            access_granted[0] = granted
            if error:
                print(f"Reminders access error: {error}")
            semaphore.release()
        
        # Request full access to reminders (macOS 14+) or fallback to legacy
        try:
            self.event_store.requestFullAccessToRemindersWithCompletion_(completion_handler)
        except AttributeError:
            self.event_store.requestAccessToEntityType_completion_(
                EventKit.EKEntityTypeReminder,
                completion_handler
            )
        
        semaphore.acquire()
        self._reminder_access_granted = access_granted[0]
        
        if self._reminder_access_granted:
            print("✓ Reminders access granted")
        else:
            print("✗ Reminders access denied")
        
        return self._reminder_access_granted
    
    def _nsdate_to_datetime(self, nsdate) -> Optional[datetime.datetime]:
        """Convert NSDate to Python datetime."""
        if nsdate is None:
            return None
        timestamp = nsdate.timeIntervalSince1970()
        return datetime.datetime.fromtimestamp(timestamp)
    
    def fetch_calendars(self) -> list:
        """Fetch all available calendars."""
        if not self._calendar_access_granted:
            print("Calendar access not granted. Call request_calendar_access() first.")
            return []
        
        calendars = self.event_store.calendarsForEntityType_(EventKit.EKEntityTypeEvent)
        self.data.calendars = []
        
        for cal in calendars:
            cal_info = {
                'title': cal.title(),
                'identifier': cal.calendarIdentifier(),
                'type': str(cal.type()),
                'color': str(cal.color()) if cal.color() else None,
                'allows_content_modifications': cal.allowsContentModifications(),
                'is_subscribed': cal.isSubscribed() if hasattr(cal, 'isSubscribed') else False,
            }
            self.data.calendars.append(cal_info)
        
        print(f"Found {len(self.data.calendars)} calendars")
        return self.data.calendars
    
    def fetch_events(self, days_back: int = 365, days_forward: int = 365) -> list:
        """
        Fetch calendar events within the specified date range.
        
        Note: EventKit has a ~4 year limit per query, so we fetch in yearly batches.
        
        Args:
            days_back: Number of days in the past to fetch
            days_forward: Number of days in the future to fetch
        """
        if not self._calendar_access_granted:
            print("Calendar access not granted. Call request_calendar_access() first.")
            return []
        
        calendars = self.event_store.calendarsForEntityType_(EventKit.EKEntityTypeEvent)
        
        now = datetime.datetime.now()
        all_events = []
        batch_days = 365
        
        # Fetch past events in yearly batches
        total_days_processed = 0
        while total_days_processed < days_back:
            chunk_end = now - datetime.timedelta(days=total_days_processed)
            remaining_days = days_back - total_days_processed
            chunk_size = min(batch_days, remaining_days)
            chunk_start = chunk_end - datetime.timedelta(days=chunk_size)
            
            start_nsdate = NSDate.dateWithTimeIntervalSince1970_(chunk_start.timestamp())
            end_nsdate = NSDate.dateWithTimeIntervalSince1970_(chunk_end.timestamp())
            
            predicate = self.event_store.predicateForEventsWithStartDate_endDate_calendars_(
                start_nsdate, end_nsdate, calendars
            )
            events = self.event_store.eventsMatchingPredicate_(predicate)
            if events:
                all_events.extend(events)
            
            total_days_processed += chunk_size
            print(f"  Fetched past events: {total_days_processed}/{days_back} days...")
        
        # Fetch future events in yearly batches
        total_days_processed = 0
        while total_days_processed < days_forward:
            chunk_start = now + datetime.timedelta(days=total_days_processed)
            remaining_days = days_forward - total_days_processed
            chunk_size = min(batch_days, remaining_days)
            chunk_end = chunk_start + datetime.timedelta(days=chunk_size)
            
            start_nsdate = NSDate.dateWithTimeIntervalSince1970_(chunk_start.timestamp())
            end_nsdate = NSDate.dateWithTimeIntervalSince1970_(chunk_end.timestamp())
            
            predicate = self.event_store.predicateForEventsWithStartDate_endDate_calendars_(
                start_nsdate, end_nsdate, calendars
            )
            events = self.event_store.eventsMatchingPredicate_(predicate)
            if events:
                all_events.extend(events)
            
            total_days_processed += chunk_size
            if days_forward > batch_days:
                print(f"  Fetched future events: {total_days_processed}/{days_forward} days...")
        
        # Deduplicate events by event ID
        seen_ids = set()
        unique_events = []
        for event in all_events:
            event_id = event.eventIdentifier()
            if event_id not in seen_ids:
                seen_ids.add(event_id)
                unique_events.append(event)
        
        self.data.events = []
        
        for event in unique_events:
            attendees = []
            if event.attendees():
                for attendee in event.attendees():
                    attendees.append({
                        'name': attendee.name() if attendee.name() else None,
                        'email': attendee.emailAddress() if hasattr(attendee, 'emailAddress') else None,
                        'status': str(attendee.participantStatus()),
                    })
            
            recurrence_rules = []
            if event.recurrenceRules():
                for rule in event.recurrenceRules():
                    recurrence_rules.append({
                        'frequency': str(rule.frequency()),
                        'interval': rule.interval(),
                    })
            
            calendar_event = CalendarEvent(
                title=event.title() or "(No Title)",
                start_date=self._nsdate_to_datetime(event.startDate()),
                end_date=self._nsdate_to_datetime(event.endDate()),
                location=event.location(),
                notes=event.notes(),
                calendar_name=event.calendar().title() if event.calendar() else "Unknown",
                is_all_day=event.isAllDay(),
                event_id=event.eventIdentifier(),
                url=str(event.URL()) if event.URL() else None,
                attendees=attendees,
                recurrence_rules=recurrence_rules,
            )
            self.data.events.append(calendar_event)
        
        print(f"Found {len(self.data.events)} events")
        return self.data.events
    
    def fetch_reminder_lists(self) -> list:
        """Fetch all reminder lists."""
        if not self._reminder_access_granted:
            print("Reminders access not granted. Call request_reminder_access() first.")
            return []
        
        calendars = self.event_store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)
        self.data.reminder_lists = []
        
        for cal in calendars:
            list_info = {
                'title': cal.title(),
                'identifier': cal.calendarIdentifier(),
                'color': str(cal.color()) if cal.color() else None,
                'allows_content_modifications': cal.allowsContentModifications(),
            }
            self.data.reminder_lists.append(list_info)
        
        print(f"Found {len(self.data.reminder_lists)} reminder lists")
        return self.data.reminder_lists
    
    def fetch_reminders(self, include_completed: bool = True) -> list:
        """
        Fetch all reminders.
        
        Args:
            include_completed: Whether to include completed reminders
        """
        if not self._reminder_access_granted:
            print("Reminders access not granted. Call request_reminder_access() first.")
            return []
        
        semaphore = threading.Semaphore(0)
        fetched_reminders = []
        
        calendars = self.event_store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)
        
        if include_completed:
            predicate = self.event_store.predicateForRemindersInCalendars_(calendars)
        else:
            predicate = self.event_store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(
                None, None, calendars
            )
        
        def completion_handler(reminders):
            if reminders:
                fetched_reminders.extend(reminders)
            semaphore.release()
        
        self.event_store.fetchRemindersMatchingPredicate_completion_(predicate, completion_handler)
        semaphore.acquire()
        
        self.data.reminders = []
        
        for reminder in fetched_reminders:
            priority_value = reminder.priority()
            if priority_value == 0:
                priority = ReminderPriority.NONE
            elif priority_value <= 4:
                priority = ReminderPriority.HIGH
            elif priority_value == 5:
                priority = ReminderPriority.MEDIUM
            else:
                priority = ReminderPriority.LOW
            
            due_date = None
            if reminder.dueDateComponents():
                due_components = reminder.dueDateComponents()
                try:
                    due_date = datetime.datetime(
                        year=due_components.year() if due_components.year() != 0x7fffffffffffffff else datetime.datetime.now().year,
                        month=due_components.month() if due_components.month() != 0x7fffffffffffffff else 1,
                        day=due_components.day() if due_components.day() != 0x7fffffffffffffff else 1,
                        hour=due_components.hour() if due_components.hour() != 0x7fffffffffffffff else 0,
                        minute=due_components.minute() if due_components.minute() != 0x7fffffffffffffff else 0,
                    )
                except (ValueError, OverflowError):
                    due_date = None
            
            reminder_obj = Reminder(
                title=reminder.title() or "(No Title)",
                notes=reminder.notes(),
                due_date=due_date,
                completion_date=self._nsdate_to_datetime(reminder.completionDate()),
                is_completed=reminder.isCompleted(),
                priority=priority,
                list_name=reminder.calendar().title() if reminder.calendar() else "Unknown",
                reminder_id=reminder.calendarItemIdentifier(),
                url=str(reminder.URL()) if reminder.URL() else None,
            )
            self.data.reminders.append(reminder_obj)
        
        print(f"Found {len(self.data.reminders)} reminders")
        return self.data.reminders
    
    def fetch_all(self, days_back: int = 365, days_forward: int = 365, include_completed_reminders: bool = True) -> CalendarData:
        """
        Fetch all calendar and reminder data.
        
        Args:
            days_back: Number of days in the past to fetch events
            days_forward: Number of days in the future to fetch events
            include_completed_reminders: Whether to include completed reminders
        
        Returns:
            CalendarData object containing all fetched data
        """
        self.fetch_calendars()
        self.fetch_events(days_back, days_forward)
        self.fetch_reminder_lists()
        self.fetch_reminders(include_completed_reminders)
        return self.data


def is_eventkit_available() -> bool:
    """Check if EventKit is available on this system."""
    return EVENTKIT_AVAILABLE
