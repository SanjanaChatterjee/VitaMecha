/**
 * VitaMecha — Live Monitoring Module (Page 3)
 * Simulates sequential streaming of sensor cycles and displays dynamic RUL trend.
 */
const VitaMonitoring = (function () {
  'use strict';

  let _dom = {};
  let _chart = null;
  let _streamState = {
    active: false,
    timer: null,
    machineId: null,
    cycleIndex: 0,
    speedMs: 150,
    trajectory: [],
    log: []
  };

  function init() {
    _dom = {
      machineSelect: document.getElementById('mon-select-machine'),
      playBtn: document.getElementById('mon-btn-play'),
      resetBtn: document.getElementById('mon-btn-reset'),
      speedSelect: document.getElementById('mon-select-speed'),
      progressBar: document.getElementById('mon-progress-bar'),
      cycleLabel: document.getElementById('mon-cycle-label'),
      currentRul: document.getElementById('mon-current-rul'),
      healthBadge: document.getElementById('mon-health-badge'),
      logBody: document.getElementById('mon-log-body'),
      chartCanvas: document.getElementById('chart-mon-live')
    };

    if (_dom.playBtn) _dom.playBtn.addEventListener('click', toggleStream);
    if (_dom.resetBtn) _dom.resetBtn.addEventListener('click', resetStream);
    if (_dom.speedSelect) {
      _dom.speedSelect.addEventListener('change', (e) => {
        _streamState.speedMs = parseInt(e.target.value, 10);
        if (_streamState.active) {
          clearInterval(_streamState.timer);
          _streamState.timer = setInterval(stepStream, _streamState.speedMs);
        }
      });
    }
    if (_dom.machineSelect) {
      _dom.machineSelect.addEventListener('change', (e) => {
        setupMachine(e.target.value);
      });
    }

    populateMachines();
    initChart();
  }

  function populateMachines() {
    if (!_dom.machineSelect) return;
    _dom.machineSelect.innerHTML = '';
    const engines = (window.VITAMECHA_DATA && window.VITAMECHA_DATA.available_engines) || [];
    engines.forEach(id => {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = `${id} (${id.split('_')[0]})`;
      _dom.machineSelect.appendChild(opt);
    });

    if (engines.length > 0) {
      setupMachine(engines[0]);
    }
  }

  function setupMachine(machineId) {
    resetStream();
    _streamState.machineId = machineId;
    if (window.VITAMECHA_DATA && window.VITAMECHA_DATA.engines[machineId]) {
      _streamState.trajectory = window.VITAMECHA_DATA.engines[machineId].trajectory || [];
    } else {
      _streamState.trajectory = [];
    }
  }

  function initChart() {
    if (!_dom.chartCanvas) return;
    const ctx = _dom.chartCanvas;
    _chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Streamed RUL (cycles)',
          data: [],
          borderColor: '#16a34a',
          backgroundColor: 'rgba(22, 163, 74, 0.1)',
          borderWidth: 2,
          pointRadius: 2,
          fill: true,
          tension: 0.15
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 100 },
        scales: {
          x: {
            title: { display: true, text: 'Streamed Cycle', color: '#64748b' },
            grid: { color: 'rgba(0,0,0,0.05)' }
          },
          y: {
            title: { display: true, text: 'Predicted RUL', color: '#64748b' },
            min: 0,
            grid: { color: 'rgba(0,0,0,0.05)' }
          }
        },
        plugins: {
          legend: { labels: { font: { family: 'Inter' } } }
        }
      }
    });

    VitaApp.registerChart('mon-live', _chart);
  }

  function toggleStream() {
    if (_streamState.active) {
      pauseStream();
    } else {
      startStream();
    }
  }

  function startStream() {
    if (_streamState.trajectory.length === 0) return;
    _streamState.active = true;
    if (_dom.playBtn) {
      _dom.playBtn.textContent = '⏸ Pause Stream';
      _dom.playBtn.classList.replace('btn-primary', 'btn-secondary');
    }
    _streamState.timer = setInterval(stepStream, _streamState.speedMs);
  }

  function pauseStream() {
    _streamState.active = false;
    if (_dom.playBtn) {
      _dom.playBtn.textContent = '▶ Resume Stream';
      _dom.playBtn.classList.replace('btn-secondary', 'btn-primary');
    }
    clearInterval(_streamState.timer);
  }

  function resetStream() {
    pauseStream();
    _streamState.cycleIndex = 0;
    _streamState.log = [];
    if (_dom.playBtn) _dom.playBtn.textContent = '▶ Start Stream';
    if (_dom.progressBar) _dom.progressBar.style.width = '0%';
    if (_dom.cycleLabel) _dom.cycleLabel.textContent = 'Cycle 0';
    if (_dom.currentRul) _dom.currentRul.innerHTML = '-- <span class="metric-unit">cycles</span>';
    if (_dom.healthBadge) {
      _dom.healthBadge.className = 'badge badge-healthy';
      _dom.healthBadge.textContent = 'READY';
    }
    if (_dom.logBody) _dom.logBody.innerHTML = '';
    if (_chart) {
      _chart.data.labels = [];
      _chart.data.datasets[0].data = [];
      _chart.update();
    }
  }

  function stepStream() {
    if (_streamState.cycleIndex >= _streamState.trajectory.length) {
      pauseStream();
      if (_dom.playBtn) _dom.playBtn.textContent = '✓ Stream Complete';
      return;
    }

    const obs = _streamState.trajectory[_streamState.cycleIndex];
    _streamState.cycleIndex++;

    const total = _streamState.trajectory.length;
    const pct = ((_streamState.cycleIndex / total) * 100).toFixed(0);

    if (_dom.progressBar) _dom.progressBar.style.width = `${pct}%`;
    if (_dom.cycleLabel) _dom.cycleLabel.textContent = `Cycle ${obs.cycle} (${pct}%)`;
    if (_dom.currentRul) _dom.currentRul.innerHTML = `${Number(obs.predicted_rul).toFixed(1)} <span class="metric-unit">cycles</span>`;

    const status = (obs.health_status || 'HEALTHY').toUpperCase();
    if (_dom.healthBadge) {
      _dom.healthBadge.className = `badge badge-${status.toLowerCase()}`;
      _dom.healthBadge.textContent = status;
    }

    if (_chart) {
      _chart.data.labels.push(obs.cycle);
      _chart.data.datasets[0].data.push(obs.predicted_rul);

      // Adjust color according to health state
      if (status === 'CRITICAL') {
        _chart.data.datasets[0].borderColor = '#dc2626';
        _chart.data.datasets[0].backgroundColor = 'rgba(220, 38, 38, 0.15)';
      } else if (status === 'DEGRADED') {
        _chart.data.datasets[0].borderColor = '#ea580c';
        _chart.data.datasets[0].backgroundColor = 'rgba(234, 88, 12, 0.15)';
      } else if (status === 'WARNING') {
        _chart.data.datasets[0].borderColor = '#d97706';
        _chart.data.datasets[0].backgroundColor = 'rgba(217, 119, 6, 0.15)';
      } else {
        _chart.data.datasets[0].borderColor = '#16a34a';
        _chart.data.datasets[0].backgroundColor = 'rgba(22, 163, 74, 0.1)';
      }
      _chart.update('none');
    }

    _streamState.log.unshift(obs);
    if (_streamState.log.length > 8) _streamState.log.pop();

    if (_dom.logBody) {
      _dom.logBody.innerHTML = _streamState.log.map(item => `
        <tr>
          <td class="cell-mono">#${item.cycle}</td>
          <td class="cell-mono font-semibold">${Number(item.predicted_rul).toFixed(1)} cyc</td>
          <td><span class="badge badge-${(item.health_status || 'healthy').toLowerCase()}">${item.health_status || 'HEALTHY'}</span></td>
          <td class="text-muted cell-mono">${item.inference_ms ? Number(item.inference_ms).toFixed(1) : 2.1} ms</td>
        </tr>
      `).join('');
    }
  }

  return { init };
})();
