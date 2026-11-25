# Bhudi Online Architecture

## Overview

Bhudi Online is organized as a multi-component application with a web frontend, API backend, remote-management components, data services and automated CI/CD.

## Components

### Frontend

Next.js, React and TypeScript provide the web application, user interface, authenticated API consumption, validation and administrative workflows. Client-side controls are usability controls, not the final security boundary.

### Backend

Python and FastAPI provide API routing, authentication/session processing, authorization, business logic, validation, database access and observability. Server-side authorization is the authoritative enforcement point.

### Data layer

The application uses PostgreSQL/Supabase-related services and database tooling. Security-sensitive data access should be constrained by application-level authorization and appropriate database controls.

### Agent / remote management

Agent-related components support remote-management functionality. Because remote execution can be high impact, these paths receive additional regression testing and explicit authentication boundaries.

## Trust boundaries

1. Browser → frontend
2. Frontend → API
3. API → database
4. API → remote agent/channel
5. Developer change → CI/CD
6. CI/CD → deployment infrastructure

Each boundary should have an explicit authentication, authorization, validation or integrity control.

## CI/CD architecture

Developer → Git push/Pull Request → GitHub Actions → backend tests + security regression + frontend build + agent validation + Docker build → validated artifact.

## Design principles

- Least privilege
- Defense in depth
- Explicit trust boundaries
- Server-side authorization
- Automated regression testing
- Reproducible builds
- Minimal production changes
- Observable failures
- Safe rollback and recovery

## Portfolio interpretation

This architecture demonstrates the ability to reason across application, identity, database, CI/CD and production boundaries rather than treating cybersecurity as a standalone scanning exercise.
