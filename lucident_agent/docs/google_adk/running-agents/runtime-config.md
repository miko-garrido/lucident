# Runtime Config

`RunConfig` controls runtime behavior for ADK agents: speech, streaming, function calling, artifact saving, and LLM call limits.

## Class Definition

```python
class RunConfig(BaseModel):
    """Configs for runtime behavior of agents."""
    speech_config: Optional[types.SpeechConfig] = None
    response_modalities: Optional[list[str]] = None
    save_input_blobs_as_artifacts: bool = False
    support_cfc: bool = False
    streaming_mode: StreamingMode = StreamingMode.NONE
    output_audio_transcription: Optional[types.AudioTranscriptionConfig] = None
    max_llm_calls: int = 500
```

## Parameters

| Parameter                         | Type                                       | Default            | Description                                                        |
| --------------------------------- | ------------------------------------------ | ------------------ | ------------------------------------------------------------------ |
| speech_config                     | Optional[types.SpeechConfig]               | None               | Speech synthesis config (voice, language)                          |
| response_modalities               | Optional[list[str]]                        | None               | Output modalities (e.g., ["TEXT", "AUDIO"])                      |
| save_input_blobs_as_artifacts     | bool                                       | False              | Save input blobs as artifacts                                      |
| support_cfc                       | bool                                       | False              | Enable Compositional Function Calling (experimental, SSE only)     |
| streaming_mode                    | StreamingMode                              | NONE               | Streaming: NONE, SSE, or BIDI                                      |
| output_audio_transcription        | Optional[types.AudioTranscriptionConfig]    | None               | Transcribe generated audio output                                  |
| max_llm_calls                     | int                                        | 500                | Max LLM calls per run (<=0: unlimited, sys.maxsize: error)         |

## Streaming Modes
- `NONE`: No streaming
- `SSE`: Server-Sent Events (one-way)
- `BIDI`: Bidirectional

## Speech Config Example

```python
from google.genai import types
speech = types.SpeechConfig(
    language_code="en-US",
    voice_config=types.VoiceConfig(
        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
    ),
)
```

## Examples

**Basic config:**
```python
from google.genai.adk import RunConfig, StreamingMode
config = RunConfig(streaming_mode=StreamingMode.NONE, max_llm_calls=100)
```

**Enable streaming:**
```python
config = RunConfig(streaming_mode=StreamingMode.SSE, max_llm_calls=200)
```

**Speech, CFC, and artifact saving:**
```python
config = RunConfig(
    speech_config=speech,
    response_modalities=["AUDIO", "TEXT"],
    save_input_blobs_as_artifacts=True,
    support_cfc=True,
    streaming_mode=StreamingMode.SSE,
    max_llm_calls=1000,
)
```

**Experimental CFC:**
```python
config = RunConfig(streaming_mode=StreamingMode.SSE, support_cfc=True, max_llm_calls=150)
```

## Validation
- Pydantic enforces types.
- `max_llm_calls == sys.maxsize` raises ValueError.
- `max_llm_calls <= 0` allows unlimited calls (warned).

[Source](https://google.github.io/adk-docs/runtime/runconfig/) 