#!/bin/bash

# Start the FastAPI application with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 