package web

import (
	"fmt"
	"time"

	"github.com/gofiber/fiber/v2"
)

// ── Data types ─────────────────────────────────────────────────────────

// BusinessDecision represents a pending decision in the queue
type BusinessDecision struct {
	ID          string
	Type        string
	Severity    string
	Description string
	Timestamp   string
	Status      string
}

// GuardrailStatusData represents current guardrail system state
type GuardrailStatusData struct {
	ApprovalTier     string
	Reversible       bool
	InvestorFacing   bool
	PrivacySensitive bool
	ActiveBlocks     int
	BlockReasons     []string
}

// FinanceRiskData represents current financial risk metrics
type FinanceRiskData struct {
	BurnMultiple        float64
	RunwayDays          int
	WorkingCapitalRatio float64
	WACC                float64
	LastUpdated         string
}

// ── Handler: Decision Queue ────────────────────────────────────────────

// APIBusinessDecisionQueue serves the decision queue HTMX partial
func (h *Handler) APIBusinessDecisionQueue(c *fiber.Ctx) error {
	if c.Get("HX-Request") == "true" {
		data := getDefaultDecisions()
		return c.SendString(renderDecisionQueueHTML(data))
	}
	return c.SendString("Decision queue")
}

// ── Handler: Guardrail Status ──────────────────────────────────────────

// APIGuardrailStatus serves the guardrail status HTMX partial
func (h *Handler) APIGuardrailStatus(c *fiber.Ctx) error {
	if c.Get("HX-Request") == "true" {
		data := GuardrailStatusData{
			ApprovalTier:     "auto",
			Reversible:       true,
			InvestorFacing:   false,
			PrivacySensitive: false,
			ActiveBlocks:     0,
			BlockReasons:     []string{},
		}
		return c.SendString(renderGuardrailStatusHTML(data))
	}
	return c.SendString("Guardrail status")
}

// ── Handler: Finance Risk ─────────────────────────────────────────────

// APIFinanceRisk serves the finance risk HTMX partial
func (h *Handler) APIFinanceRisk(c *fiber.Ctx) error {
	if c.Get("HX-Request") == "true" {
		data := FinanceRiskData{
			BurnMultiple:        1.2,
			RunwayDays:          210,
			WorkingCapitalRatio: 2.5,
			WACC:                0.114,
			LastUpdated:         time.Now().UTC().Format("2006-01-02 15:04:05 UTC"),
		}
		return c.SendString(renderFinanceRiskHTML(data))
	}
	return c.SendString("Finance risk")
}

// ── Action handlers ───────────────────────────────────────────────────

// APIBusinessDecisionApprove approves a pending decision
func (h *Handler) APIBusinessDecisionApprove(c *fiber.Ctx) error {
	id := c.Params("id")
	if c.Get("HX-Request") == "true" {
		// Return empty to remove row from view (HTMX swap)
		return c.SendString("")
	}
	return c.SendString(fmt.Sprintf("Approved decision %s", id))
}

// APIBusinessDecisionReject rejects a pending decision
func (h *Handler) APIBusinessDecisionReject(c *fiber.Ctx) error {
	id := c.Params("id")
	if c.Get("HX-Request") == "true" {
		return c.SendString("")
	}
	return c.SendString(fmt.Sprintf("Rejected decision %s", id))
}

// ── HTMX rendering helpers ────────────────────────────────────────────

func getDefaultDecisions() []BusinessDecision {
	// Default demo decisions — in production these come from the business pipeline
	now := time.Now().UTC()
	return []BusinessDecision{
		{ID: "DEC-001", Type: "finance", Severity: "warning", Description: "Burn rate exceeded 2x threshold", Timestamp: now.Add(-30 * time.Minute).Format(time.RFC3339), Status: "pending"},
		{ID: "DEC-002", Type: "bi", Severity: "info", Description: "MRR growth trend declining for 3 weeks", Timestamp: now.Add(-2 * time.Hour).Format(time.RFC3339), Status: "pending"},
		{ID: "DEC-003", Type: "ops", Severity: "critical", Description: "Error rate spike in production", Timestamp: now.Add(-5 * time.Hour).Format(time.RFC3339), Status: "blocked"},
	}
}

