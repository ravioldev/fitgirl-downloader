#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration manager for FitGirl Updater
Handles loading, saving, and validating configurations
"""

import os
import json
import yaml
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging

@dataclass
class AppSettings:
    """
    Web application configuration
    """
    
    # Scraping configuration
    max_concurrent_requests: int = 5
    timeout: int = 30  # timeout in seconds
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Database configuration
    database_path: str = "fitgirl_releases.json"
    
    # Updates configuration
    last_update_check: Optional[datetime] = None
    
    # Release synchronization configuration
    last_sync_check: Optional[datetime] = None
    
    # Logging configuration
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_to_file: bool = True
    max_log_files: int = 30
    
    # Web server configuration
    web_port: int = 2121
    web_host: str = "0.0.0.0"
    debug_mode: bool = True
    
    # Application information
    version: str = "0.1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        data = asdict(self)
        # Convert datetime to string
        if self.last_update_check:
            data['last_update_check'] = self.last_update_check.isoformat()
        if self.last_sync_check:
            data['last_sync_check'] = self.last_sync_check.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppSettings':
        """Create configuration from dictionary"""
        # Convert string to datetime
        if data.get('last_update_check'):
            try:
                data['last_update_check'] = datetime.fromisoformat(data['last_update_check'])
            except (ValueError, TypeError):
                data['last_update_check'] = None
                
        if data.get('last_sync_check'):
            try:
                data['last_sync_check'] = datetime.fromisoformat(data['last_sync_check'])
            except (ValueError, TypeError):
                data['last_sync_check'] = None
        
        # Create instance with default values for missing fields
        settings = cls()
        for key, value in data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        return settings

class SettingsManager:
    """
    Application configuration manager
    """
    
    def __init__(self, config_file: str = "config.yaml"):
        """
        Initialize the configuration manager
        
        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.settings = AppSettings()
        self.logger = logging.getLogger(__name__)
        
        # Create configuration directory if it doesn't exist
        config_dir = os.path.dirname(config_file) if os.path.dirname(config_file) else "."
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
    
    def load_settings(self) -> bool:
        """
        Load configuration from file
        
        Returns:
            bool: True if loaded successfully
        """
        try:
            if not os.path.exists(self.config_file):
                self.logger.info(f"📄 Configuration file not found: {self.config_file}")
                self.logger.info("🔧 Creating default configuration...")
                return self.save_settings()
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            self.settings = AppSettings.from_dict(data)
            self.logger.info(f"✅ Configuration loaded from: {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error loading configuration: {e}")
            self.logger.info("🔧 Using default configuration")
            return False
    
    def save_settings(self) -> bool:
        """
        Save current configuration to file
        
        Returns:
            bool: True if saved successfully
        """
        try:
            data = self.settings.to_dict()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)
                else:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"✅ Configuration saved to: {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error saving configuration: {e}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value
        
        Args:
            key: Configuration key
            default: Default value if it doesn't exist
            
        Returns:
            Any: Configuration value
        """
        return getattr(self.settings, key, default)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """
        Set a configuration value
        
        Args:
            key: Configuration key
            value: New value
            
        Returns:
            bool: True if set successfully
        """
        try:
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
                return True
            else:
                self.logger.warning(f"⚠️ Unknown configuration: {key}")
                return False
        except Exception as e:
            self.logger.error(f"❌ Error setting configuration {key}: {e}")
            return False
    
    def update_last_check(self):
        """Update the last verification date"""
        self.settings.last_update_check = datetime.now()
    
    def update_last_sync(self):
        """Updates the last release synchronization date"""
        self.settings.last_sync_check = datetime.now()
        self.logger.info(f"🔄 Last synchronization updated: {self.settings.last_sync_check}")
    
    def get_last_sync(self) -> Optional[datetime]:
        """Gets the last synchronization date"""
        return self.settings.last_sync_check
    

    
    def is_first_sync(self) -> bool:
        """
        Determines if this is the first synchronization
        
        Returns:
            bool: True if it's the first time
        """
        return self.settings.last_sync_check is None
    

    
    def get_database_path(self) -> str:
        """
        Get the full database path
        
        Returns:
            str: Database path
        """
        if os.path.isabs(self.settings.database_path):
            return self.settings.database_path
        return os.path.abspath(self.settings.database_path)
    
    def get_log_level(self) -> int:
        """
        Get logging level as constant
        
        Returns:
            int: Logging level
        """
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return level_map.get(self.settings.log_level.upper(), logging.INFO)
    
    def validate_settings(self) -> bool:
        """
        Validate current configuration
        
        Returns:
            bool: True if configuration is valid
        """
        try:
            # Validate URLs
            if not self.settings.fitgirl_base_url.startswith(('http://', 'https://')):
                self.logger.warning("⚠️ Invalid FitGirl base URL")
                return False
            
            if not self.settings.fitgirl_rss_url.startswith(('http://', 'https://')):
                self.logger.warning("⚠️ Invalid FitGirl RSS URL")
                return False
            
            # Validate numeric values
            if self.settings.max_concurrent_requests <= 0:
                self.logger.warning("⚠️ Concurrent requests number must be greater than 0")
                return False
            

            
            if self.settings.timeout <= 0:
                self.logger.warning("⚠️ Timeout must be greater than 0")
                return False
            
            # Validate theme
            if self.settings.theme not in ['dark', 'light', 'auto']:
                self.logger.warning("⚠️ Invalid theme, using 'dark'")
                self.settings.theme = 'dark'
            
            self.logger.info("✅ Configuration validated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error validating configuration: {e}")
            return False
    
    def reset_to_defaults(self):
        """Reset configuration to default values"""
        self.settings = AppSettings()
        self.logger.info("🔄 Configuration reset to default values")
    
    def export_settings(self, export_path: str) -> bool:
        """
        Export configuration to a file
        
        Args:
            export_path: Path where to export
            
        Returns:
            bool: True if exported successfully
        """
        try:
            data = self.settings.to_dict()
            
            with open(export_path, 'w', encoding='utf-8') as f:
                if export_path.endswith('.yaml') or export_path.endswith('.yml'):
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)
                else:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"✅ Configuration exported to: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error exporting configuration: {e}")
            return False
    
    def import_settings(self, import_path: str) -> bool:
        """
        Import configuration from a file
        
        Args:
            import_path: Path of the file to import
            
        Returns:
            bool: True if imported successfully
        """
        try:
            if not os.path.exists(import_path):
                self.logger.error(f"❌ File not found: {import_path}")
                return False
            
            with open(import_path, 'r', encoding='utf-8') as f:
                if import_path.endswith('.yaml') or import_path.endswith('.yml'):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            self.settings = AppSettings.from_dict(data)
            
            if self.validate_settings():
                self.logger.info(f"✅ Configuration imported from: {import_path}")
                return True
            else:
                self.logger.error("❌ Invalid imported configuration")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error importing configuration: {e}")
            return False 