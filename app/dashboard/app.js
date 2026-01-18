/**
 * RiskRadar Dashboard Application
 * 
 * Loads data from JSON files and renders an interactive risk map.
 */

// ==================== CONFIGURATION ====================

const DATA_PATHS = {
    sites: 'data/sites.json',
    routes: 'data/routes.json',
    riskData: '/outputs/risk_data.json'
};

// ==================== GLOBAL STATE ====================

let map = null;
let sitesData = [];
let routesData = [];
let riskData = {};
let siteMarkers = {};
let routePolylines = {};

// Route builder state
let customRoute = [];
let customRoutePolyline = null;

// Selected route state
let selectedRouteId = null;
let activeRoutePolyline = null;

// Historical event layers
let firesLayer = null;
let quakesLayer = null;

// ==================== DATA LOADING ====================

async function loadAllData() {
    console.log('Loading data...');

    try {
        // Load all three JSON files in parallel
        const [sitesRes, routesRes, riskRes] = await Promise.all([
            fetch(DATA_PATHS.sites),
            fetch(DATA_PATHS.routes),
            fetch(DATA_PATHS.riskData)
        ]);

        if (!sitesRes.ok) throw new Error(`Failed to load sites.json: ${sitesRes.status}`);
        if (!routesRes.ok) throw new Error(`Failed to load routes.json: ${routesRes.status}`);
        if (!riskRes.ok) throw new Error(`Failed to load risk_data.json: ${riskRes.status}`);

        sitesData = await sitesRes.json();
        routesData = await routesRes.json();
        riskData = await riskRes.json();

        console.log(`Loaded ${sitesData.length} sites`);
        console.log(`Loaded ${routesData.length} routes`);
        console.log(`Loaded predictions for ${Object.keys(riskData.predictions || {}).length} sites`);

        // Update UI
        document.getElementById('loading-indicator').classList.add('hidden');
        document.getElementById('data-status').style.display = 'block';

        if (riskData.metadata && riskData.metadata.generated_at) {
            const date = new Date(riskData.metadata.generated_at);
            document.getElementById('data-timestamp').textContent = date.toLocaleString('de-DE');
        }

        return true;
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('loading-indicator').innerHTML =
            `<p style="color: red;">Fehler beim Laden: ${error.message}</p>`;
        return false;
    }
}

// ==================== RISK CALCULATIONS ====================

/**
 * Calculate aggregated route risk using probability formula.
 * Risk = 1 - product(1 - point_risks)
 */
function calculateAggregatedRisk(points) {
    if (!points || points.length === 0) return { fire: 0, quake: 0, combined: 0 };

    let fireProduct = 1;
    let quakeProduct = 1;
    let combinedProduct = 1;

    for (const point of points) {
        const prediction = riskData.predictions?.[point.name];
        if (prediction) {
            fireProduct *= (1 - prediction.fire_risk / 100);
            quakeProduct *= (1 - prediction.quake_risk / 100);
            combinedProduct *= (1 - prediction.combined / 100);
        }
    }

    return {
        fire: (1 - fireProduct) * 100,
        quake: (1 - quakeProduct) * 100,
        combined: (1 - combinedProduct) * 100
    };
}

/**
 * Get risk color based on value.
 */
function getRiskColor(risk) {
    if (risk >= 75) return '#dc3545';  // Red
    if (risk >= 50) return '#fd7e14';  // Orange
    if (risk >= 25) return '#ffc107';  // Yellow
    return '#28a745';  // Green
}

/**
 * Get risk label based on value.
 */
function getRiskLabel(risk) {
    if (risk >= 75) return 'Very High';
    if (risk >= 50) return 'High';
    if (risk >= 25) return 'Medium';
    return 'Low';
}

// ==================== MAP INITIALIZATION ====================

function initializeMap() {
    console.log('Initializing map...');

    map = L.map('map').setView([20, 0], 2);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
}

// ==================== HISTORICAL EVENT LAYERS ====================

