// API Configuration
const API_BASE_URL = 'http://localhost:8000/api';

// DOM Elements
const phase1Section = document.getElementById('phase1');
const phase2Section = document.getElementById('phase2');
const apiStatus = document.getElementById('apiStatus');
const loadingModal = document.getElementById('loadingModal');
const loadingText = document.getElementById('loadingText');

// State Management
let currentEvents = [];
let currentAttendees = [];

// Initialize the application - ZERO AUTO API CALLS
document.addEventListener('DOMContentLoaded', function() {
    initializeDates();
    setupEventListeners();
    updateAPIStatus('ready');
});

function initializeDates() {
    const today = new Date();
    const nextMonth = new Date(today);
    nextMonth.setMonth(today.getMonth() + 1);
    
    document.getElementById('startDate').value = today.toISOString().split('T')[0];
    document.getElementById('endDate').value = nextMonth.toISOString().split('T')[0];
}

function setupEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetPhase = this.getAttribute('href').substring(1);
            switchPhase(targetPhase);
        });
    });

    // Manual event input sync with dropdown
    document.getElementById('manualEvent').addEventListener('input', function() {
        if (this.value.trim()) {
            document.getElementById('eventSelect').value = '';
        }
    });

    document.getElementById('eventSelect').addEventListener('change', function() {
        if (this.value) {
            document.getElementById('manualEvent').value = '';
        }
    });

    // Real-time validation
    document.getElementById('maxEvents').addEventListener('input', function() {
        const value = parseInt(this.value);
        if (value > 20) this.value = 20;
        if (value < 1) this.value = 1;
    });

    document.getElementById('maxAttendees').addEventListener('input', function() {
        const value = parseInt(this.value);
        if (value > 30) this.value = 30;
        if (value < 1) this.value = 1;
    });
}

function updateAPIStatus(status) {
    const statusConfig = {
        'ready': {
            icon: 'fa-check-circle',
            text: 'READY - Click buttons to make API calls',
            bgColor: 'rgba(34, 197, 94, 0.2)',
            textColor: '#16a34a'
        },
        'loading': {
            icon: 'fa-spinner fa-spin',
            text: 'Making API calls...',
            bgColor: 'rgba(245, 158, 11, 0.2)',
            textColor: '#d97706'
        },
        'success': {
            icon: 'fa-check-circle',
            text: 'API calls completed successfully',
            bgColor: 'rgba(34, 197, 94, 0.2)',
            textColor: '#16a34a'
        },
        'error': {
            icon: 'fa-exclamation-circle',
            text: 'API call failed - check console',
            bgColor: 'rgba(239, 68, 68, 0.2)',
            textColor: '#dc2626'
        }
    };

    const config = statusConfig[status];
    apiStatus.innerHTML = `<i class="fas ${config.icon}"></i> ${config.text}`;
    apiStatus.style.background = config.bgColor;
    apiStatus.style.color = config.textColor;
}

