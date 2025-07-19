#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FitGirl Downloader - Web Application
Flask server for the web application
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
import sys
import os
import logging
from datetime import datetime
import json
import threading
import traceback

# Add the backend directory to the path
sys.path.append('backend')

from backend.json_database_manager import JsonDatabaseManager
from backend.settings_manager import SettingsManager
from backend.x1337_scraper import X1337Scraper
from backend.game_release import ReleaseStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fitgirl-downloader-secret-key-2025'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
db_manager = None
settings_manager = None
scraper = None
sync_in_progress = False
sync_progress = {
    'status': 'idle',
    'current_page': 0,
    'total_pages': 0,
    'current_release': 0,
    'total_releases': 0,
    'new_releases': 0,
    'updated_releases': 0,
    'message': ''
}

def initialize_components():
    """Initialize system components"""
    global db_manager, settings_manager, scraper
    
    try:
        # Initialize managers
        settings_manager = SettingsManager()
        settings_manager.load_settings()
        
        db_manager = JsonDatabaseManager()
        if not db_manager.initialize():
            logger.error("❌ Error initializing JSON database")
            return False
        
        scraper = X1337Scraper()
        scraper.initialize(settings_manager)
        
        logger.info("✅ Components initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error initializing components: {e}")
        return False

# Initialize components when importing the module
initialize_components()

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info("🔌 WebSocket client connected")
    emit('sync_progress', sync_progress)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info("🔌 WebSocket client disconnected")

@socketio.on('get_sync_status')
def handle_get_sync_status():
    """Send current synchronization status"""
    emit('sync_progress', sync_progress)

def update_sync_progress(status, message, **kwargs):
    """Update synchronization progress and emit to all clients"""
    global sync_progress
    
    sync_progress.update({
        'status': status,
        'message': message,
        **kwargs
    })
    
    socketio.emit('sync_progress', sync_progress)
    logger.info(f"📊 Progress: {status} - {message}")

