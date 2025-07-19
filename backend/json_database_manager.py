#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON database manager for FitGirl Downloader
Handles all database operations using JSON files
"""

import json
import os
import shutil
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import logging
from contextlib import contextmanager

from .game_release import GameRelease, ReleaseStatus

class JsonDatabaseManager:
    """
    JSON database manager for FitGirl Downloader
    """
    
    def __init__(self, db_path: str = "fitgirl_releases.json"):
        """
        Initialize the JSON database manager
        
        Args:
            db_path: Path to the JSON database file
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Default database structure
        self.db_structure = {
            "metadata": {
                "version": 1,
                "created_at": None,
                "last_updated": None,
                "total_releases": 0
            },
            "releases": [],
            "operation_logs": []
        }
        
        # Automatically load the database
        self._load_database()
    
    def initialize(self) -> bool:
        """
        Initialize the database
        
        Returns:
            bool: True if initialized successfully
        """
        try:
            # Load existing database or create new
            self._load_database()
            
            # Run migration to ensure state consistency
            self.migrate_database()
            
            self.logger.info("✅ Database initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing database: {e}")
            return False
    
    def _load_database(self):
        """
        Load the database from the JSON file
        """
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Migrate structure if necessary
            if "metadata" not in data:
                data["metadata"] = self.db_structure["metadata"]
                data["metadata"]["created_at"] = datetime.now().isoformat()
            
            if "operation_logs" not in data:
                data["operation_logs"] = []
            
            # Update metadata
            data["metadata"]["last_updated"] = datetime.now().isoformat()
            data["metadata"]["total_releases"] = len(data.get("releases", []))
            
            self.db_structure = data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ JSON decode error: {e}")
            # Create backup of the corrupted file
            backup_path = f"{self.db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.db_path, backup_path)
            self.logger.info(f"📦 Backup created: {backup_path}")
            
            # Recreate database
            self.db_structure["metadata"]["created_at"] = datetime.now().isoformat()
            self.db_structure["metadata"]["last_updated"] = datetime.now().isoformat()
            self._save_database()
            
        except FileNotFoundError:
            # File does not exist, create new
            self.db_structure["metadata"]["created_at"] = datetime.now().isoformat()
            self.db_structure["metadata"]["last_updated"] = datetime.now().isoformat()
            self._save_database()
    
    def _save_database(self):
        """
        Save the database to the JSON file
        """
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.db_structure, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"💾 Database saved: {self.db_path}")
        except Exception as e:
            self.logger.error(f"❌ Error saving database: {e}")
    
    def _get_next_id(self) -> int:
        """
        Generate the next unique ID for a release
        
        Returns:
            int: Next available ID
        """
        if not self.db_structure["releases"]:
            return 1
        
        max_id = max([r.get("id", 0) for r in self.db_structure["releases"]], default=0)
        return max_id + 1
    
    def insert_release(self, release: GameRelease) -> Optional[int]:
        """
        Insert a new release
        
        Args:
            release: Release to insert
            
        Returns:
            Optional[int]: ID of the inserted release or None if failed
        """
        try:
            # Check if already exists (URL + magnet_link)
            magnet_key = release.magnet_link if release.magnet_link else "no_magnet"
            
            for existing_release in self.db_structure["releases"]:
                existing_magnet = existing_release.get("magnet_link", "no_magnet")
                if existing_magnet is None:
                    existing_magnet = "no_magnet"
                
                # Check both URL and magnet_link to avoid duplicates
                if (existing_release["url"] == release.url and 
                    existing_magnet == magnet_key):
                    self.logger.warning(f"⚠️ Release already exists (URL + magnet): {release.title}")
                    return None
            
            # Generate new ID
            new_id = self._get_next_id()
            release.id = new_id
            
            # Convert to dictionary
            release_dict = self._release_to_dict(release)
            release_dict["id"] = new_id
            
            # Detailed image logging
            self.logger.info(f"💾 Inserting release with images:")
            self.logger.info(f"   - Cover: {release.cover_image_url}")
            self.logger.info(f"   - Screenshots: {len(release.screenshot_urls)} images")
            if release.screenshot_urls:
                for i, screenshot in enumerate(release.screenshot_urls[:3]):  # Only show first 3
                    self.logger.info(f"     {i+1}. {screenshot}")
            
            # Add to list
            self.db_structure["releases"].append(release_dict)
            
            # Save to file
            self._save_database()
            
            self.logger.info(f"✅ Release inserted: {new_id} - {release.title}")
            return new_id
            
        except Exception as e:
            self.logger.error(f"❌ Error inserting release: {e}")
            return None
    
    def update_release(self, release: GameRelease) -> bool:
        """
        Update an existing release
        
        Args:
            release: Release to update
            
        Returns:
            bool: True if updated successfully
        """
        try:
            # Find existing release
            for i, existing_release in enumerate(self.db_structure["releases"]):
                if existing_release["url"] == release.url:
                    # Update data
                    release_dict = self._release_to_dict(release)
                    release_dict["id"] = existing_release["id"]
                    release_dict["created_at"] = existing_release["created_at"]
                    release_dict["updated_at"] = datetime.now().isoformat()
                    
                    self.db_structure["releases"][i] = release_dict
                    self._save_database()
                    
                    self.logger.info(f"✅ Release updated: {existing_release['id']} - {release.title}")
                    return True
            
            self.logger.warning(f"⚠️ Release not found for update: {release.url}")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error updating release: {e}")
            return False

    def update_release_by_id(self, release_id: int, release: GameRelease) -> bool:
        """
        Update an existing release by ID
        
        Args:
            release_id: ID of the release to update
            release: Release data to update with
            
        Returns:
            bool: True if updated successfully
        """
        try:
            # Find existing release by ID
            for i, existing_release in enumerate(self.db_structure["releases"]):
                if existing_release["id"] == release_id:
                    self.logger.info(f"🔍 Found existing release: {existing_release.get('title', 'No title')}")
                    self.logger.info(f"🔍 Existing release keys: {list(existing_release.keys())}")
                    
                    # Update data
                    release_dict = self._release_to_dict(release)
                    release_dict["id"] = release_id  # Preserve the original ID
                    
                    # Preserve created_at if it exists, otherwise use current time
                    if "created_at" in existing_release and existing_release["created_at"]:
                        release_dict["created_at"] = existing_release["created_at"]
                        self.logger.info(f"🔍 Preserved created_at: {existing_release['created_at']}")
                    else:
                        release_dict["created_at"] = datetime.now().isoformat()
                        self.logger.info(f"🔍 Set new created_at: {release_dict['created_at']}")
                    
                    release_dict["updated_at"] = datetime.now().isoformat()
                    
                    self.db_structure["releases"][i] = release_dict
                    self._save_database()
                    
                    self.logger.info(f"✅ Release updated by ID: {release_id} - {release.title}")
                    return True
            
            self.logger.warning(f"⚠️ Release not found for update by ID: {release_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error updating release by ID: {e}")
            import traceback
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return False
    
    def upsert_release(self, release: GameRelease) -> Optional[int]:
        """
        Insert or update a release
        
        Args:
            release: Release to insert/update
            
        Returns:
            Optional[int]: ID of the release or None if failed
        """
        try:
            # Check if exists
            existing_release = self.get_release_by_url(release.url)
            
            if existing_release:
                # Update
                success = self.update_release(release)
                return existing_release.id if success else None
            else:
                # Insert
                return self.insert_release(release)
                
        except Exception as e:
            self.logger.error(f"❌ Error in upsert release: {e}")
            return None
    
    def get_release_by_id(self, release_id: int) -> Optional[GameRelease]:
        """
        Gets a release by ID
        
        Args:
            release_id: Release ID
            
        Returns:
            Optional[GameRelease]: Found release or None
        """
        try:
            for release_dict in self.db_structure["releases"]:
                if release_dict["id"] == release_id:
                    return self._dict_to_release(release_dict)
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error getting release by ID: {e}")
            return None
    
    def get_release_by_url(self, url: str) -> Optional[GameRelease]:
        """
        Gets a release by URL
        
        Args:
            url: Release URL
            
        Returns:
            Optional[GameRelease]: Found release or None
        """
        try:
            for release_dict in self.db_structure["releases"]:
                if release_dict["url"] == url:
                    return self._dict_to_release(release_dict)
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error getting release by URL: {e}")
            return None
    
    def get_all_releases(self, limit: Optional[int] = None, 
                        offset: int = 0, sort_by: str = "date_desc") -> List[GameRelease]:
        """
        Gets all releases with pagination and sorting
        
        Args:
            limit: Limit of releases to get
            offset: Offset for pagination
            sort_by: Sorting type ('date_desc', 'date_asc', 'title_asc', 'title_desc')
            
        Returns:
            List[GameRelease]: List of releases
        """
        try:
            releases = []
            
            # Define sorting logic based on sort_by parameter
            if sort_by == "date_desc":
                # Sort by publish date (most recent first)
                sorted_releases = sorted(
                    self.db_structure["releases"],
                    key=lambda x: x.get("publish_date", ""),
                    reverse=True
                )
            elif sort_by == "date_asc":
                # Sort by publish date (oldest first)
                sorted_releases = sorted(
                    self.db_structure["releases"],
                    key=lambda x: x.get("publish_date", ""),
                    reverse=False
                )
            elif sort_by == "title_asc":
                # Sort by title (A-Z)
                sorted_releases = sorted(
                    self.db_structure["releases"],
                    key=lambda x: x.get("title", "").lower(),
                    reverse=False
                )
            elif sort_by == "title_desc":
                # Sort by title (Z-A)
                sorted_releases = sorted(
                    self.db_structure["releases"],
                    key=lambda x: x.get("title", "").lower(),
                    reverse=True
                )
            else:
                # Default to date descending if invalid sort_by
                sorted_releases = sorted(
                    self.db_structure["releases"],
                    key=lambda x: x.get("publish_date", ""),
                    reverse=True
                )
            
            # Apply pagination
            start = offset
            end = start + limit if limit else len(sorted_releases)
            paginated_releases = sorted_releases[start:end]
            
            # Convert to GameRelease objects
            for release_dict in paginated_releases:
                release = self._dict_to_release(release_dict)
                if release:
                    releases.append(release)
            
            return releases
            
        except Exception as e:
            self.logger.error(f"❌ Error getting releases: {e}")
            return []
    
    def search_releases(self, query: str, status_filter: Optional[ReleaseStatus] = None,
                       limit: Optional[int] = None) -> List[GameRelease]:
        """
        Searches releases by title or description
        
        Args:
            query: Search term
            status_filter: Status filter
            limit: Limit of results
            
        Returns:
            List[GameRelease]: List of matching releases
        """
        try:
            results = []
            query_lower = query.lower()
            
            for release_dict in self.db_structure["releases"]:
                # Search in title and description
                title_match = query_lower in release_dict.get("title", "").lower()
                desc_match = query_lower in release_dict.get("description", "").lower()
                
                if title_match or desc_match:
                    # Apply status filter if specified
                    if status_filter:
                        release_status = ReleaseStatus[release_dict.get("status", "NEW")]
                        if release_status != status_filter:
                            continue
                    
                    release = self._dict_to_release(release_dict)
                    if release:
                        results.append(release)
                        
                        # Apply limit if specified
                        if limit and len(results) >= limit:
                            break
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Error searching releases: {e}")
            return []
    
    def update_release_status(self, release_id: int, status: ReleaseStatus) -> bool:
        """
        Updates the status of a release
        
        Args:
            release_id: ID of the release
            status: New status
            
        Returns:
            bool: True if updated successfully
        """
        try:
            for release_dict in self.db_structure["releases"]:
                if release_dict["id"] == release_id:
                    release_dict["status"] = status.name
                    release_dict["updated_at"] = datetime.now().isoformat()
                    self._save_database()
                    
                    self.logger.info(f"✅ Status updated: {release_id} -> {status.name}")
                    return True
            
            self.logger.warning(f"⚠️ Release not found for status update: {release_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error updating status: {e}")
            return False
    
    def delete_release(self, release_id: int) -> bool:
        """
        Deletes a release
        
        Args:
            release_id: ID of the release to delete
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            for i, release_dict in enumerate(self.db_structure["releases"]):
                if release_dict["id"] == release_id:
                    deleted_release = self.db_structure["releases"].pop(i)
                    self._save_database()
                    
                    self.logger.info(f"✅ Release deleted: {release_id} - {deleted_release.get('title', '')}")
                    return True
            
            self.logger.warning(f"⚠️ Release not found for deletion: {release_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error deleting release: {e}")
            return False
    
    def clear_all_releases(self) -> bool:
        """
        Deletes all releases
        
        Returns:
            bool: True if deleted successfully
        """
        try:
            count = len(self.db_structure["releases"])
            self.db_structure["releases"] = []
            self._save_database()
            
            self.logger.info(f"✅ All releases deleted: {count} releases")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error deleting all releases: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Gets database statistics
        
        Returns:
            Dict[str, Any]: Statistics
        """
        try:
            releases = self.db_structure["releases"]
            
            # Count by status
            status_counts = {}
            for status in ReleaseStatus:
                status_counts[status.name] = len([
                    r for r in releases 
                    if r.get("status", "NEW") == status.name
                ])
            
            # Get dates
            dates = [r.get("publish_date") for r in releases if r.get("publish_date")]
            latest_date = max(dates) if dates else None
            earliest_date = min(dates) if dates else None
            
            stats = {
                "total_releases": len(releases),
                "new_releases": status_counts.get("NEW", 0),
                "downloaded_releases": status_counts.get("DOWNLOADED", 0),
                "ignored_releases": status_counts.get("IGNORED", 0),
                "latest_release_date": latest_date,
                "earliest_release_date": earliest_date,
                "database_size_mb": os.path.getsize(self.db_path) / (1024 * 1024) if os.path.exists(self.db_path) else 0
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"❌ Error getting statistics: {e}")
            return {
                "total_releases": 0,
                "new_releases": 0,
                "downloaded_releases": 0,
                "ignored_releases": 0,
                "latest_release_date": None,
                "earliest_release_date": None,
                "database_size_mb": 0
            }
    
    def backup_database(self, backup_path: str) -> bool:
        """
        Creates a backup of the database
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            bool: True if created successfully
        """
        try:
            shutil.copy2(self.db_path, backup_path)
            self.logger.info(f"📦 Backup created: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error creating backup: {e}")
            return False
    
    def migrate_database(self) -> bool:
        """
        Migrates the database to ensure all releases have an explicit status
        
        Returns:
            bool: True if executed successfully
        """
        try:
            migrated_count = 0
            
            for release_dict in self.db_structure["releases"]:
                # If the release does not have a status defined, assign NEW
                if "status" not in release_dict or release_dict["status"] is None:
                    release_dict["status"] = "NEW"
                    migrated_count += 1
                    self.logger.info(f"📦 Migrated status for: {release_dict.get('title', 'No title')}")
            
            if migrated_count > 0:
                self._save_database()
                self.logger.info(f"✅ Migration completed: {migrated_count} releases updated")
            else:
                self.logger.info("ℹ️ No migration required - all releases have status")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error in migration: {e}")
            return False

    def _release_to_dict(self, release: GameRelease) -> Dict[str, Any]:
        """
        Converts a GameRelease object to a dictionary
        
        Args:
            release: GameRelease object
            
        Returns:
            Dict[str, Any]: Dictionary with release data
        """
        return {
            "url": release.url,
            "title": release.title,
            "description": release.description,
            "short_description": release.short_description,
            "publish_date": release.publish_date.isoformat() if release.publish_date else None,
            "game_release_date": release.game_release_date.isoformat() if release.game_release_date else None,
            "magnet_link": release.magnet_link,
            "size": release.size,
            "additional_data": release.additional_data,
            "cover_image_url": release.cover_image_url,
            "screenshot_urls": release.screenshot_urls,
            "status": release.status.name
        }
    
    def _dict_to_release(self, release_dict: Dict[str, Any]) -> Optional[GameRelease]:
        """
        Converts a dictionary to a GameRelease object
        
        Args:
            release_dict: Dictionary with release data
            
        Returns:
            Optional[GameRelease]: GameRelease object or None if failed
        """
        try:
            # Parse dates
            publish_date = None
            if release_dict.get("publish_date"):
                try:
                    publish_date = datetime.fromisoformat(release_dict["publish_date"])
                except:
                    pass
            
            game_release_date = None
            if release_dict.get("game_release_date"):
                try:
                    game_release_date = datetime.fromisoformat(release_dict["game_release_date"])
                except:
                    pass
            
            # Create GameRelease object
            release = GameRelease(
                url=release_dict["url"],
                title=release_dict["title"],
                description=release_dict.get("description", ""),
                short_description=release_dict.get("short_description", ""),
                publish_date=publish_date,
                game_release_date=game_release_date,
                magnet_link=release_dict.get("magnet_link", ""),
                size=release_dict.get("size", ""),
                additional_data=release_dict.get("additional_data", {}),
                cover_image_url=release_dict.get("cover_image_url", ""),
                screenshot_urls=release_dict.get("screenshot_urls", []),
                status=ReleaseStatus[release_dict.get("status", "NEW")]
            )
            
            # Assign ID if exists
            if "id" in release_dict:
                release.id = release_dict["id"]
            
            return release
            
        except Exception as e:
            self.logger.error(f"❌ Error converting dictionary to release: {e}")
            return None
    
    def close(self):
        """
        Closes the database connection
        """
        try:
            self._save_database()
            self.logger.info("🔒 JSON database closed")
        except Exception as e:
            self.logger.error(f"❌ Error closing database: {e}") 