from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime
import re
from db_connection import create_db_connection
# Define the scopes you need for accessing GMail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.labels']


# Function to authenticate and get the GMail service
def authenticate():

    # Create the flow using the client ID and client secret obtained in Step 2
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES
    )

    # Run the OAuth flow to authorize the application and get the credentials
    credentials = flow.run_local_server(port=0)

    # Build the GMail service using the obtained credentials
    service = build('gmail', 'v1', credentials=credentials)

    return service

# Function to fetch a list of emails from the Inbox
def fetch_emails():
    # Authenticate and get the GMail service
    service = authenticate()
    # Fetch the list of emails from the Inbox
    results = service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
    messages = results.get('messages', [])

    conn = create_db_connection()
    cursor = conn.cursor()

    if not messages:
        print('No emails found.')
    else:
        print('Emails:')
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            # print(msg)

            data = {
                'email_id': msg['id'],
                'from': None,
                'to': None,
                'subject': None,
                'date_received': None,
                'body': msg['snippet'],
                'labels': ','.join(list(msg['labelIds']))
            }
            payload_headers = msg['payload']['headers']
            for header in payload_headers:
                if header['name'] == 'From':
                    data['from'] = header['value']
                elif header['name'] == 'To':
                    data['to'] = header['value']
                elif header['name'] == 'Delivered-To':
                    data['delivered-to'] = header['value']
                elif header['name'] == 'Subject':
                    data['subject'] = header['value']
                elif header['name'] == 'Date':
                    date_string = re.sub(r'\s*\(.+\)\s*$', '', header['value'])
                    # Convert the date string to a Python datetime object
                    date_received = datetime.strptime(date_string, '%a, %d %b %Y %H:%M:%S %z')
                    # Convert the datetime object to a PostgreSQL-compatible timestamp string
                    data['date_received'] = date_received.strftime('%Y-%m-%d')


            insert_query = """
                INSERT INTO emails (email_id, "from", "to", subject, date_received, body)
                VALUES (%(email_id)s, %(from)s, %(to)s, %(subject)s, %(date_received)s, %(body)s)
                ON CONFLICT (email_id) DO UPDATE
                SET "from" = %(from)s, "to" = %(to)s, subject = %(subject)s,
                date_received = %(date_received)s, body = %(body)s, labels = %(labels)s;
            """
            

            # Insert the email into the database
            cursor.execute(insert_query, data)


            # print()

    # Commit the changes and close the database connection
    conn.commit()
    cursor.close()
    conn.close()



# Call the fetch_emails function to retrieve the emails
fetch_emails()
