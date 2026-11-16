/**
 * VitaMecha — Machine Problem Analysis Page
 * The primary page: prediction, health display, findings, recommendation, sensor table, RUL chart.
 */
const VitaProblemAnalysis = (function () {
  'use strict';

  let _dom = {};
  let _chart = null;
  let _lastResult = null;

  function init() {
    _dom = {
      // Metrics
      rulValue: document.getElementById('pa-rul-value'),
      rulInterval: document.getElementById('pa-rul-interval'),
      healthBadge: document.getElementById('pa-health-badge'),
      healthNote: document.getElementById('pa-health-note'),
      riskValue: document.getElementById('pa-risk-value'),
      trendValue: document.getElementById('pa-trend-value'),
      latencyValue: document.getElementById('pa-latency-value'),
      // Sections
      resultsArea: document.getElementById('pa-results-area'),
      loadingState: document.getElementById('pa-loading'),
      emptyState: document.getElementById('pa-empty-state'),
      errorState: document.getElementById('pa-error-state'),
      errorMessage: document.getElementById('pa-error-message'),
      retryBtn: document.getElementById('pa-retry-btn'),
      // Findings
      findingsList: document.getElementById('pa-findings-list'),
      findingsShowMore: document.getElementById('pa-findings-show-more'),
      // Explanation
      explanationSection: document.getElementById('pa-explanation'),
      explainObserved: document.getElementById('pa-explain-observed'),
      explainMatters: document.getElementById('pa-explain-matters'),
      explainCheck: document.getElementById('pa-explain-check'),
      // Recommendation
      recPanel: document.getElementById('pa-recommendation'),
      recAction: document.getElementById('pa-rec-action'),
      recPriority: document.getElementById('pa-rec-priority'),
      recDetails: document.getElementById('pa-rec-details'),
      recSensorNote: document.getElementById('pa-rec-sensor-note'),
      recDisclaimer: document.getElementById('pa-rec-disclaimer'),
      // Sensor evidence
      sensorToggle: document.getElementById('pa-sensor-toggle'),
      sensorContent: document.getElementById('pa-sensor-content'),
      sensorBody: document.getElementById('pa-sensor-body'),
      // RUL chart
      chartCanvas: document.getElementById('chart-rul-analysis'),
      // Data quality
      dataToggle: document.getElementById('pa-data-toggle'),
      dataContent: document.getElementById('pa-data-content'),
      dataInfo: document.getElementById('pa-data-info'),
      // Demo banner
      demoBanner: document.getElementById('pa-demo-banner')
    };

    // Expandable toggles
    setupExpandable(_dom.sensorToggle, _dom.sensorContent);
    setupExpandable(_dom.dataToggle, _dom.dataContent);

    // Retry button
    if (_dom.retryBtn) {
      _dom.retryBtn.addEventListener('click', () => {
        const sel = VitaMachineSelector.getState();
        if (sel.machineId) runAnalysis(sel);
      });
    }

    // Findings "show more"
    if (_dom.findingsShowMore) {
      _dom.findingsShowMore.addEventListener('click', showAllFindings);
    }

    // Register for analyse button
    VitaMachineSelector.onSelectionChange(runAnalysis);

    // Show empty state initially
    showState('empty');
  }

  function setupExpandable(toggle, content) {
    if (!toggle || !content) return;
    toggle.addEventListener('click', () => {
      toggle.classList.toggle('expanded');
      content.classList.toggle('expanded');
    });
  }

  // ── State Display ──────────────────────────────────────────────────────
  function showState(stateName) {
    const states = ['loading', 'empty', 'error', 'results'];
    if (_dom.loadingState) _dom.loadingState.classList.toggle('hidden', stateName !== 'loading');
    if (_dom.emptyState) _dom.emptyState.classList.toggle('hidden', stateName !== 'empty');
    if (_dom.errorState) _dom.errorState.classList.toggle('hidden', stateName !== 'error');
    if (_dom.resultsArea) _dom.resultsArea.classList.toggle('hidden', stateName !== 'results');
  }

  // ── Analysis ───────────────────────────────────────────────────────────
  async function runAnalysis(selection) {
    showState('loading');
    hideDemoBanner();

    const { machineId, cycle, engineData } = selection;
    const sensorReading = VitaMachineSelector.getSensorReading(machineId, cycle);

    // Try live API first
    if (VitaAPI.isConnected() && VitaAPI.isModelLoaded() && sensorReading) {
      try {
        const result = await VitaAPI.predict(sensorReading);
        _lastResult = result;
        renderResults(result, machineId, cycle, sensorReading);
        renderRulChart(machineId, cycle);
        renderDataInfo(selection, sensorReading, 'api');
        showState('results');
        return;
      } catch (err) {
        console.warn('API prediction failed, falling back to edge data:', err.message);
      }
    }

    // Fallback to edge data
    const edgeResult = VitaMachineSelector.getEdgeResult(machineId, cycle);
    if (edgeResult) {
      const normalizedResult = normalizeEdgeResult(edgeResult, machineId, cycle);
      _lastResult = normalizedResult;
      renderResults(normalizedResult, machineId, cycle, sensorReading);
      renderRulChart(machineId, cycle);
      renderDataInfo(selection, sensorReading, 'edge');
      showDemoBanner();
      showState('results');
      return;
    }

    // No data available
    showState('error');
    if (_dom.errorMessage) {
      _dom.errorMessage.textContent =
        'No data available for this machine/cycle. Connect to the FastAPI backend or ensure telemetry data is loaded.';
    }
  }

  /**
   * Normalize edge data to match the PredictResponse schema.
   */
  function normalizeEdgeResult(obs, machineId, cycle) {
    return {
      machine_id: machineId,
      cycle: obs.cycle || cycle,
      predicted_rul: obs.predicted_rul,
      rul_lower: obs.rul_lower ?? null,
      rul_upper: obs.rul_upper ?? null,
      health_status: obs.health_status || 'HEALTHY',
      risk_level: obs.risk_level || 'Low',
      trend: obs.trend || 'Unknown',
      recommendation: obs.recommendation || {
        action: 'Connect to backend for recommendations.',
        priority: 'ROUTINE',
        details: ['Backend unavailable — showing cached data.'],
        sensor_note: '',
        disclaimer: 'Advisory guidance only.'
      },
      top_features: obs.top_features || [],
      inference_ms: obs.inference_ms || 0,
      timestamp: new Date().toISOString()
    };
  }

  // ── Render Results ─────────────────────────────────────────────────────
  function renderResults(result, machineId, cycle, sensorReading) {
    // RUL value
    if (_dom.rulValue) {
      _dom.rulValue.innerHTML =
        `${Number(result.predicted_rul).toFixed(1)} <span class="metric-unit">cycles</span>`;
    }

    // RUL interval
    if (_dom.rulInterval) {
      if (result.rul_lower != null && result.rul_upper != null) {
        _dom.rulInterval.textContent =
          `80% interval: [${Number(result.rul_lower).toFixed(1)}, ${Number(result.rul_upper).toFixed(1)}]`;
      } else {
        _dom.rulInterval.textContent = 'Point estimate';
      }
    }

    // Health badge
    const status = (result.health_status || 'HEALTHY').toUpperCase();
    if (_dom.healthBadge) {
      _dom.healthBadge.className = `badge badge-${status.toLowerCase()}`;
      _dom.healthBadge.textContent = status;
    }
    if (_dom.healthNote) {
      const thresholds = VitaConfig.HEALTH_THRESHOLDS;
      const notes = {
        'HEALTHY': `RUL > ${thresholds.HEALTHY} cycles`,
        'WARNING': `${thresholds.DEGRADED}–${thresholds.HEALTHY} cycles`,
        'DEGRADED': `${thresholds.CRITICAL}–${thresholds.WARNING} cycles`,
        'CRITICAL': `RUL < ${thresholds.DEGRADED} cycles`
      };
      _dom.healthNote.textContent = notes[status] || '';
    }

    // Risk
    if (_dom.riskValue) {
      const risk = result.risk_level || 'Low';
      _dom.riskValue.textContent = risk;
      const riskColors = { 'Low': 'var(--healthy)', 'Medium': 'var(--warning)', 'High': 'var(--degraded)', 'Critical': 'var(--critical)' };
      _dom.riskValue.style.color = riskColors[risk] || 'var(--text-primary)';
    }

    // Trend
    if (_dom.trendValue) {
      _dom.trendValue.textContent = result.trend || 'Unknown';
    }

    // Latency
    if (_dom.latencyValue) {
      if (result.inference_ms && result.inference_ms > 0) {
        _dom.latencyValue.innerHTML =
          `${Number(result.inference_ms).toFixed(1)} <span class="metric-unit">ms</span>`;
      } else {
        _dom.latencyValue.textContent = '—';
      }
    }

    // Findings
    renderFindings(result.top_features || []);

    // Explanation
    VitaExplanation.render(result);

    // Recommendation
    renderRecommendation(result.recommendation);

    // Sensor evidence
    renderSensorTable(sensorReading, result.top_features);
  }

  // ── Findings ───────────────────────────────────────────────────────────
  function renderFindings(topFeatures) {
    if (!_dom.findingsList) return;

    if (!topFeatures || topFeatures.length === 0) {
      _dom.findingsList.innerHTML =
        '<div class="state-message"><div class="state-message-text">No SHAP feature contributions available.</div></div>';
      if (_dom.findingsShowMore) _dom.findingsShowMore.classList.add('hidden');
      return;
    }

    const initialCount = VitaConfig.FINDINGS_INITIAL_COUNT;
    const html = topFeatures.map((f, i) => {
      const isNeg = f.impact < 0;
      const direction = isNeg ? 'Reduces predicted RUL' : 'Increases predicted RUL';
      const impactClass = isNeg ? 'negative' : 'positive';
      const hiddenClass = i >= initialCount ? ' hidden finding-extra' : '';

      return `
        <div class="finding-card${hiddenClass}">
          <div class="finding-card-header">
            <div class="finding-title">Sensor reading influences predicted RUL</div>
            <div class="finding-impact ${impactClass}">
              ${isNeg ? '↓' : '↑'} ${f.impact > 0 ? '+' : ''}${Number(f.impact).toFixed(2)} cycles
            </div>
          </div>
          <div style="display: flex; flex-direction: column; gap: 0.25rem; margin-top: 0.375rem;">
            <div class="finding-detail">
              <span class="finding-detail-label">Feature:</span>
              <span class="text-mono font-semibold">${escHtml(f.feature)}</span>
            </div>
            <div class="finding-detail">
              <span class="finding-detail-label">Direction:</span>
              <span>${direction}</span>
            </div>
          </div>
          <div class="finding-explanation">
            ${escHtml(f.description || `'${f.feature}' has a ${Math.abs(f.impact) < 2 ? 'moderate' : 'significant'} influence on this prediction.`)}
          </div>
        </div>`;
    }).join('');

    _dom.findingsList.innerHTML = html;

    if (_dom.findingsShowMore) {
      _dom.findingsShowMore.classList.toggle('hidden', topFeatures.length <= initialCount);
      _dom.findingsShowMore.textContent = `Show all ${topFeatures.length} features`;
      _dom.findingsShowMore._expanded = false;
    }
  }

  function showAllFindings() {
    const extras = document.querySelectorAll('.finding-extra');
    const isExpanded = _dom.findingsShowMore._expanded;
    extras.forEach(el => el.classList.toggle('hidden', isExpanded));
    _dom.findingsShowMore._expanded = !isExpanded;
    _dom.findingsShowMore.textContent = isExpanded
      ? `Show all ${extras.length + VitaConfig.FINDINGS_INITIAL_COUNT} features`
      : `Show fewer`;
  }

  // ── Recommendation ─────────────────────────────────────────────────────
  function renderRecommendation(rec) {
    if (!rec || !_dom.recPanel) return;

    const priority = (rec.priority || 'ROUTINE').toUpperCase();
    const priorityClass = {
      'ROUTINE': 'priority-routine',
      'MONITOR': 'priority-monitor',
      'URGENT': 'priority-urgent',
      'EMERGENCY': 'priority-emergency'
    }[priority] || 'priority-routine';

    _dom.recPanel.className = `recommendation-panel ${priorityClass}`;
    if (_dom.recAction) _dom.recAction.textContent = rec.action || '';
    if (_dom.recPriority) _dom.recPriority.textContent = `ADVISORY LEVEL: ${priority}`;

    if (_dom.recDetails) {
      _dom.recDetails.innerHTML = (rec.details || [])
        .map(d => `<li>${escHtml(d)}</li>`).join('');
    }
    if (_dom.recSensorNote) {
      _dom.recSensorNote.textContent = rec.sensor_note || '';
      _dom.recSensorNote.classList.toggle('hidden', !rec.sensor_note);
    }
    if (_dom.recDisclaimer) {
      _dom.recDisclaimer.textContent = rec.disclaimer || '';
    }
  }

  // ── Sensor Evidence Table ──────────────────────────────────────────────
  function renderSensorTable(sensorReading, topFeatures) {
    if (!_dom.sensorBody) return;

    const contributions = {};
    if (topFeatures) {
      topFeatures.forEach(f => { contributions[f.feature] = f.impact; });
    }

    const sensors = [];
    for (let i = 1; i <= 21; i++) {
      const key = `sensor_${i}`;
      const val = sensorReading ? sensorReading[key] : null;
      const contrib = contributions[key] || null;
      sensors.push({ key, value: val, contribution: contrib });
    }

    // Also add op_settings and cycle
    if (sensorReading) {
      ['op_setting_1', 'op_setting_2', 'op_setting_3'].forEach(key => {
        sensors.push({
          key, value: sensorReading[key],
          contribution: contributions[key] || null
        });
      });
    }

    _dom.sensorBody.innerHTML = sensors.map(s => {
      const valStr = s.value != null ? formatNumber(s.value) : '—';
      const contStr = s.contribution != null
        ? `<span class="${s.contribution < 0 ? 'text-critical' : 'text-healthy'}">${s.contribution > 0 ? '+' : ''}${Number(s.contribution).toFixed(2)}</span>`
        : '—';
      return `
        <tr>
          <td class="cell-mono cell-highlight">${s.key}</td>
          <td class="cell-mono">${valStr}</td>
          <td>${contStr}</td>
        </tr>`;
    }).join('');
  }

  // ── RUL Trend Chart ────────────────────────────────────────────────────
  function renderRulChart(machineId, activeCycle) {
    const trajectory = VitaMachineSelector.getTrajectory(machineId, activeCycle);
    if (!trajectory || trajectory.length === 0) return;

    const labels = trajectory.map(t => t.cycle);
    const predicted = trajectory.map(t => t.predicted_rul);
    const lower = trajectory.map(t => t.rul_lower ?? null);
    const upper = trajectory.map(t => t.rul_upper ?? null);

    const ctx = _dom.chartCanvas;
    if (!ctx) return;

    if (_chart) {
      _chart.data.labels = labels;
      _chart.data.datasets[0].data = predicted;
      _chart.data.datasets[1].data = upper;
      _chart.data.datasets[2].data = lower;
      _chart.update('none');
      return;
    }

    _chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Predicted RUL',
            data: predicted,
            borderColor: '#0ea5e9',
            backgroundColor: 'rgba(14, 165, 233, 0.08)',
            borderWidth: 2,
            pointRadius: 2,
            pointHoverRadius: 4,
            tension: 0.2,
            fill: false
          },
          {
            label: '90th Percentile',
            data: upper,
            borderColor: 'rgba(14, 165, 233, 0.25)',
            borderDash: [4, 4],
            borderWidth: 1,
            pointRadius: 0,
            fill: false
          },
          {
            label: '10th Percentile',
            data: lower,
            borderColor: 'rgba(14, 165, 233, 0.25)',
            borderDash: [4, 4],
            borderWidth: 1,
            pointRadius: 0,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 300 },
        scales: {
          x: {
            title: { display: true, text: 'Observation Cycle', color: '#64748b', font: { family: 'Inter' } },
            grid: { color: 'rgba(0,0,0,0.05)' },
            ticks: { color: '#64748b', font: { family: 'Inter', size: 11 } }
          },
          y: {
            title: { display: true, text: 'Predicted RUL (cycles)', color: '#64748b', font: { family: 'Inter' } },
            min: 0,
            grid: { color: 'rgba(0,0,0,0.05)' },
            ticks: { color: '#64748b', font: { family: 'Inter', size: 11 } }
          }
        },
        plugins: {
          legend: {
            labels: { color: '#334155', font: { family: 'Inter', size: 12 }, usePointStyle: true, pointStyle: 'line' }
          },
          tooltip: {
            backgroundColor: '#0f172a',
            titleColor: '#f8fafc',
            bodyColor: '#e2e8f0',
            borderColor: '#334155',
            borderWidth: 1,
            cornerRadius: 6
          }
        }
      }
    });

    VitaApp.registerChart('rul-analysis', _chart);
  }

  // ── Data Quality Section ───────────────────────────────────────────────
  function renderDataInfo(selection, sensorReading, mode) {
    if (!_dom.dataInfo) return;

    const missingInputs = [];
    if (sensorReading) {
      for (let i = 1; i <= 21; i++) {
        if (sensorReading[`sensor_${i}`] === 0 || sensorReading[`sensor_${i}`] == null) {
          // 0 can be valid, only flag null/undefined
          if (sensorReading[`sensor_${i}`] == null) missingInputs.push(`sensor_${i}`);
        }
      }
    }

    _dom.dataInfo.innerHTML = `
      <div class="info-row"><span class="info-label">Dataset</span><span class="info-value">${escHtml(selection.dataset)}</span></div>
      <div class="info-row"><span class="info-label">Machine ID</span><span class="info-value">${escHtml(selection.machineId)}</span></div>
      <div class="info-row"><span class="info-label">Observation Cycle</span><span class="info-value">${selection.cycle}</span></div>
      <div class="info-row"><span class="info-label">Missing Inputs</span><span class="info-value">${missingInputs.length === 0 ? 'None' : missingInputs.join(', ')}</span></div>
      <div class="info-row"><span class="info-label">Data Source</span><span class="info-value">${mode === 'api' ? 'Live FastAPI' : 'Edge Simulation'}</span></div>
      <div class="info-row"><span class="info-label">Timestamp</span><span class="info-value">${new Date().toLocaleString()}</span></div>
    `;
  }

  // ── Demo Banner ────────────────────────────────────────────────────────
  function showDemoBanner() {
    if (_dom.demoBanner) _dom.demoBanner.classList.remove('hidden');
  }
  function hideDemoBanner() {
    if (_dom.demoBanner) _dom.demoBanner.classList.add('hidden');
  }

  // ── Helpers ────────────────────────────────────────────────────────────
  function escHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function formatNumber(val) {
    if (typeof val !== 'number') return String(val);
    if (Number.isInteger(val)) return String(val);
    // 4 decimal places for small values, 2 for larger
    return Math.abs(val) < 1 ? val.toFixed(4) : val.toFixed(2);
  }

  return { init };
})();
