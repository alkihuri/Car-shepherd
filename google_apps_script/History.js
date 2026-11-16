// ✅ ИСПРАВЛЕННЫЙ History.js
// Дата исправления: 16 ноября 2026
// Изменения:
// 1. Добавлены столбцы: detected_make, status, camera_ids
// 2. Обновлена функция registerDeparture_

// ✅ НОВАЯ СТРУКТУРА ТАБЛИЦЫ
var HISTORY_HEADERS = [
  "Номер автомобиля",        // [0]
  "Марка (ручная)",          // [1] vehicle_make
  "Марка (распознана)",      // [2] detected_make ← НОВОЕ
  "Имя владельца",           // [3] owner_name
  "Фамилия владельца",       // [4] owner_surname
  "Дата и время прибытия",   // [5] first_seen
  "Дата и время выезда",     // [6] left_at
  "Статус",                  // [7] status ← НОВОЕ
  "Камеры",                  // [8] camera_ids ← НОВОЕ
  "Продолжительность нахождения" // [9] duration
];

// ✅ ОБНОВЛЕННАЯ ФУНКЦИЯ с новыми полями
function registerDeparture_(vehicle, leftAt) {
  var sheet = getOrCreateSheet_("Current Cars", CURRENT_CARS_HEADERS);
  var row = findPlateRow_(sheet, vehicle.plate_number);
  var arrival = new Date(vehicle.first_seen);
  var departure = new Date(leftAt);
  var history = getOrCreateSheet_("History", HISTORY_HEADERS);
  var cameraIds = vehicle.camera_ids ? vehicle.camera_ids.join(",") : "";
  history.appendRow([
    sheetSafeText_(vehicle.plate_number),
    sheetSafeText_(vehicle.vehicle_make || ""),
    sheetSafeText_(vehicle.detected_make || ""),           // ✅ ДОБАВЛЕНО
    sheetSafeText_(vehicle.owner_name || ""),
    sheetSafeText_(vehicle.owner_surname || ""),
    arrival,
    departure,
    sheetSafeText_(vehicle.status || "left"),             // ✅ ДОБАВЛЕНО
    sheetSafeText_(cameraIds),                            // ✅ ДОБАВЛЕНО
    formatDuration_(departure.getTime() - arrival.getTime())
  ]);
  if (row) sheet.deleteRow(row);
}
