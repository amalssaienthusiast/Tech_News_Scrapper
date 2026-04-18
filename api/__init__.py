# Tech News Scraper - API Module

"""
FastAPI integration layer for C++ Qt GUI communication.

This module exposes the Python backend via REST endpoints
and ZeroMQ for real-time event streaming.
"""

from .main import app, get_app

__all__ = ['app', 'get_app']
