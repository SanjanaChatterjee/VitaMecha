/**
 * VitaMecha — Machine & Cycle Selector
 * Handles dataset selection, machine list population, and cycle selection.
 * Uses the telemetry-data.js for available engine data and sensor readings.
 */
const VitaMachineSelector = (function () {
  'use strict';

  let _dom = {};
  let _state = {
    dataset: 'ALL',
    machineId: null,
    cycle: 1,
    maxCycle: 100,
    engineData: null // Loaded engine trajectory data
  };

  let _onSelectionChange = null;

  function init() {
    _dom = {
      datasetSelect: document.getElementById('select-dataset'),
      machineSelect: document.getElementById('select-machine'),
      cycleInput: document.getElementById('input-cycle'),
      cycleMax: document.getElementById('cycle-max-display'),
      analyseBtn: document.getElementById('btn-analyse')
    };

    if (_dom.datasetSelect) {
      _dom.datasetSelect.addEventListener('change', onDatasetChange);
    }
    if (_dom.machineSelect) {
      _dom.machineSelect.addEventListener('change', onMachineChange);
    }
    if (_dom.cycleInput) {
      _dom.cycleInput.addEventListener('change', onCycleChange);
    }
    if (_dom.analyseBtn) {
      _dom.analyseBtn.addEventListener('click', onAnalyse);
    }

    // Load machines
    loadMachines();
  }

  async function loadMachines() {
    // Try API first
    try {
      if (VitaAPI.isConnected()) {
        const data = await VitaAPI.getMachines();
        if (data.machines && data.machines.length > 0) {
          populateMachineSelect(data.machines);
          return;
        }
      }
    } catch (_) { /* fall through to edge data */ }

    // Fallback to telemetry-data.js (edge mode)
    if (window.VITAMECHA_DATA && window.VITAMECHA_DATA.available_engines) {
      populateMachineSelect(window.VITAMECHA_DATA.available_engines);
    } else {
      populateMachineSelect([]);
    }
  }

  function populateMachineSelect(machines) {
    if (!_dom.machineSelect) return;

    // Filter by dataset if needed
    let filtered = machines;
    if (_state.dataset !== 'ALL') {
      filtered = machines.filter(m => m.startsWith(_state.dataset));
    }

    _dom.machineSelect.innerHTML = '';

    if (filtered.length === 0) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No machines available';
      _dom.machineSelect.appendChild(opt);
      _state.machineId = null;
      return;
    }

    filtered.forEach(id => {
      const opt = document.createElement('option');
      opt.value = id;
      const dataset = id.split('_')[0];
      opt.textContent = `${id} (${dataset})`;
      _dom.machineSelect.appendChild(opt);
    });

    _state.machineId = filtered[0];
    onMachineChange();
  }

  function onDatasetChange() {
    _state.dataset = _dom.datasetSelect.value;
    loadMachines();
  }

  function onMachineChange() {
    _state.machineId = _dom.machineSelect.value;

    // Load engine data from telemetry-data.js
    if (window.VITAMECHA_DATA && window.VITAMECHA_DATA.engines[_state.machineId]) {
      _state.engineData = window.VITAMECHA_DATA.engines[_state.machineId];
      _state.maxCycle = _state.engineData.total_cycles;
    } else {
      _state.engineData = null;
      _state.maxCycle = 100;
    }

    if (_dom.cycleInput) {
      _dom.cycleInput.max = _state.maxCycle;
      _dom.cycleInput.value = _state.maxCycle; // default to last cycle
      _state.cycle = _state.maxCycle;
    }
    if (_dom.cycleMax) {
      _dom.cycleMax.textContent = _state.maxCycle;
    }
  }

  function onCycleChange() {
    let val = parseInt(_dom.cycleInput.value, 10);
    if (isNaN(val) || val < 1) val = 1;
    if (val > _state.maxCycle) val = _state.maxCycle;
    _dom.cycleInput.value = val;
    _state.cycle = val;
  }

  function onAnalyse() {
    if (!_state.machineId) {
      return;
    }
    if (_onSelectionChange) {
      _onSelectionChange({
        dataset: _state.dataset,
        machineId: _state.machineId,
        cycle: _state.cycle,
        maxCycle: _state.maxCycle,
        engineData: _state.engineData
      });
    }
  }

  /**
   * Get sensor reading for a specific cycle from telemetry data.
   * Returns the SensorReading object ready for API submission.
   */
  function getSensorReading(machineId, cycle) {
    if (!window.VITAMECHA_DATA || !window.VITAMECHA_DATA.engines[machineId]) {
      return null;
    }
    const engine = window.VITAMECHA_DATA.engines[machineId];
    const obs = engine.trajectory.find(t => t.cycle === cycle);
    if (!obs || !obs.sensors) return null;

    const reading = {
      machine_id: machineId,
      cycle: cycle,
      op_setting_1: obs.op_settings?.op_setting_1 ?? 0,
      op_setting_2: obs.op_settings?.op_setting_2 ?? 0,
      op_setting_3: obs.op_settings?.op_setting_3 ?? 0
    };

    // Add all 21 sensors
    for (let i = 1; i <= 21; i++) {
      reading[`sensor_${i}`] = obs.sensors[`sensor_${i}`] ?? 0;
    }

    return reading;
  }

  /**
   * Get pre-computed result for a specific cycle from telemetry data (edge mode).
   */
  function getEdgeResult(machineId, cycle) {
    if (!window.VITAMECHA_DATA || !window.VITAMECHA_DATA.engines[machineId]) {
      return null;
    }
    const engine = window.VITAMECHA_DATA.engines[machineId];
    // Find closest cycle
    const obs = engine.trajectory.reduce((prev, curr) =>
      Math.abs(curr.cycle - cycle) < Math.abs(prev.cycle - cycle) ? curr : prev
    );
    return obs || null;
  }

  /**
   * Get full trajectory up to a given cycle.
   */
  function getTrajectory(machineId, upToCycle) {
    if (!window.VITAMECHA_DATA || !window.VITAMECHA_DATA.engines[machineId]) {
      return [];
    }
    const engine = window.VITAMECHA_DATA.engines[machineId];
    if (upToCycle !== undefined) {
      return engine.trajectory.filter(t => t.cycle <= upToCycle);
    }
    return engine.trajectory;
  }

  function onSelectionChange(callback) {
    _onSelectionChange = callback;
  }

  function getState() {
    return { ..._state };
  }

  return {
    init,
    loadMachines,
    getSensorReading,
    getEdgeResult,
    getTrajectory,
    onSelectionChange,
    getState
  };
})();
