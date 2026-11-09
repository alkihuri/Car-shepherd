var CONFIG_DEFAULTS = {
  telegram_enabled: false,
  notify_on_arrival: true,
  notify_on_departure: true,
  telegram_chat_id: "",
  scan_interval: 30,
  departure_timeout: 300,
  recognition_confidence_threshold: 0.8
};

function getConfig_() {
  var sheet = getOrCreateSheet_("Config", ["Parameter", "Value"]);
  var values = sheet.getDataRange().getValues();
  var config = {};
  for (var i = 1; i < values.length; i++) {
    var key = String(values[i][0] || "").trim();
    if (key) {
      config[key] = parseConfigValue_(key, values[i][1]);
    }
  }
  Object.keys(CONFIG_DEFAULTS).forEach(function (key) {
    if (typeof config[key] === "undefined" || config[key] === "") {
      config[key] = CONFIG_DEFAULTS[key];
    }
  });
  return config;
}

function parseConfigValue_(key, value) {
  if (key === "telegram_enabled" || key === "notify_on_arrival" || key === "notify_on_departure") {
    if (value === true || String(value).toUpperCase() === "TRUE") return true;
    if (value === false || String(value).toUpperCase() === "FALSE") return false;
    throw new Error("Invalid Boolean value for " + key);
  }
  if (key === "scan_interval" || key === "departure_timeout" ||
      key === "recognition_confidence_threshold") {
    var number = Number(value);
    if (!isFinite(number) ||
        (key !== "recognition_confidence_threshold" && number <= 0) ||
        (key === "recognition_confidence_threshold" && (number < 0 || number > 1))) {
      throw new Error("Invalid numeric value for " + key);
    }
    return number;
  }
  return String(value == null ? "" : value);
}
