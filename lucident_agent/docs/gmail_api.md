# Gmail API Documentation

The Gmail API is a RESTful API that provides access to Gmail mailboxes and the ability to send mail. It is the recommended choice for web applications that require authorized access to a user's Gmail data.

## Use Cases
- Read-only mail extraction, indexing, and backup
- Automated or programmatic message sending
- Email account migration
- Email organization (filtering, sorting)
- Standardization of email signatures across an organization

**Note:** The Gmail API is not intended to replace IMAP for building full-featured email clients. For that, use IMAP, POP, and SMTP.

## Key Concepts
- **Message:** An email message with sender, recipients, subject, and body. Immutable after creation. Represented by a message resource.
- **Thread:** A collection of related messages forming a conversation.
- **Label:** Used to organize messages and threads. Includes system labels (e.g., `INBOX`, `TRASH`, `SPAM`) and user-created labels.
- **Draft:** An unsent message. Sending a draft deletes it and creates a message with the `SENT` label.

## Main Features
- **Authentication & Authorization:** Uses OAuth 2.0. Scopes control access level.
- **Create & Send Mail:** Create drafts, send email, upload attachments.
- **Manage Mailboxes:** Work with threads, labels, search, sync, and push notifications.
- **Manage Settings:** Aliases, signatures, forwarding, filters, vacation, POP/IMAP, delegates, language, inbox feed.
- **Best Practices:** Batch requests, handle errors, use push notifications for mailbox changes.

## Example: List User's Labels (Python)
```python
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/gmail.readonly'])
service = build('gmail', 'v1', credentials=creds)

results = service.users().labels().list(userId='me').execute()
labels = results.get('labels', [])

for label in labels:
    print(label['name'])
```

