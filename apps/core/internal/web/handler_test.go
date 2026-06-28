package web

import (
	"testing"

	"github.com/gofiber/fiber/v2"
)

func TestChatBroadcastDoesNotBlockOnFullBuffer(t *testing.T) {
	h := NewHandler(nil, nil)
	// Fill the buffer
	for i := 0; i < 100; i++ {
		h.chatBroadcast <- fiber.Map{"sender": "test"}
	}
	// This should not block (select + default)
	h.tryBroadcast("test", "Test", "This should not block")
	// If we reach here, the test passes (non-blocking behavior confirmed)
}
