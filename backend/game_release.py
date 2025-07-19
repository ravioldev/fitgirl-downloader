#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data model for FitGirl game releases
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class ReleaseStatus(Enum):
    """Possible states for a release"""
    NEW = "New"
    DOWNLOADED = "Downloaded"
    IGNORED = "Ignored"

@dataclass
class GameRelease:
    """
    Data model for a FitGirl game release
    Contains all necessary information about a game
    """
    
    # Unique identifiers
    id: Optional[int] = None
    url: str = ""
    title: str = ""
    
    # Basic information
    description: str = ""
    short_description: str = ""
    publish_date: Optional[datetime] = None  # Torrent publication date
    game_release_date: Optional[datetime] = None  # Original game release date
    
    # Links and downloads
    magnet_link: str = ""
    size: str = ""  # Torrent size (e.g: "8.0 GB")
    
    # Additional game data
    additional_data: Dict[str, Any] = field(default_factory=dict)  # Game details
    
    # Images
    cover_image_url: str = ""
    screenshot_urls: List[str] = field(default_factory=list)
    
    # Status and metadata
    status: ReleaseStatus = ReleaseStatus.NEW
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Computed properties for UI
    @property
    def status_text(self) -> str:
        """Status text for UI display"""
        return self.status.value
    
    @property
    def status_color(self) -> str:
        """Hexadecimal color according to status"""
        color_map = {
            ReleaseStatus.NEW: "#FFA500",      # Orange
            ReleaseStatus.DOWNLOADED: "#32CD32", # Green
            ReleaseStatus.IGNORED: "#FF6B6B"    # Red
        }
        return color_map.get(self.status, "#808080")  # Gray by default
    
    @property
    def has_download_links(self) -> bool:
        """Verifies if it has download links"""
        return bool(self.magnet_link)
    
    @property
    def image_count(self) -> int:
        """Total number of images"""
        count = 0
        if self.cover_image_url:
            count += 1
        if self.screenshot_urls:
            count += len(self.screenshot_urls)
        return count
    
    @property
    def formatted_date(self) -> str:
        """Formatted date for display (torrent publication date)"""
        if self.publish_date:
            return self.publish_date.strftime("%d/%m/%Y")
        return "No date"
    
    @property
    def formatted_game_release_date(self) -> str:
        """Formatted game release date"""
        if self.game_release_date:
            return self.game_release_date.strftime("%d/%m/%Y")
        return "No date"
    

    
    def to_dict(self) -> Dict[str, Any]:
        """Converts the object to dictionary for serialization"""
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'description': self.description,
            'short_description': self.short_description,
            'publish_date': self.publish_date.isoformat() if self.publish_date else None,
            'game_release_date': self.game_release_date.isoformat() if self.game_release_date else None,
            'magnet_link': self.magnet_link,
            'size': self.size,
            'additional_data': self.additional_data,
            'cover_image_url': self.cover_image_url,
            'screenshot_urls': self.screenshot_urls,
            'status': self.status.name,
            'status_text': self.status_text,
            'status_color': self.status_color,
            'has_download_links': self.has_download_links,
            'image_count': self.image_count,
            'formatted_date': self.formatted_date,
            'formatted_game_release_date': self.formatted_game_release_date,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameRelease':
        """Creates an object from a dictionary"""
        # Convert dates
        publish_date = None
        if data.get('publish_date'):
            publish_date = datetime.fromisoformat(data['publish_date'])
        
        game_release_date = None
        if data.get('game_release_date'):
            game_release_date = datetime.fromisoformat(data['game_release_date'])
        
        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
            
        updated_at = None
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'])
        
        # Convert status
        status = ReleaseStatus.NEW
        if data.get('status'):
            try:
                status = ReleaseStatus[data['status']]
            except KeyError:
                status = ReleaseStatus.NEW
        
        return cls(
            id=data.get('id'),
            url=data.get('url', ''),
            title=data.get('title', ''),
            description=data.get('description', ''),
            short_description=data.get('short_description', ''),
            publish_date=publish_date,
            game_release_date=game_release_date,
            magnet_link=data.get('magnet_link', ''),
            size=data.get('size', ''),
            additional_data=data.get('additional_data', {}),
            cover_image_url=data.get('cover_image_url', ''),
            screenshot_urls=data.get('screenshot_urls', []),
            status=status,
            created_at=created_at,
            updated_at=updated_at
        )
    
    def __str__(self) -> str:
        """String representation of the object"""
        return f"GameRelease(id={self.id}, title='{self.title}', status={self.status.value})"
    
    def __repr__(self) -> str:
        """Detailed representation of the object"""
        return (f"GameRelease(id={self.id}, title='{self.title}', "
                f"status={self.status.value}, date={self.formatted_date})")

@dataclass
class SearchFilter:
    """
    Filters for release search
    """
    text_query: str = ""
    status_filter: Optional[ReleaseStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    has_downloads_only: bool = False
    
    def matches(self, release: GameRelease) -> bool:
        """
        Verifies if a release matches the filters
        
        Args:
            release: Release to verify
            
        Returns:
            bool: True if it matches all filters
        """
        # Text filter
        if self.text_query:
            query_lower = self.text_query.lower()
            if not (query_lower in release.title.lower() or 
                   query_lower in release.description.lower()):
                return False
        
        # Status filter
        if self.status_filter and release.status != self.status_filter:
            return False
        
        # Date from filter
        if self.date_from and release.publish_date:
            if release.publish_date < self.date_from:
                return False
        
        # Date to filter
        if self.date_to and release.publish_date:
            if release.publish_date > self.date_to:
                return False
        
        # Downloads only filter
        if self.has_downloads_only and not release.has_download_links:
            return False
        
        return True 