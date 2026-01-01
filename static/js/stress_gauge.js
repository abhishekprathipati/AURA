// Draws a doughnut gauge for today's stress level
async function fetchStress() {
  try {
    const r = await fetch('/student/api/stress/today');
    const j = await r.json();
    if (j && typeof j.score === 'number') return j.score;
  } catch (e) { console.warn('stress fetch', e); }
  return 50;
}

function gaugeColors(score){
  // Use --theme-accent for the gauge arc, fallback to neon white or deep indigo for visibility
  let accent = getComputedStyle(document.body).getPropertyValue('--theme-accent') || '#4785ff';
  accent = accent.trim();
  // If accent is very light, use deep indigo for contrast
  const isLight = (c) => {
    // Simple luminance check for hex colors
    if (!c.startsWith('#') || c.length < 7) return false;
    const r = parseInt(c.substr(1,2),16), g = parseInt(c.substr(3,2),16), b = parseInt(c.substr(5,2),16);
    return (0.299*r + 0.587*g + 0.114*b) > 200;
  };
  if (isLight(accent)) accent = '#1a237e'; // Deep Indigo
  if(score <= 40) return [accent, '#064e3b'];
  if(score <= 75) return [accent, '#7c2d12'];
  return [accent, '#7f1d1d'];
}

async function drawStressGauge(){
  const el = document.getElementById('stressGauge');
  if(!el) return;
  const score = await fetchStress();
  const colors = gaugeColors(score);
  const rest = Math.max(0, 100 - score);
  const ctx = el.getContext('2d');
  // eslint-disable-next-line no-undef
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Stress','Remaining'],
      datasets: [{
        data: [score, rest],
        backgroundColor: [colors[0], 'rgba(255,255,255,0.08)'],
        borderWidth: 0,
        cutout: '70%'
      }]
    },
    options: {
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          position: 'nearest',
          intersect: false,
          yAlign: 'bottom',
          displayColors: false,
          caretPadding: 10,
          callbacks: {
            label: function(context) {
              return `${context.label}: ${context.parsed}`;
            }
          }
        }
      },
      responsive: true,
      maintainAspectRatio: false,
    }
  });
  const badge = document.getElementById('stressGaugeLabel');
  if(badge) badge.textContent = `${score}`;
}

window.addEventListener('DOMContentLoaded', drawStressGauge);
