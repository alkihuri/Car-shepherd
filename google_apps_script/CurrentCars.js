// ✅ ИСПРАВЛЕННЫЙ CurrentCars.js
// Дата исправления: 16 ноября 2026
// Изменения:
// 1. Добавлены столбцы: detected_make, status, camera_ids
// 2. Обновлена функция currentCarRow_

// ✅ НОВАЯ СТРУКТУРА ТАБЛИЦЫ
var CURRENT_CARS_HEADERS = [
  "Номер автомобиля",        // [0]
  "Марка (ручная)",          // [1] vehicle_make
  "Марка (распознана)",      // [2] detected_make ← НОВОЕ
  "Имя владельца",           // [3] owner_name
  "Фамилия владельца",       // [4] owner_surname
  "Дата и время прибытия",   // [5] first_seen
  "Последнее обнаружение",   // [6] last_seen
  "Статус",                  // [7] status ← НОВОЕ
  "Камеры",                  // [8] camera_ids ← НОВОЕ
  "Время нахождения"         // [9] duration
];

function getCurrentCars_() {
  var sheet = getOrCreateSheet_("Current Cars", CURRENT_CARS_HEADERS);
  var values = sheet.getDataRange().getValues();
  var cars = [];
  for (var i = 1; i < values.length; i++) {
    if (values[i][0]) {
      cars.push({
        plate_number: String(values[i][0]),
        vehicle_make: values[i][1] || "",
        detected_make: values[i][2] || "",        // ✅ ДОБАВЛЕНО
        owner_name: values[i][3] || "",
        owner_surname: values[i][4] || "",
        first_seen: toIsoString_(values[i][5]),
        last_seen: toIsoString_(values[i][6]),
        status: values[i][7] || "present",        // ✅ ДОБАВЛЕНО
        camera_ids: (values[i][8] || "").split(",").filter(x => x) // ✅ ДОБАВЛЕНО
      });
    }
  }
  return cars;
}

function registerArrival_(vehicle) {
  console.log("REGISTER ARRIVAL START");
  console.log("VEHICLE: " + JSON.stringify(vehicle));
  console.log("FIRST SEEN: " + vehicle.first_seen);

  var sheet = getOrCreateSheet_("Current Cars", CURRENT_CARS_HEADERS);

  var row = findPlateRow_(sheet, vehicle.plate_number);

  var values = currentCarRow_(vehicle);

  console.log("ROW VALUES: " + JSON.stringify(values));

  if (row) {
    sheet.getRange(row, 1, 1, values.length).setValues([values]);
  } else {
    sheet.appendRow(values);
  }

  console.log("REGISTER ARRIVAL SUCCESS");
}

function updateCar_(vehicle) {
  var sheet = getOrCreateSheet_("Current Cars", CURRENT_CARS_HEADERS);
  var row = findPlateRow_(sheet, vehicle.plate_number);
  var values = currentCarRow_(vehicle);
  if (row) {
    sheet.getRange(row, 1, 1, values.length).setValues([values]);
  } else {
    sheet.appendRow(values);
  }
}

function removeCurrentCar_(plateNumber) {
  var sheet = getOrCreateSheet_("Current Cars", CURRENT_CARS_HEADERS);
  var row = findPlateRow_(sheet, plateNumber);
  if (row) sheet.deleteRow(row);
}

// ✅ ОБНОВЛЕННАЯ ФУНКЦИЯ с новыми полями

function currentCarRow_(vehicle) {
  var now = new Date();

  var firstSeen = vehicle.first_seen
    ? new Date(vehicle.first_seen)
    : now;

  var lastSeen = vehicle.last_seen
    ? new Date(vehicle.last_seen)
    : now;

  // Проверяем корректность дат
  if (isNaN(firstSeen.getTime())) {
    firstSeen = now;
  }

  if (isNaN(lastSeen.getTime())) {
    lastSeen = now;
  }

  var cameraIds = Array.isArray(vehicle.camera_ids)
    ? vehicle.camera_ids.join(",")
    : "";

  return [
    sheetSafeText_(vehicle.plate_number || ""),
    sheetSafeText_(vehicle.vehicle_make || ""),
    sheetSafeText_(vehicle.detected_make || ""),
    sheetSafeText_(vehicle.owner_name || ""),
    sheetSafeText_(vehicle.owner_surname || ""),
    firstSeen,
    lastSeen,
    sheetSafeText_(vehicle.status || "present"),
    sheetSafeText_(cameraIds),
    formatDuration_(now.getTime() - firstSeen.getTime())
  ];
}

