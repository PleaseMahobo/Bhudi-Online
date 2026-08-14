# Phase 15 — Real-Agent E2E Gate

Phase 15 proves the Bhudi RMM agent can operate as a real process over HTTP rather than only through in-process API tests.

## Verified lifecycle

1. Start a live Bhudi runtime HTTP server.
2. Start the actual `agent/bhudi_agent.py` process.
3. Enroll the agent and persist its issued identity.
4. Send a real heartbeat with host metadata and metrics.
5. Create a technician command through the runtime API.
6. Start the real agent process again and let it poll the command.
7. Execute the command on the agent host.
8. Post the command result back to the server.
9. Verify persisted command history reports successful completion and stdout.
10. Verify an invalid agent token is rejected.

## What this proves

The test crosses process and network boundaries: the agent is not calling Python functions in the server process. It uses the same HTTP enrollment, heartbeat, command polling, execution, and result callback path used by the operational agent.

This is a CI smoke gate. The next production gate should run the same agent against a deployed/staging Bhudi backend and then verify telemetry persistence, dashboard state, alert generation, and ITSM synchronization.
