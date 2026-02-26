/**
 * MASTER VALIDATOR: 
 * 1. Validates FB and Metric Position (Latin Square)
 * 2. Validates Total Letter Distribution (A,B,C,D)
 * 3. Analyzes Pairings for all 4 pattern columns (Baseline, Explore, BestPerf, Instructed)
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
  
  // Configuration for the 4 pattern columns
  let pairingConfigs = [
    { index: 6, label: "Baseline", target: 6, data: {} },
    { index: 7, label: "Explore", target: 6, data: {} },
    { index: 8, label: "BestPerf", target: 3, data: {} },
    { index: 9, label: "Instructed", target: 3, data: {} }
  ];

  const letters = ["A", "B", "C", "D"];
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

    // B. Letter Distribution Logic
    if (!patternMetricMap[metric]) patternMetricMap[metric] = {A:0, B:0, C:0, D:0};
    let allPatternsInRow = (data[i][6]||"") + (data[i][7]||"") + (data[i][8]||"") + (data[i][9]||"");
    letters.forEach(L => {
      let count = (allPatternsInRow.split(L).length - 1);
      patternMetricMap[metric][L] += count;
    });

    // C. Multi-Column Pairing Logic
    pairingConfigs.forEach(config => {
      let patternValue = data[i][config.index];
      let pairKey = metricOrderStr + " + " + patternValue;
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

  // Table 4-7: Pairing Analysis (Baseline, Explore, BestPerf, Instructed)
  pairingConfigs.forEach(config => {
    sheet.getRange(outputRow, startCol).setValue(config.label + " Pairing (Target: " + config.target + ")").setFontWeight("bold");
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
  sheet.getRange(row, col).setValue("Total Letter Balance (Target 216)").setFontWeight("bold");
  sheet.getRange(row + 1, col, 1, 5).setValues([["Metric", "A", "B", "C", "D"]]).setBackground("#eeeeee");
  let currRow = row + 2;
  for (let m in patternMetricMap) {
    let rowData = [m, patternMetricMap[m].A, patternMetricMap[m].B, patternMetricMap[m].C, patternMetricMap[m].D];
    let range = sheet.getRange(currRow, col, 1, 5);
    range.setValues([rowData]);
    rowData.forEach((v, idx) => { if(idx > 0) range.getCell(1, idx+1).setBackground(v === 216 ? "#b6d7a8" : "#ea9999"); });
    currRow++;
  }
}