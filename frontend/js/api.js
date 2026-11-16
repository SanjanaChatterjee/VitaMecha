/**
 * VitaMecha — Centralised API Communication Layer
 * All backend communication goes through this module.
 * Uses fetch(), async/await, try/catch, timeouts, and JSON validation.
 */
const VitaAPI = (function () {
  'use strict';

  /** Internal state. */
  let _connected = false;
  let _modelLoaded = false;
  let _healthPollTimer = null;
  let _onStatusChange = null;

  // ── Helpers ──────────────────────────────────────────────────────────────

  function _baseUrl() {
    return VitaConfig.API_BASE_URL.replace(/\/+$/, '');
  }

  /**
   * Fetch with timeout wrapper.
   * @param {string} url
   * @param {RequestInit} options
   * @returns {Promise<Response>}
   */
  async function _fetchWithTimeout(url, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), VitaConfig.REQUEST_TIMEOUT_MS);
    try {
      const response = await fetch(url, { ...options, signal: controller.signal });
      return response;
    } finally {
      clearTimeout(timeout);
    }
  }

  /**
   * Make a GET request and return parsed JSON.
   * @param {string} path - API path (e.g., '/health')
   * @returns {Promise<Object>}
   */
  async function _get(path) {
    const res = await _fetchWithTimeout(`${_baseUrl()}${path}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Make a POST request with JSON body and return parsed JSON.
   * @param {string} path
   * @param {Object} body
   * @returns {Promise<Object>}
   */
  async function _post(path, body) {
    const res = await _fetchWithTimeout(`${_baseUrl()}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(body)
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const errBody = await res.json();
        detail = errBody.detail || JSON.stringify(errBody);
      } catch (_) { /* ignore */ }
      throw new Error(`HTTP ${res.status}: ${detail}`);
    }
    return res.json();
  }

  /**
   * Make a DELETE request.
   */
  async function _delete(path) {
    const res = await _fetchWithTimeout(`${_baseUrl()}${path}`, {
      method: 'DELETE',
      headers: { 'Accept': 'application/json' }
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    return res.json();
  }

  // ── Public API Methods ──────────────────────────────────────────────────

  /**
   * Check backend health and model status.
   * @returns {Promise<{status: string, model_loaded: boolean}>}
   */
  async function checkHealth() {
    try {
      const data = await _get('/health');
      _connected = true;
      _modelLoaded = !!data.model_loaded;
      _notifyStatus();
      return { connected: true, modelLoaded: _modelLoaded, data };
    } catch (err) {
      _connected = false;
      _modelLoaded = false;
      _notifyStatus();
      return { connected: false, modelLoaded: false, error: err.message };
    }
  }

  /**
   * Get system info from root endpoint.
   */
  async function getSystemInfo() {
    return _get('/');
  }

  /**
   * Fetch available machine IDs.
   * @returns {Promise<{machines: string[], note: string}>}
   */
  async function getMachines() {
    return _get('/machines');
  }

  /**
   * Submit a sensor reading for prediction.
   * Returns full prediction result: RUL, health, recommendation, SHAP features.
   * @param {Object} sensorReading - Must contain machine_id, cycle, op_setting_1-3, sensor_1-21
   * @returns {Promise<Object>} PredictResponse
   */
  async function predict(sensorReading) {
    _validateSensorReading(sensorReading);
    return _post('/predict', sensorReading);
  }

  /**
   * Submit a sensor reading for streaming (sequential inference).
   * @param {Object} sensorReading
   * @returns {Promise<Object>} PredictResponse
   */
  async function stream(sensorReading) {
    _validateSensorReading(sensorReading);
    return _post('/stream', sensorReading);
  }

  /**
   * Get SHAP explanation for a sensor reading.
   * @param {Object} sensorReading
   * @returns {Promise<Object>} ExplainResponse
   */
  async function explain(sensorReading) {
    _validateSensorReading(sensorReading);
    return _post('/explain', sensorReading);
  }

  /**
   * Get prediction history for a machine.
   * @param {string} machineId
   * @returns {Promise<{machine_id: string, n_observations: number, rul_history: number[]}>}
   */
  async function getHistory(machineId) {
    if (!machineId) throw new Error('Machine ID is required.');
    return _get(`/history/${encodeURIComponent(machineId)}`);
  }

  /**
   * Clear prediction history for a machine.
   * @param {string} machineId
   */
  async function clearHistory(machineId) {
    if (!machineId) throw new Error('Machine ID is required.');
    return _delete(`/history/${encodeURIComponent(machineId)}`);
  }

  // ── Validation ──────────────────────────────────────────────────────────

  function _validateSensorReading(reading) {
    if (!reading || typeof reading !== 'object') {
      throw new Error('Sensor reading must be an object.');
    }
    const required = ['machine_id', 'cycle', 'op_setting_1', 'op_setting_2', 'op_setting_3'];
    for (let i = 1; i <= 21; i++) required.push(`sensor_${i}`);

    const missing = required.filter(key => reading[key] === undefined || reading[key] === null);
    if (missing.length > 0) {
      throw new Error(`Missing required fields: ${missing.join(', ')}`);
    }
    if (typeof reading.machine_id !== 'string' || reading.machine_id.length === 0) {
      throw new Error('machine_id must be a non-empty string.');
    }
    if (typeof reading.cycle !== 'number' || reading.cycle < 1) {
      throw new Error('cycle must be a positive integer.');
    }
  }

  // ── Status Monitoring ───────────────────────────────────────────────────

  function _notifyStatus() {
    if (_onStatusChange) {
      _onStatusChange({ connected: _connected, modelLoaded: _modelLoaded });
    }
  }

  /**
   * Register a callback for connection status changes.
   * @param {function} callback - receives {connected, modelLoaded}
   */
  function onStatusChange(callback) {
    _onStatusChange = callback;
  }

  /**
   * Start periodic health polling.
   */
  function startHealthPolling() {
    stopHealthPolling();
    if (VitaConfig.HEALTH_POLL_INTERVAL_MS > 0) {
      checkHealth(); // immediate first check
      _healthPollTimer = setInterval(checkHealth, VitaConfig.HEALTH_POLL_INTERVAL_MS);
    }
  }

  /**
   * Stop periodic health polling.
   */
  function stopHealthPolling() {
    if (_healthPollTimer) {
      clearInterval(_healthPollTimer);
      _healthPollTimer = null;
    }
  }

  /**
   * Update the API base URL at runtime.
   * @param {string} url
   */
  function setBaseUrl(url) {
    VitaConfig.API_BASE_URL = url.replace(/\/+$/, '');
    localStorage.setItem('vitamecha_api_url', VitaConfig.API_BASE_URL);
  }

  /**
   * Get current connection state.
   */
  function isConnected() { return _connected; }
  function isModelLoaded() { return _modelLoaded; }

  // ── Public Interface ────────────────────────────────────────────────────

  return {
    checkHealth,
    getSystemInfo,
    getMachines,
    predict,
    stream,
    explain,
    getHistory,
    clearHistory,
    onStatusChange,
    startHealthPolling,
    stopHealthPolling,
    setBaseUrl,
    isConnected,
    isModelLoaded
  };
})();
