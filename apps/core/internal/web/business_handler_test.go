package web

import (
	"io"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gofiber/fiber/v2"
)

// ── Decision Queue ────────────────────────────────────────────────────

func TestBusinessDecisionQueue_ReturnsHTMXPartialOnHXRequest(t *testing.T) {
	app := fiber.New()
	h := NewHandler(nil, nil)

	app.Get("/api/business/decision-queue", h.APIBusinessDecisionQueue)

	req := httptest.NewRequest("GET", "/api/business/decision-queue", nil)
	req.Header.Set("HX-Request", "true")
	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("Failed: %v", err)
	}

	body, _ := io.ReadAll(resp.Body)
	bodyStr := strings.TrimSpace(string(body))

	if !strings.Contains(bodyStr, "Decision Queue") {
		t.Errorf("FAIL: Expected Decision Queue title, got: %q", bodyStr)
	}
}

func TestBusinessDecisionQueue_ShowsPendingDecisions(t *testing.T) {
	app := fiber.New()
	h := NewHandler(nil, nil)

	app.Get("/api/business/decision-queue", h.APIBusinessDecisionQueue)

	req := httptest.NewRequest("GET", "/api/business/decision-queue", nil)
	req.Header.Set("HX-Request", "true")
	resp, _ := app.Test(req)

	body, _ := io.ReadAll(resp.Body)
	bodyStr := strings.ToLower(string(body))

	// Should show decision entries
	if !strings.Contains(bodyStr, "dec-001") && !strings.Contains(bodyStr, "pending") {
		t.Errorf("FAIL: Expected decision entries, got: %q", bodyStr)
	}
}

func TestBusinessDecisionQueue_ShowsEmptyState(t *testing.T) {
	// Test by checking the template renders with empty decisions
	html := renderDecisionQueueHTML([]BusinessDecision{})
	if !strings.Contains(html, "All decisions processed") {
		t.Errorf("FAIL: Expected empty state message, got: %q", html)
	}
}

func TestBusinessDecisionQueue_ApproveButtonExists(t *testing.T) {
	app := fiber.New()
	h := NewHandler(nil, nil)

	app.Get("/api/business/decision-queue", h.APIBusinessDecisionQueue)

	req := httptest.NewRequest("GET", "/api/business/decision-queue", nil)
	req.Header.Set("HX-Request", "true")
	resp, _ := app.Test(req)

	body, _ := io.ReadAll(resp.Body)
	bodyStr := string(body)

	if !strings.Contains(bodyStr, "hx-post") || !strings.Contains(bodyStr, "approve") {
		t.Errorf("FAIL: Expected approve button with hx-post, got: %q", bodyStr)
	}
}

// ── Guardrail Status ──────────────────────────────────────────────────

func TestGuardrailStatus_ReturnsHTMXPartialOnHXRequest(t *testing.T) {
	app := fiber.New()
	h := NewHandler(nil, nil)

	app.Get("/api/business/guardrail-status", h.APIGuardrailStatus)

	req := httptest.NewRequest("GET", "/api/business/guardrail-status", nil)
	req.Header.Set("HX-Request", "true")
	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("Failed: %v", err)
	}

	body, _ := io.ReadAll(resp.Body)
	bodyStr := strings.TrimSpace(string(body))

	if !strings.Contains(bodyStr, "Guardrail Status") {
		t.Errorf("FAIL: Expected Guardrail Status title, got: %q", bodyStr)
	}
}

func TestGuardrailStatus_ShowsAllFourGuardrails(t *testing.T) {
	app := fiber.New()
	h := NewHandler(nil, nil)

	app.Get("/api/business/guardrail-status", h.APIGuardrailStatus)

	req := httptest.NewRequest("GET", "/api/business/guardrail-status", nil)
	req.Header.Set("HX-Request", "true")
	resp, _ := app.Test(req)

	body, _ := io.ReadAll(resp.Body)
	bodyStr := string(body)

	// Should show all 4 guardrail metrics
	checks := []string{"Approval Tier", "Reversibility", "Investor Facing", "Privacy Filter"}
	for _, check := range checks {
		if !strings.Contains(bodyStr, check) {
			t.Errorf("FAIL: Expected guardrail metric '%s' in response", check)
		}
	}
}

