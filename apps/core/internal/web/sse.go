package web

import (
	"bufio"
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/gofiber/fiber/v2"
)

// AgentEvent represents an agent activity event
type AgentEvent struct {
	ID        string                 `json:"id"`
	Timestamp time.Time              `json:"timestamp"`
	Agent     string                 `json:"agent"` // supervisor, researcher, sre, swe, reviewer
	Type      string                 `json:"type"`  // planning, executing, reviewing, completing
	TaskID    string                 `json:"task_id"`
	Data      map[string]interface{} `json:"data"`
}

// SSEHandler handles Server-Sent Events streaming
type SSEHandler struct {
	db *sql.DB
}

// NewSSEHandler creates a new SSE handler
func NewSSEHandler(db *sql.DB) *SSEHandler {
	return &SSEHandler{db: db}
}

// HandleSSE streams agent events via Server-Sent Events
func (h *SSEHandler) HandleSSE(c *fiber.Ctx) error {
	c.Set("Content-Type", "text/event-stream")
	c.Set("Cache-Control", "no-cache")
	c.Set("Connection", "keep-alive")
	c.Set("X-Accel-Buffering", "no")

	done := c.Context().Done()
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()
	notifyChan := make(chan string, 10)

	if h.db != nil {
		go func() {
			defer close(notifyChan)
			pollTicker := time.NewTicker(3 * time.Second)
			defer pollTicker.Stop()
			var lastCheck time.Time
			for {
				select {
				case <-pollTicker.C:
					rows, err := h.db.Query(`SELECT event_type FROM agent_events WHERE created_at > $1 ORDER BY created_at ASC LIMIT 10`, lastCheck)
					if err == nil {
						var events []string
						for rows.Next() {
							var et string
							rows.Scan(&et)
							events = append(events, et)
						}
						rows.Close()
						if len(events) > 0 {
							data, _ := json.Marshal(map[string]interface{}{"events": events, "count": len(events)})
							notifyChan <- string(data)
						}
					}
					lastCheck = time.Now()
				case <-done:
					return
				}
			}
		}()
	}

	c.Response().SetBodyStreamWriter(func(w *bufio.Writer) {
		fmt.Fprintf(w, "event: connected\ndata: {\"status\":\"connected\"}\n\n")
		w.Flush()

		for {
			select {
			case <-ticker.C:
				fmt.Fprintf(w, "event: heartbeat\ndata: {}\n\n")
				w.Flush()
			case data, ok := <-notifyChan:
				if !ok {
					return
				}
				fmt.Fprintf(w, "event: message\ndata: %s\n\n", data)
				w.Flush()
			case <-done:
				return
			}
		}
	})

	return nil
}

// PublishAgentEvent publishes an agent event to PostgreSQL
func PublishAgentEvent(ctx context.Context, db *sql.DB, event AgentEvent) error {
	// Insert event into database - trigger will send NOTIFY
	metadataJSON, err := json.Marshal(event.Data)
	if err != nil {
		return err
	}

	_, err = db.ExecContext(ctx, `
		INSERT INTO agent_events (event_type, task_id, agent_name, message, severity, metadata)
		VALUES ($1, $2, $3, $4, $5, $6)
	`, event.Type, event.TaskID, event.Agent, "", "info", metadataJSON)

	return err
}
