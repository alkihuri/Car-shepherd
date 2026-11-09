var HISTORY_HEADERS = [
  "Номер автомобиля", "Марка автомобиля", "Имя владельца", "Фамилия владельца",
  "Дата и время прибытия", "Дата и время выезда", "Продолжительность нахождения"
];

function registerDeparture_(vehicle, leftAt) {
  var sheet = getOrCreateSheet_("Current Cars", CURRENT_CARS_HEADERS);
  var row = findPlateRow_(sheet, vehicle.plate_number);
  var arrival = new Date(vehicle.first_seen);
  var departure = new Date(leftAt);
  var history = getOrCreateSheet_("History", HISTORY_HEADERS);
  history.appendRow([
    sheetSafeText_(vehicle.plate_number),
    sheetSafeText_(vehicle.vehicle_make || ""),
    sheetSafeText_(vehicle.owner_name || ""),
    sheetSafeText_(vehicle.owner_surname || ""),
    arrival,
    departure,
    formatDuration_(departure.getTime() - arrival.getTime())
  ]);
  if (row) sheet.deleteRow(row);
}