function renderHistoricalLayers() {
    console.log('Rendering historical event layers...');

    const fires = riskData.historical_events?.fires || [];
    const quakes = riskData.historical_events?.quakes || [];

    console.log(`Historical data: ${fires.length} fires, ${quakes.length} quakes`);

    // Create fires layer group
    firesLayer = L.layerGroup();
    fires.forEach(fire => {
        if (fire.lat && fire.lon) {
            const marker = L.circleMarker([fire.lat, fire.lon], {
                radius: 4,
                color: '#ff6600',
                fillColor: '#ff6600',
                fillOpacity: 0.6,
                weight: 1
            });
            marker.bindTooltip(`🔥 Fire: ${fire.date}<br>Brightness: ${fire.brightness?.toFixed(0) || 'N/A'}`);
            firesLayer.addLayer(marker);
        }
    });

    // Create quakes layer group
    quakesLayer = L.layerGroup();
    quakes.forEach(quake => {
        if (quake.lat && quake.lon) {
            const mag = quake.mag || 0;
            const radius = Math.max(3, mag * 1.5);
            const marker = L.circleMarker([quake.lat, quake.lon], {
                radius: radius,
                color: '#9933ff',
                fillColor: '#9933ff',
                fillOpacity: 0.5,
                weight: 1
            });
            marker.bindTooltip(`🌍 Quake: M${mag.toFixed(1)}<br>${quake.date}<br>${quake.place || ''}`);
            quakesLayer.addLayer(marker);
        }
    });

    // Add layer control
    const overlayMaps = {
        "🔥 Historical Fires": firesLayer,
        "🌍 Historical Quakes": quakesLayer
    };

    L.control.layers(null, overlayMaps, {
        position: 'topright',
        collapsed: false
    }).addTo(map);

    console.log(`Added layer control: ${firesLayer.getLayers().length} fires, ${quakesLayer.getLayers().length} quakes`);
}

// ==================== SITE MARKERS ====================

function renderSiteMarkers() {
    console.log('Rendering site markers...');

    for (const site of sitesData) {
        const prediction = riskData.predictions?.[site.name];
        const combinedRisk = prediction?.combined || 0;
        const fireRisk = prediction?.fire_risk || 0;
        const quakeRisk = prediction?.quake_risk || 0;

        const color = getRiskColor(combinedRisk);

        // Create popup content
        const popupHtml = `
            <div style="width: 250px; font-family: Arial, sans-serif;">
                <h4 style="margin: 0 0 10px 0;">${site.name}</h4>
                <hr>
                <div style="margin: 5px 0;">
                    <strong>🔥 Fire Risk:</strong> ${fireRisk.toFixed(1)}%
                    <div style="background: #ffcccc; height: 8px; border-radius: 4px;">
                        <div style="background: #dc3545; height: 8px; width: ${Math.min(fireRisk, 100)}%; border-radius: 4px;"></div>
                    </div>
                </div>
                <div style="margin: 5px 0;">
                    <strong>🌍 Quake Risk:</strong> ${quakeRisk.toFixed(1)}%
                    <div style="background: #cce5ff; height: 8px; border-radius: 4px;">
                        <div style="background: #0d6efd; height: 8px; width: ${Math.min(quakeRisk, 100)}%; border-radius: 4px;"></div>
                    </div>
                </div>
                <hr>
                <div style="margin: 5px 0;">
                    <strong>⚠️ Combined:</strong> ${combinedRisk.toFixed(1)}%
                </div>
                <button onclick="addToRoute('${site.name}')"
                        style="width: 100%; margin-top: 10px; padding: 8px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9em;">
                    ➕ Zur Route hinzufügen
                </button>
            </div>
        `;

        const marker = L.circleMarker([site.lat, site.lon], {
            radius: 8,
            color: color,
            fillColor: color,
            fillOpacity: 0.7,
            weight: 2
        })
            .bindPopup(popupHtml)
            .bindTooltip(`${site.name}: ${combinedRisk.toFixed(0)}%`)
            .addTo(map);

        siteMarkers[site.name] = marker;
    }
}

// ==================== ROUTE RENDERING ====================

