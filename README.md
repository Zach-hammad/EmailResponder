# EmailResponder

This simple script checks a Gmail inbox for unread messages and drafts a reply to each one. It polls every 10 minutes and creates a draft response thanking the sender. The message is not sent automatically.

## Installation

1. Create and activate a Python 3 virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

## Setup

1. In the [Google Cloud Console](https://console.cloud.google.com/), create OAuth client credentials for a desktop application.
2. Download the `credentials.json` file and place it in the project root.
3. The first time you run the script, a browser window will open to authorize access to Gmail. A `token.json` file will be generated and saved for future runs.
4. The Gmail service is built with discovery caching disabled to avoid writing
   cache files to disk.

## Usage

Run the responder with Python:

```bash
python mail.py
```

Every ten minutes the script looks for unread messages and creates a draft reply thanking the sender. You can review these drafts in Gmail before sending them.

