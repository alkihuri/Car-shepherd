function testWorkflow() {
  try {
    // 1. Добавление машины с номерами BRDG491
    registerArrival_("BRDG491", {
      plate_number: "BRDG491",
      vehicle_make: "Toyota",
      vehicle_coloe : "Red",
      owner_name: "John",
      owner_surname: "Doe",
      first_seen: new Date().toISOString()
    });

    // 2. Обновление состояния BRDG491
    updateCar_("BRDG491", {
      plate_number: "BRDG491",
      vehicle_make: "Toyota",
      vehicle_coloe : "Red",
      owner_name: "John",
      owner_surname: "Doe",
      last_seen: new Date().toISOString()
    });

    // 3. Удаление машины
    //removeCurrentCar_("BRDG491");

    // 4. Тестовый метод который вывод список всех активных машин
    var currentCars = getCurrentCars_();
    Logger.log("Current Cars: " + JSON.stringify(currentCars));

    // 5. Поиск по номеру
    var foundCar = findCarByPlateNumber_("BRDG491");
    if (foundCar) {
      Logger.log("Found Car: " + JSON.stringify(foundCar));
    } else {
      Logger.log("Car not found");
    }

  } catch (error) {
    Logger.log("Error: " + error.message);
  }
}

 

function registerArrival_(plateNumber, vehicle) {
  var sheet = getOrCreateSheet_("Current Cars", CURRENT_CARS_HEADERS);
  var row = findPlateRow_(sheet, plateNumber);
  var values = currentCarRow_(vehicle);
  if (row) {
    sheet.getRange(row, 1, 1, values.length).setValues([values]);
  } else {
    sheet.appendRow(values);
  }
}

function updateCar_(plateNumber, vehicle) {
  var sheet = getOrCreateSheet_("Current Cars", CURRENT_CARS_HEADERS);
  var row = findPlateRow_(sheet, plateNumber);
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

function findCarByPlateNumber_(plateNumber) {
  var sheet = getOrCreateSheet_("Current Cars", CURRENT_CARS_HEADERS);
  var row = findPlateRow_(sheet, plateNumber);
  if (row) {
    var values = sheet.getRange(row, 1, 1, sheet.getLastColumn()).getValues()[0];
    return {
      plate_number: String(values[0]),
      vehicle_make: values[1] || "",
      owner_name: values[2] || "",
      owner_surname: values[3] || "",
      first_seen: toIsoString_(values[4]),
      last_seen: toIsoString_(values[5]),
      duration: values[6] || ""
    };
  }
  return null;
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

function findPlateRow_(sheet, plateNumber) {
  if (sheet.getLastRow() < 2) return 0;
  var values = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).getValues();
  var normalized = String(plateNumber).trim().toUpperCase();
  for (var i = 0; i < values.length; i++) {
    if (String(values[i][0]).trim().toUpperCase() === normalized) return i + 2;
  }
  return 0;
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
