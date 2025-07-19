#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1337x Scraper to get FitGirl releases
"""

import requests
import time
import re
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Callable
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from .game_release import GameRelease, ReleaseStatus
import logging
from .settings_manager import SettingsManager


class X1337Scraper:
    """
    Scraper to get FitGirl releases from 1337x
    """
    
    def __init__(self):
        """Initialize the scraper"""
        # Logger - initialize first
        self.logger = logging.getLogger(__name__)
        
        self.base_url = "https://1337x.to"
        self.fitgirl_torrents_url = "https://1337x.to/FitGirl-torrents/"
        self.fitgirl_profile_url = "https://1337x.to/user/FitGirl/"
        
        # Requests configuration
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Selenium configuration
        self.driver = None
        self._setup_selenium()
        
        # State control
        self._is_running = False
        self.progress_callback = None
        self.insert_callback = None
        self.url_check_callback = None
        
        self.logger.info("🔧 X1337Scraper initialized")
    
    def initialize(self, settings_manager: SettingsManager):
        """
        Initialize the scraper
        
        Args:
            settings_manager: Configuration manager
        """
        self.settings_manager = settings_manager
        self.logger.info("🔧 X1337Scraper initialized")
    
    def set_progress_callback(self, callback: Callable[[str, str, dict], None]):
        """
        Set the callback function for progress
        
        Args:
            callback: Function that receives (status, message, **kwargs)
        """
        self.progress_callback = callback
    
    def set_insert_callback(self, callback: Callable[[GameRelease], bool]):
        """
        Configure the callback to insert releases immediately
        
        Args:
            callback: Function that receives a GameRelease and returns bool
        """
        self.insert_callback = callback
    
    def set_url_check_callback(self, callback: Callable[[str], bool]):
        """
        Configure the callback to check if a URL already exists
        
        Args:
            callback: Function that receives a URL and returns True if it already exists
        """
        self.url_check_callback = callback
    
    def _update_progress(self, status: str, message: str, **kwargs):
        """
        Update progress using callback if available
        
        Args:
            status: Progress status
            message: Descriptive message
            **kwargs: Additional data
        """
        if self.progress_callback:
            self.progress_callback(status, message, **kwargs)
        self.logger.info(f"📊 {status}: {message}")
    
    def _setup_selenium(self):
        """Configure the Selenium driver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run without window
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            self.logger.info("🌐 Selenium Chrome driver configured")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Could not configure Selenium (will continue without dynamic images): {e}")
            self.driver = None
    
    def get_fitgirl_releases(self, max_pages: int = 100) -> List[GameRelease]:
        """
        Gets all FitGirl releases from 1337x
        
        Args:
            max_pages: Maximum number of pages to process (default 50 to get all)
            
        Returns:
            List[GameRelease]: List of releases
        """
        releases = []
        
        try:
            self._is_running = True
            self._update_progress('scraping', 'Starting FitGirl releases download...')
            
            # Get torrent list from complete pagination URL
            torrent_links = self._get_torrent_links_from_torrents_page(max_pages)
            
            if not torrent_links:
                self._update_progress('error', 'No torrent links found')
                return []
            
            self._update_progress('processing', f'Processing {len(torrent_links)} torrents...', 
                               current_release=0, total_releases=len(torrent_links))
            
            # Process each torrent to get complete details
            for i, torrent_url in enumerate(torrent_links):
                try:
                    self._update_progress('processing', f'Processing torrent {i+1} of {len(torrent_links)}...', 
                                       current_release=i+1, total_releases=len(torrent_links))
                    
                    release = self._extract_release_details(torrent_url)
                    
                    if release and release.has_download_links:
                        releases.append(release)
                        self._update_progress('processing', f'Release {len(releases)}: {release.title}',
                                           current_release=i+1, total_releases=len(torrent_links), 
                                           processed_releases=len(releases))
                    else:
                        if release:
                            self.logger.warning(f"⚠️ Release without magnet link: {release.title}")
                        else:
                            self.logger.warning(f"⚠️ Could not extract release from: {torrent_url}")
                        self._update_progress('processing', f'Skipping torrent without complete data', 
                                           current_release=i+1, total_releases=len(torrent_links))
                    
                    # Pause between requests
                    time.sleep(1)
                    
                except Exception as e:
                    self._update_progress('processing', f'Error processing torrent: {str(e)}...', 
                                       current_release=i+1, total_releases=len(torrent_links))
                    continue
            
            self._update_progress('completed', f'Processing completed: {len(releases)} releases obtained', 
                               processed_releases=len(releases))
            
        except Exception as e:
            self._update_progress('error', f'Error getting releases: {str(e)}')
            self.logger.error(f"❌ Error getting releases: {e}")
        
        finally:
            self._is_running = False
        
        return releases

    def get_all_releases(self) -> List[GameRelease]:
        """
        Gets all releases (100 complete pages)
        
        Returns:
            List[GameRelease]: List of all releases
        """
        return self.get_fitgirl_releases(max_pages=100)

    def get_releases_from_pages(self, start_page: int, end_page: int) -> List[GameRelease]:
        """
        Gets releases from a specific range of pages
        
        Args:
            start_page: Initial page (1-based)
            end_page: Final page (inclusive)
            
        Returns:
            List[GameRelease]: List of releases from the specified range
        """
        releases = []
        
        try:
            self._is_running = True
            self._update_progress('scraping', f'Getting releases from pages {start_page} to {end_page}')
            
            # Get torrent links from specified range
            torrent_links = []
            
            for page in range(start_page, end_page + 1):
                page_url = f"{self.fitgirl_torrents_url}{page}/"
                self._update_progress('scraping', f'Downloading page {page} of {end_page}...', 
                                   current_page=page, total_pages=end_page)
                
                response = self.session.get(page_url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Search for torrent links in the table
                torrent_rows = soup.find_all('tr')
                page_links = []
                
                for row in torrent_rows:
                    # Search for torrent link
                    torrent_link = row.find('a', href=lambda x: x and '/torrent/' in x)
                    if torrent_link:
                        full_url = self.base_url + torrent_link['href']
                        if full_url not in torrent_links:
                            torrent_links.append(full_url)
                            page_links.append(full_url)
                
                self._update_progress('scraping', f'Page {page}: {len(page_links)} torrents found', 
                                   current_page=page, total_pages=end_page, total_torrents=len(torrent_links))
                
                # Pause between pages
                time.sleep(2)
            
            self._update_progress('processing', f'Processing {len(torrent_links)} torrents...', 
                               current_release=0, total_releases=len(torrent_links))
            
            # Process each torrent to get complete details
            for i, torrent_url in enumerate(torrent_links):
                try:
                    self._update_progress('processing', f'Verifying torrent {i+1} of {len(torrent_links)}...', 
                                       current_release=i+1, total_releases=len(torrent_links))
                    
                    # OPTIMIZATION: Check if URL already exists before processing
                    if self.url_check_callback and self.url_check_callback(torrent_url):
                        self.logger.info(f"⏭️ URL already exists, skipping processing: {torrent_url}")
                        self._update_progress('processing', f'URL already exists, skipped', 
                                           current_release=i+1, total_releases=len(torrent_links))
                        continue
                    
                    # Only extract details if URL doesn't exist
                    self._update_progress('processing', f'Extracting torrent details {i+1} of {len(torrent_links)}...', 
                                       current_release=i+1, total_releases=len(torrent_links))
                    
                    release = self._extract_release_details(torrent_url)
                    
                    if release and release.has_download_links:
                        if self.insert_callback:
                            # Insert immediately using callback
                            if self.insert_callback(release):
                                releases.append(release)
                                self._update_progress('processing', f'Release inserted: {release.title}', 
                                                   current_release=i+1, total_releases=len(torrent_links), 
                                                   processed_releases=len(releases))
                            else:
                                self.logger.warning(f"⚠️ Could not insert release: {release.title}")
                                self._update_progress('processing', f'Error inserting release: {release.title}', 
                                                   current_release=i+1, total_releases=len(torrent_links))
                        else:
                            # Normal mode: add to list
                            releases.append(release)
                            self._update_progress('processing', f'Release {len(releases)}: {release.title}', 
                                               current_release=i+1, total_releases=len(torrent_links), 
                                               processed_releases=len(releases))
                    else:
                        if release:
                            self.logger.warning(f"⚠️ Release without magnet link: {release.title}")
                        else:
                            self.logger.warning(f"⚠️ Could not extract release from: {torrent_url}")
                        self._update_progress('processing', f'Skipping torrent without complete data', 
                                           current_release=i+1, total_releases=len(torrent_links))
                    
                    # Pause between requests
                    time.sleep(1)
                    
                except Exception as e:
                    self._update_progress('processing', f'Error processing torrent: {str(e)}...', 
                                       current_release=i+1, total_releases=len(torrent_links))
                    continue
            
            self._update_progress('completed', f'Processing completed: {len(releases)} releases obtained', 
                               processed_releases=len(releases))
            
        except Exception as e:
            self._update_progress('error', f'Error getting releases: {str(e)}')
            self.logger.error(f"❌ Error getting releases: {e}")
        
        finally:
            self._is_running = False
        
        return releases
    
    def _get_torrent_links_from_torrents_page(self, max_pages: int) -> List[str]:
        """
        Gets torrent links from the torrents page with complete pagination
        
        Args:
            max_pages: Maximum number of pages
            
        Returns:
            List[str]: List of torrent URLs
        """
        torrent_links = []
        
        try:
            self._update_progress('scraping', f'Downloading pages 1 to {max_pages}...', current_page=0, total_pages=max_pages)
            
            for page in range(1, max_pages + 1):
                page_url = f"{self.fitgirl_torrents_url}{page}/"
                self._update_progress('scraping', f'Downloading page {page} of {max_pages}...', current_page=page, total_pages=max_pages)
                
                response = self.session.get(page_url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Search for torrent links in the table
                torrent_rows = soup.find_all('tr')
                page_links = []
                
                for row in torrent_rows:
                    # Search for torrent link
                    torrent_link = row.find('a', href=lambda x: x and '/torrent/' in x)
                    if torrent_link:
                        full_url = self.base_url + torrent_link['href']
                        if full_url not in torrent_links:
                            torrent_links.append(full_url)
                            page_links.append(full_url)
                
                self._update_progress('scraping', f'Page {page}: {len(page_links)} torrents found', 
                                   current_page=page, total_pages=max_pages, total_torrents=len(torrent_links))
                
                # If there are no torrents on this page, we probably reached the end
                if not page_links:
                    self._update_progress('scraping', f'No more torrents, ending on page {page}', 
                                       current_page=page, total_pages=max_pages)
                    break
                
                # Pause between pages
                time.sleep(2)
            
            self._update_progress('scraping', f'Download completed: {len(torrent_links)} torrents found', 
                               current_page=max_pages, total_pages=max_pages, total_torrents=len(torrent_links))
            
        except Exception as e:
            self._update_progress('error', f'Error downloading pages: {str(e)}')
            self.logger.error(f"❌ Error getting torrent links: {e}")
        
        return torrent_links
    
    def _get_torrent_links_from_profile(self, max_pages: int) -> List[str]:
        """
        Gets torrent links from FitGirl profile
        
        Args:
            max_pages: Maximum number of pages
            
        Returns:
            List[str]: List of torrent URLs
        """
        torrent_links = []
        
        try:
            for page in range(1, max_pages + 1):
                if page == 1:
                    page_url = self.fitgirl_profile_url  # First page without number
                else:
                    page_url = f"{self.fitgirl_profile_url}{page}/"
                self.logger.info(f"📄 Getting page {page}: {page_url}")
                
                response = self.session.get(page_url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Search for torrent links in the table
                torrent_rows = soup.find_all('tr')
                page_links = []
                
                for row in torrent_rows:
                    # Search for torrent link
                    torrent_link = row.find('a', href=lambda x: x and '/torrent/' in x)
                    if torrent_link:
                        full_url = self.base_url + torrent_link['href']
                        if full_url not in torrent_links:
                            torrent_links.append(full_url)
                            page_links.append(full_url)
                
                self.logger.info(f"📦 Found {len(page_links)} torrents on page {page}")
                
                # If there are no torrents on this page, we probably reached the end
                if not page_links:
                    self.logger.info(f"📄 No more torrents, ending on page {page}")
                    break
                
                # Pause between pages
                time.sleep(2)
            
            self.logger.info(f"📋 Total torrents found: {len(torrent_links)}")
            
        except Exception as e:
            self.logger.error(f"❌ Error getting torrent links: {e}")
        
        return torrent_links
    
    def _extract_release_details(self, torrent_url: str) -> Optional[GameRelease]:
        """
        Extracts complete details of a release from its individual page
        
        Args:
            torrent_url: Torrent URL
            
        Returns:
            Optional[GameRelease]: GameRelease object with all details
        """
        try:
            # Try first with requests (faster)
            response = self.session.get(torrent_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract basic information - use title tag first to get complete title
            title_tag = soup.find('title')
            if title_tag:
                # Extract title from <title> tag and clean
                full_title = title_tag.get_text(strip=True)
                # Remove "Download " from start and " Torrent | 1337x" from end
                if full_title.startswith('Download '):
                    full_title = full_title[9:]  # Remove "Download "
                if ' Torrent | 1337x' in full_title:
                    full_title = full_title.split(' Torrent | 1337x')[0]
                title = self._clean_title(full_title)
            else:
                # Fallback to H1 element if no title tag
                title_element = soup.find('h1')
                title = title_element.get_text(strip=True) if title_element else "Title not found"
                title = self._clean_title(title)
            
            # Extract torrent size
            size = self._extract_size(soup)
            self.logger.info(f"📦 Size extracted: {size}")
            
            # Extract magnet link
            magnet_link = self._extract_magnet_link(soup)
            if not magnet_link:
                self.logger.warning(f"⚠️ Magnet link not found for: {title}")
                return None
            
            # Extract description using more specific selectors for 1337x
            description_div = None
            
            # Test multiple common selectors in 1337x
            description_selectors = [
                'div.torrent-detail-page',
                'div.box-info-detail', 
                'div.tab-pane.active',
                'div.tab-content div',
                'div#description',
                'div.description'
            ]
            
            for selector in description_selectors:
                description_div = soup.select_one(selector)
                if description_div:
                    self.logger.info(f"✅ Description found with selector: {selector}")
                    break
            
            cover_image_url = ""
            screenshot_urls = []
            
            if description_div:
                # Extract complete game description
                full_description = self._extract_game_description(description_div)
                
                # The description is the complete description without cutting
                description = full_description
                
                # The short_description is the description cut to 300 characters
                if len(description) > 300:
                    short_description = description[:300].strip() + "..."
                else:
                    short_description = description
                
                self.logger.info(f"📝 Complete description ({len(description)} chars): {description[:100]}...")
                self.logger.info(f"📋 Technical info ({len(short_description)} chars): {short_description[:100]}...")
                
                # Try to extract images with requests first
                cover_image_url = self._extract_game_cover_image(description_div)
                screenshot_urls = self._extract_screenshots(description_div, cover_image_url)
                
                # If we don't find images, use Selenium with improved timeout and retry
                if not cover_image_url and not screenshot_urls and self.driver:
                    # Use Selenium to load dynamic images with retry mechanism
                    self.logger.info(f"🌐 Using Selenium to load dynamic images: {title}")
                    
                    driver = None
                    max_retries = 2
                    
                    for attempt in range(max_retries):
                        try:
                            self.logger.info(f"🔄 Selenium attempt {attempt + 1}/{max_retries}")
                            
                            # Configure Chrome headless
                            chrome_options = Options()
                            chrome_options.add_argument('--headless')
                            chrome_options.add_argument('--no-sandbox')
                            chrome_options.add_argument('--disable-dev-shm-usage')
                            chrome_options.add_argument('--disable-gpu')
                            chrome_options.add_argument('--window-size=1920,1080')
                            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
                            
                            driver = webdriver.Chrome(options=chrome_options)
                            driver.set_page_load_timeout(30)  # Increased timeout
                            driver.get(torrent_url)
                            
                            # Wait for initial load with longer timeout
                            WebDriverWait(driver, 20).until(
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )
                            time.sleep(5)  # Increased initial wait
                            
                            # Enhanced lazy loading techniques with longer waits
                            # 1. Gradual scroll down with longer pauses
                            for i in range(8):  # More scroll steps
                                driver.execute_script(f"window.scrollTo(0, {i * 400});")
                                time.sleep(1)  # Longer pause between scrolls
                            
                            # 2. Scroll to the end and wait longer
                            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(4)  # Longer wait at bottom
                            
                            # 3. Scroll back up gradually
                            for i in range(8, 0, -1):
                                driver.execute_script(f"window.scrollTo(0, {i * 400});")
                                time.sleep(1)
                            
                            # 4. Back to top
                            driver.execute_script("window.scrollTo(0, 0);")
                            time.sleep(3)
                            
                            # 5. Enhanced image triggering with more images
                            try:
                                image_containers = driver.find_elements(By.TAG_NAME, "img")
                                self.logger.info(f"🔍 Found {len(image_containers)} total images on page")
                                
                                for i, container in enumerate(image_containers[:15]):  # More images
                                    try:
                                        driver.execute_script("arguments[0].scrollIntoView(true);", container)
                                        time.sleep(0.5)  # Longer pause for each image
                                    except:
                                        pass
                            except Exception as e:
                                self.logger.warning(f"⚠️ Error triggering images: {e}")
                            
                            # 6. Final wait for any remaining lazy loading
                            time.sleep(5)  # Longer final wait
                            
                            # Get processed HTML
                            html = driver.page_source
                            selenium_soup = BeautifulSoup(html, 'html.parser')
                            selenium_description_div = selenium_soup.find('div', class_='torrent-detail-page')
                            if not selenium_description_div:
                                selenium_description_div = selenium_soup.find('div', class_='box-info-detail')
                            
                            if selenium_description_div:
                                # Add detailed HTML logging for debugging
                                all_images = selenium_description_div.find_all('img')
                                self.logger.info(f"🔍 Selenium attempt {attempt + 1} found {len(all_images)} images in description")
                                
                                for i, img in enumerate(all_images[:10]):
                                    src = img.get('src', '')
                                    alt = img.get('alt', '')
                                    self.logger.info(f"   Image {i+1}: {src} (alt: {alt[:50]})")
                                
                                # Extract images from HTML with executed JavaScript
                                if not cover_image_url:
                                    cover_image_url = self._extract_game_cover_image(selenium_description_div)
                                if not screenshot_urls:
                                    screenshot_urls = self._extract_screenshots(selenium_description_div, cover_image_url)
                                
                                # If we found images, break the retry loop
                                if cover_image_url or screenshot_urls:
                                    self.logger.info(f"✅ Found images on attempt {attempt + 1}")
                                    break
                                else:
                                    self.logger.warning(f"⚠️ No images found on attempt {attempt + 1}")
                            else:
                                self.logger.warning(f"⚠️ No description div found on attempt {attempt + 1}")
                                
                        except Exception as e:
                            self.logger.error(f"❌ Error with Selenium attempt {attempt + 1}: {e}")
                        finally:
                            if driver:
                                driver.quit()
                                driver = None
                        
                        # If we found images, no need for more attempts
                        if cover_image_url or screenshot_urls:
                            break
                        
                        # Wait between attempts
                        if attempt < max_retries - 1:
                            self.logger.info(f"⏳ Waiting 3 seconds before retry...")
                            time.sleep(3)
                
                # Results logging
                if cover_image_url:
                    self.logger.info(f"🖼️ Cover found: {cover_image_url}")
                else:
                    self.logger.warning(f"⚠️ No cover found for: {title}")
                
                if screenshot_urls:
                    self.logger.info(f"📸 Screenshots found: {len(screenshot_urls)} images")
                    for i, screenshot in enumerate(screenshot_urls[:3]):  # Only show first 3
                        self.logger.info(f"   {i+1}. {screenshot}")
                else:
                    self.logger.warning(f"⚠️ No screenshots found for: {title}")
                
                # Extract game details
                game_details = self._extract_game_details(description_div)
                
                # Detailed HTML logging for debugging
                self.logger.debug(f"🔍 Description HTML for {title}:")
                self.logger.debug(f"   - HTML length: {len(str(description_div))}")
                self.logger.debug(f"   - Total images: {len(description_div.find_all('img'))}")
                
                # Verify that images are assigned correctly
                self.logger.info(f"📋 Extraction summary for {title}:")
                self.logger.info(f"   - Cover: {cover_image_url or 'NOT FOUND'}")
                self.logger.info(f"   - Screenshots: {len(screenshot_urls)} found")
                self.logger.info(f"   - Magnet: {bool(magnet_link)}")
                
                # Extract original game release date
                game_release_date = self._extract_game_release_date(description_div)
                self.logger.info(f"   - Game date: {game_release_date}")
            else:
                description = ""
                short_description = ""
                game_details = {}
                game_release_date = None
                self.logger.warning(f"⚠️ No description found for: {title}")
            
            # Extract torrent publication date on 1337x
            torrent_publish_date = self._extract_release_date(soup)
            if not torrent_publish_date:
                # If "Date uploaded" not found, use current date as last resort
                self.logger.warning(f"⚠️ 'Date uploaded' not found for: {title}")
                torrent_publish_date = datetime.now()
                self.logger.warning(f"❌ FALLBACK: Using current date for {title} - REVIEW MANUALLY!")
            
            # Crear objeto GameRelease
            release = GameRelease(
                url=torrent_url,
                title=title,
                description=description,
                short_description=short_description,
                publish_date=torrent_publish_date,
                game_release_date=game_release_date,
                magnet_link=magnet_link,
                size=size,
                status=ReleaseStatus.NEW,
                additional_data=game_details,
                cover_image_url=cover_image_url or "",
                screenshot_urls=screenshot_urls
            )
            
            # Log of created object
            self.logger.info(f"🎮 Release created:")
            self.logger.info(f"   - Title: {release.title}")
            self.logger.info(f"   - Description: {len(release.description)} chars")
            self.logger.info(f"   - Short description: {len(release.short_description)} chars")
            self.logger.info(f"   - Size: {release.size}")
            self.logger.info(f"   - Publish date: {release.publish_date}")
            self.logger.info(f"   - Game date: {release.game_release_date}")
            self.logger.info(f"   - Magnet: {bool(release.magnet_link)}")
            self.logger.info(f"   - Cover: {release.cover_image_url}")
            self.logger.info(f"   - Screenshots: {len(release.screenshot_urls)}")
            
            return release
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting details from {torrent_url}: {e}")
            return None
    


    def _extract_release_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """
        Extracts the torrent publication date from 1337x HTML
        Searches specifically: <li> <strong>Date uploaded</strong> <span>relative date</span> </li>
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Optional[datetime]: Torrent publication date or None if not found
        """
        try:
            self.logger.info("🔍 Searching for 'Date uploaded' element in specific format...")
            
            # Search specifically for <strong>Date uploaded</strong> element
            date_uploaded_element = soup.find('strong', string='Date uploaded')
            
            if not date_uploaded_element:
                self.logger.warning("⚠️ <strong>Date uploaded</strong> element not found")
                return None
            
            self.logger.info("✅ Found <strong>Date uploaded</strong> element")
            
            # Search for next <span> element that should contain the relative date
            parent_li = date_uploaded_element.parent
            if parent_li:
                # Search for span within the same li element
                span_element = parent_li.find('span')
                if span_element:
                    date_text = span_element.get_text(strip=True)
                    self.logger.info(f"🔍 Relative date found in span: '{date_text}'")
                    
                    # Process the relative date
                    parsed_date = self._parse_relative_date(date_text)
                    if parsed_date:
                        self.logger.info(f"✅ Date processed successfully: {parsed_date}")
                        return parsed_date
                    else:
                        self.logger.warning(f"⚠️ Could not process relative date: '{date_text}'")
                        return None
                else:
                    self.logger.warning("⚠️ <span> element not found after 'Date uploaded'")
                    return None
            else:
                self.logger.warning("⚠️ Parent <li> element not found for 'Date uploaded'")
                return None
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting publication date: {e}")
            return None
    
    def _parse_relative_date(self, date_text: str) -> Optional[datetime]:
        """
        Processes a relative date like "1 year ago", "10 hours ago", etc.
        
        Args:
            date_text: Text with relative date
            
        Returns:
            Optional[datetime]: Calculated date or None
        """
        if not date_text:
            return None
        
        try:
            self.logger.debug(f"🔍 Processing relative date: '{date_text}'")
            
            # Clean the text
            date_text = date_text.strip().lower()
            
            # Search for relative date pattern
            pattern = r'(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago'
            match = re.search(pattern, date_text, re.IGNORECASE)
            
            if match:
                amount = int(match.group(1))
                unit = match.group(2).lower()
                
                self.logger.debug(f"🔍 Amount: {amount}, Unit: {unit}")
                
                return self._calculate_date_from_ago(amount, unit)
            
            # Try shorter patterns (sec, min, hr, etc.)
            short_pattern = r'(\d+)\s*(sec|min|hr|hrs|h|d|w|mo|y)\s+ago'
            match = re.search(short_pattern, date_text, re.IGNORECASE)
            
            if match:
                amount = int(match.group(1))
                unit = match.group(2).lower()
                
                self.logger.debug(f"🔍 Cantidad (formato corto): {amount}, Unidad: {unit}")
                
                # Mapear unidades cortas a largas
                unit_mapping = {
                    'sec': 'second',
                    'min': 'minute', 
                    'hr': 'hour',
                    'h': 'hour',
                    'd': 'day',
                    'w': 'week',
                    'mo': 'month',
                    'y': 'year'
                }
                
                full_unit = unit_mapping.get(unit, unit)
                return self._calculate_date_from_ago(amount, full_unit)
            
            self.logger.debug(f"❌ Could not process relative date: '{date_text}'")
            
        except Exception as e:
            self.logger.error(f"❌ Error processing relative date: {e}")
        
        return None
    
    def _calculate_date_from_ago(self, amount: int, unit: str) -> Optional[datetime]:
        """
        Calculates date from "X time ago" format
        
        Args:
            amount: Amount of time
            unit: Time unit
            
        Returns:
            Optional[datetime]: Calculated date or None
        """
        now = datetime.now()
        unit = unit.lower()
        
        try:
            if unit.startswith('sec') or unit == 's':
                return now - timedelta(seconds=amount)
            elif unit.startswith('min') or unit == 'm':
                return now - timedelta(minutes=amount)
            elif unit.startswith('hour') or unit.startswith('hr') or unit == 'h':
                return now - timedelta(hours=amount)
            elif unit.startswith('day') or unit == 'd':
                return now - timedelta(days=amount)
            elif unit.startswith('week') or unit == 'w':
                return now - timedelta(weeks=amount)
            elif unit.startswith('month') or unit == 'mo':
                return now - timedelta(days=amount * 30)  # Approximation
            elif unit.startswith('year') or unit == 'y':
                return now - timedelta(days=amount * 365)  # Approximation
        except (ValueError, OverflowError):
            pass
        
        return None
    
    def _is_reasonable_torrent_date(self, date: datetime) -> bool:
        """
        Verifies if a date is reasonable for a torrent
        
        Args:
            date: Date to verify
            
        Returns:
            bool: True if the date is reasonable
        """
        now = datetime.now()
        
        # Cannot be future (with a margin of 1 day)
        if date > now + timedelta(days=1):
            return False
        
        # Cannot be too old (before 2000, when BitTorrent did not exist)
        if date.year < 2000:
            return False
        
        # Cannot be too old for FitGirl (started around 2012)
        if date.year < 2010:
            return False
        
        return True

 
    
    def _extract_game_release_date(self, description_div) -> Optional[datetime]:
        """
        Extracts the original game release date from the description
        
        Args:
            description_div: Div with the game description
            
        Returns:
            Optional[datetime]: Game release date
        """
        try:
            if not description_div:
                self.logger.debug("🔍 No description_div para extraer fecha")
                return None
            
            text = description_div.get_text()
            html_text = str(description_div)
            
            self.logger.debug(f"🔍 Searching for release date in text: {text[:200]}...")
            
            # Specific patterns to search for game release date
            html_patterns = [
                r'<strong>Release Date:\s*</strong>\s*([^<\n\r]+)',  # HTML format
            ]
            
            text_patterns = [
                r'Release Date:\s*([^<\n\r]+)',
                r'Released:\s*([^<\n\r]+)',
                r'Launch Date:\s*([^<\n\r]+)',
                r'Game Release:\s*([^<\n\r]+)',
                r'Original Release:\s*([^<\n\r]+)',
                r'First Released:\s*([^<\n\r]+)',
            ]
            
            # Buscar primero en HTML
            for pattern in html_patterns:
                date_match = re.search(pattern, html_text, re.IGNORECASE)
                if date_match:
                    date_str = date_match.group(1).strip()
                    self.logger.debug(f"🔍 Date found in HTML: '{date_str}'")
                    
                    # Clean extra text
                    date_str = re.sub(r'\s*\([^)]*\)', '', date_str)  # Remove parentheses
                    date_str = re.sub(r'\s*\[[^\]]*\]', '', date_str)  # Remove brackets
                    date_str = date_str.strip()
                    
                    # Intentar parsear diferentes formatos de fecha
                    date_formats = [
                        '%B %d, %Y',      # June 30, 2025
                        '%b %d, %Y',      # Jun 30, 2025
                        '%d %B %Y',       # 30 June 2025
                        '%d %b %Y',       # 30 Jun 2025
                        '%Y-%m-%d',       # 2025-06-30
                        '%d/%m/%Y',       # 30/06/2025
                        '%m/%d/%Y',       # 06/30/2025
                        '%B %Y',          # June 2025
                        '%b %Y',          # Jun 2025
                    ]
                    
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            self.logger.debug(f"✅ Date parsed successfully: {parsed_date}")
                            return parsed_date
                        except ValueError:
                            continue
            
            # Search in plain text
            for pattern in text_patterns:
                date_match = re.search(pattern, text, re.IGNORECASE)
                if date_match:
                    date_str = date_match.group(1).strip()
                    self.logger.debug(f"🔍 Date found in text: '{date_str}'")
                    
                    # Clean extra text
                    date_str = re.sub(r'\s*\([^)]*\)', '', date_str)  # Remove parentheses
                    date_str = re.sub(r'\s*\[[^\]]*\]', '', date_str)  # Remove brackets
                    date_str = date_str.strip()
                    
                    # Intentar parsear diferentes formatos de fecha
                    date_formats = [
                        '%B %d, %Y',      # June 30, 2025
                        '%b %d, %Y',      # Jun 30, 2025
                        '%d %B %Y',       # 30 June 2025
                        '%d %b %Y',       # 30 Jun 2025
                        '%Y-%m-%d',       # 2025-06-30
                        '%d/%m/%Y',       # 30/06/2025
                        '%m/%d/%Y',       # 06/30/2025
                        '%Y',             # 2025
                        '%B %Y',          # June 2025
                        '%b %Y',          # Jun 2025
                    ]
                    
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            self.logger.debug(f"✅ Fecha parseada exitosamente: {parsed_date}")
                            return parsed_date
                        except ValueError:
                            continue
            
            self.logger.debug("❌ No valid release date found")
            
        except Exception as e:
            self.logger.debug(f"Error extracting game release date: {e}")
        
        return None
    
    def _extract_game_description(self, description_div) -> str:
        """
        Extracts the game description that is between <strong>Description: </strong> and the next <strong>
        If the description is empty, it searches for the next <strong> and its content
        
        Args:
            description_div: Div with the game description
            
        Returns:
            str: Game description
        """
        try:
            if not description_div:
                return ""
            
            self.logger.info("📝 Searching for description between <strong>Description: </strong>...")
            
            # Search for the <strong> element that contains "Description:"
            description_strong = description_div.find('strong', string=re.compile(r'Description\s*:', re.IGNORECASE))
            
            if not description_strong:
                self.logger.warning("⚠️ <strong>Description: </strong> not found")
                return ""
            
            self.logger.info("✅ Found <strong>Description: </strong>")
            
            # Get all elements after the strong until the next strong
            description_text = ""
            current_element = description_strong.next_sibling
            
            while current_element:
                # If we find another <strong>, stop
                if current_element.name == 'strong':
                    self.logger.info(f"🛑 Found next <strong>, stopping extraction")
                    break
                
                # If it's text, add it
                if isinstance(current_element, str):
                    description_text += current_element
                # If it's an element, get its text
                elif hasattr(current_element, 'get_text'):
                    description_text += current_element.get_text()
                
                current_element = current_element.next_sibling
            
            # Clean the text
            description_text = description_text.strip()
            description_text = re.sub(r'\s+', ' ', description_text)
            
            # If the description is empty, search for the next <strong> and its content
            if not description_text:
                self.logger.info("📝 Empty description, searching for next <strong>...")
                
                # Search for the next <strong> after "Description:"
                next_strong = description_strong.find_next_sibling('strong')
                
                if next_strong:
                    self.logger.info(f"✅ Found next <strong>: {next_strong.get_text()}")
                    
                    # Get content until the next <strong>
                    next_description_text = ""
                    current_element = next_strong.next_sibling
                    
                    while current_element:
                        # If we find another <strong>, stop
                        if current_element.name == 'strong':
                            self.logger.info(f"🛑 Found next <strong>, stopping extraction")
                            break
                        
                        # If it's text, add it
                        if isinstance(current_element, str):
                            next_description_text += current_element
                        # If it's an element, get its text
                        elif hasattr(current_element, 'get_text'):
                            next_description_text += current_element.get_text()
                        
                        current_element = current_element.next_sibling
                    
                    # Clean the text
                    next_description_text = next_description_text.strip()
                    next_description_text = re.sub(r'\s+', ' ', next_description_text)
                    
                    if next_description_text:
                        self.logger.info(f"📝 Next <strong> description extracted: {len(next_description_text)} characters")
                        self.logger.info(f"📝 Content: {next_description_text[:100]}...")
                        return next_description_text
                    else:
                        self.logger.warning("⚠️ The next <strong> also has empty content")
                else:
                    self.logger.warning("⚠️ No next <strong> found")
            
            self.logger.info(f"📝 Description extracted: {len(description_text)} characters")
            self.logger.info(f"📝 Content: {description_text[:100]}...")
            
            return description_text
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting description: {e}")
            return ""
    

    
    def _extract_game_cover_image(self, description_div):
        """Extract game cover image URL from the description"""
        try:
            # Search for all images
            all_images = description_div.find_all('img')
            self.logger.info(f"🔍 Searching for cover among {len(all_images)} images")
            
            for i, img in enumerate(all_images):
                src = img.get('src', '')
                alt = img.get('alt', '').lower()
                
                self.logger.info(f"   Evaluating image {i+1}: {src}")
                self.logger.info(f"   Alt text: {alt}")
                
                # Filter valid images for covers - only legitimate domains
                if (src and 
                    not src.endswith('.svg') and 
                    not src.endswith('.gif') and  # Don't take GIFs as cover
                    'profile-load' not in src and
                    'fakes2.jpg' not in src and
                    'fitgirl-repacks.site' not in src and
                    'limeiptv.to' not in src and  # Skip advertising
                    any(domain in src for domain in ['imageban.ru', 'imgur.com', 'postimg.cc', 'imgbb.com', 'fastpic.ru'])):
                    
                    self.logger.info(f"✅ Cover found: {src}")
                    return src
                else:
                    self.logger.info(f"❌ Image rejected: {src}")
            
            self.logger.warning("⚠️ No valid cover found")
            return ""
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting cover: {e}")
            return ""

    def _extract_screenshots(self, description_div, cover_image_url=""):
        """Extract screenshot URLs from the description"""
        try:
            # Search for all images
            all_images = description_div.find_all('img')
            self.logger.info(f"🔍 Searching for screenshots among {len(all_images)} images")
            
            screenshots = []
            for i, img in enumerate(all_images):
                src = img.get('src', '')
                alt = img.get('alt', '').lower()
                
                self.logger.info(f"   Evaluating screenshot {i+1}: {src}")
                
                # Filter valid images for screenshots - skip advertising
                if (src and 
                    not src.endswith('.svg') and 
                    'profile-load' not in src and
                    'limeiptv.to' not in src and  # Skip advertising
                    # Avoid duplicating cover as screenshot
                    src != cover_image_url and
                    any(domain in src for domain in ['riotpixels.net', 'imgur.com', 'postimg.cc', 'imgbb.com', 'imageban.ru', 'fastpic.ru'])):
                    
                    # Save original URL in 240p - conversion to 720p will be done in frontend
                    self.logger.info(f"✅ Screenshot found: {src}")
                    screenshots.append(src)
                else:
                    self.logger.info(f"❌ Screenshot rejected: {src}")
            
            self.logger.info(f"📸 Total screenshots found: {len(screenshots)}")
            return screenshots
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting screenshots: {e}")
            return []
    
    def _extract_game_details(self, description_div) -> Dict[str, str]:
        """
        Extract specific game details (relevant technical information)
        
        Args:
            description_div: Div with the description
            
        Returns:
            Dict[str, str]: Game details (only relevant technical information)
        """
        details = {}
        
        try:
            text = description_div.get_text()
            
            # Only extract relevant and specific technical information
            patterns = {
                'genres': r'Genres/Tags:\s*([^\r\n]+?)(?:\r|\n|Developer:)',
                'developer': r'Developer:\s*([^\r\n]+?)(?:\r|\n|Publisher:)',
                'publisher': r'Publisher:\s*([^\r\n]+?)(?:\r|\n|Platform:)',
                'platform': r'Platform:\s*([^\r\n]+?)(?:\r|\n|Engine:)',
                'engine': r'Engine:\s*([^\r\n]+?)(?:\r|\n|Steam User Rating:|Interface Language:)',
                'interface_language': r'Interface Language:\s*([^\r\n]+?)(?:\r|\n|Audio Language:)',
                'audio_language': r'Audio Language:\s*([^\r\n]+?)(?:\r|\n|Crack:)',
                'crack': r'Crack:\s*([^\r\n]+?)(?:\r|\n|Minimum requirements:)',
                'steam_rating': r'Steam User Rating:\s*([^\r\n]+?)(?:\r|\n|Interface Language:)',
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match:
                    value = match.group(1).strip()
                    # Clean the value
                    value = re.sub(r'\s+', ' ', value)  # Normalize spaces
                    value = value.split('\n')[0].strip()  # Only the first line
                    
                    # Only save if not empty and not too long
                    if value and len(value) <= 150:
                        details[key] = value
        except Exception as e:
            pass
        return details
    
    def _extract_magnet_link(self, soup) -> Optional[str]:
        """
        Extracts the magnet link from the torrent page
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Optional[str]: Magnet link or None if not found
        """
        try:
            # Search for magnet link
            magnet_element = soup.find('a', href=lambda x: x and x.startswith('magnet:'))
            if magnet_element:
                return magnet_element['href']
            
            # Search in buttons or divs that contain magnet
            magnet_elements = soup.find_all(string=re.compile(r'magnet:', re.IGNORECASE))
            for element in magnet_elements:
                parent = element.parent
                if parent and parent.name == 'a':
                    href = parent.get('href', '')
                    if href.startswith('magnet:'):
                        return href
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting magnet link: {e}")
            return None

    def _clean_title(self, title: str) -> str:
        """
        Cleans the game title while preserving special characters
        
        Args:
            title: Original title
            
        Returns:
            str: Clean title without cutting
        """
        if not title:
            return ""
        
        # Remove "FitGirl Repack" from the end if it exists
        title = re.sub(r'\s*-?\s*FitGirl\s*Repack\s*$', '', title, flags=re.IGNORECASE)
        
        # Keep important special characters (don't remove them)
        # Only remove extra spaces and normalize
        title = re.sub(r'\s+', ' ', title)  # Normalize multiple spaces
        
        return title.strip()  # No character limit
    
    def _extract_size(self, soup: BeautifulSoup) -> str:
        """
        Extracts the torrent size from the page
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            str: Torrent size (e.g: "8.0 GB")
        """
        try:
            self.logger.info("🔍 Starting size extraction...")
            
            # Method 1: Search in specific information table
            info_tables = soup.find_all(['table', 'ul', 'div'], class_=['torrent-info', 'list', 'info-table'])
            for table in info_tables:
                text = table.get_text()
                self.logger.info(f"🔍 Checking table: {text[:100]}...")
                
                # Search for "Total size", "Size", etc.
                size_match = re.search(r'(?:Total\s+size|Size)\s*:?\s*([0-9.]+\s*[KMGT]B)', text, re.IGNORECASE)
                if size_match:
                    size = size_match.group(1)
                    self.logger.info(f"✅ Size found in table: {size}")
                    return size
            
            # Method 2: Search in specific 1337x metadata
            # Search in td elements that contain size
            for td in soup.find_all('td'):
                text = td.get_text(strip=True)
                # Search for size patterns in table cells
                size_match = re.search(r'^(\d+(?:\.\d+)?\s*[KMGT]B)$', text, re.IGNORECASE)
                if size_match:
                    size = size_match.group(1)
                    self.logger.debug(f"✅ Size found in cell: {size}")
                    return size
            
            # Method 3: Search in entire page with more specific patterns
            page_text = soup.get_text()
            self.logger.info(f"🔍 Searching in complete text ({len(page_text)} chars)...")
            
            # Specific patterns for 1337x
            size_patterns = [
                r'(?:Total\s+size|File\s+size|Size)\s*:?\s*(\d+(?:\.\d+)?\s*[KMGT]B)',  # "Total size: 8.0 GB"
                r'(\d+(?:\.\d+)?\s*GB)(?=\s|$)',  # Only GB at end of line or space
                r'(\d+(?:\.\d+)?\s*MB)(?=\s|$)',  # Only MB at end of line or space
                r'(\d+(?:\.\d+)?\s*TB)(?=\s|$)',  # Only TB at end of line or space
            ]
            
            for i, pattern in enumerate(size_patterns):
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                self.logger.debug(f"🔍 Pattern {i+1}: found {len(matches)} matches")
                
                if matches:
                    for match in matches:
                        try:
                            # Extract number and unit
                            size_text = match if isinstance(match, str) else match[0]
                            size_match = re.search(r'(\d+(?:\.\d+)?)\s*([KMGT]B)', size_text, re.IGNORECASE)
                            if size_match:
                                size_value = float(size_match.group(1))
                                unit = size_match.group(2).upper()
                                
                                self.logger.debug(f"🔍 Evaluating: {size_value} {unit}")
                                
                                # Filter reasonable sizes for games
                                if unit == 'GB' and 0.1 <= size_value <= 100:
                                    result = f"{size_value} {unit}"
                                    self.logger.debug(f"✅ Valid size found: {result}")
                                    return result
                                elif unit == 'MB' and 100 <= size_value <= 20000:
                                    result = f"{size_value} {unit}"
                                    self.logger.debug(f"✅ Valid size found: {result}")
                                    return result
                                elif unit == 'TB' and 0.5 <= size_value <= 10:
                                    result = f"{size_value} {unit}"
                                    self.logger.debug(f"✅ Valid size found: {result}")
                                    return result
                                else:
                                    self.logger.debug(f"❌ Size out of range: {size_value} {unit}")
                        except (ValueError, AttributeError) as e:
                            self.logger.debug(f"❌ Error processing match: {e}")
                            continue
            
            self.logger.warning("⚠️ No valid size found")
            return "N/A"
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting size: {str(e)}")
            return "Error"
    
    def is_running(self) -> bool:
        """Check if the scraper is running"""
        return self._is_running
    
    def stop(self):
        """Stop the scraper"""
        self._is_running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass 
    
    def close(self):
        """Close the Selenium driver and clean up resources"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                if hasattr(self, 'logger'):
                    self.logger.info("🔒 Selenium driver closed")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"❌ Error closing Selenium: {e}")
    
    def __del__(self):
        """Destructor to ensure Selenium is closed"""
        try:
            self.close()
        except:
            pass  # Ignore errors in destructor 

