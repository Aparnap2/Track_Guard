"""Temporal Workflows for TrackGuard AI Agents."""

from src.workflows.pulse_workflow import PulseWorkflow
from src.workflows.investor_workflow import InvestorWorkflow
from src.workflows.qa_workflow import QAWorkflow
from src.workflows.self_analysis_workflow import SelfAnalysisWorkflow
from src.workflows.eval_loop_workflow import EvalLoopWorkflow
from src.workflows.compression_workflow import CompressionWorkflow
from src.workflows.weight_decay_workflow import WeightDecayWorkflow
from src.workflows.finance_workflow import FinanceWorkflow
from src.workflows.data_workflow import DataWorkflow
from src.workflows.ops_workflow import OpsWorkflow

__all__ = [
    "PulseWorkflow",
    "InvestorWorkflow",
    "QAWorkflow",
    "SelfAnalysisWorkflow",
    "EvalLoopWorkflow",
    "CompressionWorkflow",
    "WeightDecayWorkflow",
    "FinanceWorkflow",
    "DataWorkflow",
    "OpsWorkflow",
]
