/**
 * VitaMecha — Application Configuration
 * Central configuration for API URLs and application settings.
 */
const VitaConfig = {
  /** Base URL for the FastAPI backend. Change for deployment. */
  API_BASE_URL: 'http://localhost:8000',

  /** Request timeout in milliseconds. */
  REQUEST_TIMEOUT_MS: 15000,

  /** Health check polling interval in ms (0 = disabled). */
  HEALTH_POLL_INTERVAL_MS: 30000,

  /** Maximum top SHAP features to display. */
  SHAP_TOP_N: 8,

  /** Maximum findings to show before "show more". */
  FINDINGS_INITIAL_COUNT: 5,

  /** Health thresholds (must match backend src/config.py). */
  HEALTH_THRESHOLDS: {
    HEALTHY: 80,
    WARNING: 40,
    DEGRADED: 15,
    CRITICAL: 0
  },

  /** RUL cap used by the model. */
  RUL_CAP: 125,

  /** Application version. */
  VERSION: '2.0.0'
};

// Allow runtime override from localStorage
(function () {
  const saved = localStorage.getItem('vitamecha_api_url');
  if (saved) {
    VitaConfig.API_BASE_URL = saved;
  }
})();
