# agent-factory-sdk

Contract, runtime loader, and test harness for standardized LangGraph sub-agent packages.

- `contract.py` — `AgentManifest` + `SubAgent` protocol (Phase 1)
- `compat.py` — semver compatibility gate between SDK and agents
- `llm.py` — env-driven ChatAnthropic factory (LM Studio compatible)
- `loader.py` — entry-point (mode A) and drop-in file (mode B) loading with failure isolation (Phase 3)
- `testing.py` — `assert_agent_valid()` + `ScriptedChatModel` for LLM-free agent tests

See the repository root README for the full pattern.
