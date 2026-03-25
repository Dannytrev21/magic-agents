# Feature 2.8: Checkpoint & Resume Implementation

This document describes the implementation of Feature 2.8 (Checkpoint & Resume) from the Epic 2 Playbook.

## Overview

**Problem:** Negotiation takes 10+ minutes for complex tickets. If the browser closes or the session times out, all state is lost and the developer must start over.

**Solution:** Serialize `VerificationContext` to JSON after each phase advance, allowing resumption from the last checkpoint.

## Architecture

### Components

1. **Checkpoint Module** (`src/verify/negotiation/checkpoint.py`)
   - Core serialization/deserialization logic
   - Session management utilities
   - File I/O operations

2. **Harness Integration** (`src/verify/negotiation/harness.py`)
   - Automatically saves checkpoint after each phase advance
   - Transparent to the rest of the system

3. **Web API** (`src/verify/negotiation/web.py`)
   - GET `/api/session/{jira_key}` - Check for existing checkpoints
   - POST `/api/session/{jira_key}/resume` - Resume a checkpoint

## API Reference

### Checkpoint Module Functions

#### `save_checkpoint(context, phase) -> Path`

Saves a `VerificationContext` to disk after phase completion.

**Arguments:**
- `context: VerificationContext` - The context to save
- `phase: str` - The phase name (e.g., "phase_1", "phase_2")

**Returns:**
- `Path` - The path to the saved checkpoint file

**Location:**
- `.verify/sessions/{jira_key}/checkpoint_{phase}.json`

**Example:**
```python
from verify.context import VerificationContext
from verify.negotiation.checkpoint import save_checkpoint

ctx = VerificationContext(
    jira_key="TICKET-001",
    jira_summary="User authentication",
    raw_acceptance_criteria=[...],
    constitution={...}
)

save_checkpoint(ctx, "phase_1")
# Creates: .verify/sessions/TICKET-001/checkpoint_phase_1.json
```

#### `load_checkpoint(jira_key) -> Optional[Tuple[VerificationContext, int]]`

Loads the most recent checkpoint for a given Jira key.

**Arguments:**
- `jira_key: str` - The Jira ticket key

**Returns:**
- `Tuple[VerificationContext, int]` - The restored context and phase index
- `None` - If no checkpoint exists

**Example:**
```python
from verify.negotiation.checkpoint import load_checkpoint

result = load_checkpoint("TICKET-001")
if result:
    ctx, phase_idx = result
    print(f"Resuming from {ctx.current_phase} (index {phase_idx})")
else:
    print("No checkpoint found")
```

#### `has_checkpoint(jira_key) -> bool`

Checks if a checkpoint exists for a given Jira key.

**Arguments:**
- `jira_key: str` - The Jira ticket key

**Returns:**
- `bool` - True if at least one checkpoint file exists

**Example:**
```python
from verify.negotiation.checkpoint import has_checkpoint

if has_checkpoint("TICKET-001"):
    print("This ticket has a checkpoint available")
```

#### `get_session_info(jira_key) -> Optional[dict]`

Retrieves metadata about the most recent session.

**Arguments:**
- `jira_key: str` - The Jira ticket key

**Returns:**
- `dict` - Session metadata with keys:
  - `jira_key: str` - The ticket key
  - `current_phase: str` - Current phase (e.g., "phase_1")
  - `checkpoint_path: str` - Path to the checkpoint file
  - `log_entries: int` - Number of negotiation log entries
  - `approved: bool` - Whether the context has been approved
- `None` - If no checkpoint exists

**Example:**
```python
from verify.negotiation.checkpoint import get_session_info

info = get_session_info("TICKET-001")
if info:
    print(f"Session at {info['current_phase']} with {info['log_entries']} log entries")
```

#### `clear_session(jira_key) -> bool`

Deletes all checkpoints for a given Jira key.

**Arguments:**
- `jira_key: str` - The Jira ticket key

**Returns:**
- `bool` - True if a session was cleared, False if no session existed

**Example:**
```python
from verify.negotiation.checkpoint import clear_session

if clear_session("TICKET-001"):
    print("Session cleared")
```

### Web Endpoints

#### GET `/api/session/{jira_key}`

Check if a checkpoint exists for a given Jira key.

**Response (with checkpoint):**
```json
{
  "has_checkpoint": true,
  "session": {
    "jira_key": "TICKET-001",
    "current_phase": "phase_2",
    "checkpoint_path": ".verify/sessions/TICKET-001/checkpoint_phase_2.json",
    "log_entries": 5,
    "approved": false
  }
}
```

**Response (without checkpoint):**
```json
{
  "has_checkpoint": false
}
```

#### POST `/api/session/{jira_key}/resume`

Resume a negotiation from a saved checkpoint.

**Response (success):**
```json
{
  "resumed": true,
  "jira_key": "TICKET-001",
  "jira_summary": "User authentication",
  "current_phase": "phase_2",
  "phase_number": 2,
  "log_entries": 5,
  "approved": false
}
```

**Response (error - no checkpoint):**
```json
{
  "error": "No checkpoint found for TICKET-001"
}
```

## Data Format

Checkpoints are stored as JSON files with the complete `VerificationContext` serialized:

**File:** `.verify/sessions/{jira_key}/checkpoint_{phase}.json`

**Structure:**
```json
{
  "jira_key": "TICKET-001",
  "jira_summary": "User authentication",
  "current_phase": "phase_2",
  "raw_acceptance_criteria": [...],
  "constitution": {...},
  "classifications": [...],
  "postconditions": [...],
  "preconditions": [...],
  "failure_modes": [...],
  "invariants": [...],
  "verification_routing": {...},
  "ears_statements": [...],
  "traceability_map": {...},
  "approved": false,
  "approved_by": "",
  "approved_at": "",
  "spec_path": "",
  "generated_files": {},
  "verdicts": [],
  "all_passed": false,
  "negotiation_log": [...]
}
```

