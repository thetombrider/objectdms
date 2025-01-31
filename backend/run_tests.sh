#!/bin/bash

# Run pytest with coverage
pytest tests/ \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html \
    -v \
    --asyncio-mode=auto 