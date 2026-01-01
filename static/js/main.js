import { initChat } from './chat.js';

function initLayout(){
	// Mobile sidebar toggle or other layout hooks can go here
}

window.addEventListener('DOMContentLoaded', () => {
	initLayout();
	initChat();

	// Auto-hide/reveal header at top edge
	const body = document.body;
	const header = document.querySelector('header');
	let hotspot = document.getElementById('topEdgeHotspot');
	let hideTimer = null;
	let zenMode = false;
	const zenBtn = document.getElementById('zenModeToggle');

	// Ensure hotspot exists
	if (!hotspot) {
		const hotspotEl = document.createElement('div');
		hotspotEl.id = 'topEdgeHotspot';
		hotspotEl.setAttribute('aria-hidden', 'true');
		document.body.prepend(hotspotEl);
		hotspot = hotspotEl;
	}

	const showHeader = () => {
		if (zenMode) return; // Disabled when Zen Mode is active
		clearTimeout(hideTimer);
		body.classList.add('header-visible');
		body.classList.remove('header-hidden');
	};

	const hideHeader = (delay = 600) => {
		clearTimeout(hideTimer);
		hideTimer = setTimeout(() => {
			// Only hide if neither hotspot nor header are hovered/focused
			const hoveringHeader = header.matches(':hover');
			const hoveringHotspot = hotspot.matches(':hover');
			const headerHasFocus = header.contains(document.activeElement);
			if (!hoveringHeader && !hoveringHotspot && !headerHasFocus) {
				body.classList.add('header-hidden');
				body.classList.remove('header-visible');
			}
		}, delay);
	};

	// Start hidden by default
	body.classList.add('header-hidden');
	body.classList.remove('header-visible');

	// Reveal when hovering the top edge
	hotspot.addEventListener('mouseenter', showHeader);
	hotspot.addEventListener('mousemove', showHeader);

	// Hide when leaving header area
	header.addEventListener('mouseleave', () => hideHeader(700));

	// Keep visible while interacting with header via keyboard
	header.addEventListener('focusin', showHeader);
	header.addEventListener('focusout', () => hideHeader(700));

	// On touch devices, a tap near top edge reveals; tap elsewhere hides
	window.addEventListener('touchstart', (e) => {
		const y = e.touches && e.touches[0] ? e.touches[0].clientY : 9999;
		if (y <= 12) {
			showHeader();
		} else if (!header.contains(e.target)) {
			hideHeader(400);
		}
	});
});