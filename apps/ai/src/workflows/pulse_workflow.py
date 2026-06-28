"""
PulseWorkflow — Daily Metrics Digest.

Orchestrates the daily pulse run:
1. Run PulseAgent activity to compute metrics and generate narrative
2. Send Slack notification with results
3. Handle errors by sending failure notification
"""
from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activities at module level for workflow context
with workflow.unsafe.imports_passed_through():
    from src.activities.run_pulse_agent import run_pulse_agent
    from src.activities.send_slack_message import send_slack_message
    from src.activities.run_guardian_watchlist import run_guardian_watchlist


@workflow.defn(name="PulseWorkflow")
class PulseWorkflow:
    """
    Daily PulseWorkflow for computing and broadcasting metrics.

    This workflow:
    1. Executes run_pulse_agent activity to compute daily metrics
    2. Sends Slack notification with the results
    3. Handles failures by sending error notification to Slack
    """

    @workflow.run
    async def run(self, input: dict) -> dict:
        """
        Execute the daily pulse workflow.

        Args:
            input: dict with keys:
                - tenant_id: str (required)
                - notify_channel: str (optional, defaults to #metrics)

        Returns:
            dict with keys:
                - ok: bool
                - tenant_id: str
                - pulse_result: dict (from PulseAgent)
                - slack_result: dict (from send_slack_message)
                - error: str (only if ok=False)
        """
        tenant_id = input.get("tenant_id", "")
        notify_channel = input.get("notify_channel", "#metrics")

        if not tenant_id:
            return {"ok": False, "error": "tenant_id is required"}

        workflow.logger.info(f"PulseWorkflow starting for tenant {tenant_id}")

        # Retry policy for activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=5),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(minutes=1),
            maximum_attempts=3,
            non_retryable_error_types=["ValueError"],
        )

        # Step 1: Run PulseAgent
        try:
            pulse_result = await workflow.execute_activity(
                run_pulse_agent,
                tenant_id,
                retry_policy=retry_policy,
                start_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(minutes=2),
            )

            if not pulse_result.get("ok"):
                error_msg = pulse_result.get("error", "Unknown error")
                workflow.logger.error(f"PulseAgent failed: {error_msg}")

                # Send failure notification
                await workflow.execute_activity(
                    send_slack_message,
                    f"❌ PulseAgent failed for {tenant_id}: {error_msg}",
                    retry_policy=retry_policy,
                    start_to_close_timeout=timedelta(minutes=2),
                )

                return {"ok": False, "tenant_id": tenant_id, "error": error_msg}

            workflow.logger.info(f"PulseAgent completed: {pulse_result.get('narrative', '')[:100]}")

            # Step 1.5: Run Guardian watchlist analysis
            try:
                guardian_result = await workflow.execute_activity(
                    run_guardian_watchlist,
                    args=[tenant_id, pulse_result],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=2),
                )

                workflow.logger.info(
                    f"Guardian watchlist: {guardian_result.get('match_count', 0)} blindspots triggered"
                )
            except Exception as e:
                workflow.logger.warning(f"Guardian watchlist failed (non-blocking): {e}")
                guardian_result = {"ok": False, "error": str(e), "blindspots_triggered": [], "match_count": 0}

        except Exception as e:
            workflow.logger.error(f"PulseAgent activity failed: {e}")

            # Send failure notification
            await workflow.execute_activity(
                send_slack_message,
                f"❌ PulseWorkflow failed for {tenant_id}: {str(e)}",
                retry_policy=retry_policy,
                start_to_close_timeout=timedelta(minutes=2),
            )

            return {"ok": False, "tenant_id": tenant_id, "error": str(e)}

        # Step 2: Send Slack notification with results
        try:
            narrative = pulse_result.get("narrative", "No narrative generated")
            slack_blocks = pulse_result.get("slack_blocks", [])

            slack_result = await workflow.execute_activity(
                send_slack_message,
                args=[narrative, slack_blocks] if slack_blocks else [narrative],
                retry_policy=retry_policy,
                start_to_close_timeout=timedelta(minutes=2),
            )

            workflow.logger.info(f"Slack notification sent: {slack_result}")

        except Exception as e:
            workflow.logger.error(f"Slack notification failed: {e}")
            # Don't fail the workflow if Slack fails — just log
            slack_result = {"ok": False, "error": str(e)}

        return {
            "ok": True,
            "tenant_id": tenant_id,
            "pulse_result": pulse_result,
            "guardian_result": guardian_result,
            "slack_result": slack_result,
        }