// renderDecisionQueueHTML builds the HTML for the decision queue panel
func renderDecisionQueueHTML(decisions []BusinessDecision) string {
	var rows string
	for _, d := range decisions {
		// Type badge class
		typeBadge := ""
		switch d.Type {
		case "finance":
			typeBadge = "bg-red-100 text-red-800"
		case "bi":
			typeBadge = "bg-blue-100 text-blue-800"
		case "ops":
			typeBadge = "bg-gray-100 text-gray-800"
		default:
			typeBadge = "bg-gray-100 text-gray-800"
		}

		// Severity badge class
		sevBadge := ""
		switch d.Severity {
		case "critical":
			sevBadge = "bg-red-100 text-red-800"
		case "warning":
			sevBadge = "bg-yellow-100 text-yellow-800"
		case "info":
			sevBadge = "bg-blue-100 text-blue-800"
		default:
			sevBadge = "bg-gray-100 text-gray-800"
		}

		// Status badge class
		statusBadge := ""
		switch d.Status {
		case "pending":
			statusBadge = "bg-amber-100 text-amber-800"
		case "approved":
			statusBadge = "bg-green-100 text-green-800"
		case "rejected":
			statusBadge = "bg-red-100 text-red-800"
		case "blocked":
			statusBadge = "bg-gray-100 text-gray-800"
		default:
			statusBadge = "bg-gray-100 text-gray-800"
		}

		rows += fmt.Sprintf(`
		<tr class="border-b hover:bg-gray-50" id="decision-%s">
			<td class="px-4 py-3 text-sm font-medium text-gray-900">%s</td>
			<td class="px-4 py-3"><span class="px-2 py-1 text-xs rounded-full %s">%s</span></td>
			<td class="px-4 py-3"><span class="px-2 py-1 text-xs rounded-full %s">%s</span></td>
			<td class="px-4 py-3 text-sm text-gray-600">%s</td>
			<td class="px-4 py-3 text-xs text-gray-500">%s</td>
			<td class="px-4 py-3"><span class="px-2 py-1 text-xs rounded-full %s">%s</span></td>
			<td class="px-4 py-3">
				<button hx-post="/api/business/decisions/%s/approve" hx-target="closest tr" hx-swap="outerHTML swap:0.3s" class="text-green-600 hover:text-green-900 mr-2 text-sm">Approve</button>
				<button hx-post="/api/business/decisions/%s/reject" hx-target="closest tr" hx-swap="outerHTML swap:0.3s" class="text-red-600 hover:text-red-900 mr-2 text-sm">Reject</button>
				<button class="text-indigo-600 hover:text-indigo-900 text-sm">View</button>
			</td>
		</tr>`, d.ID, d.ID, typeBadge, d.Type, sevBadge, d.Severity, d.Description, d.Timestamp, statusBadge, d.Status, d.ID, d.ID)
	}

	emptyMsg := ""
	if len(decisions) == 0 {
		emptyMsg = `<tr><td colspan="7" class="px-4 py-8 text-center text-gray-500">✨ All decisions processed. No pending items.</td></tr>`
	}

	return fmt.Sprintf(`
	<div class="card bg-white rounded-xl shadow-md overflow-hidden">
		<div class="card-header bg-gradient-to-r from-amber-600 to-orange-600 px-6 py-4">
			<div class="flex items-center justify-between">
				<h3 class="text-lg font-semibold text-white"><i class="fas fa-bolt mr-2"></i>Decision Queue</h3>
				<span class="px-3 py-1 bg-white/20 text-white rounded-full text-xs font-semibold"><i class="fas fa-clock mr-1"></i>%d pending</span>
			</div>
		</div>
		<div class="p-6" hx-get="/api/business/decision-queue" hx-trigger="every 10s" id="decision-queue">
			<div class="htmx-indicator flex justify-center py-4"><i class="fas fa-circle-notch fa-spin text-2xl text-amber-600"></i></div>
			<table class="w-full">
				<thead><tr class="text-left text-xs font-medium text-gray-500 uppercase"><th class="px-4 py-2">ID</th><th class="px-4 py-2">Type</th><th class="px-4 py-2">Severity</th><th class="px-4 py-2">Description</th><th class="px-4 py-2">Time</th><th class="px-4 py-2">Status</th><th class="px-4 py-2">Actions</th></tr></thead>
				<tbody>%s%s</tbody>
			</table>
		</div>
	</div>`, len(decisions), emptyMsg, rows)
}

