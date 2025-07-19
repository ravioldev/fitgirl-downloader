/**
 * FitGirl Updater - Web Application
 * JavaScript functionality for the frontend
 */

class FitGirlDownloader {
    constructor() {
        this.currentPage = 1;
        this.currentLimit = 50;
        this.hasMore = true;
        this.isLoading = false;
        this.currentSearch = '';
        this.currentStatus = '';
        this.currentSort = 'date_desc';
        
        // WebSocket connection
        this.socket = null;
        this.syncInProgress = false;
        
        // Screenshot navigation
        this.currentScreenshots = [];
        this.currentScreenshotIndex = 0;
        
        this.initializeWebSocket();
        this.initializeEventListeners();
        this.loadReleases();
        this.loadStatistics();
        this.loadConfig();
    }

    /**
     * Initialize WebSocket connection
     */
    initializeWebSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('🔌 WebSocket connected');
            this.socket.emit('get_sync_status');
        });
        
        this.socket.on('disconnect', () => {
            console.log('🔌 WebSocket disconnected');
        });
        
        this.socket.on('sync_progress', (progress) => {
            this.updateSyncProgress(progress);
        });
        
        // Listen for new releases added in real-time
        this.socket.on('new_release_added', (data) => {
            if (data.success && data.release) {
                this.addNewReleaseToView(data.release);
                console.log('🆕 New release added in real-time:', data.release.title);
            }
        });
    }

    /**
     * Update sync progress display
     */
    updateSyncProgress(progress) {
        const progressSection = document.getElementById('syncProgressSection');
        const progressBar = document.getElementById('syncProgressBar');
        const syncMessage = document.getElementById('syncMessage');
        const syncCurrent = document.getElementById('syncCurrent');
        const syncTotal = document.getElementById('syncTotal');
        const syncLabel = document.getElementById('syncLabel');
        const syncNewCount = document.getElementById('syncNewCount');
        const syncUpdatedCount = document.getElementById('syncUpdatedCount');
        const syncBtn = document.getElementById('syncBtn');
        
        // Update sync button state
        this.syncInProgress = progress.status !== 'idle' && progress.status !== 'completed' && progress.status !== 'error';
        syncBtn.disabled = this.syncInProgress;
        syncBtn.innerHTML = this.syncInProgress ? 
            '<i class="fas fa-spinner fa-spin"></i> Syncing...' : 
            '<i class="fas fa-sync-alt"></i> Sync';
        
        // Show/hide progress section
        if (this.syncInProgress || progress.status === 'completed' || progress.status === 'error') {
            progressSection.style.display = 'block';
        } else {
            progressSection.style.display = 'none';
            return;
        }
        
        // Update progress bar based on current phase
        let progressPercent = 0;
        let currentValue = 0;
        let totalValue = 0;
        
        if (progress.status === 'scraping') {
            // During scraping, use pages
            currentValue = progress.current_page || 0;
            totalValue = progress.total_pages || 0;
            if (totalValue > 0) {
                progressPercent = (currentValue / totalValue) * 100;
            }
        } else if (progress.status === 'processing') {
            // Durante procesamiento, usar releases
            currentValue = progress.current_release || 0;
            totalValue = progress.total_releases || 0;
            if (totalValue > 0) {
                progressPercent = (currentValue / totalValue) * 100;
            }
        } else if (progress.status === 'completed') {
            progressPercent = 100;
        }
        
        progressBar.style.width = `${progressPercent}%`;
        
        // Update text content with appropriate labels
        syncMessage.textContent = progress.message;
        
        if (progress.status === 'scraping') {
            syncCurrent.textContent = progress.current_page || 0;
            syncTotal.textContent = progress.total_pages || 0;
            syncLabel.textContent = 'pages';
            // Show found torrents if available
            if (progress.total_torrents !== undefined) {
                syncMessage.textContent += ` (${progress.total_torrents} torrents found)`;
            }
        } else if (progress.status === 'processing') {
            syncCurrent.textContent = progress.current_release || 0;
            syncTotal.textContent = progress.total_releases || 0;
            syncLabel.textContent = 'releases';
            // Show processed releases if available
            if (progress.processed_releases !== undefined) {
                syncMessage.textContent += ` (${progress.processed_releases} processed)`;
            }
        } else {
            syncCurrent.textContent = currentValue;
            syncTotal.textContent = totalValue;
            syncLabel.textContent = 'items';
        }
        
        syncNewCount.textContent = progress.new_releases || 0;
        syncUpdatedCount.textContent = progress.updated_releases || 0;
        
        // Handle completion
        if (progress.status === 'completed') {
            setTimeout(() => {
                progressSection.style.display = 'none';
                this.showToast(`Sync completed: ${progress.new_releases} new, ${progress.updated_releases} updated`, 'success');
                this.loadReleases(); // Reload releases to show new ones
                this.loadStatistics(); // Reload statistics
            }, 3000);
        }
        
        // Handle error
        if (progress.status === 'error') {
            setTimeout(() => {
                progressSection.style.display = 'none';
                this.showToast(`Sync error: ${progress.message}`, 'error');
            }, 5000);
        }
    }

    /**
     * Add a new release to the view in real-time
     */
    addNewReleaseToView(release) {
        const releasesGrid = document.getElementById('releasesGrid');
        
        // Create the new release card
        const releaseCard = this.createReleaseCard(release);
        
        // Add the new release to the beginning of the list (most recent first)
        if (releasesGrid.firstChild) {
            releasesGrid.insertBefore(releaseCard, releasesGrid.firstChild);
        } else {
            releasesGrid.appendChild(releaseCard);
        }
        
        // Show toast notification
        this.showToast(`New release added: ${release.title}`, 'success');
        
        // Update counters if they are visible
        this.updateReleaseCounters();
    }

    /**
     * Update release counters in the UI
     */
    updateReleaseCounters() {
        const releasesGrid = document.getElementById('releasesGrid');
        const totalReleases = releasesGrid.children.length;
        
        // Update counter in statistics if visible
        const totalReleasesElement = document.getElementById('totalReleases');
        if (totalReleasesElement && document.getElementById('statsSection').style.display !== 'none') {
            totalReleasesElement.textContent = totalReleases;
        }
    }

    /**
     * Initialize all event listeners
     */
    initializeEventListeners() {
        // Stats button (now in dropdown)
        document.getElementById('statsBtn').addEventListener('click', () => {
            this.closeDropdownMenu(); // Close dropdown first
            this.toggleStatsSection();
        });

        // Sync button
        document.getElementById('syncBtn').addEventListener('click', () => {
            this.syncReleases();
        });

        // Clear database button
        document.getElementById('clearDatabaseBtn').addEventListener('click', () => {
            this.closeDropdownMenu(); // Close dropdown first
            this.clearDatabase();
        });



        // Dropdown menu
        document.getElementById('menuBtn').addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdownMenu();
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            const dropdown = document.getElementById('dropdownContent');
            const menuBtn = document.getElementById('menuBtn');
            if (!menuBtn.contains(e.target) && !dropdown.contains(e.target)) {
                this.closeDropdownMenu();
            }
        });

        // Search functionality
        const searchInput = document.getElementById('searchInput');

        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });

        // Auto-search while typing with debounce
        let searchTimeout;
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.performSearch();
            }, 500); // 500ms delay
            this.toggleClearButton();
        });

        // Clear button functionality
        const clearBtn = document.getElementById('clearBtn');
        console.log('🔍 Clear button element:', clearBtn);
        
        if (clearBtn) {
            clearBtn.addEventListener('click', (e) => {
                console.log('🔘 Clear button clicked!', e);
                e.preventDefault();
                e.stopPropagation();
                this.clearSearch();
            });
            console.log('✅ Clear button event listener added');
        } else {
            console.error('❌ Clear button not found!');
        }

        // Initialize clear button state
        this.toggleClearButton();
        
        // Event delegation as backup for clear button
        document.addEventListener('click', (e) => {
            if (e.target.closest('#clearBtn')) {
                console.log('🔘 Clear button clicked via delegation!');
                this.clearSearch();
            }
        });

        // Filters
        document.getElementById('statusFilter').addEventListener('change', (e) => {
            this.currentStatus = e.target.value;
            this.resetAndReload();
        });

        document.getElementById('sortFilter').addEventListener('change', (e) => {
            this.currentSort = e.target.value;
            this.resetAndReload();
        });

        // Load more button
        document.getElementById('loadMoreBtn').addEventListener('click', () => {
            this.loadMoreReleases();
        });

        // Modal close
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal();
            }
        });

        // Modal status change
        document.getElementById('modalStatusSelect').addEventListener('change', (e) => {
            this.updateModalReleaseStatus(e.target.value);
        });

        // Modal action buttons
        document.getElementById('modalMagnetBtn').addEventListener('click', () => {
            this.openMagnetLink();
        });

        // Event delegation for dynamically created release action buttons
        document.addEventListener('click', (e) => {
            // Handle status update buttons
            if (e.target.closest('.btn-downloaded') || e.target.closest('.btn-ignore')) {
                const button = e.target.closest('.action-btn');
                if (button) {
                    const releaseId = button.dataset.releaseId;
                    const action = button.dataset.action;
                    console.log('🔘 Button clicked:', {releaseId, action, button});
                    
                    // Show immediate feedback with longer duration
                    const actionText = action === 'DOWNLOADED' ? 'Downloaded' : 'Ignored';
                    this.showToast(`⏳ Marking as ${actionText}...`, 'action', 3000);
                    
                    this.updateReleaseStatus(releaseId, action);
                }
            }
            
            // Handle magnet link buttons
            if (e.target.closest('.btn-magnet')) {
                const button = e.target.closest('.btn-magnet');
                if (button && button.dataset.magnet) {
                    // Show immediate feedback with shorter duration for magnet
                    this.showToast('🧲 Opening magnet link...', 'action', 2000);
                    this.openMagnetLink(button.dataset.magnet);
                }
            }

            // Handle delete buttons
            if (e.target.closest('.btn-delete')) {
                const button = e.target.closest('.btn-delete');
                if (button) {
                    const releaseId = button.dataset.releaseId;
                    console.log('🗑️ Delete button clicked:', {releaseId, button});
                    this.deleteRelease(releaseId);
                }
            }

            // Handle link buttons
            if (e.target.closest('.btn-link')) {
                const button = e.target.closest('.btn-link');
                if (button && button.dataset.url) {
                    console.log('🔗 Link button clicked:', {url: button.dataset.url});
                    this.openReleaseLink(button.dataset.url);
                } else {
                    console.error('❌ Link button clicked but no URL found');
                    this.showToast('❌ No URL available for this release', 'error');
                }
            }

            // Handle update buttons
            if (e.target.closest('.btn-update')) {
                const button = e.target.closest('.btn-update');
                if (button) {
                    const releaseId = button.dataset.releaseId;
                    console.log('🔄 Update button clicked:', {releaseId, button});
                    console.log('🔍 Button dataset:', button.dataset);
                    console.log('🔍 Release ID from dataset:', button.dataset.releaseId);
                    this.syncSingleRelease(releaseId);
                } else {
                    console.warn('⚠️ Update button found but no button element');
                }
            }

            // Handle description expand/collapse toggle
            if (e.target.closest('.release-description-toggle')) {
                const toggle = e.target.closest('.release-description-toggle');
                if (toggle) {
                    const releaseId = toggle.dataset.releaseId;
                    this.toggleDescription(releaseId);
                }
            }
        });
    }

    /**
     * Load releases from the API
     */
    async loadReleases() {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoading(true);

        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                limit: this.currentLimit,
                search: this.currentSearch,
                status: this.currentStatus,
                sort: this.currentSort  // Add sort parameter
            });

            const response = await fetch(`/api/releases?${params}`);
            const data = await response.json();

            if (data.success) {
                this.displayReleases(data.releases);
                this.hasMore = data.has_more;
                this.updateLoadMoreButton();
            } else {
                this.showToast('Error loading releases: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Error loading releases:', error);
            this.showToast('Connection error loading releases', 'error');
        } finally {
            this.isLoading = false;
            this.showLoading(false);
        }
    }

    /**
     * Display releases in the grid
     */
    displayReleases(releases) {
        const grid = document.getElementById('releasesGrid');
        
        if (this.currentPage === 1) {
            grid.innerHTML = '';
        }

        if (releases.length === 0 && this.currentPage === 1) {
            this.showNoResults();
            return;
        }

        this.hideNoResults();

        releases.forEach(release => {
            const card = this.createReleaseCard(release);
            grid.appendChild(card);
        });
    }

    /**
     * Create a release card element
     */
    createReleaseCard(release) {
        const card = document.createElement('div');
        card.className = 'release-card';
        card.dataset.releaseId = release.id;

        // Generate screenshots carousel
        const screenshotsHtml = this.generateScreenshotsCarousel(release);
        
        // Extract year from game release date (DD/MM/YYYY format)
        const gameYear = this.extractYearFromFormattedDate(release.game_release_date);
        


        card.innerHTML = `
            <!-- ROW 1: Cover (left) + Banner/Date/Year/Size (right, vertical) -->
            <div class="release-row-1">
                <!-- Cover on the left -->
                <div class="release-cover">
                    ${release.cover_image_url ? 
                        `<img src="${release.cover_image_url}" alt="${this.escapeHtml(release.title)}" loading="lazy">` :
                        `<div class="release-cover-placeholder">
                            <i class="fas fa-gamepad"></i>
                        </div>`
                    }
                </div>

                <!-- Vertical info on the right -->
                <div class="release-info-vertical">
                    <!-- Status banner -->
                    <span class="release-status status-${release.status.toLowerCase()}">
                        ${release.status_text}
                    </span>
                    
                    <!-- Publish date -->
                    <div class="release-info-item">
                        <i class="fas fa-calendar"></i>
                        <span>Uploaded on: <strong>${release.publish_date}</strong></span>
                    </div>
                    
                    <!-- Release year -->
                    <div class="release-info-item">
                        <i class="fas fa-gamepad"></i>
                        <span>Release Year: <strong>${gameYear}</strong></span>
                    </div>
                    
                    <!-- Size -->
                    <div class="release-info-item">
                        <i class="fas fa-hdd"></i>
                        <span>Size: <strong>${release.size || 'N/A'}</strong></span>
                    </div>
                </div>
            </div>

            <!-- Card Content -->
            <div class="release-card-content">
                <!-- ROW 2: Title + Description + Screenshots (no buttons) -->
                <div class="release-row-2">
                    <!-- Content area (title and description) -->
                    <div class="release-content-area">
                        <!-- Title -->
                        <h3 class="release-title">${this.escapeHtml(release.title)}</h3>
                        
                        <!-- Description -->
                        <div class="description-container">
                            <p class="release-description" data-release-id="${release.id}">
                                ${this.escapeHtml(release.description)}
                            </p>
                            ${this.shouldShowExpandToggle(release.description) ? `
                                <span class="release-description-toggle" data-release-id="${release.id}">
                                    <span class="toggle-text">Show more</span>
                                    <i class="fas fa-chevron-down"></i>
                                </span>
                            ` : ''}
                        </div>
                    </div>

                    <!-- Screenshots aligned to bottom -->
                    ${screenshotsHtml}
                </div>
            </div>

            <!-- Card Footer with reorganized buttons -->
            <div class="release-card-footer">
                <!-- Magnet button full width -->
                ${release.magnet_link ? `
                    <div class="release-actions-primary">
                        <button class="action-btn btn-magnet" data-magnet="${release.magnet_link}">
                            <i class="fas fa-magnet"></i> Magnet
                        </button>
                    </div>
                ` : ''}
                
                <!-- Secondary actions row -->
                <div class="release-actions-secondary">
                    <button class="action-btn btn-downloaded" data-release-id="${release.id}" data-action="DOWNLOADED">
                        <i class="fas fa-download"></i> Mark Downloaded
                    </button>
                    <button class="action-btn btn-ignore" data-release-id="${release.id}" data-action="IGNORED">
                        <i class="fas fa-times"></i> Mark Ignored
                    </button>
                    <button class="action-btn btn-link" data-url="${release.url}" title="Open release page">
                        <i class="fas fa-external-link-alt"></i>
                    </button>
                    <button class="action-btn btn-update" data-release-id="${release.id}" title="Sync release data">
                        <i class="fas fa-sync-alt"></i>
                    </button>
                    <button class="action-btn btn-delete" data-release-id="${release.id}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;

        return card;
    }

    /**
     * Generate screenshots carousel HTML
     */
    generateScreenshotsCarousel(release) {
        if (!release.screenshot_urls || release.screenshot_urls.length === 0) {
            return '';
        }

        const screenshotsHtml = release.screenshot_urls.map((url, index) => 
            `<div class="screenshot-thumb" onclick="app.openScreenshotModal('${url}', ${index}, ${JSON.stringify(release.screenshot_urls).replace(/"/g, '&quot;')})">
                <img src="${url}" alt="Screenshot" loading="lazy">
            </div>`
        ).join('');

        return `
            <div class="release-screenshots">
                <div class="screenshots-title">
                    <i class="fas fa-images"></i>
                    Screenshots (${release.screenshot_urls.length})
                </div>
                <div class="screenshots-carousel">
                    ${screenshotsHtml}
                </div>
            </div>
        `;
    }



    /**
     * Convert 240p image URL to 720p for better quality
     */
    convertImageUrlTo720p(imageUrl) {
        try {
            // Para riotpixels.net y otros, cambiar .240p.jpg a .720p.jpg
            if (imageUrl.includes('.240p.jpg')) {
                return imageUrl.replace('.240p.jpg', '.720p.jpg');
            }
            
            // Para imageban.ru, cambiar patrones de 240 a 720
            if (imageUrl.includes('imageban.ru')) {
                // Buscar patrones como /240/ o _240 o -240
                let processed = imageUrl.replace(/\/(\d{3,4})\//g, '/720/');
                processed = processed.replace(/_(\d{3,4})/g, '_720');
                processed = processed.replace(/-(\d{3,4})/g, '-720');
                return processed;
            }
            
            // Para otros dominios, mantener la URL original
            return imageUrl;
        } catch (error) {
            console.error('Error processing image URL:', error);
            return imageUrl;
        }
    }

    /**
     * Open screenshot modal with navigation
     */
    openScreenshotModal(imageUrl, currentIndex = 0, screenshotsArray = [imageUrl]) {
        // Store navigation data
        this.currentScreenshots = Array.isArray(screenshotsArray) ? screenshotsArray : [imageUrl];
        this.currentScreenshotIndex = currentIndex;
        
        let modal = document.getElementById('screenshotModal');
        
        if (!modal) {
            // Create modal if it doesn't exist
            const modalHtml = `
                <div id="screenshotModal" class="screenshot-modal" onclick="app.closeScreenshotModal()">
                    <button class="screenshot-modal-close" onclick="app.closeScreenshotModal()">
                        <i class="fas fa-times"></i>
                    </button>
                    <button class="screenshot-nav-btn screenshot-nav-prev" onclick="app.navigateScreenshot(-1); event.stopPropagation();" style="display: none;">
                        <i class="fas fa-chevron-left"></i>
                    </button>
                    <button class="screenshot-nav-btn screenshot-nav-next" onclick="app.navigateScreenshot(1); event.stopPropagation();" style="display: none;">
                        <i class="fas fa-chevron-right"></i>
                    </button>
                    <img id="screenshotModalImg" src="" alt="Screenshot" onclick="event.stopPropagation()">
                    <div class="screenshot-counter" style="display: none;">
                        <span id="screenshotCounterText">1 / 1</span>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            modal = document.getElementById('screenshotModal');
        }
        
        // Update screenshot
        this.updateScreenshotModal();
        
        // Show/hide navigation based on number of screenshots
        const hasMultiple = this.currentScreenshots.length > 1;
        document.querySelector('.screenshot-nav-prev').style.display = hasMultiple ? 'block' : 'none';
        document.querySelector('.screenshot-nav-next').style.display = hasMultiple ? 'block' : 'none';
        document.querySelector('.screenshot-counter').style.display = hasMultiple ? 'block' : 'none';
        
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        
        // Add keyboard navigation
        document.addEventListener('keydown', this.handleScreenshotModalKeydown);
    }

    /**
     * Close screenshot modal
     */
    closeScreenshotModal() {
        const modal = document.getElementById('screenshotModal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
            
            // Remove keyboard listener
            document.removeEventListener('keydown', this.handleScreenshotModalKeydown);
            
            // Clear navigation data
            this.currentScreenshots = [];
            this.currentScreenshotIndex = 0;
        }
    }

    /**
     * Update screenshot modal image and counter
     */
    updateScreenshotModal() {
        if (!this.currentScreenshots || this.currentScreenshots.length === 0) return;
        
        const imageUrl = this.currentScreenshots[this.currentScreenshotIndex];
        const highQualityUrl = this.convertImageUrlTo720p(imageUrl);
        console.log(`🖼️ Converting image: ${imageUrl} → ${highQualityUrl}`);
        
        document.getElementById('screenshotModalImg').src = highQualityUrl;
        
        // Update counter
        const counterElement = document.getElementById('screenshotCounterText');
        if (counterElement) {
            counterElement.textContent = `${this.currentScreenshotIndex + 1} / ${this.currentScreenshots.length}`;
        }
    }

    /**
     * Navigate through screenshots
     */
    navigateScreenshot(direction) {
        if (!this.currentScreenshots || this.currentScreenshots.length <= 1) return;
        
        // Calculate new index with wrapping
        this.currentScreenshotIndex += direction;
        
        if (this.currentScreenshotIndex < 0) {
            this.currentScreenshotIndex = this.currentScreenshots.length - 1;
        } else if (this.currentScreenshotIndex >= this.currentScreenshots.length) {
            this.currentScreenshotIndex = 0;
        }
        
        this.updateScreenshotModal();
    }

    /**
     * Handle keyboard events for screenshot modal
     */
    handleScreenshotModalKeydown = (event) => {
        if (event.key === 'Escape') {
            this.closeScreenshotModal();
        } else if (event.key === 'ArrowLeft') {
            event.preventDefault();
            this.navigateScreenshot(-1);
        } else if (event.key === 'ArrowRight') {
            event.preventDefault();
            this.navigateScreenshot(1);
        }
    }

    /**
     * Update release status via API
     */
    async updateReleaseStatus(releaseId, newStatus) {
        console.log('🔄 updateReleaseStatus called with:', {releaseId, newStatus, type: typeof releaseId});
        
        try {
            // Convert releaseId to integer to ensure backend compatibility
            const releaseIdInt = parseInt(releaseId, 10);
            if (isNaN(releaseIdInt)) {
                console.error('❌ Invalid releaseId:', releaseId);
                this.showToast('Error: Invalid release ID', 'error');
                return;
            }
            
            console.log('📤 Sending request to /api/update_status...');
            const response = await fetch('/api/update_status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    release_id: releaseIdInt,
                    status: newStatus
                })
            });

            console.log('📥 Response received:', response.status, response.statusText);
            const data = await response.json();
            console.log('📋 Response data:', data);

            if (data.success) {
                // Check if there are active filters that would affect what should be shown
                const hasStatusFilter = this.currentStatus && this.currentStatus !== '';
                
                if (hasStatusFilter) {
                    // If filtering by status, reload the entire view to show/hide cards appropriately
                    console.log('🔄 Status filter active, reloading view...');
                    this.resetAndReload();
                    // Show success notification after reload
                    setTimeout(() => {
                        this.showToast(`✅ Status updated to ${this.getStatusText(newStatus)}`, 'success');
                    }, 500);
                } else {
                    // No status filter, just update the card's status element
                    console.log('🎴 No status filter, updating card locally...');
                    const card = document.querySelector(`[data-release-id="${releaseId}"]`);
                    console.log('🎴 Found card for update:', card);
                    if (card) {
                        const statusElement = card.querySelector('.release-status');
                        console.log('🏷️ Found status element:', statusElement);
                        if (statusElement) {
                            statusElement.className = `release-status status-${newStatus.toLowerCase()}`;
                            statusElement.textContent = this.getStatusText(newStatus);
                            console.log('✅ Status element updated');
                        }
                    }
                    // Show immediate success notification since no reload
                    this.showToast(`✅ Status updated to ${this.getStatusText(newStatus)}`, 'success');
                }
                
                // Always update counters and statistics
                this.updateReleaseCounters();
                this.loadStatistics();
                
            } else {
                console.error('❌ API returned error:', data.error);
                this.showToast('Error updating status: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('❌ Error updating release status:', error);
            this.showToast('Connection error updating status', 'error');
        }
    }

    /**
     * Get status text in English
     */
    getStatusText(status) {
        const statusTexts = {
            'NEW': 'New',
            'DOWNLOADED': 'Downloaded',
            'IGNORED': 'Ignored'
        };
        return statusTexts[status] || status;
    }

    /**
     * Check if description should show expand toggle
     */
    shouldShowExpandToggle(description) {
        if (!description) return false;
        // Estimate if text would exceed 3 lines (approximately 180 characters)
        return description.length > 180;
    }

    /**
     * Toggle description expand/collapse
     */
    toggleDescription(releaseId) {
        const description = document.querySelector(`.release-description[data-release-id="${releaseId}"]`);
        const toggle = document.querySelector(`.release-description-toggle[data-release-id="${releaseId}"]`);
        
        if (!description || !toggle) return;

        const isExpanded = description.classList.contains('expanded');
        const toggleText = toggle.querySelector('.toggle-text');
        const toggleIcon = toggle.querySelector('i');

        if (isExpanded) {
            // Collapse
            description.classList.remove('expanded');
            toggle.classList.remove('expanded');
            toggleText.textContent = 'Show more';
            toggleIcon.className = 'fas fa-chevron-down';
        } else {
            // Expand
            description.classList.add('expanded');
            toggle.classList.add('expanded');
            toggleText.textContent = 'Show less';
            toggleIcon.className = 'fas fa-chevron-up';
        }
    }

    /**
     * Delete a specific release
     */
    async deleteRelease(releaseId) {
        // Show confirmation dialog with detailed explanation
        const confirmed = confirm('⚠️ This will delete the release from the database, but it will be downloaded again in the next sync.\n\nAre you sure you want to delete this release?');
        
        if (!confirmed) {
            return;
        }

        try {
            console.log('🗑️ Deleting release:', releaseId);
            this.showToast('⏳ Deleting release...', 'action', 3000);

            const response = await fetch(`/api/releases/${releaseId}`, {
                method: 'DELETE'
            });

            console.log('📥 Delete response received:', response.status, response.statusText);
            const data = await response.json();
            console.log('📋 Delete response data:', data);

            if (data.success) {
                this.showToast('✅ Release deleted successfully', 'success');
                // Remove the card from DOM immediately
                const card = document.querySelector(`[data-release-id="${releaseId}"]`);
                if (card) {
                    card.remove();
                }
                // Update counters and statistics
                this.updateReleaseCounters();
                this.loadStatistics();
            } else {
                console.error('❌ API returned error:', data.error);
                this.showToast('Error deleting release: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('❌ Error deleting release:', error);
            this.showToast('Connection error deleting release', 'error');
        }
    }

    /**
     * Sync a single release by re-scraping its data
     */
    async syncSingleRelease(releaseId) {
        try {
            console.log('🔄 Syncing single release:', releaseId);
            console.log('🔍 Release ID type:', typeof releaseId);
            console.log('🔍 Release ID value:', releaseId);
            
            this.showToast('⏳ Syncing release data...', 'action', 3000);

            const url = `/api/releases/${releaseId}/sync`;
            console.log('🌐 Making request to:', url);

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            console.log('📥 Sync response received:', response.status, response.statusText);
            
            if (!response.ok) {
                console.error('❌ HTTP Error:', response.status, response.statusText);
                this.showToast(`HTTP Error: ${response.status}`, 'error');
                return;
            }
            
            const data = await response.json();
            console.log('📋 Sync response data:', data);

            if (data.success) {
                this.showToast('✅ Release synced successfully', 'success');
                
                // Update the card with new data if provided
                if (data.release) {
                    const card = document.querySelector(`[data-release-id="${releaseId}"]`);
                    console.log('🔍 Found card:', card);
                    if (card) {
                        // Replace the card with updated data
                        const newCard = this.createReleaseCard(data.release);
                        card.replaceWith(newCard);
                        console.log('✅ Card updated successfully');
                    } else {
                        console.warn('⚠️ Card not found for release ID:', releaseId);
                    }
                }
                
                // Update statistics
                this.loadStatistics();
            } else {
                console.error('❌ API returned error:', data.error);
                this.showToast('Error syncing release: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('❌ Error syncing release:', error);
            console.error('❌ Error details:', error.message);
            this.showToast('Connection error syncing release', 'error');
        }
    }

    /**
     * Clear all releases from database
     */
    async clearDatabase() {
        // Show detailed confirmation dialog
        const confirmed = confirm('⚠️ CLEAR DATABASE WARNING\n\n' +
            'This action will permanently DELETE ALL releases from your database!\n\n' +
            '• All game releases will be removed\n' +
            '• All screenshots and metadata will be lost\n' +
            '• You will need to sync again to reload data\n' +
            '• This action CANNOT be undone\n\n' +
            'Are you absolutely sure you want to continue?');
        
        if (!confirmed) {
            return;
        }

        // Second confirmation for extra safety
        const secondConfirmed = confirm('🚨 FINAL CONFIRMATION\n\n' +
            'You are about to delete ALL ' + (document.querySelectorAll('.release-card').length || '2000+') + ' releases!\n\n' +
            'This will clear your entire database and cannot be reversed.\n\n' +
            'Click OK to PERMANENTLY DELETE everything, or Cancel to abort.');
        
        if (!secondConfirmed) {
            return;
        }

        try {
            console.log('🧨 Clearing all releases from database');
            this.showToast('⏳ Clearing database...', 'action', 5000);

            const response = await fetch('/api/releases/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    confirm: true
                })
            });

            console.log('📥 Clear response received:', response.status, response.statusText);
            const data = await response.json();
            console.log('📋 Clear response data:', data);

            if (data.success) {
                this.showToast('✅ Database cleared successfully', 'success');
                // Clear all releases from the display
                const releasesContainer = document.getElementById('releasesContainer');
                if (releasesContainer) {
                    releasesContainer.innerHTML = '<div class="no-releases">No releases found. Use the Sync button to fetch new releases.</div>';
                }
                // Reset pagination
                this.currentPage = 1;
                this.hasMore = false;
                // Update counters and statistics
                this.updateReleaseCounters();
                this.loadStatistics();
            } else {
                console.error('❌ API returned error:', data.error);
                this.showToast('Error clearing database: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('❌ Error clearing database:', error);
            this.showToast('Connection error clearing database', 'error');
        }
    }

    /**
     * Load more releases (pagination)
     */
    async loadMoreReleases() {
        if (this.isLoading || !this.hasMore) return;

        this.currentPage++;
        await this.loadReleases();
    }

    /**
     * Reset pagination and reload releases
     */
    resetAndReload() {
        this.currentPage = 1;
        this.hasMore = true;
        this.loadReleases();
    }

    /**
     * Perform search
     */
    performSearch() {
        const searchInput = document.getElementById('searchInput');
        this.currentSearch = searchInput.value.trim();
        this.resetAndReload();
    }

    /**
     * Clear search
     */
    clearSearch() {
        console.log('🧹 Clear search function called');
        const searchInput = document.getElementById('searchInput');
        searchInput.value = '';
        this.currentSearch = '';
        console.log('✅ Input cleared, currentSearch reset');
        this.toggleClearButton(); // Hide the clear button
        this.resetAndReload();
        console.log('✅ Search cleared and reloaded');
    }

    /**
     * Toggle clear button visibility
     */
    toggleClearButton() {
        const searchInput = document.getElementById('searchInput');
        const clearBtn = document.getElementById('clearBtn');
        
        console.log('🔍 Toggle clear button:', {
            inputValue: searchInput.value,
            hasValue: searchInput.value.trim().length > 0,
            buttonElement: clearBtn,
            currentDisplay: clearBtn.style.display
        });
        
        if (searchInput.value.trim()) {
            clearBtn.style.display = 'flex';
            console.log('✅ Clear button shown');
        } else {
            clearBtn.style.display = 'none';
            console.log('❌ Clear button hidden');
        }
    }

    /**
     * Load statistics
     */
    async loadStatistics() {
        try {
            const response = await fetch('/api/statistics');
            const data = await response.json();

            if (data.success) {
                this.updateStatistics(data.statistics);
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
        }
    }

    /**
     * Update statistics display
     */
    updateStatistics(stats) {
        document.getElementById('totalReleases').textContent = stats.total_releases;
        document.getElementById('newReleases').textContent = stats.new_releases;
        document.getElementById('downloadedReleases').textContent = stats.downloaded_releases;
        document.getElementById('ignoredReleases').textContent = stats.ignored_releases;

        if (stats.last_sync) {
            const date = new Date(stats.last_sync);
            document.getElementById('lastSync').textContent = date.toLocaleString('en-US');
        } else {
            document.getElementById('lastSync').textContent = 'Never';
        }
    }

    /**
     * Toggle statistics section visibility
     */
    toggleStatsSection() {
        const statsSection = document.getElementById('statsSection');
        const isVisible = statsSection.style.display !== 'none';
        
        statsSection.style.display = isVisible ? 'none' : 'block';
        
        if (!isVisible) {
            this.loadStatistics();
        }
    }



    /**
     * Sync releases from the server
     */
    async syncReleases() {
        if (this.syncInProgress) {
            this.showToast('A sync is already in progress', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                this.showToast('Sync started in background', 'info');
                // Progress will be shown automatically via WebSocket
            } else {
                this.showToast('Error starting sync: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Error syncing releases:', error);
            this.showToast('Connection error syncing', 'error');
        }
    }

    /**
     * Open release modal
     */
    async openReleaseModal(releaseId) {
        try {
            const response = await fetch(`/api/releases?limit=1&search=${releaseId}`);
            const data = await response.json();

            if (data.success && data.releases.length > 0) {
                const release = data.releases[0];
                this.populateModal(release);
                this.showModal();
            } else {
                this.showToast('Could not load release information', 'error');
            }
        } catch (error) {
            console.error('Error opening modal:', error);
            this.showToast('Error loading release details', 'error');
        }
    }

    /**
     * Populate modal with release data
     */
    populateModal(release) {
        document.getElementById('modalTitle').textContent = release.title;
        document.getElementById('modalPublishDate').textContent = release.publish_date;
        document.getElementById('modalGameDate').textContent = release.game_release_date;
        document.getElementById('modalSize').textContent = release.size;
        document.getElementById('modalStatus').textContent = release.status_text;
        document.getElementById('modalDescription').textContent = release.description;

        // Set status select
        const statusSelect = document.getElementById('modalStatusSelect');
        statusSelect.value = release.status;

        // Store release data for actions
        this.currentModalRelease = release;
    }

    /**
     * Show modal
     */
    showModal() {
        document.getElementById('releaseModal').style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    /**
     * Close modal
     */
    closeModal() {
        document.getElementById('releaseModal').style.display = 'none';
        document.body.style.overflow = 'auto';
        this.currentModalRelease = null;
    }

    /**
     * Update release status from modal
     */
    async updateModalReleaseStatus(newStatus) {
        if (!this.currentModalRelease) return;

        try {
            const response = await fetch(`/api/releases/${this.currentModalRelease.id}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: newStatus })
            });

            const data = await response.json();

            if (data.success) {
                this.showToast('Status updated successfully', 'success');
                this.loadStatistics();
                this.resetAndReload();
            } else {
                this.showToast('Error updating status: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Error updating status:', error);
            this.showToast('Connection error updating status', 'error');
        }
    }

    /**
     * Open magnet link
     */
    openMagnetLink(magnetLink = null) {
        const link = magnetLink || (this.currentModalRelease?.magnet_link);
        if (link) {
            window.open(link, '_blank');
        } else {
            this.showToast('No magnet link available', 'error');
        }
    }

    /**
     * Open release link in new tab
     */
    openReleaseLink(url) {
        if (url) {
            console.log('🔗 Opening URL in new tab:', url);
            window.open(url, '_blank');
            this.showToast('🔗 Opening release page...', 'info', 2000);
        } else {
            console.error('❌ No URL provided to openReleaseLink');
            this.showToast('❌ No URL available', 'error');
        }
    }

    /**
     * Open torrent link
     */
    openTorrentLink() {
        const link = this.currentModalRelease?.torrent_link;
        if (link) {
            window.open(link, '_blank');
        } else {
            this.showToast('No torrent link available', 'error');
        }
    }

    /**
     * Show/hide loading indicator
     */
    showLoading(show) {
        const indicator = document.getElementById('loadingIndicator');
        indicator.style.display = show ? 'flex' : 'none';
    }

    /**
     * Show/hide no results message
     */
    showNoResults() {
        document.getElementById('noResults').style.display = 'block';
    }

    hideNoResults() {
        document.getElementById('noResults').style.display = 'none';
    }

    /**
     * Update load more button visibility
     */
    updateLoadMoreButton() {
        const loadMoreBtn = document.getElementById('loadMoreBtn');
        loadMoreBtn.style.display = this.hasMore ? 'inline-flex' : 'none';
    }

    /**
     * Show a toast notification
     */
    showToast(message, type = 'info', duration = 5000) {
        const toast = document.getElementById('toast');
        const toastIcon = document.getElementById('toastIcon');
        const toastMessage = document.getElementById('toastMessage');

        // Clear any existing timeout
        if (this.toastTimeout) {
            clearTimeout(this.toastTimeout);
        }

        // Set icon and styling based on type
        switch (type) {
            case 'success':
                toastIcon.className = 'fas fa-check-circle';
                toast.className = 'toast toast-success';
                break;
            case 'error':
                toastIcon.className = 'fas fa-exclamation-circle';
                toast.className = 'toast toast-error';
                break;
            case 'warning':
                toastIcon.className = 'fas fa-exclamation-triangle';
                toast.className = 'toast toast-warning';
                break;
            case 'action':
                toastIcon.className = 'fas fa-clock';
                toast.className = 'toast toast-info toast-action';
                break;
            default:
                toastIcon.className = 'fas fa-info-circle';
                toast.className = 'toast toast-info';
        }

        // Set message content
        toastMessage.textContent = message;
        
        // Show toast with proper animation
        toast.style.display = 'block';
        
        // Use setTimeout to ensure display change takes effect before adding show class
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);

        // Auto hide after specified duration
        this.toastTimeout = setTimeout(() => {
            toast.classList.remove('show');
            // Hide completely after animation finishes
            setTimeout(() => {
                toast.style.display = 'none';
            }, 300); // Match CSS transition duration
        }, duration);
    }

    /**
     * Toggle dropdown menu visibility
     */
    toggleDropdownMenu() {
        const dropdown = document.getElementById('dropdownContent');
        const menuBtn = document.getElementById('menuBtn');
        dropdown.classList.toggle('show');
        menuBtn.classList.toggle('active');
    }

    /**
     * Close dropdown menu
     */
    closeDropdownMenu() {
        const dropdown = document.getElementById('dropdownContent');
        const menuBtn = document.getElementById('menuBtn');
        dropdown.classList.remove('show');
        menuBtn.classList.remove('active');
    }

    /**
     * Load configuration from API
     */
    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();
            
            if (data.success) {
                // Update version display
                const versionElement = document.getElementById('appVersion');
                if (versionElement && data.config.version) {
                    versionElement.textContent = `v${data.config.version}`;
                }
                
                console.log('⚙️ Configuration loaded:', data.config);
            } else {
                console.error('❌ Error loading config:', data.error);
            }
        } catch (error) {
            console.error('❌ Error fetching config:', error);
        }
    }

    /**
     * Extract year from formatted date string (DD/MM/YYYY format)
     */
    extractYearFromFormattedDate(dateString) {
        if (!dateString || dateString === 'No date') {
            return 'N/A';
        }
        
        // Handle DD/MM/YYYY format
        const parts = dateString.split('/');
        if (parts.length === 3) {
            const year = parts[2];
            // Validate year is a 4-digit number
            if (/^\d{4}$/.test(year)) {
                return year;
            }
        }
        
        return 'N/A';
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global functions for onclick handlers
window.app = null;

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new FitGirlDownloader();
});

// Global function for modal close
window.closeModal = function() {
    if (window.app) {
        window.app.closeModal();
    }
}; 