# Chat Flow — @Mention → Specialist Workflow → SSE Result

> **Purpose**: Document the end-to-end chat flow from user typing `@finance` to seeing the response rendered in the browser via HTMX SSE.

## Sequence Diagram

```
Browser (HTMX)          Go Core (Fiber)          Temporal Server      Python AI Worker
     │                       │                        │                    │
     │ 1. type @finance      │                        │                    │
     │ 2. POST /chat/send    │                        │                    │
     │ ───────────────────►  │                        │                    │
     │                       │ 3. extractMentions()   │                    │
     │                       │    specialistRoutes[]  │                    │
     │                       │ 4. "🤔 Thinking..."    │                    │
     │                       │    via tryBroadcast()  │                    │
     │  ◄── SSE event:chat── │                        │                    │
     │  [Thinking bubble]    │                        │                    │
     │                       │ 5. ExecuteWorkflow()   │                    │
     │                       │ ───────────────────►  │                    │
     │                       │                        │ 6. Schedule task   │
     │                       │                        │ ───────────────►  │
     │                       │                        │                    │ 7. agent.invoke()
     │                       │                        │                    │    (LangGraph + Groq)
     │                       │                        │                    │
     │                       │                        │  ◄── result ────  │
     │                       │  ◄── result ─────────  │                    │
     │                       │                        │                    │
     │                       │ 8. renderChatBubble()  │                    │
     │                       │    tryBroadcast(result)│                    │
     │  ◄── SSE event:chat── │                        │                    │
     │  [Answer bubble]      │                        │                    │
     │                       │                        │                    │
```

## Step-by-Step Flow

### 1. HTMX Form Submission

File: `command_chat.html` (lines 67-86)
```html
<form hx-post="/api/command/chat/send"
      hx-target="#chat-messages"
      hx-swap="beforeend"
      hx-indicator="#chat-loading">
  <select name="mention">
    <option value="@all">@all</option>
    <option value="@sarthi">Sarthi (Manager)</option>
    <option value="@finance">Finance (Analyst)</option>
    <option value="@data">Data (Analyst)</option>
    <option value="@ops">Ops (Analyst)</option>
  </select>
  <input type="text" name="message" required>
  <button type="submit">Send</button>
</form>
```

The form uses `hx-target="#chat-messages"` with `hx-swap="beforeend"` to append the returned HTML to the chat container.

### 2. Go Handler: APICommandChatSend

File: `handler.go` (lines 1197-1351)

The handler:
1. Extracts `message` and `mention` from form values
2. Calls `extractMentions(message)` to find inline `@mentions`
3. Deduplicates mentions
4. Persists the message to `chat_messages` table (if DB available)
5. Broadcasts the user message via `h.chatBroadcast` channel → SSE
6. Matches mention against `specialistRoutes` map
7. If matched: shows "🤔 Thinking..." via `tryBroadcast()`, then dispatches Temporal workflow in goroutine
8. Returns the user's chat bubble as HTML

```go
// specialistRoutes maps @mentions to workflow types and display names
var specialistRoutes = map[string]specialistRoute{
    "@sarthi":  {"QAWorkflow", "Sarthi"},
    "@agent":   {"QAWorkflow", "Sarthi"},
    "@qa":      {"QAWorkflow", "Sarthi"},
    "@ask":     {"QAWorkflow", "Sarthi"},
    "@finance": {"FinanceWorkflow", "Finance"},
    "@data":    {"DataWorkflow", "Data"},
    "@ops":     {"OpsWorkflow", "Ops"},
    "@comms":   {"CommsWorkflow", "Comms"},
    "@hiring":  {"HiringWorkflow", "Hiring"},
}
```

### 3. Temporal Workflow Dispatch (Goroutine)

The goroutine (handler.go:1286-1343):
1. Creates a context with 5-minute timeout
2. Calls `handler.temporal.Client.ExecuteWorkflow(ctx, opts, workflowType, input)`
3. Waits for result via `run.Get(ctx, &result)`
4. Extracts `qa_result.answer` or falls back to error message
5. Persists agent response to `chat_messages` table
6. Broadcasts result via `tryBroadcast()` → SSE channel

**Goroutine safety**: Uses `handler.wg.Add(1)/Done()` for WaitGroup tracking, context cancellation via passed `reqCtx`.

### 4. SSE Broadcasting

File: `handler.go` — `APICommandChatEvents` (lines 1470-1515)