## Integration Points

### With NegotiationHarness

The harness automatically saves checkpoints after each `advance_phase()` call:

```python
from verify.negotiation.harness import NegotiationHarness
from verify.context import VerificationContext

ctx = VerificationContext(...)
harness = NegotiationHarness(ctx)

# When conditions are met, advance_phase() will:
# 1. Move to the next phase
# 2. Call save_checkpoint(ctx, next_phase)
harness.advance_phase()
```

### With Web UI

The web UI can:
1. Check for existing checkpoints on page load
2. Offer a "Resume" button if one is found
3. Call `/api/session/{jira_key}/resume` to restore the session

Example UI flow:
```javascript
// On page load
const response = await fetch(`/api/session/${jiraKey}`);
const data = await response.json();

if (data.has_checkpoint) {
  // Show "Resume from Phase N" button
  showResumeButton(data.session.current_phase);
}

// When user clicks Resume
const resume = await fetch(`/api/session/${jiraKey}/resume`, {
  method: 'POST'
});
const session = await resume.json();
// Continue from session.phase_number
```

## Usage Examples

### Example 1: Save and Load a Checkpoint

```python
from verify.context import VerificationContext
from verify.negotiation.checkpoint import save_checkpoint, load_checkpoint

# Create a context
ctx = VerificationContext(
    jira_key="AUTH-123",
    jira_summary="Implement JWT authentication",
    raw_acceptance_criteria=[
        {"index": 0, "text": "Users can login with JWT token", "checked": False}
    ],
    constitution={"project": {"framework": "fastapi"}}
)

# Add some classification data
ctx.classifications = [
    {"ac_index": 0, "type": "api_behavior", "actor": "anonymous_user"}
]

# Save the checkpoint
path = save_checkpoint(ctx, "phase_1")
print(f"Saved to {path}")

# Later, load it back
result = load_checkpoint("AUTH-123")
if result:
    loaded_ctx, phase_idx = result
    print(f"Loaded context for {loaded_ctx.jira_key}")
    print(f"Phase index: {phase_idx}")
```

### Example 2: Check Session Status in Web UI

```python
# In a FastAPI endpoint
from verify.negotiation.checkpoint import has_checkpoint, get_session_info

@app.get("/api/session-status/{jira_key}")
async def check_session(jira_key: str):
    if has_checkpoint(jira_key):
        info = get_session_info(jira_key)
        return {
            "status": "has_checkpoint",
            "phase": info["current_phase"],
            "approved": info["approved"]
        }
    else:
        return {"status": "no_checkpoint"}
```

## Design Decisions

### 1. Checkpoint Location

Checkpoints are stored in `.verify/sessions/{jira_key}/` to:
- Organize by Jira key for easy browsing
- Keep them out of version control (`.verify/` is typically in `.gitignore`)
- Separate from generated artifacts

### 2. One File Per Phase

Each phase gets its own checkpoint file (e.g., `checkpoint_phase_1.json`) to:
- Allow independent inspection of each phase
- Enable potential rollback to earlier phases
- Maintain a clear audit trail

The latest checkpoint is loaded by default (alphabetical sort of files).

### 3. Phase Index Return Value

`load_checkpoint()` returns both the context AND the phase index to:
- Enable the web UI to know which phase to display
- Map to PHASE_SKILLS for correct phase numbering
- Avoid having to recalculate the phase index

### 4. Automatic Harness Integration

The harness automatically saves checkpoints because:
- Developers shouldn't need to remember to call save
- It follows the principle of implicit vs explicit tradeoffs
- Checkpoints are a safety feature, not a core requirement

## Testing

The implementation includes comprehensive tests:

- **Unit Tests** (`tests/test_checkpoint.py`):
  - 27 tests covering all checkpoint operations
  - Tests for edge cases and error handling
  - Round-trip serialization tests
  - Harness integration tests

- **Web Endpoint Tests** (`tests/test_checkpoint_web.py`):
  - 12 tests for the web API
  - Tests for session checking and resuming
  - Full workflow integration tests

All tests use temporary directories to avoid interfering with actual sessions.

## Future Enhancements

Potential future improvements:

1. **Checkpoint Cleanup**: Automatically delete old checkpoints after N days
2. **Checkpoint Diff**: Show what changed between checkpoints
3. **Checkpoint Restore UI**: Allow reverting to earlier checkpoints
4. **Compression**: Compress checkpoint JSON for storage efficiency
5. **Encryption**: Encrypt checkpoints containing sensitive data
6. **Cloud Backup**: Sync checkpoints to cloud storage

## Migration Path

To enable checkpoints in existing negotiations:

1. No migration needed - checkpoints are optional
2. Existing sessions without checkpoints will work normally
3. New sessions will automatically create checkpoints
4. Can manually save checkpoint of existing context with `save_checkpoint(ctx, phase)`

## Troubleshooting

### No checkpoint found

If `load_checkpoint()` returns `None`:
- Check that the session directory exists: `.verify/sessions/{jira_key}/`
- Verify checkpoint files exist: `ls .verify/sessions/{jira_key}/checkpoint_*.json`
- Ensure the jira_key matches exactly (case-sensitive)

### Stale checkpoint

To clear a stale checkpoint:
```python
from verify.negotiation.checkpoint import clear_session
clear_session("OLD-TICKET-001")
```

### Checkpoint file is corrupted

If a checkpoint file is corrupted (invalid JSON):
- Delete the corrupted file manually
- `load_checkpoint()` will ignore it and look for the next most recent
- If all are corrupted, use `clear_session()` to start fresh
