package main

import (
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gofiber/fiber/v2"
	"iterateswarm-core/internal/web"
)

func setupTestAppWithRealHandlers() *fiber.App {
	app := fiber.New()
	h := web.NewHandler()

	apiGroup := app.Group("/api")
	apiGroup.Get("/hitl/count", h.APIPendingHITL)
	apiGroup.Get("/hitl/queue", h.APIHITLQueue)
	apiGroup.Post("/hitl/:id/approve", h.APIHITLApprove)
	apiGroup.Post("/hitl/:id/reject", h.APIHITLReject)

	return app
}

func TestPendingQueueReturnsHTMXPartialOnHXRequest(t *testing.T) {
	app := setupTestAppWithRealHandlers()

	req := httptest.NewRequest("GET", "/api/hitl/queue", nil)
	req.Header.Set("HX-Request", "true")

	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("Failed to test request: %v", err)
	}

	body := make([]byte, 2048)
	resp.Body.Read(body)
	responseBody := strings.TrimSpace(string(body))

	if !strings.Contains(responseBody, "HITL-001") {
		t.Errorf("FAIL: Expected HTMX partial with HITL row, got: %q", responseBody)
	}
}

func TestApproveEndpointReturnsPartialForHTMX(t *testing.T) {
	app := setupTestAppWithRealHandlers()

	req := httptest.NewRequest("POST", "/api/hitl/1/approve", nil)
	req.Header.Set("HX-Request", "true")

	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("Failed to test request: %v", err)
	}

	body := make([]byte, 2048)
	resp.Body.Read(body)
	responseBody := strings.TrimSpace(string(body))

	if responseBody != "" {
		t.Errorf("FAIL: Expected empty partial for HTMX, got: %q", responseBody)
	}
}

func TestRejectEndpointReturnsPartialForHTMX(t *testing.T) {
	app := setupTestAppWithRealHandlers()

	req := httptest.NewRequest("POST", "/api/hitl/1/reject", nil)
	req.Header.Set("HX-Request", "true")

	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("Failed to test request: %v", err)
	}

	body := make([]byte, 2048)
	resp.Body.Read(body)
	responseBody := strings.TrimSpace(string(body))

	if responseBody != "" {
		t.Errorf("FAIL: Expected empty partial for HTMX, got: %q", responseBody)
	}
}

func TestApproveEndpointRespectsHXRequestHeader(t *testing.T) {
	app := setupTestApp()

	reqHTMX := httptest.NewRequest("POST", "/api/approvals/123/approve", nil)
	reqHTMX.Header.Set("HX-Request", "true")
	respHTMX, _ := app.Test(reqHTMX)

	bodyHTMX := make([]byte, 2048)
	respHTMX.Body.Read(bodyHTMX)
	responseHTMX := strings.TrimSpace(string(bodyHTMX))

	reqNonHTMX := httptest.NewRequest("POST", "/api/approvals/123/approve", nil)
	respNonHTMX, _ := app.Test(reqNonHTMX)

	bodyNonHTMX := make([]byte, 2048)
	respNonHTMX.Body.Read(bodyNonHTMX)
	responseNonHTMX := strings.TrimSpace(string(bodyNonHTMX))

	if responseHTMX == responseNonHTMX {
		t.Errorf("FAIL: Handler returns same response for HTMX and non-HTMX requests. HTMX: %q, Non-HTMX: %q", responseHTMX, responseNonHTMX)
		t.Log("Handler should check c.Get('HX-Request') and return different response (partial vs redirect)")
	}

	if respHTMX.StatusCode == 302 || respHTMX.StatusCode == 303 {
		t.Error("FAIL: HTMX request should NOT redirect, should return partial")
	}
}

func TestDismissEndpointRespectsHXRequestHeader(t *testing.T) {
	app := setupTestApp()

	reqHTMX := httptest.NewRequest("POST", "/api/approvals/123/dismiss", nil)
	reqHTMX.Header.Set("HX-Request", "true")
	respHTMX, _ := app.Test(reqHTMX)

	bodyHTMX := make([]byte, 2048)
	respHTMX.Body.Read(bodyHTMX)
	responseHTMX := strings.TrimSpace(string(bodyHTMX))

	reqNonHTMX := httptest.NewRequest("POST", "/api/approvals/123/dismiss", nil)
	respNonHTMX, _ := app.Test(reqNonHTMX)

	bodyNonHTMX := make([]byte, 2048)
	respNonHTMX.Body.Read(bodyNonHTMX)
	responseNonHTMX := strings.TrimSpace(string(bodyNonHTMX))

	if responseHTMX == responseNonHTMX {
		t.Errorf("FAIL: Handler returns same response for HTMX and non-HTMX requests. HTMX: %q, Non-HTMX: %q", responseHTMX, responseNonHTMX)
		t.Log("Handler should check c.Get('HX-Request') and return different response (empty partial vs redirect)")
	}

	if respHTMX.StatusCode == 302 || respHTMX.StatusCode == 303 {
		t.Error("FAIL: HTMX request should NOT redirect, should return empty for swap")
	}
}