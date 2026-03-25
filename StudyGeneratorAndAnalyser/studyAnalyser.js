/**
 * MASTER VALIDATOR: 
 * 1. Validates FB and Metric Position (Latin Square)
 * 2. Validates total letter and token distribution from tokenized patterns
 * 3. Analyzes Pairings for all 5 pattern columns (Baseline, Explore, BestPerf, Instructed, NoFeedbackInstructed)
 */
function validateStudyBalance() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const startCol = sheet.getLastColumn() + 2; 
  
  // 1. INITIALIZE TRACKING MAPS
  let fbPositionMap = {"1":{}, "2":{}, "3":{}}; 
  let metricPositionMap = {"1":{}, "2":{}, "3":{}, "4":{}, "5":{}, "6":{}, "7":{}, "8":{}, "9":{}};
  let patternMetricMap = {};
  let tokenMetricMap = {};
  
  // Configuration for the 5 pattern columns
  let pairingConfigs = [
    { index: 6, label: "Baseline", data: {} },
    { index: 7, label: "Explore", data: {} },
    { index: 8, label: "BestPerf", data: {} },
    { index: 9, label: "Instructed", data: {} },
    { index: 10, label: "NoFeedbackInstructed", data: {} }
  ];

  const patternTokens = ["A1", "A2", "B1", "B2", "C1", "C2", "D1", "D2"];
  const fbTypes = ["OperationFB", "ActionFB", "TaskFB"];
  const metrics = ["Time", "Distance", "MaxSpeed"];
  let currentFBOrder = ""; 

  // 2. SINGLE PASS DATA PROCESSING
  for (let i = 1; i < data.length; i++) {
    let condition = data[i][0].toString().trim();   
    let metric = data[i][1].toString().trim();      
    let pOrder = data[i][3];      
    let fbOrderStr = data[i][4].toString().trim(); 
    let metricOrderStr = data[i][5].toString().trim(); 

    if (fbOrderStr !== "") currentFBOrder = fbOrderStr;

    // A. Position Logic
    let fbAbbr = condition.substring(0, 2);
    let fbBlockPos = (currentFBOrder.indexOf(fbAbbr) / 2) + 1;
    if (isNaN(fbBlockPos) || fbBlockPos < 1) fbBlockPos = 1; 
    let globalTrialNum = ((Math.floor(fbBlockPos) - 1) * 3) + pOrder;

    fbPositionMap[fbBlockPos.toString()][condition] = (fbPositionMap[fbBlockPos.toString()][condition] || 0) + 1;
    metricPositionMap[globalTrialNum.toString()][metric] = (metricPositionMap[globalTrialNum.toString()][metric] || 0) + 1;

    // B. Letter and token distribution logic
    if (!patternMetricMap[metric]) patternMetricMap[metric] = {A:0, B:0, C:0, D:0};
    if (!tokenMetricMap[metric]) tokenMetricMap[metric] = {A1:0, A2:0, B1:0, B2:0, C1:0, C2:0, D1:0, D2:0};

    pairingConfigs.forEach(config => {
      let tokens = parsePatternTokens(data[i][config.index]);

      // Count letter and token usage from parsed token list.
      tokens.forEach(token => {
        let letter = token.charAt(0);
        if (patternMetricMap[metric][letter] !== undefined) {
          patternMetricMap[metric][letter] += 1;
        }
        if (tokenMetricMap[metric][token] !== undefined) {
          tokenMetricMap[metric][token] += 1;
        }
      });

      // Normalize sequence style for cleaner pairing aggregation.
      let normalizedPattern = tokens.join("-");
      let pairKey = metricOrderStr + " + " + normalizedPattern;
      config.data[pairKey] = (config.data[pairKey] || 0) + 1;
    });
  }

  // 3. RENDERING TABLES
  let outputRow = 1;

  // Table 1 & 2: Positions
  renderSimpleTable(sheet, outputRow, startCol, "FB Position (Target 24)", ["Block", ...fbTypes], fbPositionMap, fbTypes, 24);
  outputRow += 6;
  renderSimpleTable(sheet, outputRow, startCol, "Metric Position (Target 8)", ["Trial", ...metrics], metricPositionMap, metrics, 8);
  outputRow += 12;

  // Table 3: Letter Totals
  renderLetterTable(sheet, outputRow, startCol, patternMetricMap);
  outputRow += 7;

  // Table 4: Token Totals
  renderTokenTable(sheet, outputRow, startCol, tokenMetricMap, patternTokens);
  outputRow += 7;

  // Pairing Analysis (Baseline, Explore, BestPerf, Instructed, NoFeedbackInstructed)
  pairingConfigs.forEach(config => {
    sheet.getRange(outputRow, startCol).setValue(config.label + " Pairing").setFontWeight("bold");
    outputRow++;

    let sorted = Object.keys(config.data).map(key => [key, config.data[key]]);
    sorted.sort((a, b) => b[1] - a[1]);

    let mostFreq = sorted.slice(0, 3);
    let leastFreq = sorted.slice(-3).reverse();

    sheet.getRange(outputRow, startCol, 1, 2).setValues([["Most Frequent", "Count"]]).setBackground("#d9ead3");
    outputRow++;
    sheet.getRange(outputRow, startCol, mostFreq.length, 2).setValues(mostFreq);
    outputRow += mostFreq.length;

    sheet.getRange(outputRow, startCol, 1, 2).setValues([["Least Frequent", "Count"]]).setBackground("#f4cccc");
    outputRow++;
    sheet.getRange(outputRow, startCol, leastFreq.length, 2).setValues(leastFreq);
    outputRow += 2; 
  });

  sheet.autoResizeColumns(startCol, startCol + 1);
}