func TestGuardrailStatus_ShowsActiveBlocks(t *testing.T) {
	html := renderGuardrailStatusHTML(GuardrailStatusData{
		ApprovalTier:     "auto",
		Reversible:       true,
		InvestorFacing:   false,
		PrivacySensitive: false,
		ActiveBlocks:     0,
		BlockReasons:     []string{},
	})
	if !strings.Contains(html, "No active guardrail blocks") {
		t.Errorf("FAIL: Expected 'no active blocks' message, got: %q", html)
	}
}

// ── Finance Risk ──────────────────────────────────────────────────────

func TestFinanceRisk_ReturnsHTMXPartialOnHXRequest(t *testing.T) {
	app := fiber.New()
	h := NewHandler(nil, nil)

	app.Get("/api/business/finance-risk", h.APIFinanceRisk)

	req := httptest.NewRequest("GET", "/api/business/finance-risk", nil)
	req.Header.Set("HX-Request", "true")
	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("Failed: %v", err)
	}

	body, _ := io.ReadAll(resp.Body)
	bodyStr := strings.TrimSpace(string(body))

	if !strings.Contains(bodyStr, "Finance Risk") {
		t.Errorf("FAIL: Expected Finance Risk title, got: %q", bodyStr)
	}
}

func TestFinanceRisk_ShowsAllFourMetrics(t *testing.T) {
	app := fiber.New()
	h := NewHandler(nil, nil)

	app.Get("/api/business/finance-risk", h.APIFinanceRisk)

	req := httptest.NewRequest("GET", "/api/business/finance-risk", nil)
	req.Header.Set("HX-Request", "true")
	resp, _ := app.Test(req)

	body, _ := io.ReadAll(resp.Body)
	bodyStr := string(body)

	checks := []string{"Burn Multiple", "Runway", "Working Capital", "WACC"}
	for _, check := range checks {
		if !strings.Contains(bodyStr, check) {
			t.Errorf("FAIL: Expected metric '%s' in response", check)
		}
	}
}

func TestFinanceRisk_ColorCodesByRiskLevel(t *testing.T) {
	// Test green (safe) values
	html := renderFinanceRiskHTML(FinanceRiskData{BurnMultiple: 1.0, RunwayDays: 300, WorkingCapitalRatio: 2.5, WACC: 0.1, LastUpdated: "test"})
	if !strings.Contains(html, "text-green-600") {
		t.Errorf("FAIL: Expected green coloring for safe values, got: %q", html)
	}

	// Test red (danger) values
	html = renderFinanceRiskHTML(FinanceRiskData{BurnMultiple: 2.5, RunwayDays: 60, WorkingCapitalRatio: 0.5, WACC: 0.1, LastUpdated: "test"})
	if !strings.Contains(html, "text-red-600") {
		t.Errorf("FAIL: Expected red coloring for dangerous values, got: %q", html)
	}
}

func TestFinanceRisk_ShowsLastUpdated(t *testing.T) {
	html := renderFinanceRiskHTML(FinanceRiskData{BurnMultiple: 1.0, RunwayDays: 300, WorkingCapitalRatio: 2.0, WACC: 0.1, LastUpdated: "test-timestamp"})
	if !strings.Contains(html, "test-timestamp") {
		t.Errorf("FAIL: Expected LastUpdated timestamp in output, got: %q", html)
	}
}

// ── Approve/Reject Actions ────────────────────────────────────────────

func TestBusinessDecisionApprove_ReturnsEmptyOnHTMX(t *testing.T) {
	app := fiber.New()
	h := NewHandler(nil, nil)

	app.Post("/api/business/decisions/:id/approve", h.APIBusinessDecisionApprove)

	req := httptest.NewRequest("POST", "/api/business/decisions/DEC-001/approve", nil)
	req.Header.Set("HX-Request", "true")
	resp, _ := app.Test(req)

	body, _ := io.ReadAll(resp.Body)
	if strings.TrimSpace(string(body)) != "" {
		t.Errorf("FAIL: Expected empty body on HTMX approve, got: %q", string(body))
	}
}

func TestBusinessDecisionReject_ReturnsEmptyOnHTMX(t *testing.T) {
	app := fiber.New()
	h := NewHandler(nil, nil)

	app.Post("/api/business/decisions/:id/reject", h.APIBusinessDecisionReject)

	req := httptest.NewRequest("POST", "/api/business/decisions/DEC-001/reject", nil)
	req.Header.Set("HX-Request", "true")
	resp, _ := app.Test(req)

	body, _ := io.ReadAll(resp.Body)
	if strings.TrimSpace(string(body)) != "" {
		t.Errorf("FAIL: Expected empty body on HTMX reject, got: %q", string(body))
	}
}
