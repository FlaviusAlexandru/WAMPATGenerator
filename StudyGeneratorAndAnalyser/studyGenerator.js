/**
 * GENERATOR: Fully Balanced HCI Study.
 * Ensures Baseline/Explore (Target 6) and BestPerf/Instructed (Target 3) 
 * are perfectly balanced against every Metric Order.
 */
function generateHCIStudy() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getActiveSheet();
  sheet.clear();
  
  const numParticipants = 24;
  const fbTypes = ["OperationFB", "ActionFB", "TaskFB"];
  const metrics = ["Time", "Distance", "MaxSpeed"];
  const patterns = ["A", "B", "C", "D"];
  const fbAbbr = {"OperationFB": "Op", "ActionFB": "Ac", "TaskFB": "Ta"};
  const metricAbbr = {"Time": "Ti", "Distance": "Di", "MaxSpeed": "Sp"};

  // 1. PRE-CALCULATE PERMUTATIONS
  // 2-letter permutations (12 total)
  let perms2 = [];
  for (let i=0; i<4; i++) for (let j=0; j<4; j++) if (i!==j) perms2.push(patterns[i]+patterns[j]);

  // 4-letter permutations (24 total)
  let perms4 = [];
  function getPerms4(current, remaining) {
    if (remaining.length === 0) { perms4.push(current); return; }
    for (let i=0; i<remaining.length; i++) {
      getPerms4(current + remaining[i], remaining.slice(0,i).concat(remaining.slice(i+1)));
    }
  }
  getPerms4("", patterns);

  // 2. BUILD DECKS FOR EACH METRIC ORDER
  let pools = { 
    "TiDiSp": { base: [], best: [], inst: [], nofbInst: [] }, 
    "DiSpTi": { base: [], best: [], inst: [], nofbInst: [] }, 
    "SpTiDi": { base: [], best: [], inst: [], nofbInst: [] } 
  };

  Object.keys(pools).forEach(orderKey => {
    // Fill Baseline Pool (12 perms * 6 = 72)
    perms2.forEach(p => { for(let i=0; i<6; i++) pools[orderKey].base.push(p); });
    // Fill BestPerf, Instructed, and NoFeedbackInstructed pools (24 perms * 3 = 72 each)
    perms4.forEach(p => { 
      for(let i=0; i<3; i++) {
        pools[orderKey].best.push(p);
        pools[orderKey].inst.push(p);
        pools[orderKey].nofbInst.push(p);
      }
    });
    // Shuffle all decks
    shuffleArray(pools[orderKey].base);
    shuffleArray(pools[orderKey].best);
    shuffleArray(pools[orderKey].inst);
    shuffleArray(pools[orderKey].nofbInst);
  });

  // 3. GENERATE THE DATA
  const headers = [
    "Condition", "Metric", "Participant", "Order", "FB Order", "Metric Order",
    "Baseline", "Explore", "BestPerf", "Instructed", "NoFeedbackInstructed"
  ];
  sheet.appendRow(headers);

  let data = [];
  for (let p = 1; p <= numParticipants; p++) {
    let fbOrderIdx = (p - 1) % 3; 
    let pFbTypes = rotateArray(fbTypes, fbOrderIdx);
    let fbOrderString = pFbTypes.map(f => fbAbbr[f]).join("");

    pFbTypes.forEach((fb, fbIdx) => {
      let metricOrderIdx = (p + fbIdx - 1) % 3;
      let pMetrics = rotateArray(metrics, metricOrderIdx);
      let metricOrderString = pMetrics.map(m => metricAbbr[m]).join("");

      pMetrics.forEach((metric, mIdx) => {
        // Draw from the specialized decks
        let baseline = pools[metricOrderString].base.pop();
        let bestPerf = pools[metricOrderString].best.pop();
        let instructed = pools[metricOrderString].inst.pop();
        let noFeedbackInstructed = popFirstNonMatching(pools[metricOrderString].nofbInst, instructed);
        
        // Explore is derived from Baseline to avoid letter repetition
        let remaining = patterns.filter(char => !baseline.includes(char));
        let explore = shuffleArray([...remaining]).join("");

        data.push([
          fb, metric, p, mIdx + 1, fbOrderString, metricOrderString,
          baseline, explore, bestPerf, instructed, noFeedbackInstructed
        ]);
      });
    });
  }

  sheet.getRange(2, 1, data.length, headers.length).setValues(data);
  sheet.setFrozenRows(1);
}

// Helpers (unchanged)
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

function popFirstNonMatching(pool, forbidden) {
  if (!pool.length) return forbidden;

  let idx = pool.findIndex(value => value !== forbidden);
  if (idx === -1) {
    // If only matching values remain, return a rotated fallback to keep it distinct.
    let same = pool.pop();
    if (same.length > 1) return same.slice(1) + same[0];
    return same;
  }

  let last = pool.length - 1;
  [pool[idx], pool[last]] = [pool[last], pool[idx]];
  return pool.pop();
}