var CURRENT_CARS_HEADERS = [
  "Номер автомобиля", "Марка автомобиля", "Имя владельца", "Фамилия владельца",
  "Дата и время прибытия", "Последнее обнаружение", "Время нахождения"
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
        owner_name: values[i][2] || "",
        owner_surname: values[i][3] || "",
        first_seen: toIsoString_(values[i][4]),
        last_seen: toIsoString_(values[i][5]),
        duration: values[i][6] || ""
      });
    }
  }
  return cars;
}

function registerArrival_(vehicle) {
  var sheet = getOrCreateSheet_("Current Cars", CURRENT_CARS_HEADERS);
  var row = findPlateRow_(sheet, vehicle.plate_number);
  var values = currentCarRow_(vehicle);
  if (row) {
    sheet.getRange(row, 1, 1, values.length).setValues([values]);
  } else {
    sheet.appendRow(values);
  }
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

function currentCarRow_(vehicle) {
  var firstSeen = new Date(vehicle.first_seen);
  var lastSeen = new Date(vehicle.last_seen);
  return [
    sheetSafeText_(vehicle.plate_number),
    sheetSafeText_(vehicle.vehicle_make || ""),
    sheetSafeText_(vehicle.owner_name || ""),
    sheetSafeText_(vehicle.owner_surname || ""),
    firstSeen,
    lastSeen,
    formatDuration_(new Date().getTime() - firstSeen.getTime())
  ];
}
