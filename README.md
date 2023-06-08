# Email Rules Engine

The Email Rules Engine is a Python-based application that allows you to process and organize emails based on predefined rules. It provides a RESTful API to manage email rules and apply them to a collection of emails stored in a database. The application integrates with the Gmail API for email retrieval and manipulation.

## Features

- Define rules based on email properties such as sender, subject, date received, and more.
- Perform actions on emails that match the specified rules, such as marking as read or moving to a specific folder.
- Store emails and their metadata in a database(Postgres) for efficient retrieval and processing.
- Expose a RESTful API for managing rules and triggering email processing.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/email-rules-engine.git
   ```
2. Install the required dependencies:
  ```
  pip install -r requirements.txt
  ```
3. Set up the database by running the provided SQL script.
4. Configure the Gmail API credentials by downloading the credentials.json file from google devloper console.
5. Start the server:
  ```
  python main.py
  ```
  
## Usage

Once the server is running, you can interact with the Email Rules Engine using the RESTful API endpoints. Below are the available endpoints:

- GET /: Retrieve all emails from the database.
- POST /: Apply the email rules to the stored emails and return the results.
The email rules are specified in the JSON format. An example rule payload can be:

```
{
  "rules": [
    {
      "conditions": [
        {
          "field": "from",
          "predicate": "contains",
          "value": "example@example.com"
        }
      ],
      "predicate": "all",
      "actions": [
        {
          "action": "mark_as_read",
          "value": "True"
        }
      ]
    }
  ]
}
```


