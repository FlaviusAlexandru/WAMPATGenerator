/**
 * GENERATOR: Fully Balanced HCI Study.
 * Uses 8 half-pattern tokens (A1..D2) to shorten each phase while
 * preserving study structure and Latin-square condition/metric order.
 */
function generateHCIStudy() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getActiveSheet();
  sheet.clear();
  
  const numParticipants = 24;
  const fbTypes = ["OperationFB", "ActionFB", "TaskFB"];
  const metrics = ["Time", "Distance", "MaxSpeed"];
  const patterns = ["A1", "A2", "B1", "B2", "C1", "C2", "D1", "D2"];
  const fbAbbr = {"OperationFB": "Op", "ActionFB": "Ac", "TaskFB": "Ta"};
  const metricAbbr = {"Time": "Ti", "Distance": "Di", "MaxSpeed": "Sp"};

  // Build a full trial plan first so pool sizes always match required counts.
  let trialPlan = [];
  for (let p = 1; p <= numParticipants; p++) {
    let fbOrderIdx = (p - 1) % 3;
    let pFbTypes = rotateArray(fbTypes, fbOrderIdx);
    let fbOrderString = pFbTypes.map(f => fbAbbr[f]).join("");

    pFbTypes.forEach((fb, fbIdx) => {
      let metricOrderIdx = (p + fbIdx - 1) % 3;
      let pMetrics = rotateArray(metrics, metricOrderIdx);
      let metricOrderString = pMetrics.map(m => metricAbbr[m]).join("");

      pMetrics.forEach((metric, mIdx) => {
        trialPlan.push({
          fb,
          metric,
          participant: p,
          order: mIdx + 1,
          fbOrderString,
          metricOrderString,
          poolKey: metricOrderString + "|" + metric,
        });
      });
    });
  }

  // Prepare balanced decks per metric-order and metric stratum.
  let stratumCounts = {};
  trialPlan.forEach(trial => {
    stratumCounts[trial.poolKey] = (stratumCounts[trial.poolKey] || 0) + 1;
  });

  let pools = {};
  Object.keys(stratumCounts).forEach(poolKey => {
    const totalRows = stratumCounts[poolKey] || 0;
    pools[poolKey] = {
      base: buildBalancedSequenceDeck(patterns, 2, totalRows),
      explore: buildBalancedSequenceDeck(patterns, 2, totalRows),
      best: buildBalancedSequenceDeck(patterns, 4, totalRows),
      inst: buildBalancedSequenceDeck(patterns, 4, totalRows),
      nofbInst: buildBalancedSequenceDeck(patterns, 4, totalRows),
    };
  });

  // 1. GENERATE THE DATA
  const headers = [
    "Condition", "Metric", "Participant", "Order", "FB Order", "Metric Order",
    "Baseline", "Explore", "BestPerf", "Instructed", "NoFeedbackInstructed"
  ];
  sheet.appendRow(headers);

  let data = [];
  trialPlan.forEach(trial => {
    const orderPool = pools[trial.poolKey];
    const baseline = orderPool.base.pop();
    const baselineSet = toTokenSet(baseline);

    // Prefer explore sequences with no token overlap to baseline.
    const explore = popFirstMatching(orderPool.explore, sequence =>
      isDisjointSet(toTokenSet(sequence), baselineSet)
    );

    const bestPerf = orderPool.best.pop();
    const instructed = orderPool.inst.pop();
    const noFeedbackInstructed = popFirstNonMatching(orderPool.nofbInst, instructed);

    data.push([
      trial.fb,
      trial.metric,
      trial.participant,
      trial.order,
      trial.fbOrderString,
      trial.metricOrderString,
      baseline,
      explore,
      bestPerf,
      instructed,
      noFeedbackInstructed,
    ]);
  });

  sheet.getRange(2, 1, data.length, headers.length).setValues(data);
  sheet.setFrozenRows(1);
}

// Helpers
function rotateArray(arr, shift) {
  let result = [...arr];
  for (let i = 0; i < shift; i++) { result.push(result.shift()); }
  return result;
}
function shuffleArray(array) {
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
  return array;
}

function buildBalancedSequenceDeck(tokens, seqLength, totalRows) {
  if (totalRows === 0) return [];

  const totalSlots = totalRows * seqLength;
  if (totalSlots % tokens.length !== 0) {
    throw new Error("Cannot evenly balance token usage for requested deck size.");
  }

  const perTokenTarget = totalSlots / tokens.length;

  // Retry generation to avoid rare dead-end selections.
  for (let attempt = 0; attempt < 80; attempt++) {
    let remaining = {};
    tokens.forEach(token => { remaining[token] = perTokenTarget; });

    let deck = [];
    let failed = false;

    for (let row = 0; row < totalRows; row++) {
      const sequence = takeUniqueTokens(remaining, seqLength);
      if (!sequence) {
        failed = true;
        break;
      }
      deck.push(sequence.join("-"));
    }

    if (failed) {
      continue;
    }

    const leftovers = Object.keys(remaining).some(token => remaining[token] !== 0);
    if (leftovers) {
      continue;
    }

    return shuffleArray(deck);
  }

  throw new Error("Failed to build balanced sequence deck after multiple attempts.");
}

function takeUniqueTokens(remaining, count) {
  let chosen = [];
  let chosenSet = {};

  for (let i = 0; i < count; i++) {
    const candidates = Object.keys(remaining).filter(token => remaining[token] > 0 && !chosenSet[token]);
    if (!candidates.length) {
      return null;
    }

    const picked = weightedPick(candidates, remaining);
    chosen.push(picked);
    chosenSet[picked] = true;
    remaining[picked] -= 1;
  }

  return shuffleArray(chosen);
}

function weightedPick(candidates, remaining) {
  let totalWeight = 0;
  candidates.forEach(token => { totalWeight += remaining[token]; });

  let r = Math.random() * totalWeight;
  for (let i = 0; i < candidates.length; i++) {
    const token = candidates[i];
    r -= remaining[token];
    if (r <= 0) {
      return token;
    }
  }

  return candidates[candidates.length - 1];
}

function popFirstMatching(pool, predicate) {
  if (!pool.length) return "";
  const idx = pool.findIndex(predicate);
  if (idx === -1) {
    return pool.pop();
  }

  const last = pool.length - 1;
  [pool[idx], pool[last]] = [pool[last], pool[idx]];
  return pool.pop();
}

function popFirstNonMatching(pool, forbiddenSequence) {
  if (!pool.length) return forbiddenSequence;

  let idx = pool.findIndex(value => value !== forbiddenSequence);
  if (idx === -1) {
    // If only matching values remain, rotate token order as deterministic fallback.
    const same = pool.pop();
    const tokens = same.split("-").filter(Boolean);
    if (tokens.length > 1) {
      const rotated = tokens.slice(1).concat(tokens.slice(0, 1));
      return rotated.join("-");
    }
    return same;
  }

  const last = pool.length - 1;
  [pool[idx], pool[last]] = [pool[last], pool[idx]];
  return pool.pop();
}

function toTokenSet(sequence) {
  const set = {};
  sequence.split("-").forEach(token => {
    if (token) {
      set[token] = true;
    }
  });
  return set;
}

function isDisjointSet(a, b) {
  for (let key in a) {
    if (b[key]) {
      return false;
    }
  }
  return true;
}