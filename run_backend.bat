@echo off
set PYTHONPATH=%cd%
uvicorn backend.main:app --reload