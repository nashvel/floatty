import test from 'node:test';
import assert from 'node:assert/strict';
import { gazeOffset, PetController } from '../site/pets.mjs';

class Element extends EventTarget {
  dataset = {};
  attributes = {};
  eyes = { style: {} };
  setAttribute(name, value) { this.attributes[name] = value; }
  querySelector() { return this.eyes; }
  getBoundingClientRect() { return { left: 10, top: 20, width: 36, height: 40 }; }
}

function fixture() {
  const element = new Element();
  const nap = new Element();
  let completion;
  const timers = { setTimeout(fn) { completion = fn; return 1; }, clearTimeout() { completion = null; } };
  const controller = new PetController(element, nap, timers);
  return { element, nap, controller, complete() { completion?.(); } };
}

test('eyes track off-element pointers with bounded offsets and scale correctly', () => {
  const rect = { left: 0, top: 0, width: 36, height: 40 };
  const right = gazeOffset({ x: 1200, y: 800 }, rect);
  assert.ok(right.x > 0 && right.x <= 2.8);
  assert.ok(right.y > 0 && right.y <= 1.8);
  const left = gazeOffset({ x: -900, y: -900 }, rect);
  assert.ok(left.x < 0 && left.y < 0);
  assert.deepEqual(gazeOffset({ x: 18, y: 19 }, rect), { x: 0, y: 0 });
  assert.deepEqual(gazeOffset(null, rect), { x: 0, y: 0 });
  assert.deepEqual(gazeOffset({ x: NaN, y: 1 }, rect), { x: 0, y: 0 });
  assert.deepEqual(gazeOffset({ x: 36, y: 38 }, { ...rect, width: 72, height: 80 }), { x: 0, y: 0 });
});

test('click pets the mascot, wakes it, and clears the reaction', () => {
  const f = fixture();
  f.controller.toggleNap();
  f.element.dispatchEvent(new Event('click'));
  assert.equal(f.element.dataset.sleeping, 'false');
  assert.equal(f.element.dataset.happy, 'true');
  assert.equal(f.nap.textContent, 'Nap');
  f.complete();
  assert.equal(f.element.dataset.happy, 'false');
  f.controller.dispose();
});

test('right-click and keyboard naps pause the eyes and update accessible controls', () => {
  const f = fixture();
  const context = new Event('contextmenu', { cancelable: true });
  f.element.dispatchEvent(context);
  assert.equal(context.defaultPrevented, true);
  assert.equal(f.element.dataset.sleeping, 'true');
  assert.equal(f.nap.attributes['aria-pressed'], 'true');
  f.controller.look({ x: 1000, y: 1000 });
  assert.equal(f.element.eyes.style.transform, 'translate(0px, 0px)');
  const key = new Event('keydown', { cancelable: true });
  key.key = 'n';
  f.element.dispatchEvent(key);
  assert.equal(f.element.dataset.sleeping, 'false');
  const browserShortcut = new Event('keydown', { cancelable: true });
  browserShortcut.key = 'n';
  browserShortcut.ctrlKey = true;
  f.element.dispatchEvent(browserShortcut);
  assert.equal(browserShortcut.defaultPrevented, false);
  assert.equal(f.element.dataset.sleeping, 'false');
  f.controller.look({ x: 1000, y: 1000 });
  assert.notEqual(f.element.eyes.style.transform, 'translate(0px, 0px)');
  f.nap.dispatchEvent(new Event('click'));
  assert.equal(f.element.dataset.sleeping, 'true');
  f.controller.dispose();
  f.element.dispatchEvent(new Event('click'));
  assert.equal(f.element.dataset.sleeping, 'true');
});
