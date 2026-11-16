// Class-owned two-seat chip ledger for uncontested-hand scenarios.
const edit = (value, apply) => { const copy = structuredClone(value); apply(copy.stakes); return copy; };
const stake = (value, id) => value.stakes.find(row => row.id === id);
const pots = value => [{ amount: value.stakes.reduce((sum, row) => sum + row.totalIn, 0), eligible: value.stakes.filter(row => !row.folded).map(row => row.id) }].filter(pot => pot.amount > 0);
export const ledger = {
  validateSettings: input => ({ startingStack: 1000, minimumUnit: 1, oddChipRule: 'first-listed', sidePots: true, seats: 2, ...input }),
  stakeOf: stake,
  commit(value, id, amount) {
    const committed = Math.min(amount, stake(value, id).stack);
    return { committed, ledger: edit(value, rows => { const row = rows.find(row => row.id === id); row.stack -= committed; row.bet += committed; row.totalIn += committed; }) };
  },
  fold: (value, id) => edit(value, rows => { rows.find(row => row.id === id).folded = true; }),
  endRound: value => edit(value, rows => rows.forEach(row => { row.bet = 0; })),
  returnUncalled(value) {
    const ordered = [...value.stakes].sort((a, b) => b.totalIn - a.totalIn);
    const amount = ordered[0].totalIn - ordered[1].totalIn;
    if (!amount) return { ledger: value, returned: null };
    return { returned: { id: ordered[0].id, amount }, ledger: edit(value, rows => { const row = rows.find(row => row.id === ordered[0].id); row.stack += amount; row.totalIn -= amount; row.bet = Math.max(0, row.bet - amount); }) };
  },
  buildPots: pots,
  displayPots: pots,
  awardPot: (_value, pot, winners) => ({ ...pot, winners: winners.map(id => ({ id, amount: pot.amount / winners.length })) }),
  settle: (value, awards) => edit(value, rows => { for (const pot of awards) for (const winner of pot.winners) rows.find(row => row.id === winner.id).stack += winner.amount; for (const row of rows) { row.totalIn = 0; row.bet = 0; } }),
  voidHand: value => edit(value, rows => { for (const row of rows) { row.stack += row.totalIn; row.totalIn = 0; row.bet = 0; } }),
  nextHand: value => edit(value, rows => rows.forEach(row => { row.folded = false; })),
};