## Next Steps
- [Gmail API Overview](https://developers.google.com/gmail/api)
- [Gmail API Guides](https://developers.google.com/workspace/gmail/api/guides)
- [Gmail API Reference](https://developers.google.com/workspace/gmail/api/reference/rest)
- [Quickstarts](https://developers.google.com/workspace/gmail/api/quickstart)

_Source: [Gmail API Overview](https://developers.google.com/gmail/api)_

---

For the complete documentation, see: https://developers.google.com/gmail/api

---

# Gmail API Overview

The Gmail API is a RESTful API that can be used to access Gmail mailboxes and send mail. For most web applications the Gmail API is the best choice for authorized access to a user's Gmail data and is suitable for various applications, such as:

- Read-only mail extraction, indexing, and backup
- Automated or programmatic message sending
- Email account migration
- Email organization including filtering and sorting of messages
- Standardization of email signatures across an organization

**Note:** The Gmail API shouldn't be used to replace IMAP for developing a full-fledged email client. Instead, see IMAP, POP, and SMTP.

## Common Terms

- **Message:** An email message containing the sender, recipients, subject, and body. After a message has been created, a message cannot be changed. A message is represented by a message resource.
- **Thread:** A collection of related messages forming a conversation. In an email client app, a thread is formed when one or more recipients respond to a message with their own message.
- **Label:** A mechanism for organizing messages and threads. For example, the label "taxes" might be created and applied to all messages and threads having to do with a user's taxes. There are two types of labels:
  - **System labels:** Internally-created labels, such as `INBOX`, `TRASH`, or `SPAM`. These labels cannot be deleted or modified. However, some system labels, such as `INBOX` can be applied to, or removed from, messages and threads.
  - **User labels:** Labels created by a user. These labels can be deleted or modified by the user or an application. A user label is represented by a label resource.
- **Draft:** An unsent message. A message contained within the draft can be replaced. Sending a draft automatically deletes the draft and creates a message with the `SENT` system label. A draft is represented by a draft resource.

## Next steps

- To learn about developing with Google Workspace APIs, including handling authentication and authorization, refer to Get started as a Google Workspace developer.
- To learn how to configure and run a simple Gmail API app, read the Quickstarts overview.

_Source: [Gmail API Overview](https://developers.google.com/gmail/api)_

---

# Gmail API Reference

The Gmail API lets you view and manage Gmail mailbox data like threads, messages, and labels.

## Service: gmail.googleapis.com

Base endpoint: `https://gmail.googleapis.com`

### REST Resources

#### v1.users
- **getProfile**: GET /gmail/v1/users/{userId}/profile — Gets the current user's Gmail profile.
- **stop**: POST /gmail/v1/users/{userId}/stop — Stop receiving push notifications for the given user mailbox.
- **watch**: POST /gmail/v1/users/{userId}/watch — Set up or update a push notification watch on the given user mailbox.

#### v1.users.drafts
- **create**: POST /gmail/v1/users/{userId}/drafts — Creates a new draft with the DRAFT label.
- **delete**: DELETE /gmail/v1/users/{userId}/drafts/{id} — Immediately and permanently deletes the specified draft.
- **get**: GET /gmail/v1/users/{userId}/drafts/{id} — Gets the specified draft.
- **list**: GET /gmail/v1/users/{userId}/drafts — Lists the drafts in the user's mailbox.
- **send**: POST /gmail/v1/users/{userId}/drafts/send — Sends the specified, existing draft.
- **update**: PUT /gmail/v1/users/{userId}/drafts/{id} — Replaces a draft's content.

#### v1.users.history
- **list**: GET /gmail/v1/users/{userId}/history — Lists the history of all changes to the given mailbox.

#### v1.users.labels
- **create**: POST /gmail/v1/users/{userId}/labels — Creates a new label.
- **delete**: DELETE /gmail/v1/users/{userId}/labels/{id} — Deletes the specified label.
- **get**: GET /gmail/v1/users/{userId}/labels/{id} — Gets the specified label.
- **list**: GET /gmail/v1/users/{userId}/labels — Lists all labels in the user's mailbox.
- **patch**: PATCH /gmail/v1/users/{userId}/labels/{id} — Patch the specified label.
- **update**: PUT /gmail/v1/users/{userId}/labels/{id} — Updates the specified label.

#### v1.users.messages
- **batchDelete**: POST /gmail/v1/users/{userId}/messages/batchDelete — Deletes many messages by message ID.
- **batchModify**: POST /gmail/v1/users/{userId}/messages/batchModify — Modifies the labels on the specified messages.
- **delete**: DELETE /gmail/v1/users/{userId}/messages/{id} — Deletes the specified message.
- **get**: GET /gmail/v1/users/{userId}/messages/{id} — Gets the specified message.
- **import**: POST /gmail/v1/users/{userId}/messages/import — Imports a message into the user's mailbox.
- **insert**: POST /gmail/v1/users/{userId}/messages — Directly inserts a message into the user's mailbox.
- **list**: GET /gmail/v1/users/{userId}/messages — Lists the messages in the user's mailbox.
- **modify**: POST /gmail/v1/users/{userId}/messages/{id}/modify — Modifies the labels on the specified message.
- **send**: POST /gmail/v1/users/{userId}/messages/send — Sends the specified message.
- **trash**: POST /gmail/v1/users/{userId}/messages/{id}/trash — Moves the specified message to the trash.
- **untrash**: POST /gmail/v1/users/{userId}/messages/{id}/untrash — Removes the specified message from the trash.

#### v1.users.messages.attachments
- **get**: GET /gmail/v1/users/{userId}/messages/{messageId}/attachments/{id} — Gets the specified message attachment.

#### v1.users.settings
- **getAutoForwarding**: GET /gmail/v1/users/{userId}/settings/autoForwarding — Gets the auto-forwarding setting.
- **getImap**: GET /gmail/v1/users/{userId}/settings/imap — Gets IMAP settings.
- **getLanguage**: GET /gmail/v1/users/{userId}/settings/language — Gets language settings.
- **getPop**: GET /gmail/v1/users/{userId}/settings/pop — Gets POP settings.
- **getVacation**: GET /gmail/v1/users/{userId}/settings/vacation — Gets vacation responder settings.
- **updateAutoForwarding**: PUT /gmail/v1/users/{userId}/settings/autoForwarding — Updates the auto-forwarding setting.
- **updateImap**: PUT /gmail/v1/users/{userId}/settings/imap — Updates IMAP settings.
- **updateLanguage**: PUT /gmail/v1/users/{userId}/settings/language — Updates language settings.
- **updatePop**: PUT /gmail/v1/users/{userId}/settings/pop — Updates POP settings.
- **updateVacation**: PUT /gmail/v1/users/{userId}/settings/vacation — Updates vacation responder settings.

#### v1.users.threads
- **delete**: DELETE /gmail/v1/users/{userId}/threads/{id} — Deletes the specified thread.
- **get**: GET /gmail/v1/users/{userId}/threads/{id} — Gets the specified thread.
- **list**: GET /gmail/v1/users/{userId}/threads — Lists the threads in the user's mailbox.
- **modify**: POST /gmail/v1/users/{userId}/threads/{id}/modify — Modifies the labels applied to the thread.
- **trash**: POST /gmail/v1/users/{userId}/threads/{id}/trash — Moves the specified thread to the trash.
- **untrash**: POST /gmail/v1/users/{userId}/threads/{id}/untrash — Removes the specified thread from the trash.

_See the full reference for all resources and methods: [Gmail API Reference](https://developers.google.com/gmail/api/reference/rest)_

---

# Gmail API Quickstarts

The Gmail API Quickstarts provide step-by-step instructions for getting started with the API in various programming languages. These guides help you set up authentication, make your first API call, and understand the basics of working with Gmail data.

## Available Quickstarts
- [JavaScript Quickstart](https://developers.google.com/workspace/gmail/api/quickstart/js)
- [Java Quickstart](https://developers.google.com/workspace/gmail/api/quickstart/java)
- [Python Quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python)
- [Apps Script Quickstart](https://developers.google.com/workspace/gmail/api/quickstart/apps-script)
- [Go Quickstart](https://developers.google.com/workspace/gmail/api/quickstart/go)
- [Node.js Quickstart](https://developers.google.com/workspace/gmail/api/quickstart/nodejs)

Each quickstart covers:
- Setting up a Google Cloud project
- Enabling the Gmail API
- Configuring OAuth consent
- Installing client libraries
- Running sample code to list Gmail labels

For full details and code samples, see the [Gmail API Quickstarts](https://developers.google.com/workspace/gmail/api/quickstart).

---

# Gmail API Guides

The Gmail API Guides provide in-depth documentation and best practices for using the API. Topics include:

- Authentication & Authorization
- Creating and sending mail
- Managing mailboxes (threads, labels, search, sync, push notifications)
- Managing settings (aliases, signatures, forwarding, filters, vacation, POP/IMAP, delegates, language, inbox feed)
- Batch requests and performance tips
- Error handling and troubleshooting
- Migrating from previous APIs

For detailed guides and examples, see the [Gmail API Guides](https://developers.google.com/workspace/gmail/api/guides).