package workflow

// DiscordApprovalInput is the input for sending Discord approval requests.
// Kept here as a convenience type used within this package.
type DiscordApprovalInput struct {
	TaskID  string
	Title   string
	Content string
	RunID   string
}
