# Artifacts

Artifacts in ADK are named, versioned binary data (e.g., files, images, audio) associated with a session or user. They enable agents and tools to handle data beyond text, supporting richer interactions.

## What are Artifacts?
- **Definition:** Binary data (file content) identified by a unique filename within a session or user scope. Each save creates a new version.
- **Representation:** Artifacts use `google.genai.types.Part`, with `inline_data` holding the bytes and MIME type.
- **Persistence:** Managed by an Artifact Service (e.g., `InMemoryArtifactService`, `GcsArtifactService`). Not stored in agent/session state directly.

## Why Use Artifacts?
- Store/retrieve images, audio, PDFs, or any file format.
- Persist large data outside session state.
- Manage user uploads and agent-generated files.
- Share outputs between tools/agents or across sessions (with user namespacing).
- Cache binary results to avoid recomputation.

## Common Use Cases
- Generated reports/files (PDF, CSV, images)
- Handling user uploads (images, docs)
- Storing intermediate binary results
- Persistent user data (profile pics, settings)
- Caching generated content

## Core Concepts
- **Artifact Service:** Handles storage/retrieval/versioning. Use `InMemoryArtifactService` for testing, `GcsArtifactService` for persistent storage.
- **Artifact Data:** Always a `types.Part` with `inline_data` (bytes + MIME type).
- **Filename:** String identifier, unique within scope. Use descriptive names (e.g., `report.pdf`, `user:avatar.png`).
- **Versioning:** Each save increments version. Load latest or specific version as needed.
- **Namespacing:**
  - Session scope: `filename` (e.g., `report.pdf`) is tied to session.
  - User scope: Prefix with `user:` (e.g., `user:avatar.png`) for cross-session access.

## Interacting with Artifacts
- **Configure ArtifactService** in your Runner:
```python
from google.adk.artifacts import InMemoryArtifactService
artifact_service = InMemoryArtifactService()
# Pass to Runner(..., artifact_service=artifact_service)
```
- **Save:**
```python
context.save_artifact(filename, types.Part.from_data(data=bytes, mime_type="application/pdf"))
```
- **Load:**
```python
artifact = context.load_artifact(filename)
```
- **List (ToolContext only):**
```python
files = tool_context.list_artifacts()
```

## Available Implementations
- **InMemoryArtifactService:** Fast, ephemeral, for local dev/testing.
- **GcsArtifactService:** Persistent, scalable, uses Google Cloud Storage. Requires bucket and credentials.

## Best Practices
- Use correct MIME types.
- Use `user:` prefix for user-wide data.
- Handle errors (service not configured, missing artifact).
- Clean up persistent artifacts as needed.

For full details and code examples, see the [official Artifacts docs](https://google.github.io/adk-docs/artifacts/). 