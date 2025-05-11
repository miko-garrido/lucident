# Authentication

Many tools require authentication to access APIs or cloud resources. ADK supports various authentication methods for secure agent operation.

## Methods
- API keys
- OAuth2 tokens
- Google Cloud credentials
- Service accounts

## Usage
Configure authentication as required by each tool or API. For Google Cloud, set up service account credentials and environment variables as needed.

Example (Google Cloud):
```sh
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

See the official docs for tool-specific authentication setup and security best practices.

[Source](https://google.github.io/adk-docs/tools/authentication/) 