/** Helper: Positional Tables */
function renderSimpleTable(sheet, row, col, title, headers, map, keys, target) {
  sheet.getRange(row, col).setValue(title).setFontWeight("bold");
  sheet.getRange(row + 1, col, 1, headers.length).setValues([headers]).setBackground("#eeeeee");
  let currRow = row + 2;
  for (let id in map) {
    let values = [id, ...keys.map(k => map[id][k] || 0)];
    let range = sheet.getRange(currRow, col, 1, headers.length);
    range.setValues([values]);
    values.forEach((v, idx) => { if(idx > 0) range.getCell(1, idx+1).setBackground(v === target ? "#b6d7a8" : "#ea9999"); });
    currRow++;
  }
}

/** Helper: Letter Table */
function renderLetterTable(sheet, row, col, patternMetricMap) {
  sheet.getRange(row, col).setValue("Total Letter Balance (dynamic target per metric)").setFontWeight("bold");
  sheet.getRange(row + 1, col, 1, 5).setValues([["Metric", "A", "B", "C", "D"]]).setBackground("#eeeeee");
  let currRow = row + 2;
  for (let m in patternMetricMap) {
    let rowData = [m, patternMetricMap[m].A, patternMetricMap[m].B, patternMetricMap[m].C, patternMetricMap[m].D];
    let total = patternMetricMap[m].A + patternMetricMap[m].B + patternMetricMap[m].C + patternMetricMap[m].D;
    let target = total / 4;
    let range = sheet.getRange(currRow, col, 1, 5);
    range.setValues([rowData]);
    rowData.forEach((v, idx) => {
      if (idx > 0) {
        range.getCell(1, idx + 1).setBackground(v === target ? "#b6d7a8" : "#ea9999");
      }
    });
    currRow++;
  }
}

/** Helper: Token Table */
function renderTokenTable(sheet, row, col, tokenMetricMap, patternTokens) {
  const headers = ["Metric", ...patternTokens];
  sheet.getRange(row, col).setValue("Total Token Balance (dynamic target per metric)").setFontWeight("bold");
  sheet.getRange(row + 1, col, 1, headers.length).setValues([headers]).setBackground("#eeeeee");

  let currRow = row + 2;
  for (let m in tokenMetricMap) {
    let tokenCounts = patternTokens.map(token => tokenMetricMap[m][token]);
    let rowData = [m, ...tokenCounts];
    let total = tokenCounts.reduce((sum, value) => sum + value, 0);
    let target = total / patternTokens.length;
    let range = sheet.getRange(currRow, col, 1, headers.length);
    range.setValues([rowData]);
    rowData.forEach((v, idx) => {
      if (idx > 0) {
        range.getCell(1, idx + 1).setBackground(v === target ? "#b6d7a8" : "#ea9999");
      }
    });
    currRow++;
  }
}

function parsePatternTokens(value) {
  const raw = (value || "").toString().toUpperCase().trim();
  if (!raw) return [];

  // New format: A1-B2-C1 etc.
  const halfTokens = raw.match(/[ABCD][12]/g);
  if (halfTokens && halfTokens.length) {
    return halfTokens;
  }

  // Legacy fallback: ABCD
  const fullTokens = raw.match(/[ABCD]/g);
  return fullTokens || [];
}