```go
func (h *Handler) APICommandChatEvents(c *fiber.Ctx) error {
    c.Set("Content-Type", "text/event-stream")
    c.Set("Cache-Control", "no-cache")
    c.Set("Connection", "keep-alive")

    done := c.Context().Done()
    c.Context().SetBodyStreamWriter(func(w *bufio.Writer) {
        // Send connected event
        fmt.Fprintf(w, "event: connected\ndata: {...}\n\n")

        // Heartbeat every 30s
        heartbeat := time.NewTicker(30 * time.Second)
        defer heartbeat.Stop()

        for {
            select {
            case <-heartbeat.C:
                fmt.Fprintf(w, "event: heartbeat\ndata: {}\n\n")
                w.Flush()
            case msg := <-h.chatBroadcast:
                html := h.renderChatBubble(sender, displayName, text, timeStr)
                fmt.Fprintf(w, "event: chat\ndata: %s\n\n", html)
                w.Flush()
            case <-done:
                return
            }
        }
    })
    return nil
}
```

Key patterns:
- **Fiber v2 `SetBodyStreamWriter`**: Proper SSE streaming support
- **`tryBroadcast()`**: Non-blocking send with `select/default` to prevent goroutine leaks. Also pushes to `sseHub.Broadcast("default", SSEEvent{Type: "chat", ...})` for fan-out.
- **SSEHub event-type filtering**: The SSEHub (sse_hub.go) manages per-subscriber channels with optional `Types` filter. Subscribing with `sseHub.Subscribe(tenantID, "chat")` only receives events with `Type == "chat"`.
- **Three SSE event domains** (2026-06-28):
  - `event: chat` — Chat bubble HTML fragments (for `sse-swap="chat"`)
  - `event: mission` — Mission state updates (prepared_brief, pending_decisions changes)
  - `event: hitl` — HITL approval signals (new pending, approved, rejected)
  - `event: session` — Session events (connection state, context updates)
- **SSE endpoints**: `APICommandChatEvents` (chat-specific via SSEHub), `APICommandEvents` (dashboard heartbeats), plus new typed subscribe endpoints for mission/hitl/session event types.
- **`recover()`**: Deferred in stream writer to prevent panic from closed connections

### 5. HTMX SSE Swap

File: `command_chat.html` (lines 25-31)
```html
<div id="chat-messages"
     hx-ext="sse"
     sse-connect="/api/command/chat/events"
     sse-swap="chat"
     hx-swap="beforeend">
```

- `hx-ext="sse"` enables the HTMX SSE extension
- `sse-connect` opens the EventSource connection
- `sse-swap="chat"` listens for `event: chat` and swaps the data as HTML
- `hx-swap="beforeend"` appends each bubble to the container

### 6. Chat Bubble Rendering

File: `handler.go` — `renderChatBubble` (lines 1355-1405)

Renders an HTML fragment with:
- Avatar circle with agent initial (Y/S/F/D/O/A)
- Display name ("You" / "Sarthi (Manager)" / "Finance (Analyst)" / etc.)
- Timestamp
- Message text (HTML-escaped)

Agent color classes: `agent-sarthi` (blue), `agent-finance` (green), `agent-data` (purple), `agent-ops` (yellow), `agent-system` (gray).

### 7. Special Cases

| Scenario | Behavior | File Reference |
|----------|----------|----------------|
| No DB | Returns empty string | handler.go |
| No Temporal | Skips workflow dispatch | handler.go |
| Workflow error | Broadcasts error bubble | handler.go |
| Channel full | Drops message, logs warning | handler.go |
| Empty message | Returns empty string | handler.go |
| Missing mention | No workflow dispatch, just saves message | handler.go |
| SSEHub Subscribe with type filter | Only receives matching event types | sse_hub.go:39-53 |
| SSEHub Broadcast no matching subs | Event silently dropped (no subscriber with matching type filter) | sse_hub.go:75-93 |
| SSEHub subscriber channel full | Event dropped per sub (non-blocking per-subscriber channel) | sse_hub.go:89-92 |
| SSEHub Unsubscribe | Channel closed and removed from subscriber map | sse_hub.go:56-64 |

### 8. JavaScript Integration

File: `command_chat.html` (lines 89-143)

- SSE connection status indicator (connected/disconnected/connecting)
- Auto-scroll on new messages via `MutationObserver`
- Clear input on successful send via `htmx:afterRequest` event
- `htmx:sseOpen` / `htmx:sseError` events for status updates
