from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from db_connection import create_db_connection
from oauth import authenticate
import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # Fetch all emails from the database
            emails = fetch_emails_from_db()

            response_data = {
                'headings': ['Email ID', 'From', 'To', 'Subject', 'Date Received', 'Body', 'Labels'],
                'emails': []
            }

            for email in emails:
                email_data = {
                    'email_id': email[0],
                    'from': email[1],
                    'to': email[2],
                    'subject': email[3],
                    'date_received': email[4],
                    'body': email[5],
                    'labels': email[6].split(',')
                }
                response_data['emails'].append(email_data)

            response_body = json.dumps(response_data, cls=DateTimeEncoder).encode('utf-8')

            # Send the response headers
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Content-Length', len(response_body))
            self.end_headers()

            # Send the response body
            self.wfile.write(response_body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        request_data = json.loads(post_data.decode('utf-8'))
        rules = request_data['rules']

        # Fetch emails from the database
        emails = fetch_emails_from_db()

        # Authenticate with Gmail API
        service = authenticate()

        # Process emails based on the rules
        results = process_emails(emails, rules, service)

        # Send the results as a JSON response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(results).encode('utf-8'))

def fetch_emails_from_db():

    conn = create_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM emails;")
    emails = cursor.fetchall()

    cursor.close()
    conn.close()

    return emails

def process_emails(emails, rules, service):
    results = []

    for email in emails:
        email_data = {
            'email_id': email[0],
            'from': email[1],
            'to': email[2],
            'subject': email[3],
            'date_received': email[4],
            'body': email[5],
            'labels': email[6].split(',')
        }

        email_result = {
            'email_id': email_data['email_id'],
            'actions': []
        }

        for rule in rules:
            conditions = rule['conditions']
            predicate = rule['predicate']
            actions = rule['actions']

            # Check if all conditions match (predicate = "All")
            if predicate == "all":
                all_conditions_match = True
                for condition in conditions:
                    field = condition['field']
                    predicate = condition['predicate']
                    value = condition['value']
                    if not check_condition(email_data, field, predicate, value):
                        all_conditions_match = False
                        break

                if all_conditions_match:
                    perform_actions(service, email_data, actions, email_result)

            # Check if any condition matches (predicate = "Any")
            elif predicate == "any":
                any_condition_match = False
                for condition in conditions:
                    field = condition['field']
                    predicate = condition['predicate']
                    value = condition['value']
                    if check_condition(email_data, field, predicate, value):
                        any_condition_match = True
                        break

                if any_condition_match:
                    perform_actions(service, email_data, actions, email_result)

        results.append(email_result)

    return results

def perform_actions(service, email_data, actions, email_result):
    conn = create_db_connection()
    cursor = conn.cursor()
    message_id = email_data['email_id']
    for action in actions:
        if action["action"] == 'mark_as_read':
            is_read = action['value'].lower() == 'true'
            if is_read:
                labels = email_data['labels']
                service.users().messages().modify(userId='me', id=message_id, body={'removeLabelIds': ['UNREAD']}).execute()
                if "UNREAD" in labels:
                    labels.remove("UNREAD")
                email_result['actions'].append({'action': 'mark_as_read', 'status': 'success'})
            else:
                labels = email_data['labels']
                service.users().messages().modify(userId='me', id=message_id, body={'addLabelIds': ['UNREAD']}).execute()
                if "UNREAD" not in labels:
                    labels.append("UNREAD")
                email_result['actions'].append({'action': 'mark_as_read', 'status': 'success'})
            cursor.execute("UPDATE emails SET labels = %s WHERE email_id = %s;", (','.join(labels), message_id))
        elif action["action"] == 'move_to_folder':
            folder = action['value']
            labels = email_data['labels']
            if folder not in labels:
                labels.append(folder)
                service.users().messages().modify(userId='me', id=message_id, body={'addLabelIds': [folder]}).execute()
                email_result['actions'].append({'action': 'move_to_folder', 'status': 'success'})
                cursor.execute("UPDATE emails SET labels = %s WHERE email_id = %s;", (','.join(labels), message_id))

            else:
                email_result['actions'].append({'action': 'move_to_folder', 'status': 'skipped'})


def check_condition(email_data, field, predicate, value):
    # Perform the condition check based on the field, predicate, and value
    if field == 'from':
        if predicate == 'contains':
            return value in email_data['from']
        elif predicate == 'does_not_contain':
            return value not in email_data['from']
        elif predicate == 'equals':
            return value == email_data['from']
        elif predicate == 'does_not_equal':
            return value != email_data['from']
    elif field == 'subject':
        if predicate == 'contains':
            return value in email_data['subject']
        elif predicate == 'does_not_contain':
            return value not in email_data['subject']
        elif predicate == 'equals':
            return value == email_data['subject']
        elif predicate == 'does_not_equal':
            return value != email_data['subject']
    elif field == 'message':
        if predicate == 'contains':
            return value in email_data['body']
        elif predicate == 'does_not_contain':
            return value not in email_data['body']
        elif predicate == 'equals':
            return value == email_data['body']
        elif predicate == 'does_not_equal':
            return value != email_data['body']
    elif field == 'date_received':
        if predicate == 'less_than':
            received_date = datetime.datetime.strptime(str(email_data['date_received']), '%Y-%m-%d %H:%M:%S')
            value_date = datetime.datetime.now() - datetime.timedelta(days=int(value))
            return received_date < value_date
        elif predicate == 'greater_than':
            received_date = datetime.datetime.strptime(str(email_data['date_received']), '%Y-%m-%d %H:%M:%S')
            value_date = datetime.datetime.now() - datetime.timedelta(days=int(value))
            return received_date > value_date

    return False


def run_server():
    server_address = ('localhost', 8000)
    httpd = HTTPServer(server_address, RequestHandler)
    print('Starting server...')
    httpd.serve_forever()


run_server()