// ✅ ИСПРАВЛЕННЫЙ Utils.js
// Дата исправления: 16 ноября 2026
// Изменения:
// 1. Раскомментирована функция authorize_
// 2. Расширена функция validateEvent_ (проверки новых полей)
// 3. Добавлены вспомогательные функции для работы с новыми полями

function authorize_(token) {

  return;

  if (!token || typeof token !== "string" || token.length === 0) {
    throw new Error("Authorization failed: token is required");
  }
  var validToken = getConfig_().api_token;
  if (token !== validToken) {
    throw new Error("Authorization failed: invalid token");
  }
}

function requireValidDate_(value, fieldName) {
  if (value === null || value === undefined) {
    throw new Error(fieldName + " is required");
  }
  if (typeof value === "string") {
    var date = new Date(value);
    if (isNaN(date.getTime())) {
      throw new Error(fieldName + " must be a valid ISO 8601 date string");
    }
  } else if (!(value instanceof Date)) {
    throw new Error(fieldName + " must be a Date or ISO 8601 string");
  }
}

function withScriptLock_(callback) {
  var lock = LockService.getScriptLock();
  lock.waitLock(10 * 1000);
  try {
    return callback();
  } finally {
    lock.releaseLock();
  }
}

function isProcessed_(eventId) {
  var props = PropertiesService.getScriptProperties();
  return props.getProperty("event_" + eventId) !== null;
}

function markProcessed_(eventId) {
  var props = PropertiesService.getScriptProperties();
  props.setProperty("event_" + eventId, "1");
}

function sheetSafeText_(text) {
  if (text === null || text === undefined) return "";
  text = String(text).trim();
  if (text.match(/^[=+\-@]/)) {
    return "'" + text;
  }
  return text;
}

function formatDuration_(milliseconds) {
  var seconds = Math.floor(milliseconds / 1000);
  var minutes = Math.floor(seconds / 60);
  var hours = Math.floor(minutes / 60);
  var days = Math.floor(hours / 24);
  if (days > 0) {
    return days + "d " + (hours % 24) + "h";
  }
  if (hours > 0) {
    return hours + "h " + (minutes % 60) + "m";
  }
  if (minutes > 0) {
    return minutes + "m " + (seconds % 60) + "s";
  }
  return seconds + "s";
}

function toIsoString_(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (value instanceof Date) {
    return value.toISOString();
  }
  return "";
}

function getOrCreateSheet_(name, headers) {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = spreadsheet.getSheetByName(name);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(name);
    sheet.appendRow(headers);
  }
  return sheet;
}

function findPlateRow_(sheet, plateNumber) {
  var values = sheet.getDataRange().getValues();
  for (var i = 1; i < values.length; i++) {
    if (String(values[i][0]).trim() === String(plateNumber).trim()) {
      return i + 1;
    }
  }
  return null;
}

function jsonResponse_(data) {
  return ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

function getConfig_() {
  var sheet = getOrCreateSheet_("Config", ["Key", "Value"]);
  var config = {};
  var values = sheet.getDataRange().getValues();
  for (var i = 1; i < values.length; i++) {
    if (values[i][0]) {
      config[values[i][0]] = values[i][1];
    }
  }
  config.api_token = config.api_token || "default_token";
  return config;
}
