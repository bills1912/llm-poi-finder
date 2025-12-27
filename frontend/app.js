/**
 * HeyPico Maps LLM - Frontend Application
 * 
 * A local LLM-powered location finder with Google Maps integration.
 */

// Configuration
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000',
    DEFAULT_CENTER: { lat: -7.7713, lng: 110.3774 }, // Yogyakarta
    DEFAULT_ZOOM: 13,
    MAP_ID: 'DEMO_MAP_ID'
};

// Application State
const state = {
    map: null,
    markers: [],
    directionsRenderer: null,
    currentPlaces: [],
    selectedPlace: null,
    userLocation: null,
    conversationHistory: [],
    mapsApiKey: null,
    isMapLoaded: false,
    mapLoadFailed: false
};

// DOM Elements
const elements = {
    chatMessages: document.getElementById('chat-messages'),
    chatForm: document.getElementById('chat-form'),
    chatInput: document.getElementById('chat-input'),
    sendBtn: document.getElementById('send-btn'),
    useLocation: document.getElementById('use-location'),
    llmStatus: document.getElementById('llm-status'),
    resultsCount: null, // Will be set after DOM load
    resultsList: null,  // Will be set after DOM load
    placeDetails: document.getElementById('place-details'),
    placeDetailsContent: document.getElementById('place-details-content'),
    loadingOverlay: document.getElementById('loading-overlay'),
    mapContainer: document.getElementById('map')
};

// ==========================================
// Initialization
// ==========================================

async function init() {
    console.log('Initializing HeyPico Maps LLM...');
    
    // Set elements that might not be available immediately
    elements.resultsCount = document.getElementById('results-count');
    elements.resultsList = document.getElementById('results-list');
    
    // Set up event listeners
    setupEventListeners();
    
    // Check LLM status
    await checkLLMStatus();
    
    // Get user location
    await getUserLocation();
    
    // Load Maps API configuration and initialize map
    await loadMapsConfig();
}

function setupEventListeners() {
    // Chat form submission
    elements.chatForm.addEventListener('submit', handleChatSubmit);
    
    // Input handling
    elements.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            // Allow form to submit naturally
        }
    });
}

// ==========================================
// API Functions
// ==========================================

async function fetchAPI(endpoint, options = {}) {
    const url = `${CONFIG.API_BASE_URL}${endpoint}`;
    
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP error ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        throw error;
    }
}

async function checkLLMStatus() {
    try {
        const result = await fetchAPI('/api/chat/health');
        
        if (result.llm_available) {
            elements.llmStatus.className = 'status-badge status-online';
            elements.llmStatus.innerHTML = `
                <span class="status-dot"></span>
                LLM Online (${result.model})
            `;
        } else {
            elements.llmStatus.className = 'status-badge status-offline';
            elements.llmStatus.innerHTML = `
                <span class="status-dot"></span>
                LLM Offline
            `;
        }
    } catch (error) {
        elements.llmStatus.className = 'status-badge status-offline';
        elements.llmStatus.innerHTML = `
            <span class="status-dot"></span>
            Connection Error
        `;
    }
}

async function loadMapsConfig() {
    try {
        const config = await fetchAPI('/api/maps/config');
        state.mapsApiKey = config.api_key;
        
        if (config.default_center) {
            CONFIG.DEFAULT_CENTER = config.default_center;
        }
        if (config.default_zoom) {
            CONFIG.DEFAULT_ZOOM = config.default_zoom;
        }
        
        // Check if API key is valid (not empty or placeholder)
        if (!state.mapsApiKey || state.mapsApiKey === '' || 
            state.mapsApiKey.includes('your_') || state.mapsApiKey.length < 20) {
            console.warn('Google Maps API key not configured properly');
            showMapPlaceholder();
            return;
        }
        
        // Load Google Maps API
        await loadGoogleMapsAPI(state.mapsApiKey);
        
    } catch (error) {
        console.error('Failed to load maps config:', error);
        showMapPlaceholder();
    }
}