function renderRouteList() {
    console.log('Rendering route list...');

    const routeListEl = document.getElementById('route-list');
    let html = '';

    for (const route of routesData) {
        const aggregatedRisk = calculateAggregatedRisk(route.points);
        const color = getRiskColor(aggregatedRisk.combined);
        const label = getRiskLabel(aggregatedRisk.combined);

        // Determine icons
        const fireIcon = aggregatedRisk.fire > 25 ? '🔥' : '';
        const quakeIcon = aggregatedRisk.quake > 25 ? '🌍' : '';

        // Get start and end names
        const startName = route.points[0]?.name || '?';
        const endName = route.points[route.points.length - 1]?.name || '?';

        // Store calculated risks on the route object for later use
        route._calculatedRisk = aggregatedRisk;

        html += `
            <div class="route-item" data-route-id="${route.route_id}" style="border-left: 4px solid ${color};" onclick="selectRoute('${route.route_id}')">
                <div class="route-header">
                    <strong>Route ${route.route_id}: ${startName} - ${endName}</strong>
                    <span class="route-icons">${fireIcon}${quakeIcon}</span>
                </div>
                <div class="route-risk">
                    Risk: ${label} (${aggregatedRisk.combined.toFixed(0)}%)
                </div>
            </div>
        `;
    }

    routeListEl.innerHTML = html;
}

function selectRoute(routeId) {
    console.log('Selecting route:', routeId);

    // Remove previous polyline
    if (activeRoutePolyline) {
        map.removeLayer(activeRoutePolyline);
        activeRoutePolyline = null;
    }

    // Toggle selection
    if (selectedRouteId === routeId) {
        selectedRouteId = null;
        updateRouteItemHighlight(null);
        document.getElementById('predefined-route-summary').style.display = 'none';
        return;
    }

    selectedRouteId = routeId;
    updateRouteItemHighlight(routeId);

    // Find route
    const route = routesData.find(r => r.route_id === routeId);
    if (!route || route.points.length < 2) return;

    // Build coordinates from sites
    const coords = [];
    for (const point of route.points) {
        const site = sitesData.find(s => s.name === point.name);
        if (site) {
            coords.push([site.lat, site.lon]);
        }
    }

    if (coords.length < 2) return;

    // Draw polyline
    activeRoutePolyline = L.polyline(coords, {
        color: '#3388ff',
        weight: 4,
        opacity: 0.8
    }).addTo(map);

    // Fit bounds
    map.fitBounds(L.latLngBounds(coords), {
        padding: [50, 50],
        maxZoom: 8
    });

    // Update summary
    const risk = route._calculatedRisk || calculateAggregatedRisk(route.points);
    document.getElementById('predefined-fire').textContent = risk.fire.toFixed(1) + '%';
    document.getElementById('predefined-quake').textContent = risk.quake.toFixed(1) + '%';
    document.getElementById('predefined-risk').textContent = risk.combined.toFixed(1) + '%';
    document.getElementById('predefined-route-summary').style.display = 'block';
}

function updateRouteItemHighlight(routeId) {
    document.querySelectorAll('.route-item').forEach(item => {
        if (item.getAttribute('data-route-id') === routeId) {
            item.classList.add('selected');
        } else {
            item.classList.remove('selected');
        }
    });
}

function resetRouteSelection() {
    if (activeRoutePolyline) {
        map.removeLayer(activeRoutePolyline);
        activeRoutePolyline = null;
    }
    selectedRouteId = null;
    updateRouteItemHighlight(null);
    document.getElementById('predefined-route-summary').style.display = 'none';
}

// ==================== ROUTE BUILDER ====================

function addToRoute(siteName) {
    // Check if already in route
    if (customRoute.some(p => p.name === siteName)) {
        console.log('Site already in route:', siteName);
        return;
    }

    const site = sitesData.find(s => s.name === siteName);
    const prediction = riskData.predictions?.[siteName] || { fire_risk: 0, quake_risk: 0, combined: 0 };

    if (site) {
        customRoute.push({
            name: siteName,
            lat: site.lat,
            lon: site.lon,
            fireRisk: prediction.fire_risk,
            quakeRisk: prediction.quake_risk,
            combinedRisk: prediction.combined
        });

        renderRouteBuilder();

        // Switch to builder tab
        switchTab('build');

        // Close popup
        map.closePopup();
    }
}

function removeFromRoute(index) {
    customRoute.splice(index, 1);
    renderRouteBuilder();
}

function clearRoute() {
    if (customRoutePolyline) {
        map.removeLayer(customRoutePolyline);
        customRoutePolyline = null;
    }
    customRoute = [];
    renderRouteBuilder();
}

