import { assert, load } from './runtime.mjs';
const m = await load('server/index.ts');
const none = m.checkSettings({ mode: 'none' });
assert.equal(none.enabled, false);
assert.equal(none.fillEmptySeats, false);
assert.equal(none.takeOverAbsent, false);
const fill = m.checkSettings({ mode: 'fill-empty', names: 'Ada Bob' });
assert.equal(fill.enabled, true);
assert.equal(fill.fillEmptySeats, true);
assert.deepEqual(fill.names, ['Ada', 'Bob']);
assert.deepEqual(m.parseNames('Ada Bob Ada'), ['Ada', 'Bob']);
assert.throws(() => m.checkSettings({ mode: 'unknown' }));
assert.throws(() => m.checkSettings({ names: [] }));
assert.throws(() => m.checkSettings({ thinkMinMs: -1 }));
const seating = {
  isFull: seats => seats.length >= 3,
  find: (seats, id) => seats.find(row => row.id === id),
  findByName: (seats, name) => seats.find(row => row.name === name),
  join: (seats, id, name, options) => ({ ok: true, state: [...seats, { id, name, computer: options.computer }] }),
  canAddComputer: (seats, id) => seats.some(row => row.id === id && !row.computer) ? { ok: true } : { ok: false, code: 'notAllowed' },
};
const clock = { elapsed: value => value, wallAt: (value, _which, target) => 1000 + Math.max(0, target - value) };
const strategy = { newMemory: () => ({}), choose: (_observation, _id, _rng, memory) => { memory.changed = true; return { type: 'check' }; }, observe: memory => { memory.observed = true; } };
const computers = m.createComputers({ mode: 'fill-empty', names: 'Ada Bob' }, { seating, clock, strategy });
const original = [{ id: 'p', name: 'Pat', computer: false }];
const filled = computers.fill(original);
assert.deepEqual(filled.added, ['Ada', 'Bob']);
assert.deepEqual(filled.state.map(row => row.id), ['p', 'computer-ada', 'computer-bob']);
assert.equal(original.length, 1);
assert.equal(computers.actsFor(filled.state, { id: 'p', connected: false, sittingOut: false }), true);
assert.equal(computers.moveDeadline(100, 200, () => 0.5), 5000);
const state = computers.create();
assert.deepEqual(computers.choose(state, {}, 'computer-ada', () => 0.5).move, { type: 'check' });
assert.deepEqual(state.memory, {});
assert.deepEqual(computers.observe(state, {}, 'p', {}), { memory: { observed: true } });
assert.deepEqual(state.memory, {});
