/**
 * VitaMecha — Fleet Overview Module (Page 2)
 * Summarizes the complete machine fleet, health distributions, and quick status.
 */
const VitaOverview = (function () {
  'use strict';

  let _dom = {};

  function init() {
    _dom = {
      totalMachines: document.getElementById('ov-total-machines'),
      healthyCount: document.getElementById('ov-healthy-count'),
      warningCount: document.getElementById('ov-warning-count'),
      degradedCount: document.getElementById('ov-degraded-count'),
      criticalCount: document.getElementById('ov-critical-count'),
      fleetTableBody: document.getElementById('ov-fleet-table-body'),
      datasetFilter: document.getElementById('ov-filter-dataset'),
      statusFilter: document.getElementById('ov-filter-status'),
      searchInput: document.getElementById('ov-search-machine')
    };

    if (_dom.datasetFilter) _dom.datasetFilter.addEventListener('change', renderTable);
    if (_dom.statusFilter) _dom.statusFilter.addEventListener('change', renderTable);
    if (_dom.searchInput) _dom.searchInput.addEventListener('input', renderTable);

    // Initial load
    refreshFleet();
  }

  function getFleetData() {
    const data = [];
    if (!window.VITAMECHA_DATA || !window.VITAMECHA_DATA.engines) {
      return data;
    }

    const engines = window.VITAMECHA_DATA.engines;
    Object.keys(engines).forEach(id => {
      const eng = engines[id];
      const traj = eng.trajectory || [];
      const latest = traj.length > 0 ? traj[traj.length - 1] : null;
      if (latest) {
        data.push({
          machineId: id,
          dataset: eng.dataset || id.split('_')[0],
          cycle: latest.cycle,
          predictedRul: latest.predicted_rul,
          healthStatus: (latest.health_status || 'HEALTHY').toUpperCase(),
          riskLevel: latest.risk_level || 'Low',
          trend: latest.trend || 'Unknown'
        });
      }
    });

    return data;
  }

  function refreshFleet() {
    const fleet = getFleetData();
    renderSummary(fleet);
    renderTable();
  }

  function renderSummary(fleet) {
    let healthy = 0, warning = 0, degraded = 0, critical = 0;
    fleet.forEach(m => {
      if (m.healthStatus === 'HEALTHY') healthy++;
      else if (m.healthStatus === 'WARNING') warning++;
      else if (m.healthStatus === 'DEGRADED') degraded++;
      else if (m.healthStatus === 'CRITICAL') critical++;
    });

    if (_dom.totalMachines) _dom.totalMachines.textContent = fleet.length;
    if (_dom.healthyCount) _dom.healthyCount.textContent = healthy;
    if (_dom.warningCount) _dom.warningCount.textContent = warning;
    if (_dom.degradedCount) _dom.degradedCount.textContent = degraded;
    if (_dom.criticalCount) _dom.criticalCount.textContent = critical;
  }

  function renderTable() {
    if (!_dom.fleetTableBody) return;

    let fleet = getFleetData();
    const dataset = _dom.datasetFilter ? _dom.datasetFilter.value : 'ALL';
    const status = _dom.statusFilter ? _dom.statusFilter.value : 'ALL';
    const query = _dom.searchInput ? _dom.searchInput.value.trim().toLowerCase() : '';

    if (dataset !== 'ALL') {
      fleet = fleet.filter(m => m.dataset === dataset);
    }
    if (status !== 'ALL') {
      fleet = fleet.filter(m => m.healthStatus === status);
    }
    if (query) {
      fleet = fleet.filter(m => m.machineId.toLowerCase().includes(query));
    }

    if (fleet.length === 0) {
      _dom.fleetTableBody.innerHTML = `<tr><td colspan="7" class="text-center text-muted" style="padding: 2rem;">No machines matched the selected criteria.</td></tr>`;
      return;
    }

    _dom.fleetTableBody.innerHTML = fleet.map(m => {
      const statusBadge = `<span class="badge badge-${m.healthStatus.toLowerCase()}">${m.healthStatus}</span>`;
      const riskColor = { 'Low': 'var(--healthy)', 'Medium': 'var(--warning)', 'High': 'var(--degraded)', 'Critical': 'var(--critical)' }[m.riskLevel] || 'inherit';

      return `
        <tr>
          <td class="cell-mono cell-highlight font-semibold">${esc(m.machineId)}</td>
          <td>${esc(m.dataset)}</td>
          <td class="cell-mono font-semibold">${Number(m.predictedRul).toFixed(1)} cyc</td>
          <td>${statusBadge}</td>
          <td style="color: ${riskColor}; font-weight: 600;">${esc(m.riskLevel)}</td>
          <td class="cell-mono">${m.cycle}</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="VitaOverview.viewMachine('${m.machineId}', ${m.cycle})">
              View Analysis
            </button>
          </td>
        </tr>`;
    }).join('');
  }

  function viewMachine(machineId, cycle) {
    const selDataset = document.getElementById('select-dataset');
    const selMachine = document.getElementById('select-machine');
    const inputCycle = document.getElementById('input-cycle');

    const dataset = machineId.split('_')[0];
    if (selDataset) {
      selDataset.value = dataset;
      VitaMachineSelector.loadMachines();
    }
    setTimeout(() => {
      if (selMachine) selMachine.value = machineId;
      if (inputCycle) inputCycle.value = cycle;
      VitaApp.navigateTo('problem-analysis');
      const btn = document.getElementById('btn-analyse');
      if (btn) btn.click();
    }, 100);
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  return { init, refreshFleet, viewMachine };
})();
