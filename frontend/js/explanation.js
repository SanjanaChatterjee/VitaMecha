/**
 * VitaMecha — Explanation Module
 * SHAP contribution rendering and plain-English explanation generation.
 *
 * IMPORTANT: SHAP values describe model feature contributions, NOT physical causality.
 * This module never claims that a sensor reading physically caused a failure.
 */
const VitaExplanation = (function () {
  'use strict';

  let _dom = {};

  function init() {
    _dom = {
      shapBars: document.getElementById('pa-shap-bars'),
      explainObserved: document.getElementById('pa-explain-observed'),
      explainMatters: document.getElementById('pa-explain-matters'),
      explainCheck: document.getElementById('pa-explain-check')
    };
  }

  /**
   * Render explanation from a prediction result.
   * @param {Object} result - PredictResponse from API or normalized edge data.
   */
  function render(result) {
    const features = result.top_features || [];
    renderShapBars(features);
    renderPlainEnglish(result, features);
  }

  // ── SHAP Bar Visualisation ─────────────────────────────────────────────
  function renderShapBars(features) {
    if (!_dom.shapBars) return;

    if (!features || features.length === 0) {
      _dom.shapBars.innerHTML = '<div class="text-muted text-sm">No SHAP contributions available for this prediction.</div>';
      return;
    }

    const maxAbs = Math.max(...features.map(f => Math.abs(f.impact)), 1);

    _dom.shapBars.innerHTML = features.map(f => {
      const isPos = f.impact >= 0;
      const widthPct = Math.min((Math.abs(f.impact) / maxAbs) * 45, 48);
      const fillClass = isPos ? 'positive' : 'negative';
      const valueClass = isPos ? 'positive' : 'negative';
      const sign = isPos ? '+' : '';

      return `
        <div class="shap-row">
          <div class="shap-label" title="${esc(f.feature)}">${esc(f.feature)}</div>
          <div class="shap-track">
            <div class="shap-zero"></div>
            <div class="shap-fill ${fillClass}" style="width: ${widthPct}%;"></div>
          </div>
          <div class="shap-value ${valueClass}">${sign}${Number(f.impact).toFixed(2)}</div>
        </div>`;
    }).join('');
  }

  // ── Plain-English Explanation ──────────────────────────────────────────
  function renderPlainEnglish(result, features) {
    const rul = result.predicted_rul;
    const status = (result.health_status || 'HEALTHY').toUpperCase();
    const negFeatures = features.filter(f => f.impact < 0);
    const posFeatures = features.filter(f => f.impact >= 0);

    // "What the model observed"
    if (_dom.explainObserved) {
      if (features.length === 0) {
        _dom.explainObserved.textContent = 'No SHAP feature contributions are available for this observation.';
      } else {
        const topNeg = negFeatures.slice(0, 3).map(f => f.feature);
        const topPos = posFeatures.slice(0, 2).map(f => f.feature);
        let text = '';

        if (topNeg.length > 0) {
          text += `The model identified ${topNeg.join(', ')} as the sensor reading(s) most strongly associated with a reduction in predicted remaining useful life.`;
        }
        if (topPos.length > 0) {
          text += ` Meanwhile, ${topPos.join(', ')} ${topPos.length === 1 ? 'is' : 'are'} contributing positively, indicating patterns associated with longer remaining life.`;
        }
        if (!text) {
          text = 'The model analysed all input features. No individual feature showed a dominant influence on this prediction.';
        }
        _dom.explainObserved.textContent = text;
      }
    }

    // "Why it matters"
    if (_dom.explainMatters) {
      let text = `The model estimates ${Number(rul).toFixed(1)} remaining operational cycles. `;
      if (status === 'HEALTHY') {
        text += 'This places the machine in a healthy operational state with adequate remaining life margin.';
      } else if (status === 'WARNING') {
        text += 'This places the machine in a warning zone, indicating that degradation patterns are emerging and monitoring should be increased.';
      } else if (status === 'DEGRADED') {
        text += 'This indicates significant degradation. The predicted remaining life is narrowing and maintenance planning should be prioritised.';
      } else if (status === 'CRITICAL') {
        text += 'The machine is at critical remaining life. Immediate inspection and maintenance action should be considered.';
      }

      if (result.trend && result.trend !== 'Unknown') {
        text += ` The RUL trend is ${result.trend.toLowerCase()}.`;
      }

      _dom.explainMatters.textContent = text;
    }

    // "What should be checked"
    if (_dom.explainCheck) {
      if (negFeatures.length === 0) {
        _dom.explainCheck.textContent = 'No specific sensor anomalies were flagged. Continue routine monitoring.';
      } else {
        const channels = negFeatures.slice(0, 4).map(f => f.feature).join(', ');
        _dom.explainCheck.textContent =
          `Review the historical trends for ${channels}. Compare current readings against baseline values from healthy operating periods. ` +
          'These sensor channels showed the strongest association with reduced predicted RUL in the current model observation. ' +
          'Note: SHAP contributions indicate statistical model influence, not confirmed physical causality.';
      }
    }
  }

  function esc(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  return { init, render };
})();
