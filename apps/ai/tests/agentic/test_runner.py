"""
Agentic Test Runner with Error Attribution

This is the CI entry point for Layer 3 tests.
Error attribution comments explain exactly which layer failed.
"""
import subprocess
import sys


ERROR_ATTRIBUTION = """
╔══════════════════════════════════════════════════════════════════════╗
║                    AGENTIC TEST ERROR ATTRIBUTION                    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  If test_llm_api_health FAILS                                        ║
║    → LLM API is down. Check OpenAI status / API key / quota.        ║
║    → NOT your code. NOT the parser.                                  ║
║                                                                        ║
║  If test_llm_api_health PASSES + test_finance_parse FAILS           ║
║    → Parser is wrong. Check Pydantic schema / response format.     ║
║    → NOT the LLM API.                                               ║
║                                                                        ║
║  If test_finance_parse PASSES + test_guardian_contract FAILS        ║
║    → Prompt is wrong. Check prompt engineering / max_tokens.      ║
║    → NOT the LLM API. NOT the parser.                               ║
║                                                                        ║
║  If test_* PASSES + test_langfuse_traces FAILS                     ║
║    → Observability broken. Check Langfuse credentials / keys.       ║
║    → NOT the agent. NOT the LLM.                                     ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════╝
"""


def main():
    """Run agentic tests with clear error attribution."""
    print(ERROR_ATTRIBUTION)

    # Run pytest with agentic marker
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/agentic/",
        "-v",
        "--tb=short",
        "-m", "agentic",
    ]

    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()