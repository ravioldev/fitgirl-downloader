#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend module for FitGirl Updater
Contains all the core functionality for the application
"""

# Import main classes for easy access
from .settings_manager import SettingsManager
from .json_database_manager import JsonDatabaseManager
from .game_release import GameRelease, ReleaseStatus
from .x1337_scraper import X1337Scraper

__all__ = [
    'SettingsManager',
    'JsonDatabaseManager', 
    'GameRelease',
    'ReleaseStatus',
    'X1337Scraper'
] 