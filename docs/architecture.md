# Cipher Frame Architecture

This document describes the initial project organization for Cipher Frame.

## Layers

- Backend API: FastAPI application startup, routing, configuration, logging, and database access helpers.
- Frontend Shell: Static HTML, CSS, and JavaScript served by the backend.
- Storage: Reserved for the SQLite database file and future encrypted artifacts.
- Services: Business logic will be expanded here when cryptography, session handling, and WebSocket flows are added.
- Models: Domain objects and future persistence models will live here.

## Planned Extensions

- WebSocket channel for real-time client communication.
- Cryptography service layer for image encryption and decryption.
- Admin dashboard for operational oversight.
- Database schema and migrations once persistence requirements are finalized.
