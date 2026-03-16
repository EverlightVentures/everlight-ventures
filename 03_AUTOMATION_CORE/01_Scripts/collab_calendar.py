!pip install google-auth google-auth-oauthlib google-auth-httplib2
from google.colab import auth

# Authenticate with Google
auth.authenticate_user()

# Link Colab notebook to Google Calendar
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Create an event in Google Calendar
def create_calendar_event(summary, description, start_datetime, end_datetime):
    creds = None

    # Check if token exists, otherwise request user authorization
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            auth.authenticate_user()
            creds = auth.default()

    # Create an event in the calendar
    service = build('calendar', 'v3', credentials=creds)
    event = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start_datetime},
        'end': {'dateTime': end_datetime},
    }
    service.events().insert(calendarId='primary', body=event).execute()

# Add your course titles
courses = ['Boxing', 'Kickboxing', 'Jiu Jitsu', 'MMA', 'Wrestling', 'Judo']

# Create a cell for each course
for course in courses:
    text = f"# {course}\n\nContent for {course} course."
    print(text)
    # Insert code to add the cell to the notebook

# Example usage to create a daily note event
summary = "Daily Note"
description = "Today's live notes for the Martial Arts course."
start_datetime = '2023-07-10T09:00:00'  # Replace with your desired start time
end_datetime = '2023-07-10T10:00:00'  # Replace with your desired end time
create_calendar_event(summary, description, start_datetime, end_datetime)