def sync_releases_worker():
    """Worker for background synchronization"""
    global sync_in_progress, sync_progress
    
    try:
        logger.info("🚀 Starting synchronization worker")
        sync_in_progress = True
        update_sync_progress('starting', 'Starting synchronization...')
        
        logger.info("🔍 Getting existing releases...")
        # Get existing releases for comparison
        existing_releases = db_manager.get_all_releases()
        
        # Create a more efficient lookup structure: (url, magnet_link) -> release
        existing_release_keys = {}
        existing_urls = set()  # Simple URL lookup for quick verification
        for release in existing_releases:
            # Use URL and magnet_link as composite key (magnet is unique and immutable)
            magnet_key = release.magnet_link if release.magnet_link else "no_magnet"
            key = (release.url, magnet_key)
            existing_release_keys[key] = release
            existing_urls.add(release.url)  # Add URL to quick lookup set
        
        logger.info(f"📊 Existing releases: {len(existing_releases)}")
        logger.info(f"🔑 Verification keys created: {len(existing_release_keys)}")
        logger.info(f"🔗 URLs for quick verification: {len(existing_urls)}")
        
        # Counters for progress
        new_releases = 0
        updated_releases = 0
        skipped_releases = 0  # Counter for skipped duplicates
        
        # URL check callback - fast verification before processing
        def url_exists_callback(url: str) -> bool:
            """Check if URL already exists in database (fast lookup)"""
            exists = url in existing_urls
            if exists:
                logger.info(f"⚡ Fast check: URL already exists: {url}")
            return exists
        
        # Callback to verify and process releases
        def insert_release_callback(release):
            nonlocal new_releases, updated_releases, skipped_releases
            
            # Create composite key for this release (URL + magnet_link)
            magnet_key = release.magnet_link if release.magnet_link else "no_magnet"
            release_key = (release.url, magnet_key)
            
            # Check if this exact release (URL + magnet) already exists
            if release_key in existing_release_keys:
                logger.info(f"⏭️ Release already exists (URL + magnet): {release.title}")
                skipped_releases += 1
                
                # Check if we should update the existing release
                existing_release = existing_release_keys[release_key]
                if existing_release.status == ReleaseStatus.NEW:
                    # Only update if marked as new and there might be content changes
                    logger.info(f"🔄 Checking if update is needed: {release.title}")
                    
                    # Simple check: compare some key fields to see if update is needed
                    needs_update = (
                        existing_release.description != release.description or
                        existing_release.size != release.size or
                        len(existing_release.screenshot_urls) != len(release.screenshot_urls)
                    )
                    
                    if needs_update:
                        logger.info(f"📝 Updating release content: {release.title}")
                        db_manager.update_release(release)
                        updated_releases += 1
                        update_sync_progress('processing', f'Release updated: {release.title}', 
                                           new_releases=new_releases, updated_releases=updated_releases, 
                                           skipped_releases=skipped_releases)
                    else:
                        logger.info(f"✅ Release unchanged, skipping: {release.title}")
                
                return True
            
            # New release - insert it
            logger.info(f"💾 Inserting new release: {release.title}")
            result = db_manager.insert_release(release)
            if result:
                new_releases += 1
                logger.info(f"✅ Release inserted successfully: {release.title}")
                
                # Update our lookup structures with the new release
                existing_release_keys[release_key] = release
                existing_urls.add(release.url)  # Add URL to quick lookup set
                
                # Emit WebSocket event to update the view in real time
                try:
                    # Get the newly inserted release with its ID
                    inserted_release = db_manager.get_release_by_id(result)
                    if inserted_release:
                        # Convert to JSON format for the frontend
                        release_data = {
                            'id': inserted_release.id,
                            'title': inserted_release.title,
                            'description': inserted_release.short_description,
                            'publish_date': inserted_release.formatted_date,
                            'game_release_date': inserted_release.formatted_game_release_date,
                            'status': inserted_release.status.name,
                            'status_text': inserted_release.status_text,
                            'status_color': inserted_release.status_color,
                            'has_download_links': inserted_release.has_download_links,
                            'image_count': inserted_release.image_count,
                            'magnet_link': inserted_release.magnet_link,
                            'cover_image_url': inserted_release.cover_image_url,
                            'screenshot_urls': inserted_release.screenshot_urls
                        }
                        
                        # Emit event to all connected clients
                        socketio.emit('new_release_added', {
                            'success': True,
                            'release': release_data,
                            'total_releases': len(db_manager.get_all_releases())
                        })
                        logger.info(f"📡 WebSocket event emitted for new release: {inserted_release.title}")
                except Exception as e:
                    logger.warning(f"⚠️ Error emitting WebSocket event: {e}")
                
                update_sync_progress('processing', f'New release added: {release.title}', 
                                   new_releases=new_releases, updated_releases=updated_releases,
                                   skipped_releases=skipped_releases)
                return True
            else:
                logger.error(f"❌ Error inserting release: {release.title}")
                return False
        
        # Set callbacks in the scraper
        logger.info("🔧 Setting callbacks in scraper...")
        scraper.set_progress_callback(update_sync_progress)
        scraper.set_insert_callback(insert_release_callback)
        scraper.set_url_check_callback(url_exists_callback)  # Set the URL check callback
        logger.info("✅ Callbacks set")
        
        # Determine if it's first time or incremental synchronization
        is_first_sync = len(existing_releases) == 0 or settings_manager.settings.last_sync_check is None
        logger.info(f"🆕 First synchronization: {is_first_sync}")
        
        if is_first_sync:
            logger.info("📥 Starting first synchronization (100 pages)...")
            update_sync_progress('scraping', 'First synchronization - downloading 100 pages (1337x maximum)...', total_pages=100)
            # For first synchronization, download 100 pages (1337x maximum)
            releases = scraper.get_releases_from_pages(1, 100)
        else:
            logger.info("🔄 Starting incremental synchronization (100 pages)...")
            update_sync_progress('scraping', 'Incremental synchronization - downloading first 100 pages...', total_pages=2)
            # For incremental synchronization, download only 100 pages
            releases = scraper.get_releases_from_pages(1, 100)
        
        # Verify what was obtained from the scraper
        logger.info(f"🔍 Scraper returned {len(releases)} releases")
        if not releases:
            logger.warning("⚠️ No releases were obtained from the scraper")
            update_sync_progress('completed', 'No new releases found')
            return
        
        # Update last synchronization timestamp
        settings_manager.settings.last_sync_check = datetime.now()
        settings_manager.save_settings()
        
        # Complete synchronization
        update_sync_progress('completed', f'Synchronization completed: {new_releases} new, {updated_releases} updated, {skipped_releases} skipped', 
                           new_releases=new_releases, updated_releases=updated_releases, skipped_releases=skipped_releases)
        
        # Close Selenium
        try:
            scraper.close()
        except Exception as e:
            logger.warning(f"⚠️ Error closing Selenium: {e}")
        
        logger.info(f"✅ Synchronization completed: {new_releases} new, {updated_releases} updated, {skipped_releases} skipped")
        
    except Exception as e:
        logger.error(f"❌ Synchronization error: {e}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        update_sync_progress('error', f'Synchronization error: {str(e)}')
        
        # Close Selenium in case of error too
        try:
            if 'scraper' in locals():
                logger.info("🔒 Closing Selenium after error...")
                scraper.close()
        except Exception as selenium_error:
            logger.warning(f"⚠️ Error closing Selenium after error: {selenium_error}")
        
    finally:
        sync_in_progress = False
        logger.info("🏁 Synchronization worker finished")

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/releases')
def get_releases():
    """API to get releases with filters"""
    try:
        # Verify that components are initialized
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database not initialized'
            }), 500
        
        # Request parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        search = request.args.get('search', '')
        status = request.args.get('status', '')
        sort_by = request.args.get('sort', 'date_desc')  # New parameter for sorting
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get ALL releases first (without pagination)
        all_releases = db_manager.get_all_releases(sort_by=sort_by)
        
        # Apply filters BEFORE pagination
        filtered_releases = all_releases
        
        if search:
            filtered_releases = [r for r in filtered_releases if search.lower() in r.title.lower()]
        
        if status:
            try:
                status_filter = ReleaseStatus[status.upper()]
                filtered_releases = [r for r in filtered_releases if r.status == status_filter]
            except KeyError:
                pass
        
        # Apply pagination AFTER filtering
        start_index = offset
        end_index = start_index + limit
        releases = filtered_releases[start_index:end_index]
        
        # Convert to JSON
        releases_data = []
        for release in releases:
            releases_data.append({
                'id': release.id,
                'url': release.url,
                'title': release.title,
                'description': release.description,  # Use full description instead of short
                'short_description': release.short_description,  # Keep short for backwards compatibility
                'publish_date': release.formatted_date,
                'game_release_date': release.formatted_game_release_date,
                'size': release.size,
                'status': release.status.name,
                'status_text': release.status_text,
                'status_color': release.status_color,
                'has_download_links': release.has_download_links,
                'image_count': release.image_count,
                'magnet_link': release.magnet_link,
                'cover_image_url': release.cover_image_url,
                'screenshot_urls': release.screenshot_urls
            })
        
        # Get statistics
        total_filtered_releases = len(filtered_releases)
        total_all_releases = len(all_releases)
        
        return jsonify({
            'success': True,
            'releases': releases_data,
            'total': total_all_releases,
            'filtered_total': total_filtered_releases,
            'page': page,
            'limit': limit,
            'has_more': len(filtered_releases) > end_index
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting releases: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/statistics')
def get_statistics():
    """API to get statistics"""
    try:
        # Verify that components are initialized
        if not db_manager or not settings_manager:
            return jsonify({
                'success': False,
                'error': 'Components not initialized'
            }), 500
        
        stats = db_manager.get_statistics()
        
        # Get releases by status
        all_releases = db_manager.get_all_releases()
        status_counts = {}
        for status in ReleaseStatus:
            status_counts[status.name] = len([r for r in all_releases if r.status == status])
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_releases': stats['total_releases'],
                'new_releases': stats['new_releases'],
                'downloaded_releases': stats['downloaded_releases'],
                'ignored_releases': stats['ignored_releases'],
                'status_counts': status_counts,
                'last_sync': settings_manager.settings.last_sync_check.isoformat() if settings_manager.settings.last_sync_check else None
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/config')
def get_config():
    """API to get configuration information"""
    try:
        # Verify that settings_manager is initialized
        if not settings_manager:
            return jsonify({
                'success': False,
                'error': 'Settings manager not initialized'
            }), 500
        
        # Get public configurations (non-sensitive)
        config_info = {
            'version': getattr(settings_manager.settings, 'version', '1.0.0'),
            'debug_mode': settings_manager.settings.debug_mode,
            'web_port': settings_manager.settings.web_port,
            'max_concurrent_requests': settings_manager.settings.max_concurrent_requests,
    
            'timeout': settings_manager.settings.timeout,
    
            'last_sync_check': settings_manager.settings.last_sync_check.isoformat() if settings_manager.settings.last_sync_check else None,
            'last_update_check': settings_manager.settings.last_update_check.isoformat() if settings_manager.settings.last_update_check else None
        }
        
        return jsonify({
            'success': True,
            'config': config_info
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting configuration: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync', methods=['POST'])
def sync_releases():
    """API para sincronizar releases"""
    try:
        logger.info("🔄 Synchronization endpoint called")
        
        # Verify that components are initialized
        if not db_manager:
            logger.error("❌ db_manager not initialized")
            return jsonify({
                'success': False,
                'error': 'Database not initialized'
            }), 500
            
        if not settings_manager:
            logger.error("❌ settings_manager not initialized")
            return jsonify({
                'success': False,
                'error': 'Configuration manager not initialized'
            }), 500
            
        if not scraper:
            logger.error("❌ scraper not initialized")
            return jsonify({
                'success': False,
                'error': 'Scraper not initialized'
            }), 500
        
        # Check if synchronization is already in progress
        if sync_in_progress:
            logger.warning("⚠️ Synchronization already in progress")
            return jsonify({
                'success': False,
                'error': 'Synchronization already in progress'
            }), 400
        
        # Start background synchronization
        logger.info("🔄 Starting release synchronization in background")
        
        # Create thread for synchronization
        sync_thread = threading.Thread(target=sync_releases_worker)
        sync_thread.daemon = True
        sync_thread.start()
        
        logger.info("✅ Synchronization thread started successfully")
        
        return jsonify({
            'success': True,
            'message': 'Synchronization started in background',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error starting synchronization: {e}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync/status')
def get_sync_status():
    """API to get synchronization status"""
    try:
        return jsonify({
            'success': True,
            'sync_in_progress': sync_in_progress,
            'progress': sync_progress
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting synchronization status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/update_status', methods=['POST'])
def update_release_status_simple():
    """API to update the status of a release (simple format)"""
    try:
        # Verify that components are initialized
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database not initialized'
            }), 500
        
        data = request.get_json()
        release_id = data.get('release_id')
        new_status = data.get('status')
        
        if not release_id or not new_status:
            return jsonify({
                'success': False,
                'error': 'Release ID and status required'
            }), 400
        
        try:
            status = ReleaseStatus[new_status.upper()]
        except KeyError:
            return jsonify({
                'success': False,
                'error': 'Invalid status'
            }), 400
        
        # Update status
        success = db_manager.update_release_status(release_id, status)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Status updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not update status'
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Error updating status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/releases/<int:release_id>/status', methods=['PUT'])
def update_release_status(release_id):
    """API to update the status of a release"""
    try:
        # Verify that components are initialized
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database not initialized'
            }), 500
        
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({
                'success': False,
                'error': 'Status not specified'
            }), 400
        
        try:
            status = ReleaseStatus[new_status.upper()]
        except KeyError:
            return jsonify({
                'success': False,
                'error': 'Invalid status'
            }), 400
        
        # Update status
        success = db_manager.update_release_status(release_id, status)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Status updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not update status'
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Error updating status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search')
def search_releases():
    """API to search releases"""
    try:
        # Verify that components are initialized
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database not initialized'
            }), 500
        
        query = request.args.get('q', '')
        limit = request.args.get('limit', 20, type=int)
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query required'
            }), 400
        
        # Search releases
        releases = db_manager.search_releases(query, limit=limit)
        
        # Convert to JSON
        releases_data = []
        for release in releases:
            releases_data.append({
                'id': release.id,
                'url': release.url,
                'title': release.title,
                'description': release.description,  # Use full description instead of short
                'short_description': release.short_description,  # Keep short for backwards compatibility
                'publish_date': release.formatted_date,
                'size': release.size,
                'status': release.status.name,
                'status_text': release.status_text,
                'status_color': release.status_color,
                'has_download_links': release.has_download_links
            })
        
        return jsonify({
            'success': True,
            'releases': releases_data,
            'total': len(releases_data)
        })
        
    except Exception as e:
        logger.error(f"❌ Error in search: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/releases/<int:release_id>', methods=['DELETE'])
def delete_release(release_id):
    """API to delete a specific release"""
    try:
        # Verify that components are initialized
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database not initialized'
            }), 500
        
        # Delete release
        success = db_manager.delete_release(release_id)
        
        if success:
            logger.info(f"✅ Release deleted: {release_id}")
            return jsonify({
                'success': True,
                'message': 'Release deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Release not found or could not be deleted'
            }), 404
        
    except Exception as e:
        logger.error(f"❌ Error deleting release: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/releases/clear', methods=['POST'])
def clear_all_releases():
    """API to clear the entire database"""
    try:
        # Verify that components are initialized
        if not db_manager:
            return jsonify({
                'success': False,
                'error': 'Database not initialized'
            }), 500
        
        # Get user confirmation (optional, but recommended)
        data = request.get_json() or {}
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                'success': False,
                'error': 'Confirmation required to clear all releases'
            }), 400
        
        # Clear all releases
        success = db_manager.clear_all_releases()
        
        if success:
            logger.info("✅ All releases cleared from database")
            return jsonify({
                'success': True,
                'message': 'All releases cleared successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not clear releases'
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Error clearing all releases: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/releases/<int:release_id>/sync', methods=['POST'])
def sync_single_release(release_id):
    """Sync a single release by re-scraping its URL"""
    global db_manager, scraper
    
    try:
        logger.info(f"🔄 Sync request received for release ID: {release_id}")
        logger.info(f"🔍 Release ID type: {type(release_id)}")
        
        if not db_manager or not scraper:
            logger.error("❌ Database manager or scraper not initialized")
            return jsonify({'success': False, 'error': 'Database manager or scraper not initialized'}), 500
        
        # Get the existing release
        existing_release = db_manager.get_release_by_id(release_id)
        if not existing_release:
            logger.error(f"❌ Release not found for ID: {release_id}")
            return jsonify({'success': False, 'error': 'Release not found'}), 404
        
        logger.info(f"🔄 Syncing single release: {existing_release.title} (ID: {release_id})")
        logger.info(f"🔗 URL to scrape: {existing_release.url}")
        
        # Re-scrape the release URL
        logger.info("🌐 Starting re-scraping process...")
        updated_release = scraper._extract_release_details(existing_release.url)
        
        if not updated_release:
            logger.error("❌ Failed to re-scrape release data")
            return jsonify({'success': False, 'error': 'Failed to re-scrape release data'}), 500
        
        logger.info(f"✅ Re-scraping successful: {updated_release.title}")
        
        # Update the release with new data while preserving the ID and status
        updated_release.id = release_id
        updated_release.status = existing_release.status  # Preserve current status
        
        logger.info(f"📝 Updating release in database...")
        # Update in database using ID
        success = db_manager.update_release_by_id(release_id, updated_release)
        
        if success:
            logger.info(f"✅ Successfully synced release: {updated_release.title}")
            
            # Get the updated release with all fields
            final_release = db_manager.get_release_by_id(release_id)
            logger.info(f"🔍 Final release retrieved: {final_release is not None}")
            
            if final_release:
                try:
                    release_dict = final_release.to_dict()
                    logger.info(f"✅ Release converted to dict successfully")
                    logger.info(f"📋 Dict keys: {list(release_dict.keys())}")
                    
                    return jsonify({
                        'success': True,
                        'message': f'Release synced successfully: {updated_release.title}',
                        'release': release_dict
                    })
                except Exception as dict_error:
                    logger.error(f"❌ Error converting release to dict: {dict_error}")
                    return jsonify({'success': False, 'error': f'Error serializing release: {str(dict_error)}'}), 500
            else:
                logger.error("❌ Final release is None after update")
                return jsonify({'success': False, 'error': 'Release not found after update'}), 500
        else:
            logger.error("❌ Failed to update release in database")
            return jsonify({'success': False, 'error': 'Failed to update release in database'}), 500
        
    except Exception as e:
        logger.error(f"❌ Error syncing single release: {e}")
        logger.error(f"❌ Error details: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    # Initialize components
    if not initialize_components():
        logger.error("❌ Could not initialize components")
        sys.exit(1)
    
    # Configure the server using settings
    host = settings_manager.settings.web_host
    port = settings_manager.settings.web_port
    debug = settings_manager.settings.debug_mode
    
    logger.info(f"🚀 Starting Flask server at http://{host}:{port}")
    logger.info(f"📦 Releases in DB: {len(db_manager.get_all_releases())}")
    
    # Start server
    app.run(host=host, port=port, debug=debug) 