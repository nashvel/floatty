'use strict';
const island = document.querySelector('#island-preview');
const toggle = document.querySelector('#island-toggle');
if (island && toggle) {
  const body = document.querySelector('#island-body');
  const cue = document.querySelector('#click-cue');
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(open));
    island.classList.toggle('open', open);
    body.hidden = !open;
    cue.hidden = open;
    toggle.querySelector('.expand-mark').textContent = open ? '−' : '+';
  });
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  function selectTab(tab) {
    for (const candidate of tabs) {
      const selected = candidate === tab;
      candidate.setAttribute('aria-selected', String(selected));
      candidate.tabIndex = selected ? 0 : -1;
      document.getElementById(candidate.getAttribute('aria-controls')).hidden = !selected;
    }
  }
  for (const [index, tab] of tabs.entries()) {
    tab.addEventListener('click', () => selectTab(tab));
    tab.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = tabs[(index + 1) % tabs.length];
      if (event.key === 'ArrowLeft') next = tabs[(index + tabs.length - 1) % tabs.length];
      if (event.key === 'Home') next = tabs[0];
      if (event.key === 'End') next = tabs[tabs.length - 1];
      if (next) { event.preventDefault(); selectTab(next); next.focus(); }
    });
  }
  const motion = document.querySelector('#demo-motion');
  motion.checked = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.body.classList.toggle('no-motion', !motion.checked);
  motion.addEventListener('change', () => document.body.classList.toggle('no-motion', !motion.checked));
  const stop = document.querySelector('#demo-stop');
  const dialog = document.querySelector('#stop-dialog');
  stop.addEventListener('click', () => { dialog.returnValue = ''; dialog.showModal(); });
  dialog.addEventListener('close', () => {
    if (dialog.returnValue !== 'stop') return;
    stop.disabled = true;
    stop.textContent = 'Stopped';
    document.querySelector('#service-feedback').textContent = 'Preview: web-dev stopped. No real service was changed.';
  });
}
let statusTimer;
for (const button of document.querySelectorAll('[data-copy]')) {
  button.addEventListener('click', async () => {
    const status = document.querySelector('#copy-status');
    const text = document.getElementById(button.dataset.copy).textContent;
    try {
      await navigator.clipboard.writeText(text);
      status.textContent = 'Copied to clipboard';
    } catch {
      status.textContent = 'Clipboard unavailable. Select and copy the command manually.';
    }
    clearTimeout(statusTimer);
    statusTimer = setTimeout(() => { status.textContent = ''; }, 3500);
  });
}
