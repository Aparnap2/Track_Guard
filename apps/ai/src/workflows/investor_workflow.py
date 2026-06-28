"""
InvestorWorkflow — Weekly Investor Update.

Orchestrates the weekly investor update:
1. Run InvestorAgent activity to generate investor-friendly metrics
2. Send Slack notification with results
3. Handle errors by sending failure notification
"""
from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activities at module level for workflow context
with workflow.unsafe.imports_passed_through():
    from src.activities.run_investor_agent import run_investor_agent
    from src.activities.send_slack_message import send_slack_message
    from src.activities.check_relationship_health import check_relationship_health


@workflow.defn(name="InvestorWorkflow")
class InvestorWorkflow:
    """
    Weekly InvestorWorkflow for generating investor updates.

    This workflow:
    1. Executes run_investor_agent activity to generate investor metrics
    2. Sends Slack notification with the results
    3. Handles failures by sending error notification to Slack
    """

    @workflow.run
    async def run(self, input: dict) -> dict:
        """
        Execute the weekly investor workflow.

        Args:
            input: dict with keys:
                - tenant_id: str (required)
                - notify_channel: str (optional, defaults to #investors)

        Returns:
            dict with keys:
                - ok: bool
                - tenant_id: str
                - investor_result: dict (from InvestorAgent)
                - slack_result: dict (from send_slack_message)
                - error: str (only if ok=False)
        """
        tenant_id = input.get("tenant_id", "")
        notify_channel = input.get("notify_channel", "#investors")

        if not tenant_id:
            return {"ok": False, "error": "tenant_id is required"}

        workflow.logger.info(f"InvestorWorkflow starting for tenant {tenant_id}")

        # Retry policy for activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=5),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(minutes=1),
            maximum_attempts=3,
            non_retryable_error_types=["ValueError"],
        )

        # Step 1: Check investor relationship health
        try:
            relationship_health = await workflow.execute_activity(
                check_relationship_health,
                tenant_id,
                retry_policy=retry_policy,
                start_to_close_timeout=timedelta(minutes=2),
            )

            # If there are cold high-priority investors, add alert to workflow
            if relationship_health.get("ok") and relationship_health.get("high_priority_cold", 0) > 0:
                cold_investors = relationship_health.get("cold_investors", [])
                cold_alert = f"⚠️ {relationship_health['high_priority_cold']} high-priority investors need warmup"
                workflow.logger.warning(cold_alert)
                # Note: This could be included in the investor update message

        except Exception as e:
            workflow.logger.warning(f"Relationship health check failed: {e}")

        # Step 2: Run InvestorAgent
        try:
            investor_result = await workflow.execute_activity(
                run_investor_agent,
                tenant_id,
                retry_policy=retry_policy,
                start_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(minutes=2),
            )

            if not investor_result.get("ok"):
                error_msg = investor_result.get("error", "Unknown error")
                workflow.logger.error(f"InvestorAgent failed: {error_msg}")

                # Send failure notification
                await workflow.execute_activity(
                    send_slack_message,
                    f"❌ InvestorAgent failed for {tenant_id}: {error_msg}",
                    retry_policy=retry_policy,
                    start_to_close_timeout=timedelta(minutes=2),
                )

                return {"ok": False, "tenant_id": tenant_id, "error": error_msg}

            workflow.logger.info(f"InvestorAgent completed: {investor_result.get('narrative', '')[:100]}")

        except Exception as e:
            workflow.logger.error(f"InvestorAgent activity failed: {e}")

            # Send failure notification
            await workflow.execute_activity(
                send_slack_message,
                f"❌ InvestorWorkflow failed for {tenant_id}: {str(e)}",
                retry_policy=retry_policy,
                start_to_close_timeout=timedelta(minutes=2),
            )

            return {"ok": False, "tenant_id": tenant_id, "error": str(e)}

        # Step 2: Send Slack notification with results
        try:
            narrative = investor_result.get("narrative", "No narrative generated")
            slack_blocks = investor_result.get("slack_blocks", [])

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
            "investor_result": investor_result,
            "slack_result": slack_result,
        }
