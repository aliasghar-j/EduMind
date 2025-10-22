import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from flask import current_app


class GoogleCalendarService:
    """Service class for Google Calendar API integration."""
    
    def __init__(self):
        self.service = None
    
    def build_service(self, credentials: Credentials):
        """Build Google Calendar service with user credentials."""
        try:
            self.service = build('calendar', 'v3', credentials=credentials)
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to build calendar service: {e}")
            return False
    
    def get_upcoming_events(self, max_results: int = 10, days_ahead: int = 30) -> List[Dict]:
        """
        Fetch upcoming events from user's primary calendar.
        
        Args:
            max_results: Maximum number of events to return
            days_ahead: Number of days ahead to fetch events
            
        Returns:
            List of event dictionaries with formatted data
        """
        if not self.service:
            return []
        
        try:
            # Calculate time range
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            # Call the Calendar API
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Format events for frontend consumption
            formatted_events = []
            for event in events:
                formatted_event = self._format_event(event)
                if formatted_event:
                    formatted_events.append(formatted_event)
            
            return formatted_events
            
        except HttpError as error:
            current_app.logger.error(f"Calendar API error: {error}")
            return []
        except Exception as e:
            current_app.logger.error(f"Unexpected error fetching events: {e}")
            return []
    
    def _format_event(self, event: Dict) -> Optional[Dict]:
        """
        Format a Google Calendar event for frontend display.
        
        Args:
            event: Raw event data from Google Calendar API
            
        Returns:
            Formatted event dictionary or None if invalid
        """
        try:
            # Extract basic event info
            event_id = event.get('id')
            summary = event.get('summary', 'No Title')
            description = event.get('description', '')
            location = event.get('location', '')
            
            # Handle start and end times
            start = event.get('start', {})
            end = event.get('end', {})
            
            # Check if it's an all-day event
            is_all_day = 'date' in start
            
            if is_all_day:
                start_datetime = start.get('date')
                end_datetime = end.get('date')
                start_time = None
                end_time = None
            else:
                start_datetime = start.get('dateTime')
                end_datetime = end.get('dateTime')
                
                # Extract time components for display
                if start_datetime:
                    start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                    start_time = start_dt.strftime('%H:%M')
                else:
                    start_time = None
                    
                if end_datetime:
                    end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
                    end_time = end_dt.strftime('%H:%M')
                else:
                    end_time = None
            
            # Format date for display
            if start_datetime:
                if is_all_day:
                    display_date = datetime.fromisoformat(start_datetime).strftime('%B %d, %Y')
                else:
                    display_date = datetime.fromisoformat(start_datetime.replace('Z', '+00:00')).strftime('%B %d, %Y')
            else:
                display_date = 'Unknown Date'
            
            return {
                'id': event_id,
                'title': summary,
                'description': description,
                'location': location,
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
                'start_time': start_time,
                'end_time': end_time,
                'display_date': display_date,
                'is_all_day': is_all_day,
                'html_link': event.get('htmlLink', ''),
                'status': event.get('status', 'confirmed')
            }
            
        except Exception as e:
            current_app.logger.error(f"Error formatting event: {e}")
            return None
    
    def get_calendar_list(self) -> List[Dict]:
        """
        Get list of user's calendars.
        
        Returns:
            List of calendar dictionaries
        """
        if not self.service:
            return []
        
        try:
            calendar_list = self.service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            
            formatted_calendars = []
            for calendar in calendars:
                formatted_calendars.append({
                    'id': calendar.get('id'),
                    'summary': calendar.get('summary', 'Unknown Calendar'),
                    'description': calendar.get('description', ''),
                    'primary': calendar.get('primary', False),
                    'access_role': calendar.get('accessRole', 'reader')
                })
            
            return formatted_calendars
            
        except HttpError as error:
            current_app.logger.error(f"Calendar list API error: {error}")
            return []
        except Exception as e:
            current_app.logger.error(f"Unexpected error fetching calendars: {e}")
            return []


def create_credentials_from_session(session_tokens: Dict) -> Optional[Credentials]:
    """
    Create Google OAuth2 credentials from session token data.
    
    Args:
        session_tokens: Token data from user session
        
    Returns:
        Credentials object or None if invalid
    """
    try:
        if not session_tokens:
            return None
        
        access_token = session_tokens.get('access_token')
        refresh_token = session_tokens.get('refresh_token')
        id_token = session_tokens.get('id_token')
        expires_at = session_tokens.get('expires_at')
        
        if not access_token:
            return None
        
        # Parse expiry time
        expiry = None
        if expires_at:
            try:
                expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            except:
                pass
        
        # Create credentials
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            id_token=id_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=current_app.config.get('GOOGLE_CLIENT_ID'),
            client_secret=current_app.config.get('GOOGLE_CLIENT_SECRET'),
            expiry=expiry
        )
        
        return credentials
        
    except Exception as e:
        current_app.logger.error(f"Error creating credentials: {e}")
        return None