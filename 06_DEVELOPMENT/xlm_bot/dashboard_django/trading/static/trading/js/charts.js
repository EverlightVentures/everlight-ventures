/**
 * Chart.js dark theme helpers for analytics charts.
 */

const CHART_PALETTE = [
  '#c9a84c',  // Gold
  '#8b5cf6',  // Purple
  '#22d3ee',  // Cyan
  '#22c55e',  // Green
  '#f59e0b',  // Amber
  '#ef4444',  // Red
  '#ec4899',  // Pink
  '#14b8a6',  // Teal
];

const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
      labels: { color: '#9ca3af', font: { family: 'Inter' } },
    },
    tooltip: {
      backgroundColor: '#1a1a2e',
      titleColor: '#e8e6e3',
      bodyColor: '#9ca3af',
      borderColor: 'rgba(255,255,255,0.08)',
      borderWidth: 1,
      cornerRadius: 8,
      padding: 10,
      titleFont: { family: 'Inter', weight: '600' },
      bodyFont: { family: 'Inter' },
    },
  },
  scales: {
    x: {
      grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
      ticks: { color: '#6b7280', font: { family: 'Inter', size: 11 } },
    },
    y: {
      grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
      ticks: { color: '#6b7280', font: { family: 'Inter', size: 11 } },
    },
  },
};

/**
 * Create a Chart.js line chart with dark theme.
 */
function createLineChart(ctx, labels, data, label, color) {
  color = color || CHART_PALETTE[0];
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: label || '',
        data: data,
        borderColor: color,
        backgroundColor: color + '30',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 2,
      }],
    },
    options: { ...CHART_DEFAULTS },
  });
}

/**
 * Create a Chart.js bar chart with dark theme.
 */
function createBarChart(ctx, labels, data, label, colors) {
  colors = colors || CHART_PALETTE;
  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: label || '',
        data: data,
        backgroundColor: labels.map((_, i) => colors[i % colors.length] + '40'),
        borderColor: labels.map((_, i) => colors[i % colors.length]),
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: { ...CHART_DEFAULTS },
  });
}

/**
 * Create a Chart.js doughnut chart with dark theme.
 */
function createDoughnutChart(ctx, labels, data, colors) {
  colors = colors || CHART_PALETTE;
  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors.slice(0, labels.length),
        borderColor: '#0a0a0f',
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '62%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#9ca3af', font: { family: 'Inter' }, padding: 16 },
        },
        tooltip: CHART_DEFAULTS.plugins.tooltip,
      },
    },
  });
}