function loadGoogleMapsAPI(apiKey) {
    return new Promise((resolve, reject) => {
        if (window.google && window.google.maps) {
            initMap();
            resolve();
            return;
        }
        
        // Set up error handler before loading script
        window.gm_authFailure = () => {
            console.error('Google Maps authentication failed');
            state.mapLoadFailed = true;
            showMapPlaceholder();
            reject(new Error('Google Maps authentication failed'));
        };
        
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places,geometry&callback=initMapCallback`;
        script.async = true;
        script.defer = true;
        
        window.initMapCallback = () => {
            if (!state.mapLoadFailed) {
                initMap();
                resolve();
            }
        };
        
        script.onerror = () => {
            reject(new Error('Failed to load Google Maps API'));
            showMapPlaceholder();
        };
        
        document.head.appendChild(script);
        
        // Timeout fallback
        setTimeout(() => {
            if (!state.isMapLoaded && !state.mapLoadFailed) {
                showMapPlaceholder();
            }
        }, 5000);
    });
}

function showMapPlaceholder() {
    state.mapLoadFailed = true;
    elements.mapContainer.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; 
                    height: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; text-align: center; padding: 40px;">
            <svg style="width: 80px; height: 80px; margin-bottom: 24px; opacity: 0.9;" 
                 viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" 
                      fill="currentColor"/>
                <circle cx="12" cy="9" r="2.5" fill="#667eea"/>
            </svg>
            <h2 style="font-size: 24px; margin-bottom: 12px; font-weight: 600;">Google Maps Not Configured</h2>
            <p style="font-size: 16px; opacity: 0.9; max-width: 400px; line-height: 1.6; margin-bottom: 24px;">
                To display the map, please configure your Google Maps API key in <code style="background: rgba(255,255,255,0.2); padding: 2px 6px; border-radius: 4px;">backend/.env</code>
            </p>
            <div style="background: rgba(255,255,255,0.15); padding: 20px; border-radius: 12px; text-align: left; font-size: 14px;">
                <p style="margin-bottom: 8px; font-weight: 500;">Setup Steps:</p>
                <ol style="margin: 0; padding-left: 20px; line-height: 2;">
                    <li>Go to <a href="https://console.cloud.google.com" target="_blank" style="color: #ffd700;">Google Cloud Console</a></li>
                    <li>Enable Maps JavaScript API, Places API</li>
                    <li>Create an API Key</li>
                    <li>Add key to <code style="background: rgba(255,255,255,0.2); padding: 1px 4px; border-radius: 3px;">backend/.env</code></li>
                    <li>Restart the backend server</li>
                </ol>
            </div>
            <p style="margin-top: 24px; font-size: 14px; opacity: 0.8;">
                ✓ Chat and search features still work! Results shown in the panel →
            </p>
        </div>
    `;
}

function showErrorInMap(message) {
    elements.mapContainer.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: center; height: 100%; 
                    background: #f3f4f6; color: #6b7280; text-align: center; padding: 20px;">
            <div>
                <svg style="width: 48px; height: 48px; margin-bottom: 16px; color: #9ca3af;" 
                     viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" 
                          stroke="currentColor" stroke-width="2"/>
                </svg>
                <p>${message}</p>
            </div>
        </div>
    `;
}

// ==========================================
// Map Functions
// ==========================================

function initMap() {
    const center = state.userLocation || CONFIG.DEFAULT_CENTER;
    
    try {
        state.map = new google.maps.Map(elements.mapContainer, {
            center: center,
            zoom: CONFIG.DEFAULT_ZOOM,
            mapTypeControl: true,
            mapTypeControlOptions: {
                style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
                position: google.maps.ControlPosition.TOP_RIGHT
            },
            fullscreenControl: true,
            streetViewControl: true,
            zoomControl: true
        });
        
        // Initialize directions renderer
        state.directionsRenderer = new google.maps.DirectionsRenderer({
            map: state.map,
            suppressMarkers: false,
            polylineOptions: {
                strokeColor: '#4F46E5',
                strokeWeight: 5
            }
        });
        
        // Add user location marker if available
        if (state.userLocation) {
            new google.maps.Marker({
                position: state.userLocation,
                map: state.map,
                icon: {
                    path: google.maps.SymbolPath.CIRCLE,
                    scale: 10,
                    fillColor: '#4F46E5',
                    fillOpacity: 1,
                    strokeColor: '#FFFFFF',
                    strokeWeight: 3
                },
                title: 'Your Location'
            });
        }
        
        state.isMapLoaded = true;
        console.log('Google Maps initialized successfully');
    } catch (error) {
        console.error('Failed to initialize map:', error);
        showMapPlaceholder();
    }
}

function clearMarkers() {
    state.markers.forEach(marker => marker.setMap(null));
    state.markers = [];
    
    if (state.directionsRenderer) {
        state.directionsRenderer.setDirections({ routes: [] });
    }
}

function addPlaceMarkers(places) {
    if (!state.isMapLoaded || state.mapLoadFailed) {
        console.log('Map not loaded, skipping markers');
        return;
    }
    
    clearMarkers();
    
    const bounds = new google.maps.LatLngBounds();
    
    places.forEach((place, index) => {
        if (!place.location || !place.location.lat || !place.location.lng) return;
        
        const position = {
            lat: place.location.lat,
            lng: place.location.lng
        };
        
        const marker = new google.maps.Marker({
            position: position,
            map: state.map,
            title: place.name,
            label: {
                text: String(index + 1),
                color: '#FFFFFF',
                fontSize: '12px',
                fontWeight: 'bold'
            },
            animation: google.maps.Animation.DROP
        });
        
        // Info window
        const infoWindow = new google.maps.InfoWindow({
            content: createInfoWindowContent(place)
        });
        
        marker.addListener('click', () => {
            // Close other info windows
            state.markers.forEach(m => {
                if (m.infoWindow) m.infoWindow.close();
            });
            
            infoWindow.open(state.map, marker);
            selectPlace(place);
        });
        
        marker.infoWindow = infoWindow;
        state.markers.push(marker);
        bounds.extend(position);
    });
    
    // Fit map to show all markers
    if (places.length > 0) {
        state.map.fitBounds(bounds);
        
        // Don't zoom in too much for single result
        const listener = google.maps.event.addListener(state.map, 'idle', () => {
            if (state.map.getZoom() > 16) {
                state.map.setZoom(16);
            }
            google.maps.event.removeListener(listener);
        });
    }
}

function createInfoWindowContent(place) {
    const rating = place.rating ? 
        `<div style="color: #F59E0B;">★ ${place.rating} (${place.total_ratings || 0})</div>` : '';
    
    return `
        <div style="padding: 8px; max-width: 250px;">
            <h3 style="font-size: 14px; font-weight: 600; margin-bottom: 4px;">${place.name}</h3>
            ${rating}
            <p style="font-size: 12px; color: #6B7280; margin: 4px 0;">${place.address}</p>
            <div style="margin-top: 8px;">
                <button onclick="showPlaceDetails('${place.place_id}')" 
                        style="padding: 6px 12px; background: #4F46E5; color: white; 
                               border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">
                    View Details
                </button>
                <a href="https://www.google.com/maps/dir/?api=1&destination=${place.location.lat},${place.location.lng}" 
                   target="_blank"
                   style="padding: 6px 12px; background: #10B981; color: white; 
                          border: none; border-radius: 4px; cursor: pointer; font-size: 12px;
                          text-decoration: none; display: inline-block; margin-left: 4px;">
                    Directions
                </a>
            </div>
        </div>
    `;
}

async function showDirections(destLat, destLng) {
    if (!state.userLocation) {
        alert('Please enable location to get directions');
        return;
    }
    
    // Always open in Google Maps for reliability
    const url = `https://www.google.com/maps/dir/?api=1&origin=${state.userLocation.lat},${state.userLocation.lng}&destination=${destLat},${destLng}`;
    window.open(url, '_blank');
}

// ==========================================
// Chat Functions
// ==========================================

async function handleChatSubmit(e) {
    e.preventDefault();
    
    const message = elements.chatInput.value.trim();
    if (!message) return;
    
    // Clear input and disable
    elements.chatInput.value = '';
    elements.sendBtn.disabled = true;
    
    // Add user message to chat
    addMessage('user', message);
    
    // Show loading
    showLoading(true);
    
    try {
        // Get location if enabled
        let location = null;
        if (elements.useLocation.checked && state.userLocation) {
            location = `${state.userLocation.lat},${state.userLocation.lng}`;
        }
        
        // Send to API
        const response = await fetchAPI('/api/chat', {
            method: 'POST',
            body: JSON.stringify({
                message: message,
                location: location,
                conversation_history: state.conversationHistory.slice(-10)
            })
        });
        
        // Update conversation history
        state.conversationHistory.push(
            { role: 'user', content: message },
            { role: 'assistant', content: response.message }
        );
        
        // Add assistant message
        addMessage('assistant', response.message);
        
        // Handle places if found
        if (response.has_map_results && response.places && response.places.length > 0) {
            state.currentPlaces = response.places;
            
            // Add markers to map (if map is loaded)
            if (state.isMapLoaded && !state.mapLoadFailed) {
                addPlaceMarkers(response.places);
            }
            
            // Show results panel
            showResultsPanel(response.places);
        } else {
            // Hide results if no places
            hideResultsPanel();
        }
        
    } catch (error) {
        console.error('Chat error:', error);
        addMessage('assistant', 'Sorry, I encountered an error processing your request. Please make sure the backend server is running on http://localhost:8000');
    } finally {
        showLoading(false);
        elements.sendBtn.disabled = false;
        elements.chatInput.focus();
    }
}

function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const avatar = role === 'user' ? '👤' : '🤖';
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <p>${escapeHtml(content)}</p>
        </div>
    `;
    
    elements.chatMessages.appendChild(messageDiv);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function sendSuggestion(element) {
    elements.chatInput.value = element.textContent;
    elements.chatForm.dispatchEvent(new Event('submit'));
}

// ==========================================
// Results Sidebar Functions
// ==========================================

let isSidebarVisible = true;

function toggleResultsSidebar() {
    isSidebarVisible = !isSidebarVisible;
    
    const sidebar = document.getElementById('results-sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle');
    
    if (isSidebarVisible) {
        sidebar.classList.remove('hidden');
        toggleBtn.classList.remove('sidebar-closed');
    } else {
        sidebar.classList.add('hidden');
        toggleBtn.classList.add('sidebar-closed');
    }
}

function showResultsPanel(places) {
    const sidebar = document.getElementById('results-sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle');
    const toggleBadge = document.getElementById('toggle-badge');
    
    elements.resultsCount.textContent = `${places.length} places`;
    toggleBadge.textContent = places.length;
    elements.resultsList.innerHTML = '';
    
    // Show sidebar when new results come in
    isSidebarVisible = true;
    sidebar.classList.remove('hidden');
    toggleBtn.classList.remove('sidebar-closed');
    toggleBtn.classList.add('has-results');
    
    places.forEach((place, index) => {
        const item = document.createElement('div');
        item.className = 'result-item';
        item.dataset.placeId = place.place_id;
        
        const rating = place.rating ? 
            `<span class="result-rating">★ ${place.rating}</span>` : '';
        
        item.innerHTML = `
            <div class="result-name">
                <span>${index + 1}. ${escapeHtml(place.name)}</span>
                ${rating}
            </div>
            <div class="result-address">${escapeHtml(place.address)}</div>
            <div class="result-actions">
                <button class="result-btn" onclick="showPlaceDetails('${place.place_id}')">
                    Details
                </button>
                <a class="result-btn primary" 
                   href="https://www.google.com/maps/dir/?api=1&destination=${place.location.lat},${place.location.lng}" 
                   target="_blank">
                    Directions
                </a>
            </div>
        `;
        
        item.addEventListener('click', (e) => {
            if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'A') {
                selectPlace(place);
                panToPlace(place);
            }
        });
        
        elements.resultsList.appendChild(item);
    });
    
    elements.resultsPanel.classList.add('visible');
}

function hideResultsPanel() {
    const sidebar = document.getElementById('results-sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle');
    
    sidebar.classList.add('hidden');
    toggleBtn.classList.remove('has-results');
    isSidebarVisible = false;
}

function selectPlace(place) {
    state.selectedPlace = place;
    
    // Update active state in results list
    document.querySelectorAll('.result-item').forEach(item => {
        item.classList.toggle('active', item.dataset.placeId === place.place_id);
    });
}

function panToPlace(place) {
    if (!state.map || !place.location || state.mapLoadFailed) return;
    
    state.map.panTo({
        lat: place.location.lat,
        lng: place.location.lng
    });
    state.map.setZoom(16);
    
    // Open info window for this marker
    const marker = state.markers.find(m => m.getTitle() === place.name);
    if (marker && marker.infoWindow) {
        state.markers.forEach(m => {
            if (m.infoWindow) m.infoWindow.close();
        });
        marker.infoWindow.open(state.map, marker);
    }
}

// ==========================================
// Place Details Functions
// ==========================================

async function showPlaceDetails(placeId) {
    try {
        showLoading(true);
        
        const response = await fetchAPI(`/api/maps/places/${placeId}`);
        const place = response.place;
        
        const rating = place.rating ? 
            `<span class="place-meta-item">★ ${place.rating} (${place.total_ratings || 0} reviews)</span>` : '';
        
        const priceLevel = place.price_level ? 
            `<span class="place-meta-item">${'$'.repeat(place.price_level)}</span>` : '';
        
        const website = place.website ? 
            `<a href="${place.website}" target="_blank" class="place-action-btn">Website</a>` : '';
        
        const phone = place.formatted_phone ? 
            `<a href="tel:${place.formatted_phone}" class="place-action-btn">Call</a>` : '';
        
        let hoursHtml = '';
        if (place.opening_hours && place.opening_hours.weekday_text) {
            hoursHtml = `
                <div class="place-hours">
                    <strong>Hours:</strong>
                    ${place.opening_hours.weekday_text.join('<br>')}
                </div>
            `;
        }
        
        elements.placeDetailsContent.innerHTML = `
            <h3>${escapeHtml(place.name)}</h3>
            <div class="place-meta">
                ${rating}
                ${priceLevel}
            </div>
            <p class="place-address">${escapeHtml(place.address)}</p>
            ${hoursHtml}
            <div class="place-actions">
                <a href="https://www.google.com/maps/dir/?api=1&destination=${place.location.lat},${place.location.lng}" 
                   target="_blank" 
                   class="place-action-btn primary">
                    Get Directions
                </a>
                ${website}
                ${phone}
                ${place.url ? `<a href="${place.url}" target="_blank" class="place-action-btn">View on Maps</a>` : ''}
            </div>
        `;
        
        elements.placeDetails.classList.add('visible');
        
    } catch (error) {
        console.error('Failed to load place details:', error);
        alert('Failed to load place details. Please try again.');
    } finally {
        showLoading(false);
    }
}

function closePlaceDetails() {
    elements.placeDetails.classList.remove('visible');
}

// ==========================================
// Utility Functions
// ==========================================

async function getUserLocation() {
    if (!navigator.geolocation) {
        console.log('Geolocation not supported');
        return;
    }
    
    return new Promise((resolve) => {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                state.userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                console.log('User location:', state.userLocation);
                resolve(state.userLocation);
            },
            (error) => {
                console.log('Geolocation error:', error.message);
                resolve(null);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000 // 5 minutes
            }
        );
    });
}

function showLoading(show) {
    elements.loadingOverlay.classList.toggle('visible', show);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==========================================
// Global Functions (called from HTML)
// ==========================================

window.sendSuggestion = sendSuggestion;
window.showPlaceDetails = showPlaceDetails;
window.closePlaceDetails = closePlaceDetails;
window.showDirections = showDirections;
window.toggleResultsSidebar = toggleResultsSidebar;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', init);