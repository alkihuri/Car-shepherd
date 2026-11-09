function jsonResponse_(value) {
  return ContentService.createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}

function authorize_(providedToken) {
  var expectedToken = PropertiesService.getScriptProperties().getProperty("API_TOKEN");
  if (!expectedToken || !providedToken || providedToken !== expectedToken) {
    throw new Error("Unauthorized");
  }
}

function getOrCreateSheet_(name, headers) {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = spreadsheet.getSheetByName(name);
  if (!sheet) sheet = spreadsheet.insertSheet(name);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(headers);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function findPlateRow_(sheet, plateNumber) {
  if (sheet.getLastRow() < 2) return 0;
  var values = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).getValues();
  var normalized = String(plateNumber).trim().toUpperCase();
  for (var i = 0; i < values.length; i++) {
    if (String(values[i][0]).trim().toUpperCase() === normalized) return i + 2;
  }
  return 0;
}

function withScriptLock_(callback) {
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    return callback();
  } finally {
    lock.releaseLock();
  }
}

function isProcessed_(eventId) {
  return PropertiesService.getScriptProperties().getProperty("event_" + eventId) === "1";
}

function markProcessed_(eventId) {
  PropertiesService.getScriptProperties().setProperty("event_" + eventId, "1");
}

function toIsoString_(value) {
  if (!value) return "";
  var date = value instanceof Date ? value : new Date(value);
  return isNaN(date.getTime()) ? String(value) : date.toISOString();
}

function requireValidDate_(value, fieldName) {
  if (typeof value !== "string" || isNaN(Date.parse(value))) {
    throw new Error(fieldName + " must be a valid date string");
  }
}

function sheetSafeText_(value) {
  var text = String(value == null ? "" : value);
  return /^\s*[=+\-@]/.test(text) ? "'" + text : text;
}

function formatDuration_(milliseconds) {
  var totalMinutes = Math.max(0, Math.floor(milliseconds / 60000));
  var hours = Math.floor(totalMinutes / 60);
  var minutes = totalMinutes % 60;
  return hours + " ч " + minutes + " мин";
}
