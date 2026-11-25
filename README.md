# Bhudi Online

[![CI](https://github.com/PleaseMahobo/Bhudi-Online/actions/workflows/ci.yml/badge.svg)](https://github.com/PleaseMahobo/Bhudi-Online/actions/workflows/ci.yml)

## Security-focused full-stack platform

Bhudi Online is a production-oriented web platform built as a full-stack system with a Next.js frontend, FastAPI backend, PostgreSQL/Supabase data services, authentication and identity controls, automated testing, and CI/CD.

This repository is presented as a technical and cybersecurity case study: the emphasis is not only on application features, but on how security, identity, testing, observability, and deployment validation are engineered into the system.

> Production credentials, secrets, customer data, private infrastructure details, and sensitive operational information are intentionally excluded from this repository.

## What this project demonstrates

- Application and API security
- Authentication, authorization and MFA workflows
- Identity and access management
- PostgreSQL/Supabase integration
- Secure backend services with FastAPI
- TypeScript/Next.js application engineering
- Automated backend and frontend validation
- GitHub Actions CI/CD
- Container image build and publication
- Production-oriented troubleshooting and regression testing

## Architecture

Browser / Client → Next.js / React frontend → HTTPS / API boundary → FastAPI backend → PostgreSQL / Supabase

The backend also integrates with observability tooling and remote-management components. See docs/architecture.md for the detailed security boundaries.

## Security engineering

Security work follows a repeatable lifecycle:

Threat or failure → reproduction → root-cause analysis → remediation → automated regression test → CI validation → production-safe verification.

See docs/security.md.

## Technology

Frontend: Next.js 15, React 19, TypeScript, Tailwind CSS, Prisma, Supabase client, Zod.

Backend: Python 3.12, FastAPI, Pydantic, SQLAlchemy, PostgreSQL/psycopg, Supabase, JWT/JOSE, Argon2/bcrypt, PyOTP.

Engineering: GitHub Actions, Docker, pytest, API testing, OpenTelemetry and Prometheus instrumentation.

## CI/CD

The GitHub Actions pipeline separates validation into focused jobs for backend tests, remote-input security regression, frontend type checking/builds, agent validation, and Docker image publication.

## Testing philosophy

A passing build is not treated as proof of security. Security-sensitive changes should cover authorized behaviour, denial behaviour, regression coverage, integration behaviour, CI execution, and safe production verification where appropriate.

## Portfolio evidence

| Area | Evidence |
|---|---|
| Application Security | API, authentication and authorization controls |
| IAM | Identity, authentication and MFA workflows |
| Backend Engineering | FastAPI + PostgreSQL/Supabase |
| Frontend Engineering | Next.js + TypeScript |
| DevSecOps | GitHub Actions validation pipeline |
| Testing | pytest, typecheck/build, regression tests |
| Cloud/Deployment | Containerized backend and deployment validation |
| Security Operations | Root-cause investigation and remediation documentation |

## Repository structure

backend/ — FastAPI backend

frontend/ — Next.js application

agent/ — Agent and remote-management components

.github/workflows/ — CI/CD workflows

docs/ — Security and architecture documentation

## Author

Trust Kashumba — Cybersecurity | Application Security | Cloud Security | DevSecOps

GitHub: https://github.com/PleaseMahobo
