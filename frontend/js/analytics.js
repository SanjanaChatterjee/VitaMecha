/**
 * VitaMecha — Research Analytics Module (Page 4)
 * Displays verified experimental benchmarks, model comparison, robustness, and per-dataset performance.
 * All figures match the exact experiments/ CSV files.
 */
const VitaAnalytics = (function () {
  'use strict';

  // Exact data from verified experiment CSVs
  const RESEARCH_DATA = {
    comparison: [
      { model: 'Combined XGB Baseline', mae: 12.3587, rmse: 17.8542, r2: 0.5583, phm: 855449.31, features: 25 },
      { model: 'Final VitaMecha XGBoost', mae: 11.4479, rmse: 16.7926, r2: 0.6092, phm: 834687.09, features: 25 }
    ],
    perDataset: [
      { dataset: 'FD001', model: 'Final VitaMecha XGBoost', mae: 10.5396, rmse: 15.9396, r2: 0.6660, phm: 76249.80 },
      { dataset: 'FD002', model: 'Final VitaMecha XGBoost', mae: 12.1418, rmse: 17.4634, r2: 0.6330, phm: 217313.95 },
      { dataset: 'FD003', model: 'Final VitaMecha XGBoost', mae: 9.2274, rmse: 13.9866, r2: 0.6829, phm: 78753.24 },
      { dataset: 'FD004', model: 'Final VitaMecha XGBoost', mae: 12.0584, rmse: 17.5126, r2: 0.5270, phm: 462370.10 }
    ],
    robustness: [
      { condition: 'Clean', mae: 11.9635, rmse: 16.8602, r2: 0.6061, phm: 841914.43 },
      { condition: 'Gaussian noise 5%', mae: 29.4571, rmse: 38.1630, r2: -1.0182, phm: 11302087.95 },
      { condition: 'Gaussian noise 10%', mae: 33.4791, rmse: 41.9344, r2: -1.4368, phm: 16516260.97 },
      { condition: '10% missing', mae: 15.4046, rmse: 20.5284, r2: 0.4160, phm: 1425680.71 },
      { condition: '20% missing', mae: 18.0658, rmse: 23.2614, r2: 0.2502, phm: 2295296.15 }
    ],
    globalShap: [
      { feature: 'cycle', importance: 13.4186 },
      { feature: 'sensor_15', importance: 8.2154 },
      { feature: 'sensor_11', importance: 6.3677 },
      { feature: 'sensor_13', importance: 5.9332 },
      { feature: 'sensor_4', importance: 4.3834 },
      { feature: 'sensor_14', importance: 2.4803 },
      { feature: 'sensor_21', importance: 1.9775 },
      { feature: 'sensor_20', importance: 1.7683 },
      { feature: 'sensor_9', importance: 1.2598 },
      { feature: 'sensor_17', importance: 1.2333 }
    ]
  };

  let _dom = {};

  function init() {
    _dom = {
      comparisonBody: document.getElementById('res-comparison-body'),
      perDatasetBody: document.getElementById('res-dataset-body'),
      robustnessBody: document.getElementById('res-robustness-body'),
      shapBars: document.getElementById('res-shap-bars')
    };

    renderTables();
  }

  function renderTables() {
    if (_dom.comparisonBody) {
      _dom.comparisonBody.innerHTML = RESEARCH_DATA.comparison.map(r => `
        <tr>
          <td class="cell-highlight font-semibold">${r.model}</td>
          <td class="cell-mono">${r.mae.toFixed(4)}</td>
          <td class="cell-mono font-semibold">${r.rmse.toFixed(4)}</td>
          <td class="cell-mono">${r.r2.toFixed(4)}</td>
          <td class="cell-mono">${Number(r.phm.toFixed(2)).toLocaleString()}</td>
          <td class="cell-mono">${r.features}</td>
        </tr>
      `).join('');
    }

    if (_dom.perDatasetBody) {
      _dom.perDatasetBody.innerHTML = RESEARCH_DATA.perDataset.map(r => `
        <tr>
          <td class="cell-highlight font-semibold">${r.dataset}</td>
          <td>${r.model}</td>
          <td class="cell-mono">${r.mae.toFixed(4)}</td>
          <td class="cell-mono font-semibold">${r.rmse.toFixed(4)}</td>
          <td class="cell-mono">${r.r2.toFixed(4)}</td>
          <td class="cell-mono">${Number(r.phm.toFixed(2)).toLocaleString()}</td>
        </tr>
      `).join('');
    }

    if (_dom.robustnessBody) {
      _dom.robustnessBody.innerHTML = RESEARCH_DATA.robustness.map(r => {
        const r2Display = r.r2 < 0 ? `<span class="text-critical">${r.r2.toFixed(4)}</span>` : r.r2.toFixed(4);
        return `
          <tr>
            <td class="font-semibold">${r.condition}</td>
            <td class="cell-mono">${r.mae.toFixed(4)}</td>
            <td class="cell-mono font-semibold">${r.rmse.toFixed(4)}</td>
            <td class="cell-mono">${r2Display}</td>
            <td class="cell-mono">${Number(r.phm.toFixed(2)).toLocaleString()}</td>
          </tr>
        `;
      }).join('');
    }

    if (_dom.shapBars) {
      const maxImp = RESEARCH_DATA.globalShap[0].importance;
      _dom.shapBars.innerHTML = RESEARCH_DATA.globalShap.map(s => {
        const pct = ((s.importance / maxImp) * 100).toFixed(1);
        return `
          <div style="margin-bottom: 0.6rem;">
            <div style="display: flex; justify-content: space-between; font-size: 0.8125rem; margin-bottom: 0.2rem;">
              <span class="cell-mono font-semibold">${s.feature}</span>
              <span class="cell-mono text-muted">${s.importance.toFixed(4)}</span>
            </div>
            <div class="progress-bar">
              <div class="progress-bar-fill" style="width: ${pct}%;"></div>
            </div>
          </div>
        `;
      }).join('');
    }
  }

  return { init };
})();