function renderRouteBuilder() {
    const listEl = document.getElementById('route-builder-list');
    const summaryEl = document.getElementById('route-summary');
    const hintEl = document.getElementById('builder-hint');
    const clearBtn = document.getElementById('clear-route-btn');

    if (customRoute.length === 0) {
        listEl.innerHTML = '';
        summaryEl.style.display = 'none';
        hintEl.style.display = 'block';
        clearBtn.style.display = 'none';
        return;
    }

    hintEl.style.display = 'none';
    summaryEl.style.display = 'block';
    clearBtn.style.display = 'block';

    // Render waypoint items
    let html = '';
    customRoute.forEach((point, index) => {
        html += `
            <div class="route-waypoint-item">
                <span class="waypoint-name">${index + 1}. ${point.name}</span>
                <span class="waypoint-risk">⚠️ ${point.combinedRisk.toFixed(0)}%</span>
                <span class="remove-btn" onclick="removeFromRoute(${index})">✕</span>
            </div>
        `;
    });
    listEl.innerHTML = html;

    // Calculate aggregated risks
    const risk = calculateAggregatedRisk(customRoute);

    document.getElementById('total-fire').textContent = risk.fire.toFixed(0) + '%';
    document.getElementById('total-quake').textContent = risk.quake.toFixed(0) + '%';
    document.getElementById('total-risk').textContent = risk.combined.toFixed(0) + '%';

    // Draw polyline
    drawCustomRoutePolyline();
}

function drawCustomRoutePolyline() {
    // Remove existing
    if (customRoutePolyline) {
        map.removeLayer(customRoutePolyline);
        customRoutePolyline = null;
    }

    if (customRoute.length < 2) return;

    const coords = customRoute.map(p => [p.lat, p.lon]);
    const avgRisk = customRoute.reduce((sum, p) => sum + p.combinedRisk, 0) / customRoute.length;
    const lineColor = getRiskColor(avgRisk);

    customRoutePolyline = L.polyline(coords, {
        color: lineColor,
        weight: 5,
        opacity: 0.9,
        dashArray: '10, 5'
    }).addTo(map);
}

// ==================== SEARCH & TAB FUNCTIONS ====================

function handleSearch(query, event) {
    const lowerQuery = query.toLowerCase().trim();

    if (lowerQuery.length >= 2) {
        const match = sitesData.find(site =>
            site.name.toLowerCase().includes(lowerQuery)
        );
        if (match) {
            updateLocationProfile(match.name);
        }
    }

    // On Enter, pan to location
    if (event && event.key === 'Enter' && lowerQuery.length >= 1) {
        const match = sitesData.find(site =>
            site.name.toLowerCase() === lowerQuery ||
            site.name.toLowerCase().startsWith(lowerQuery)
        );
        if (match) {
            map.flyTo([match.lat, match.lon], 6, { duration: 1.0 });
            updateLocationProfile(match.name);

            // Open popup after flying
            setTimeout(() => {
                if (siteMarkers[match.name]) {
                    siteMarkers[match.name].openPopup();
                }
            }, 1100);
        }
    }
}

function updateLocationProfile(siteName) {
    const prediction = riskData.predictions?.[siteName];
    const fireRisk = prediction?.fire_risk || 0;
    const quakeRisk = prediction?.quake_risk || 0;

    document.getElementById('profile-name').textContent = siteName;
    document.getElementById('profile-fire').textContent = fireRisk.toFixed(1) + '%';
    document.getElementById('profile-quake').textContent = quakeRisk.toFixed(1) + '%';

    document.getElementById('bar-fire').style.width = Math.min(fireRisk, 100) + '%';
    document.getElementById('bar-quake').style.width = Math.min(quakeRisk, 100) + '%';
}

function switchTab(tabId) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === 'tab-' + tabId);
    });
}

// ==================== INITIALIZATION ====================

async function init() {
    console.log('RiskRadar Dashboard initializing...');

    // Initialize map first
    initializeMap();

    // Load data
    const success = await loadAllData();

    if (success) {
        // Render everything
        renderSiteMarkers();
        renderRouteList();
        renderHistoricalLayers();

        console.log('Dashboard ready!');
    }
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', init);