function switchPhase(phase) {
    // Update navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    document.querySelector(`.nav-link[href="#${phase}"]`).classList.add('active');

    // Update sections
    document.querySelectorAll('.phase-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(phase).classList.add('active');

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==================== PHASE 1: EVENT DISCOVERY ====================

async function discoverEvents() {
    const location = document.getElementById('location').value.trim();
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const maxResults = parseInt(document.getElementById('maxEvents').value);
    
    if (!location) {
        showAlert('Please enter a location', 'error');
        return;
    }

    const categories = Array.from(document.querySelectorAll('.category-checkbox input:checked'))
        .map(checkbox => checkbox.value);

    if (categories.length === 0) {
        showAlert('Please select at least one category', 'error');
        return;
    }

    updateAPIStatus('loading');
    showLoading(`Discovering ${maxResults} events in ${location}...`);

    try {
        const response = await fetch(`${API_BASE_URL}/discover-events`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                location,
                start_date: startDate,
                end_date: endDate,
                categories,
                max_results: maxResults
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success) {
            updateAPIStatus('success');
            currentEvents = result.events || [];
            displayEvents(currentEvents, result);
            updateEventDropdown(currentEvents);
            
            if (currentEvents.length > 0) {
                showAlert(`🎉 Found ${result.total_events} events! API calls used: ${result.api_calls_used}`, 'success');
            } else {
                showAlert('No events found for your search criteria', 'warning');
            }
        } else {
            throw new Error(result.error || 'Failed to discover events');
        }
    } catch (error) {
        updateAPIStatus('error');
        showAlert('Error discovering events: ' + error.message, 'error');
        console.error('Event discovery error:', error);
    } finally {
        hideLoading();
    }
}

function displayEvents(events, metadata) {
    const resultsSection = document.getElementById('eventsResults');
    const statsElement = document.getElementById('eventsStats');
    const tableBody = document.getElementById('eventsTableBody');

    // Update stats with API usage info
    statsElement.innerHTML = `
        <span>Found: ${metadata.total_events || 0}</span>
        <span>Requested: ${metadata.requested_limit || 0}</span>
        <span>API Calls: ${metadata.api_calls_used || 0}</span>
        <span>Location: ${metadata.location || 'Unknown'}</span>
    `;

    // Clear existing rows
    tableBody.innerHTML = '';

    if (events.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = `<td colspan="6" class="no-results">No events found. Try different dates or location.</td>`;
        tableBody.appendChild(row);
    } else {
        // Add new rows
        events.forEach((event, index) => {
            const row = document.createElement('tr');
            
            const categoryEmoji = getCategoryEmoji(event.category);
            const confidenceColor = getConfidenceColor(event.confidence_score);
            const confidencePercent = Math.round((event.confidence_score || 0.5) * 100);

            row.innerHTML = `
                <td><strong>${event.event_name || 'Unknown Event'}</strong></td>
                <td>${event.exact_date || 'Date not specified'}</td>
                <td>${event.exact_venue || event.location || 'Venue not specified'}</td>
                <td><span class="category-badge">${categoryEmoji} ${event.category || 'other'}</span></td>
                <td>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${confidencePercent}%; background: ${confidenceColor}"></div>
                        <span class="confidence-text">${confidencePercent}%</span>
                    </div>
                </td>
                <td>
                    <button class="btn-secondary" onclick="analyzeAttendees('${(event.event_name || '').replace(/'/g, "\\'")}', ${index})">
                        <i class="fas fa-users"></i> Analyze
                    </button>
                </td>
            `;
            
            tableBody.appendChild(row);
        });
    }

    // Show results section with animation
    resultsSection.classList.remove('hidden');
    setTimeout(() => {
        resultsSection.style.opacity = '1';
        resultsSection.style.transform = 'translateY(0)';
    }, 100);
}

function updateEventDropdown(events) {
    const eventSelect = document.getElementById('eventSelect');
    
    // Clear existing options except the first one
    while (eventSelect.children.length > 1) {
        eventSelect.removeChild(eventSelect.lastChild);
    }
    
    // Add new events
    events.forEach(event => {
        const option = document.createElement('option');
        option.value = event.event_name;
        option.textContent = `${event.event_name} (${event.exact_date})`;
        eventSelect.appendChild(option);
    });
}

// ==================== PHASE 2: ATTENDEE DISCOVERY ====================

async function discoverAttendees() {
    const eventSelect = document.getElementById('eventSelect');
    const manualEvent = document.getElementById('manualEvent').value.trim();
    const maxResults = parseInt(document.getElementById('maxAttendees').value);

    let eventName = '';
    
    if (eventSelect.value) {
        eventName = eventSelect.value;
    } else if (manualEvent) {
        eventName = manualEvent;
    } else {
        showAlert('Please select an event from the dropdown or enter one manually', 'error');
        return;
    }

    if (!eventName.trim()) {
        showAlert('Please enter a valid event name', 'error');
        return;
    }

    updateAPIStatus('loading');
    showLoading(`Finding ${maxResults} attendees for "${eventName}"...`);

    try {
        const response = await fetch(`${API_BASE_URL}/discover-attendees`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                event_name: eventName,
                max_results: maxResults
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success) {
            updateAPIStatus('success');
            currentAttendees = result.attendees || [];
            displayAttendees(currentAttendees, result);
            
            if (currentAttendees.length > 0) {
                showAlert(`🎉 Found ${result.total_attendees} attendees!`, 'success');
            } else {
                showAlert('No attendees found for this event', 'warning');
            }
        } else {
            throw new Error(result.error || 'Failed to discover attendees');
        }
    } catch (error) {
        updateAPIStatus('error');
        showAlert('Error discovering attendees: ' + error.message, 'error');
        console.error('Attendee discovery error:', error);
    } finally {
        hideLoading();
    }
}

function displayAttendees(attendees, metadata) {
    const resultsSection = document.getElementById('attendeesResults');
    const statsElement = document.getElementById('attendeesStats');
    const tableBody = document.getElementById('attendeesTableBody');

    // Update stats with API usage info
    statsElement.innerHTML = `
        <span>Found: ${metadata.total_attendees || 0}</span>
        <span>Requested: ${metadata.requested_limit || 0}</span>
        <span>API Calls: ${metadata.api_calls_used || 0}</span>
        <span>Event: ${metadata.event_name || 'Unknown'}</span>
    `;

    // Clear existing rows
    tableBody.innerHTML = '';

    if (attendees.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = `<td colspan="6" class="no-results">No attendees found. Try a different event name.</td>`;
        tableBody.appendChild(row);
    } else {
        // Add new rows with SAFE property access
        attendees.forEach(attendee => {
            const row = document.createElement('tr');
            
            // SAFE property access with fallbacks
            const engagementType = attendee.engagement_type || 'general_discussion';
            const engagementEmoji = getEngagementEmoji(engagementType);
            const verifiedBadge = attendee.verified ? 
                '<i class="fas fa-check-circle verified-badge" title="Verified"></i>' : '';

            const username = attendee.username || '@unknown';
            const postContent = attendee.post_content || attendee.bio || 'No content available';
            const postDate = attendee.post_date || 'Unknown date';
            const followersCount = attendee.followers_count || attendee.user_followers || 0;
            const userProfile = attendee.user_profile || attendee.source_tweet || '#';
            const postLink = attendee.post_link || attendee.source_tweet || '#';

            row.innerHTML = `
                <td>
                    ${verifiedBadge}
                    <a href="${userProfile}" target="_blank" class="username-link">
                        ${username}
                    </a>
                </td>
                <td><span class="engagement-badge">${engagementEmoji} ${formatEngagementType(engagementType)}</span></td>
                <td title="${postContent}">
                    ${postContent.length > 60 ? postContent.substring(0, 60) + '...' : postContent}
                </td>
                <td>${postDate}</td>
                <td>${formatNumber(followersCount)}</td>
                <td>
                    <a href="${postLink}" target="_blank" class="btn-secondary">
                        <i class="fas fa-external-link-alt"></i> View
                    </a>
                </td>
            `;
            
            tableBody.appendChild(row);
        });
    }

    // Update analytics
    updateAnalytics(attendees);

    // Update user details
    updateUserDetails(attendees);

    // Show results section with animation
    resultsSection.classList.remove('hidden');
    setTimeout(() => {
        resultsSection.style.opacity = '1';
        resultsSection.style.transform = 'translateY(0)';
    }, 100);
}

function updateAnalytics(attendees) {
    const totalUsers = attendees.length;
    const verifiedUsers = attendees.filter(a => a.verified).length;
    const totalReach = attendees.reduce((sum, a) => sum + (a.followers_count || a.user_followers || 0), 0);

    document.getElementById('totalUsers').textContent = totalUsers;
    document.getElementById('verifiedUsers').textContent = verifiedUsers;
    document.getElementById('totalReach').textContent = formatNumber(totalReach);
    document.getElementById('searchStrategies').textContent = attendees.length > 0 ? 'Multiple' : 'None';
}

function updateUserDetails(attendees) {
    const container = document.getElementById('userDetailsContainer');
    container.innerHTML = '';

    if (attendees.length === 0) {
        container.innerHTML = '<div class="no-results">No attendee details available</div>';
        return;
    }

    attendees.slice(0, 6).forEach((user, index) => {
        const userCard = document.createElement('div');
        userCard.className = 'user-card';
        
        // SAFE property access
        const username = user.username || '@unknown';
        const engagementType = user.engagement_type || 'general_discussion';
        const searchQuery = user.search_query || 'N/A';
        const postContent = user.post_content || user.bio || 'No content';
        const postDate = user.post_date || 'Unknown date';
        const postLink = user.post_link || user.source_tweet || '#';
        const userProfile = user.user_profile || user.source_tweet || '#';
        const followersCount = user.followers_count || user.user_followers || 0;
        const likesCount = user.likes_count || 0;
        const retweetsCount = user.retweets_count || 0;
        
        userCard.innerHTML = `
            <div class="user-card-header" onclick="toggleUserCard(${index})">
                <div class="user-header-info">
                    <strong>${username}</strong>
                    <span class="engagement-tag">${getEngagementEmoji(engagementType)} ${formatEngagementType(engagementType)}</span>
                </div>
                <i class="fas fa-chevron-down user-card-arrow" id="arrow-${index}"></i>
            </div>
            <div class="user-card-content hidden" id="content-${index}">
                <div class="user-card-grid">
                    <div class="user-info">
                        <div class="info-item">
                            <strong>🎯 Event:</strong> ${searchQuery}
                        </div>
                        <div class="info-item">
                            <strong>📝 Post:</strong> ${postContent}
                        </div>
                        <div class="info-item">
                            <strong>📅 Date:</strong> ${postDate}
                        </div>
                        <div class="info-item">
                            <strong>🔗 Post Link:</strong> 
                            <a href="${postLink}" target="_blank">View Tweet</a>
                        </div>
                        <div class="info-item">
                            <strong>👤 Profile:</strong> 
                            <a href="${userProfile}" target="_blank">View Twitter</a>
                        </div>
                    </div>
                    <div class="user-stats">
                        <div class="stat-item">
                            <span>Verified:</span>
                            <span>${user.verified ? '✅ Yes' : '❌ No'}</span>
                        </div>
                        <div class="stat-item">
                            <span>Followers:</span>
                            <span>${formatNumber(followersCount)}</span>
                        </div>
                        <div class="stat-item">
                            <span>Likes:</span>
                            <span>${likesCount}</span>
                        </div>
                        <div class="stat-item">
                            <span>Retweets:</span>
                            <span>${retweetsCount}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        container.appendChild(userCard);
    });
}

function toggleUserCard(index) {
    const content = document.getElementById(`content-${index}`);
    const arrow = document.getElementById(`arrow-${index}`);
    
    if (content && arrow) {
        content.classList.toggle('hidden');
        arrow.classList.toggle('fa-chevron-down');
        arrow.classList.toggle('fa-chevron-up');
    }
}

// ==================== UTILITY FUNCTIONS ====================

function analyzeAttendees(eventName, eventIndex) {
    document.getElementById('eventSelect').value = eventName;
    document.getElementById('manualEvent').value = '';
    switchPhase('phase2');
    
    // Scroll to attendee section
    setTimeout(() => {
        document.getElementById('attendeesResults').scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });
    }, 300);
}

function getCategoryEmoji(category) {
    const emojis = {
        'music': '🎵',
        'sports': '⚽',
        'food': '🍕',
        'arts': '🎨',
        'business': '💼',
        'conference': '🏛️',
        'festival': '🎪',
        'comedy': '🎭',
        'family': '👨‍👩‍👧‍👦',
        'other': '📌'
    };
    return emojis[category] || '📌';
}

function getConfidenceColor(score) {
    if (score >= 0.8) return '#10b981';
    if (score >= 0.6) return '#f59e0b';
    return '#ef4444';
}

function getEngagementEmoji(engagementType) {
    const emojis = {
        'ticket_purchase': '🎫',
        'confirmed_attendance': '✅',
        'planning_to_attend': '📅',
        'excited': '🎉',
        'general_discussion': '💬'
    };
    return emojis[engagementType] || '💬';
}

function formatEngagementType(engagementType) {
    // FIXED: Safe handling of undefined/null
    if (!engagementType) return 'General Discussion';
    
    try {
        return engagementType.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    } catch (error) {
        console.warn('Error formatting engagement type:', engagementType, error);
        return 'General Discussion';
    }
}

function formatNumber(num) {
    if (!num || isNaN(num)) return '0';
    
    const number = parseInt(num);
    if (number >= 1000000) {
        return (number / 1000000).toFixed(1) + 'M';
    }
    if (number >= 1000) {
        return (number / 1000).toFixed(1) + 'K';
    }
    return number.toString();
}

function showLoading(text) {
    loadingText.textContent = text;
    loadingModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function hideLoading() {
    loadingModal.classList.add('hidden');
    document.body.style.overflow = 'auto';
}

function showAlert(message, type) {
    // Remove existing alerts
    const existingAlert = document.querySelector('.alert');
    if (existingAlert) {
        existingAlert.remove();
    }

    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    
    const icon = type === 'success' ? 'fa-check-circle' : 
                 type === 'warning' ? 'fa-exclamation-triangle' : 'fa-exclamation-circle';
    
    alert.innerHTML = `
        <div class="alert-content">
            <i class="fas ${icon}"></i>
            <span>${message}</span>
            <button onclick="this.parentElement.parentElement.remove()" class="alert-close">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;

    document.body.appendChild(alert);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alert.parentElement) {
            alert.remove();
        }
    }, 5000);
}

function exportEvents(format) {
    if (!currentEvents || currentEvents.length === 0) {
        showAlert('No events to export', 'warning');
        return;
    }

    const timestamp = new Date().toISOString().split('T')[0];
    const filename = `events_${timestamp}.${format}`;
    
    try {
        if (format === 'csv') {
            const csv = convertToCSV(currentEvents);
            downloadFile(csv, filename, 'text/csv');
        } else {
            const json = JSON.stringify(currentEvents, null, 2);
            downloadFile(json, filename, 'application/json');
        }
        
        showAlert(`✅ Events exported as ${format.toUpperCase()}`, 'success');
    } catch (error) {
        showAlert('Error exporting events: ' + error.message, 'error');
    }
}

function exportAttendees(format) {
    if (!currentAttendees || currentAttendees.length === 0) {
        showAlert('No attendees to export', 'warning');
        return;
    }

    const timestamp = new Date().toISOString().split('T')[0];
    const filename = `attendees_${timestamp}.${format}`;
    
    try {
        if (format === 'csv') {
            const csv = convertToCSV(currentAttendees);
            downloadFile(csv, filename, 'text/csv');
        } else {
            const json = JSON.stringify(currentAttendees, null, 2);
            downloadFile(json, filename, 'application/json');
        }
        
        showAlert(`✅ Attendees exported as ${format.toUpperCase()}`, 'success');
    } catch (error) {
        showAlert('Error exporting attendees: ' + error.message, 'error');
    }
}

function convertToCSV(data) {
    if (!data || data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const csvRows = [
        headers.join(','),
        ...data.map(row => 
            headers.map(header => {
                const value = row[header] === null || row[header] === undefined ? '' : row[header];
                return `"${String(value).replace(/"/g, '""')}"`;
            }).join(',')
        )
    ];
    
    return csvRows.join('\n');
}

function downloadFile(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Add enhanced CSS styles
const additionalStyles = `
    .category-badge {
        padding: 0.25rem 0.5rem;
        background: #f3f4f6;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    .confidence-bar {
        position: relative;
        background: #f3f4f6;
        border-radius: 10px;
        height: 20px;
        overflow: hidden;
        min-width: 80px;
    }
    
    .confidence-fill {
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
    }
    
    .confidence-text {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 0.75rem;
        font-weight: 600;
        color: white;
        text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    }
    
    .verified-badge {
        color: #1d9bf0;
        margin-right: 0.5rem;
    }
    
    .username-link {
        color: #1d9bf0;
        text-decoration: none;
        font-weight: 500;
    }
    
    .username-link:hover {
        text-decoration: underline;
    }
    
    .engagement-badge {
        padding: 0.25rem 0.5rem;
        background: #f3f4f6;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 500;
        white-space: nowrap;
    }
    
    .engagement-tag {
        background: #e0e7ff;
        color: #4f46e5;
        padding: 0.25rem 0.5rem;
        border-radius: 12px;
        font-size: 0.8rem;
        margin-left: 0.5rem;
        white-space: nowrap;
    }
    
    .user-card-arrow {
        transition: transform 0.3s ease;
    }
    
    .info-item {
        margin-bottom: 0.75rem;
        padding: 0.5rem;
        background: #f8fafc;
        border-radius: 6px;
        word-break: break-word;
    }
    
    .info-item:last-child {
        margin-bottom: 0;
    }
    
    .no-results {
        text-align: center;
        padding: 2rem;
        color: #6b7280;
        font-style: italic;
    }
    
    .alert {
        position: fixed;
        top: 100px;
        right: 20px;
        z-index: 10000;
        min-width: 300px;
        max-width: 500px;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        animation: slideInRight 0.3s ease;
    }
    
    .alert-success {
        background: #dcfce7;
        border: 1px solid #bbf7d0;
        color: #166534;
    }
    
    .alert-error {
        background: #fee2e2;
        border: 1px solid #fecaca;
        color: #991b1b;
    }
    
    .alert-warning {
        background: #fef3c7;
        border: 1px solid #fde68a;
        color: #92400e;
    }
    
    .alert-content {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    .alert-close {
        background: none;
        border: none;
        color: inherit;
        cursor: pointer;
        margin-left: auto;
        opacity: 0.7;
        padding: 0.25rem;
    }
    
    .alert-close:hover {
        opacity: 1;
    }
    
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .input-group input:invalid {
        border-color: #ef4444;
    }
    
    .input-group input:valid {
        border-color: #10b981;
    }
`;

// Inject additional styles
const styleSheet = document.createElement('style');
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet);