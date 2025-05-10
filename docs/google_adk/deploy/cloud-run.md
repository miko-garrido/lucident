# Cloud Run

Deploy ADK agents to Google Cloud Run for scalable, serverless hosting.

## Agent Sample

Use a standard ADK agent as described in the main docs. No special changes are needed for Cloud Run.

## Environment Variables

Set required environment variables for your agent (e.g., project, location, credentials) as needed by your code.

## Deployment Commands

### Using adk CLI

#### Setup environment variables

```sh
export PROJECT_ID="your-gcp-project"
export REGION="us-central1"
```

#### Minimal command

```sh
adk deploy cloudrun
```

#### Full command with optional flags

```sh
adk deploy cloudrun --project $PROJECT_ID --region $REGION --allow-unauthenticated
```

#### Authenticated access

If not using `--allow-unauthenticated`, you must provide an identity token for API access.

### Using gcloud CLI

#### Project Structure

Organize your agent code and requirements as needed. Example files: `main.py`, `requirements.txt`.

#### Deploy using gcloud

```sh
gcloud run deploy adk-agent \
  --source . \
  --project $PROJECT_ID \
  --region $REGION \
  --allow-unauthenticated
```

## Testing Your Agent

### UI Testing

Use the ADK dev UI to interact with your agent, manage sessions, and view execution details in the browser.

### API Testing (curl)

#### Set the application URL

```sh
export APP_URL="YOUR_CLOUD_RUN_SERVICE_URL"
# Example: export APP_URL="https://adk-default-service-name-abc123xyz.a.run.app"
```

#### Get an identity token (if needed)

```sh
export TOKEN=$(gcloud auth print-identity-token)
```

#### List available apps

```sh
curl -X GET -H "Authorization: Bearer $TOKEN" $APP_URL/list-apps
```

#### Create or Update a Session

```sh
curl -X POST -H "Authorization: Bearer $TOKEN" \
    $APP_URL/apps/capital_agent/users/user_123/sessions/session_abc \
    -H "Content-Type: application/json" \
    -d '{"state": {"preferred_language": "English", "visit_count": 5}}'
```

#### Run the Agent

```sh
curl -X POST -H "Authorization: Bearer $TOKEN" \
    $APP_URL/run_sse \
    -H "Content-Type: application/json" \
    -d '{
    "app_name": "capital_agent",
    "user_id": "user_123",
    "session_id": "session_abc",
    "new_message": {
        "role": "user",
        "parts": [{
        "text": "What is the capital of Canada?"
        }]
    },
    "streaming": false
    }'
```

Set `"streaming": true` for SSE responses.

[Source](https://google.github.io/adk-docs/deploy/cloud-run/) 