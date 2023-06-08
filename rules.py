import json
import datetime
from db_connection import create_db_connection
from oauth import authenticate

# for running code in terminal and testing logic

def fetch_emails_from_db():

    conn = create_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM emails;")
    emails = cursor.fetchall()

    cursor.close()
    conn.close()

    return emails


def process_emails():
    # Load rules from the JSON file
    with open('rules.json', 'r') as file:
        rules_data = json.load(file)

    rules = rules_data['rules']
    emails = fetch_emails_from_db()

    service = authenticate()

    if not emails:
        print('No emails found.')
    else:
        print('Processing emails:')
        for email in emails:
            print(email[0])
            email_data = {
                'email_id': email[0],
                'from': email[1],
                'to': email[2],
                'subject': email[3],
                'date_received': email[4],
                'body': email[5],
                'labels': email[6].split(',')
            }
            # Check if all conditions match (predicate = "All")
            for rule in rules:
                conditions = rule['conditions']
                predicate = rule['predicate']
                actions = rule['actions']

                # Check if all conditions match (predicate = "All")
                if predicate == "All":
                    all_conditions_match = True
                    for condition in conditions:
                        field = condition['field']
                        predicate = condition['predicate']
                        value = condition['value']
                        if not check_condition(email_data, field, predicate, value):
                            all_conditions_match = False
                            break

                    if all_conditions_match:
                        perform_actions(service, email_data, actions)

                # Check if any condition matches (predicate = "Any")
                elif predicate == "Any":
                    any_condition_match = False
                    for condition in conditions:
                        field = condition['field']
                        predicate = condition['predicate']
                        value = condition['value']
                        if check_condition(email_data, field, predicate, value):
                            any_condition_match = True
                            break

                    if any_condition_match:
                        perform_actions(service, email_data, actions)

def perform_actions(service, email_data, actions):
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

            else:
                labels = email_data['labels'] 
                service.users().messages().modify(userId='me', id=message_id, body={'addLabelIds': ['UNREAD']}).execute()
                if "UNREAD" not in labels:
                    labels.append("UNREAD")
            
            cursor.execute("UPDATE emails SET labels = %s WHERE email_id = %s;", (','.join(labels), message_id))
            print('Marked as read:', message_id)
        elif action["action"] == 'move_to_folder':
            folder = action['value']
            labels = email_data['labels']
            if folder not in labels:
                labels.append(folder)
                service.users().messages().modify(userId='me', id=message_id, body={'addLabelIds': [folder]}).execute()
                cursor.execute("UPDATE emails SET labels = %s WHERE email_id = %s;", (','.join(labels), message_id))
                print('Moved message:', message_id)
    cursor.close()
    conn.close()


def check_condition(email_data, field, predicate, value):
    # Perform the condition check based on the field, predicate, and value
    if field == 'From':
        if predicate == 'contains':
            return value in email_data['from']
        elif predicate == 'does_not_contain':
            return value not in email_data['from']
        elif predicate == 'equals':
            return value == email_data['from']
        elif predicate == 'does_not_equal':
            return value != email_data['from']
    elif field == 'Subject':
        if predicate == 'contains':
            return value in email_data['subject']
        elif predicate == 'does_not_contain':
            return value not in email_data['subject']
        elif predicate == 'equals':
            return value == email_data['subject']
        elif predicate == 'does_not_equal':
            return value != email_data['subject']
    elif field == 'Message':
        if predicate == 'contains':
            return value in email_data['body']
        elif predicate == 'does_not_contain':
            return value not in email_data['body']
        elif predicate == 'equals':
            return value == email_data['body']
        elif predicate == 'does_not_equal':
            return value != email_data['body']
    elif field == 'Date Received':
        if predicate == 'less_than':
            received_date = email_data['date_received']
            value_date = datetime.datetime.now() - datetime.timedelta(days=int(value))
            return received_date < value_date
        elif predicate == 'greater_than':
            received_date = email_data['date_received']
            value_date = datetime.datetime.now() - datetime.timedelta(days=int(value))
            return received_date > value_date

    return False


process_emails()

