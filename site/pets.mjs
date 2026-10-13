export function gazeOffset(pointer, rect) {
  if (!pointer || !rect || !(rect.width > 0) || !(rect.height > 0)) return { x: 0, y: 0 };
  const dx = pointer.x - (rect.left + rect.width / 2);
  const dy = pointer.y - (rect.top + rect.height * 19 / 40);
  if (!Number.isFinite(dx) || !Number.isFinite(dy)) return { x: 0, y: 0 };
  const distance = Math.max(50 * rect.width / 36, Math.hypot(dx, dy));
  return { x: 2.8 * dx / distance, y: 1.8 * dy / distance };
}

export class PetController {
  constructor(element, napButton = null, timers = { setTimeout, clearTimeout }) {
    this.element = element;
    this.napButton = napButton;
    this.timers = timers;
    this.timer = null;
    this.sleeping = false;
    this.listeners = [];
    this.bind(element, 'click', () => this.pet());
    this.bind(element, 'contextmenu', event => { event.preventDefault(); this.toggleNap(); });
    this.bind(element, 'keydown', event => {
      if (event.key?.toLowerCase() === 'n' && !event.ctrlKey && !event.metaKey && !event.altKey) { event.preventDefault(); this.toggleNap(); }
    });
    if (napButton) this.bind(napButton, 'click', () => this.toggleNap());
    this.syncNap();
  }
  bind(element, type, listener) {
    element.addEventListener(type, listener);
    this.listeners.push([element, type, listener]);
  }
  pet() {
    this.sleeping = false;
    this.syncNap();
    this.element.dataset.happy = 'true';
    if (this.timer !== null) this.timers.clearTimeout(this.timer);
    this.timer = this.timers.setTimeout(() => {
      this.element.dataset.happy = 'false';
      this.timer = null;
    }, 1400);
  }
  toggleNap() {
    if (this.timer !== null) this.timers.clearTimeout(this.timer);
    this.timer = null;
    this.element.dataset.happy = 'false';
    this.sleeping = !this.sleeping;
    this.syncNap();
    if (this.sleeping) this.look(null);
  }
  syncNap() {
    this.element.dataset.sleeping = String(this.sleeping);
    if (this.napButton) {
      this.napButton.textContent = this.sleeping ? 'Wake' : 'Nap';
      this.napButton.setAttribute('aria-pressed', String(this.sleeping));
    }
  }
  look(pointer) {
    const gaze = gazeOffset(this.sleeping ? null : pointer, this.element.getBoundingClientRect());
    this.element.querySelector('.pet-gaze').style.transform = `translate(${gaze.x}px, ${gaze.y}px)`;
  }
  dispose() {
    if (this.timer !== null) this.timers.clearTimeout(this.timer);
    for (const [element, type, listener] of this.listeners) element.removeEventListener(type, listener);
  }
}

if (typeof document !== 'undefined') {
  const pets = Array.from(document.querySelectorAll('.web-pet'), element => {
    const nap = document.querySelector(`[data-pet-target="${element.id}"]`);
    return new PetController(element, nap);
  });
  let frame = null;
  let pointer = null;
  window.addEventListener('pointermove', event => {
    pointer = { x: event.clientX, y: event.clientY };
    if (frame !== null) return;
    frame = requestAnimationFrame(() => {
      frame = null;
      for (const pet of pets) {
        if (pet.element.getClientRects().length) pet.look(pointer);
      }
    });
  }, { passive: true });
  function resetEyes() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null;
    pointer = null;
    for (const pet of pets) pet.look(null);
  }
  document.documentElement.addEventListener('pointerleave', resetEyes);
  document.addEventListener('visibilitychange', () => { if (document.hidden) resetEyes(); });
  window.addEventListener('pagehide', resetEyes);
}
