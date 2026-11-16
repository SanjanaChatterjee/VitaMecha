/**
 * VitaMecha — Application Controller
 * Navigation, initialisation, shared state, settings modal.
 */
const VitaApp = (function () {
  'use strict';

  // ── State ──────────────────────────────────────────────────────────────
  const state = {
    currentPage: 'problem-analysis',
    charts: {}
  };

  // ── DOM Cache ──────────────────────────────────────────────────────────
  let dom = {};

  function cacheDom() {
    dom = {
      sidebar: document.getElementById('sidebar'),
      sidebarOverlay: document.getElementById('sidebar-overlay'),
      mobileMenuBtn: document.getElementById('mobile-menu-btn'),
      navItems: document.querySelectorAll('[data-page]'),
      pageSections: document.querySelectorAll('.page-section'),
      breadcrumbCurrent: document.getElementById('breadcrumb-current'),
      // Connection status
      statusDot: document.getElementById('status-dot'),
      statusText: document.getElementById('status-text'),
      connectionBtn: document.getElementById('connection-btn'),
      // Settings modal
      settingsModal: document.getElementById('settings-modal'),
      settingsOpenBtn: document.getElementById('settings-open-btn'),
      settingsCloseBtn: document.getElementById('settings-close-btn'),
      settingsUrlInput: document.getElementById('settings-url-input'),
      settingsTestBtn: document.getElementById('settings-test-btn'),
      settingsSaveBtn: document.getElementById('settings-save-btn'),
      settingsTestResult: document.getElementById('settings-test-result')
    };
  }

  // ── Navigation ─────────────────────────────────────────────────────────
  function setupNavigation() {
    dom.navItems.forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        navigateTo(item.getAttribute('data-page'));
      });
    });
  }

  function navigateTo(pageId) {
    state.currentPage = pageId;

    // Update nav items
    dom.navItems.forEach(item => {
      item.classList.toggle('active', item.getAttribute('data-page') === pageId);
    });

    // Update page sections
    dom.pageSections.forEach(section => {
      section.classList.toggle('active', section.id === `page-${pageId}`);
    });

    // Update breadcrumb
    const pageNames = {
      'problem-analysis': 'Machine Problem Analysis',
      'fleet-overview': 'Fleet Overview',
      'live-monitoring': 'Live Monitoring',
      'research-analytics': 'Research Analytics'
    };
    dom.breadcrumbCurrent.textContent = pageNames[pageId] || pageId;

    // Close mobile sidebar
    closeSidebar();

    // Resize charts on the newly visible page
    Object.values(state.charts).forEach(chart => {
      if (chart && typeof chart.resize === 'function') {
        setTimeout(() => chart.resize(), 50);
      }
    });
  }

  // ── Mobile Sidebar ─────────────────────────────────────────────────────
  function setupMobileSidebar() {
    if (dom.mobileMenuBtn) {
      dom.mobileMenuBtn.addEventListener('click', toggleSidebar);
    }
    if (dom.sidebarOverlay) {
      dom.sidebarOverlay.addEventListener('click', closeSidebar);
    }
  }

  function toggleSidebar() {
    dom.sidebar.classList.toggle('open');
    dom.sidebarOverlay.classList.toggle('active');
  }

  function closeSidebar() {
    dom.sidebar.classList.remove('open');
    dom.sidebarOverlay.classList.remove('active');
  }

  // ── Connection Status ──────────────────────────────────────────────────
  function setupConnectionStatus() {
    VitaAPI.onStatusChange(updateConnectionUI);

    if (dom.connectionBtn) {
      dom.connectionBtn.addEventListener('click', () => {
        openSettingsModal();
      });
    }

    // Initial check
    updateConnectionUI({ connected: false, modelLoaded: false });
    dom.statusDot.className = 'status-dot checking';
    dom.statusText.textContent = 'Checking...';
    VitaAPI.startHealthPolling();
  }

  function updateConnectionUI({ connected, modelLoaded }) {
    if (connected && modelLoaded) {
      dom.statusDot.className = 'status-dot connected';
      dom.statusText.textContent = 'Connected';
    } else if (connected && !modelLoaded) {
      dom.statusDot.className = 'status-dot checking';
      dom.statusText.textContent = 'No Model';
    } else {
      dom.statusDot.className = 'status-dot disconnected';
      dom.statusText.textContent = 'Disconnected';
    }
  }

  // ── Settings Modal ─────────────────────────────────────────────────────
  function setupSettingsModal() {
    if (dom.settingsOpenBtn) {
      dom.settingsOpenBtn.addEventListener('click', openSettingsModal);
    }
    if (dom.settingsCloseBtn) {
      dom.settingsCloseBtn.addEventListener('click', closeSettingsModal);
    }
    if (dom.settingsModal) {
      dom.settingsModal.addEventListener('click', (e) => {
        if (e.target === dom.settingsModal) closeSettingsModal();
      });
    }
    if (dom.settingsTestBtn) {
      dom.settingsTestBtn.addEventListener('click', testConnection);
    }
    if (dom.settingsSaveBtn) {
      dom.settingsSaveBtn.addEventListener('click', saveSettings);
    }
  }

  function openSettingsModal() {
    dom.settingsUrlInput.value = VitaConfig.API_BASE_URL;
    dom.settingsTestResult.innerHTML = '';
    dom.settingsModal.classList.add('active');
  }

  function closeSettingsModal() {
    dom.settingsModal.classList.remove('active');
  }

  async function testConnection() {
    const url = dom.settingsUrlInput.value.trim().replace(/\/+$/, '');
    dom.settingsTestResult.innerHTML = '<span style="color: var(--accent);">Connecting...</span>';
    try {
      const res = await fetch(`${url}/health`, { method: 'GET' });
      if (res.ok) {
        const data = await res.json();
        dom.settingsTestResult.innerHTML =
          `<span style="color: var(--healthy);">✓ Connected — Model: ${data.model_loaded ? 'Loaded' : 'Not loaded'}</span>`;
      } else {
        dom.settingsTestResult.innerHTML =
          `<span style="color: var(--critical);">✗ HTTP ${res.status}</span>`;
      }
    } catch (err) {
      dom.settingsTestResult.innerHTML =
        `<span style="color: var(--critical);">✗ ${err.message}</span>`;
    }
  }

  function saveSettings() {
    const url = dom.settingsUrlInput.value.trim().replace(/\/+$/, '');
    VitaAPI.setBaseUrl(url);
    VitaAPI.checkHealth();
    closeSettingsModal();
  }

  // ── Chart Registry ─────────────────────────────────────────────────────
  function registerChart(name, chart) {
    state.charts[name] = chart;
  }

  function getChart(name) {
    return state.charts[name] || null;
  }

  // ── Initialise ─────────────────────────────────────────────────────────
  function init() {
    cacheDom();
    setupNavigation();
    setupMobileSidebar();
    setupConnectionStatus();
    setupSettingsModal();

    // Initialise page modules
    if (typeof VitaMachineSelector !== 'undefined') VitaMachineSelector.init();
    if (typeof VitaProblemAnalysis !== 'undefined') VitaProblemAnalysis.init();
    if (typeof VitaExplanation !== 'undefined') VitaExplanation.init();
    if (typeof VitaOverview !== 'undefined') VitaOverview.init();
    if (typeof VitaMonitoring !== 'undefined') VitaMonitoring.init();
    if (typeof VitaAnalytics !== 'undefined') VitaAnalytics.init();

    // Default page
    navigateTo('problem-analysis');
  }

  // ── Bootstrap ──────────────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  return {
    navigateTo,
    registerChart,
    getChart,
    state
  };
})();
