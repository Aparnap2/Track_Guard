package web

import (
	"encoding/json"
	"fmt"
	"sync"

	"github.com/google/uuid"
)

// SSEEvent represents a server-sent event
type SSEEvent struct {
	Type    string `json:"type"`
	Payload string `json:"payload"`
}

// Subscription represents a single SSE subscription with optional event type filtering
type Subscription struct {
	ID      string
	Channel chan []byte
	Types   []string // empty = all events
}

// SSEHub manages fan-out subscriptions for Server-Sent Events
type SSEHub struct {
	mu          sync.RWMutex
	subscribers map[string]map[string]*Subscription // tenantID -> subID -> *Subscription
}

// NewSSEHub creates a new SSEHub
func NewSSEHub() *SSEHub {
	return &SSEHub{
		subscribers: make(map[string]map[string]*Subscription),
	}
}

// Subscribe creates a new subscription for a tenant with optional event type filters.
// If eventTypes is empty, the subscriber receives all events for the tenant.
func (h *SSEHub) Subscribe(tenantID string, eventTypes ...string) Subscription {
	h.mu.Lock()
	defer h.mu.Unlock()
	subID := uuid.New().String()
	sub := Subscription{
		ID:      subID,
		Channel: make(chan []byte, 64),
		Types:   eventTypes,
	}
	if h.subscribers[tenantID] == nil {
		h.subscribers[tenantID] = make(map[string]*Subscription)
	}
	h.subscribers[tenantID][subID] = &sub
	return sub
}

// Unsubscribe removes a subscription by ID
func (h *SSEHub) Unsubscribe(tenantID, subID string) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if subs, ok := h.subscribers[tenantID]; ok {
		if sub, ok := subs[subID]; ok {
			close(sub.Channel)
			delete(subs, subID)
		}
	}
}

// Broadcast sends an event to matching subscribers of a tenant (non-blocking).
// Only subscribers whose Types filter includes event.Type (or whose Types is empty)
// will receive the event.
func (h *SSEHub) Broadcast(tenantID string, event SSEEvent) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	data, _ := json.Marshal(event)
	msg := fmt.Sprintf("event: %s\ndata: %s\n\n", event.Type, string(data))
	for _, sub := range h.subscribers[tenantID] {
		// If subscriber has type filters, skip if none match
		if len(sub.Types) > 0 {
			matches := false
			for _, t := range sub.Types {
				if t == event.Type {
					matches = true
					break
				}
			}
			if !matches {
				continue
			}
		}
		select {
		case sub.Channel <- []byte(msg):
		default:
		}
	}
}
