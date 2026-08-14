# Phase 15 — Agent E2E Operational Pipeline

## Objective

Prove and harden the operational path from agent enrollment through heartbeat, telemetry, command dispatch, command acknowledgement/result, retry handling, and authenticated agent streaming.

## Current increment

- Require the enrolled agent token for command polling.
- Require the enrolled agent token for command acknowledgement.
- Require the enrolled agent token for command results.
- Require the enrolled agent token for the agent WebSocket stream.
- Add integration coverage for enrollment → heartbeat → command → result.
- Preserve MFA protection for technician-initiated command creation.
- Verify platform-specific command translation remains part of the execution profile.

## Production gate

CI must pass the complete backend test suite before merge. The next increment will validate the real installed agent against a deployed Bhudi backend, then connect telemetry/metrics and command results into monitoring and ticketing.