// renderGuardrailStatusHTML builds the HTML for the guardrail status panel
func renderGuardrailStatusHTML(data GuardrailStatusData) string {
	tierColor := "bg-green-100 text-green-800"
	tierLabel := "Auto"
	if data.ApprovalTier == "review" {
		tierColor = "bg-yellow-100 text-yellow-800"
		tierLabel = "Review"
	}
	if data.ApprovalTier == "blocking" {
		tierColor = "bg-red-100 text-red-800"
		tierLabel = "Blocking"
	}

	revColor := "bg-green-100 text-green-800"
	revLabel := "Reversible"
	if !data.Reversible {
		revColor = "bg-red-100 text-red-800"
		revLabel = "Irreversible"
	}

	invColor := "bg-blue-100 text-blue-800"
	invLabel := "Inactive"
	if data.InvestorFacing {
		invColor = "bg-amber-100 text-amber-800"
		invLabel = "Active"
	}

	privColor := "bg-gray-100 text-gray-800"
	privLabel := "Inactive"
	if data.PrivacySensitive {
		privColor = "bg-green-100 text-green-800"
		privLabel = "Active"
	}

	blocksHTML := `<p class="text-sm text-gray-500">✅ No active guardrail blocks</p>`
	if data.ActiveBlocks > 0 {
		var reasons string
		for _, r := range data.BlockReasons {
			reasons += fmt.Sprintf(`<li class="text-sm text-red-600">• %s</li>`, r)
		}
		blocksHTML = fmt.Sprintf(`<ul class="space-y-1">%s</ul>`, reasons)
	}

	return fmt.Sprintf(`
	<div class="card bg-white rounded-xl shadow-md overflow-hidden">
		<div class="card-header bg-gradient-to-r from-violet-600 to-purple-600 px-6 py-4">
			<div class="flex items-center justify-between">
				<h3 class="text-lg font-semibold text-white"><i class="fas fa-shield-alt mr-2"></i>Guardrail Status</h3>
			</div>
		</div>
		<div class="p-6" hx-get="/api/business/guardrail-status" hx-trigger="every 15s" id="guardrail-status">
			<div class="htmx-indicator flex justify-center py-4"><i class="fas fa-circle-notch fa-spin text-2xl text-purple-600"></i></div>
			<div class="grid grid-cols-2 gap-4 mb-4">
				<div class="p-4 bg-gray-50 rounded-lg"><p class="text-xs text-gray-500 mb-1">Approval Tier</p><span class="px-2 py-1 text-sm rounded-full %s">%s</span><p class="text-xs text-gray-400 mt-1">Current approval threshold</p></div>
				<div class="p-4 bg-gray-50 rounded-lg"><p class="text-xs text-gray-500 mb-1">Reversibility</p><span class="px-2 py-1 text-sm rounded-full %s">%s</span><p class="text-xs text-gray-400 mt-1">Can decisions be undone</p></div>
				<div class="p-4 bg-gray-50 rounded-lg"><p class="text-xs text-gray-500 mb-1">Investor Facing</p><span class="px-2 py-1 text-sm rounded-full %s">%s</span><p class="text-xs text-gray-400 mt-1">Investor comms flag</p></div>
				<div class="p-4 bg-gray-50 rounded-lg"><p class="text-xs text-gray-500 mb-1">Privacy Filter</p><span class="px-2 py-1 text-sm rounded-full %s">%s</span><p class="text-xs text-gray-400 mt-1">PII detection status</p></div>
			</div>
			<div class="border-t pt-4"><h4 class="text-sm font-semibold text-gray-700 mb-2">Active Blocks</h4>%s</div>
		</div>
	</div>`, tierColor, tierLabel, revColor, revLabel, invColor, invLabel, privColor, privLabel, blocksHTML)
}

// renderFinanceRiskHTML builds the HTML for the finance risk panel
func renderFinanceRiskHTML(data FinanceRiskData) string {
	// Burn multiple color
	burnColor := "text-green-600"
	if data.BurnMultiple >= 1.5 && data.BurnMultiple <= 2.0 {
		burnColor = "text-yellow-600"
	}
	if data.BurnMultiple > 2.0 {
		burnColor = "text-red-600"
	}

	// Runway color
	runwayColor := "text-green-600"
	if data.RunwayDays >= 90 && data.RunwayDays <= 180 {
		runwayColor = "text-yellow-600"
	}
	if data.RunwayDays < 90 {
		runwayColor = "text-red-600"
	}

	// Working capital color
	wcColor := "text-green-600"
	if data.WorkingCapitalRatio >= 1.0 && data.WorkingCapitalRatio <= 1.5 {
		wcColor = "text-yellow-600"
	}
	if data.WorkingCapitalRatio < 1.0 {
		wcColor = "text-red-600"
	}

	return fmt.Sprintf(`
	<div class="card bg-white rounded-xl shadow-md overflow-hidden">
		<div class="card-header bg-gradient-to-r from-emerald-600 to-teal-600 px-6 py-4">
			<div class="flex items-center justify-between">
				<h3 class="text-lg font-semibold text-white"><i class="fas fa-chart-line mr-2"></i>Finance Risk</h3>
			</div>
		</div>
		<div class="p-6" hx-get="/api/business/finance-risk" hx-trigger="every 15s" id="finance-risk">
			<div class="htmx-indicator flex justify-center py-4"><i class="fas fa-circle-notch fa-spin text-2xl text-emerald-600"></i></div>
			<div class="grid grid-cols-2 gap-4 mb-4">
				<div class="p-4 bg-gray-50 rounded-lg text-center"><p class="text-3xl font-bold %s">%.1fx</p><p class="text-xs text-gray-500 mt-1">Burn Multiple</p></div>
				<div class="p-4 bg-gray-50 rounded-lg text-center"><p class="text-3xl font-bold %s">%dd</p><p class="text-xs text-gray-500 mt-1">Runway</p></div>
				<div class="p-4 bg-gray-50 rounded-lg text-center"><p class="text-3xl font-bold %s">%.1fx</p><p class="text-xs text-gray-500 mt-1">Working Capital</p></div>
				<div class="p-4 bg-gray-50 rounded-lg text-center"><p class="text-3xl font-bold text-blue-600">%.1f%%</p><p class="text-xs text-gray-500 mt-1">WACC</p></div>
			</div>
			<div class="border-t pt-3 text-center"><p class="text-xs text-gray-400">Last updated: %s</p></div>
		</div>
	</div>`, burnColor, data.BurnMultiple, runwayColor, data.RunwayDays, wcColor, data.WorkingCapitalRatio, data.WACC*100, data.LastUpdated)
}
