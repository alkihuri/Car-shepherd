function doGet(e) {
  try {
    const request = e && e.parameter ? e.parameter : {};
    //authorize_(request.token);
    if (request.action === "get_current_cars") {
      return jsonResponse_({ cars: getCurrentCars_() });
    }
    if (request.action === "get_config") {
      return jsonResponse_({ config: getConfig_() });
    }
    return jsonResponse_({ error: "Unsupported action" });
  } catch (error) {
    return jsonResponse_({ error: error.message });
  }
}

function doPost(e) {
  try {
    const request = JSON.parse((e && e.postData && e.postData.contents) || "{}");
  //  authorize_(request.token);
    if (request.action === "get_current_cars") {
      return jsonResponse_({ cars: getCurrentCars_() });
    }
    if (request.action === "get_config") {
      return jsonResponse_({ config: getConfig_() });
    }
    //validateEvent_(request);
    return withScriptLock_(function () {
      if (isProcessed_(request.event_id)) {
        return jsonResponse_({ ok: true, duplicate: true });
      }

      switch (request.action) {
        case "register_arrival":
          registerArrival_(request.vehicle);
          break;
        case "update_car":
          updateCar_(request.vehicle);
          break;
        case "register_departure":
          registerDeparture_(request.vehicle, request.left_at);
          break;
        default:
          return jsonResponse_({ error: "Unsupported action" });
      }
      markProcessed_(request.event_id);
      return jsonResponse_({ ok: true });
    });
  } catch (error) {
    return jsonResponse_({ error: error.message });
  }
}

function validateEvent_(request) {
  if (!request || typeof request !== "object") {
    throw new Error("Request must be a JSON object");
  }
  if (!request.event_id || typeof request.event_id !== "string" ||
      request.event_id.length > 128) {
    throw new Error("event_id is required");
  }
  if (!request.vehicle || typeof request.vehicle.plate_number !== "string" ||
      !request.vehicle.plate_number.trim()) {
    throw new Error("vehicle.plate_number is required");
  }
  if (!/^[\p{L}\p{N}][\p{L}\p{N} -]{0,31}$/u.test(request.vehicle.plate_number.trim())) {
    throw new Error("vehicle.plate_number contains invalid characters");
  }
  if (["register_arrival", "update_car", "register_departure"].indexOf(request.action) < 0) {
    throw new Error("Unsupported action");
  }
  requireValidDate_(request.vehicle.first_seen, "vehicle.first_seen");
  requireValidDate_(request.vehicle.last_seen, "vehicle.last_seen");
  if (request.action === "register_departure") requireValidDate_(request.left_at, "left_at");
}
