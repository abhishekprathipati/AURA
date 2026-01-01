// Elite Drawing UI & Keyboard Shortcuts for AURA Activities
document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('scribbleBoard');
  const ctx = canvas.getContext('2d');
  const toolbar = document.getElementById('breakroom-toolbar');
  const penSize = document.getElementById('penThickness');
  const penSizeValue = document.getElementById('penThicknessValue');
  const penColor = document.getElementById('penColor');
  let drawing = false;
  let mode = 'scribble';
  let lastX = 0, lastY = 0;
  let undoStack = [], redoStack = [];
  let maxHistory = 50;

  // --- Drawing Logic ---
  function startDraw(e) {
    drawing = true;
    [lastX, lastY] = getXY(e);
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
  }
  function draw(e) {
    if (!drawing) return;
    const [x, y] = getXY(e);
    ctx.lineWidth = penSize.valueAsNumber;
    ctx.lineCap = 'round';
    ctx.strokeStyle = penColor.value;
    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, y);
    [lastX, lastY] = [x, y];
  }
  function endDraw() {
    if (!drawing) return;
    drawing = false;
    ctx.closePath();
    saveState();
  }
  function getXY(e) {
    const rect = canvas.getBoundingClientRect();
    if (e.touches) {
      return [e.touches[0].clientX - rect.left, e.touches[0].clientY - rect.top];
    } else {
      return [e.clientX - rect.left, e.clientY - rect.top];
    }
  }

  // --- State Management ---
  function saveState() {
    if (undoStack.length >= maxHistory) undoStack.shift();
    undoStack.push(canvas.toDataURL());
    redoStack = [];
  }
  function undoStroke() {
    if (undoStack.length === 0) return;
    redoStack.push(canvas.toDataURL());
    const data = undoStack.pop();
    let img = new window.Image();
    img.onload = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);
    };
    img.src = data;
  }
  function redoStroke() {
    if (redoStack.length === 0) return;
    undoStack.push(canvas.toDataURL());
    const data = redoStack.pop();
    let img = new window.Image();
    img.onload = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);
    };
    img.src = data;
  }
  function clearCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    saveState();
  }

  // --- Toolbar Actions ---
  window.exportCanvasPNG = function() {
    const link = document.createElement('a');
    link.download = 'aura-art.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
  };
  window.toggleFullscreenCanvas = function() {
    if (!document.fullscreenElement) {
      canvas.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  };
  window.setPhysicsMode = function(m) {
    mode = m;
    // For demo: just highlight button, real physics can be added later
    Array.from(toolbar.querySelectorAll('button')).forEach(btn => btn.classList.remove('active'));
    if (m === 'scribble') toolbar.querySelector('[title="Scribble Mode"]').classList.add('active');
    if (m === 'break') toolbar.querySelector('[title="Break Objects"]').classList.add('active');
  };
  window.undoCanvas = undoStroke;
  window.redoCanvas = redoStroke;
  window.clearCanvas = clearCanvas;

  // --- Event Listeners ---
  canvas.addEventListener('mousedown', startDraw);
  canvas.addEventListener('mousemove', draw);
  canvas.addEventListener('mouseup', endDraw);
  canvas.addEventListener('mouseleave', endDraw);
  canvas.addEventListener('touchstart', startDraw);
  canvas.addEventListener('touchmove', draw);
  canvas.addEventListener('touchend', endDraw);

  penSize.addEventListener('input', () => {
    penSizeValue.textContent = penSize.value;
  });

  // --- Keyboard Shortcuts ---
  // Keyboard Shortcuts: Ctrl+Z (Undo), Ctrl+Y (Redo)
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key.toLowerCase() === 'z') {
      e.preventDefault();
      undoStroke();
    }
    if (e.ctrlKey && e.key.toLowerCase() === 'y') {
      e.preventDefault();
      redoStroke();
    }
  });

  // --- Initial State ---
  saveState();
  setPhysicsMode('scribble');
});
