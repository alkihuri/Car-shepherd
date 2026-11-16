
function doGet(e) {
  try {
    const request = Object.assign({}, e && e.parameter ? e.parameter : {});

    console.log("ACTION: " + request.action);

    if (typeof request.vehicle === "string") {
      request.vehicle = JSON.parse(request.vehicle);
    }

    switch (request.action) {

      case "get_current_cars":
        return jsonResponse_({
          cars: getCurrentCars_()
        });

      case "get_config":
        return jsonResponse_({
          config: getConfig_()
        });

      case "register_arrival":

        if (!request.vehicle) {
          throw new Error("vehicle is missing");
        }

        if (!request.vehicle.plate_number) {
          throw new Error("plate_number is missing");
        }

        console.log(
          "REGISTER ARRIVAL VEHICLE: " +
          JSON.stringify(request.vehicle)
        );

        registerArrival_(request.vehicle);

        return jsonResponse_({ ok: true });

      case "update_car":

        if (!request.vehicle) {
          throw new Error("vehicle is missing");
        }

        updateCar_(request.vehicle);

        return jsonResponse_({ ok: true });

      case "register_departure":

        if (!request.vehicle) {
          throw new Error("vehicle is missing");
        }

        registerDeparture_(request.vehicle, request.left_at);

        return jsonResponse_({ ok: true });

      case "test_doget":

        return jsonResponse_({
          ok: true,
          received: request,
          first_seen: request.vehicle
            ? request.vehicle.first_seen
            : null
        });

      default:
        return jsonResponse_({
          error: "Unsupported action: " + request.action
        });
    }

  } catch (error) {

    console.error("DOGET ERROR: " + error.stack);

    return jsonResponse_({
      ok: false,
      error: error.message,
      stack: error.stack
    });
  }
}
