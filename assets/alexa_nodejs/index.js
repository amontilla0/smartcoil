/** This is the nodeJS function used in AWS Lambda to enable the Alexa Smart Home skill.
*/
const tok = '<simple-auth-token-here>';

exports.handler = function (request, context) {
    if (request.directive.header.namespace === 'Alexa.Discovery' && request.directive.header.name === 'Discover') {
        handleDiscovery(request, context, "");
    }
    else {
        handleSmartcoilControl(request, context);
    }

    function handleDiscovery(request, context) {
      /*The skill has three types of interfaces defined in the discovery payload:
      - ThermostatController, which controls the SmartCoil on/off status as well as target
          temperature.
      - TemperatureSensor, which gets current indoor temperature info.
      - RangeController, which controls the SmartCoil's fan speed to low, medium or high.
      */
        var payload = {
            "endpoints":
            [
                {
                    "endpointId": "smartcoil_id",
                    "manufacturerName": "SmartCoil",
                    "friendlyName": "smartcoil",
                    "description": "Smart Fancoil Unit",
                    "displayCategories": ["THERMOSTAT"],
                    "capabilities": [{
                        "type": "AlexaInterface",
                        "interface": "Alexa.ThermostatController",
                        "version": "3",
                        "properties": {
                          "supported": [{
                              "name": "targetSetpoint"
                            },
                            {
                              "name": "thermostatMode"
                            }
                          ],
                          "proactivelyReported": true,
                          "retrievable": true
                        },
                        "configuration": {
                          "supportsScheduling": false,
                          "supportedModes": [
                            "HEAT",
                            "COOL",
                          ]
                        }
                      },
                      {
                          "type": "AlexaInterface",
                          "interface": "Alexa.TemperatureSensor",
                          "version": "3",
                          "properties": {
                              "supported": [
                                  {
                                      "name": "temperature"
                                  }
                              ],
                              "proactivelyReported": true,
                              "retrievable": true
                          }
                      },
                      {
                          "type": "AlexaInterface",
                          "interface": "Alexa.RangeController",
                          "version": "3",
                          "instance": "Fancoil.Speed",
                          "capabilityResources": {
                            "friendlyNames": [
                              {
                                "@type": "asset",
                                "value": {
                                  "assetId": "Alexa.Setting.FanSpeed"
                                }
                              }
                            ]
                          },
                          "properties": {
                            "supported": [
                              {
                                "name": "rangeValue"
                              }
                            ],
                            "proactivelyReported": true,
                            "retrievable": true
                          },
                          "configuration": {
                            "supportedRange": {
                              "minimumValue": 1,
                              "maximumValue": 3,
                              "precision": 1
                            },
                            "presets": [
                              {
                                "rangeValue": 1,
                                "presetResources": {
                                  "friendlyNames": [
                                    {
                                      "@type": "asset",
                                      "value": {
                                        "assetId": "Alexa.Value.Minimum"
                                      }
                                    },
                                    {
                                      "@type": "asset",
                                      "value": {
                                        "assetId": "Alexa.Value.Low"
                                      }
                                    },
                                    {
                                      "@type": "text",
                                      "value": {
                                        "text": "Lowest",
                                        "locale": "en-US"
                                      }
                                    }
                                  ]
                                }
                              },

                              {
                                "rangeValue": 2,
                                "presetResources": {
                                  "friendlyNames": [
                                    {
                                      "@type": "asset",
                                      "value": {
                                        "assetId": "Alexa.Value.Medium"
                                      }
                                    }
                                  ]
                                }
                              },

                              {
                                "rangeValue": 3,
                                "presetResources": {
                                  "friendlyNames": [
                                    {
                                      "@type": "asset",
                                      "value": {
                                        "assetId": "Alexa.Value.Maximum"
                                      }
                                    },
                                    {
                                      "@type": "asset",
                                      "value": {
                                        "assetId": "Alexa.Value.High"
                                      }
                                    },
                                    {
                                      "@type": "text",
                                      "value": {
                                        "text": "Highest",
                                        "locale": "en-US"
                                      }
                                    }
                                  ]
                                }
                              }
                            ]
                          }
                        }
                    ]
                }
            ]
        };
        var header = request.directive.header;
        header.name = "Discover.Response";
        context.succeed({ event: { header: header, payload: payload } });
    }

    async function handleSmartcoilControl(request, context) {
        var requestNamespace = request.directive.header.namespace;
        var requestMethod = request.directive.header.name;
        var response = null;
        var value = null;

        if (requestNamespace === 'Alexa.ThermostatController' && requestMethod === "SetThermostatMode") {
          value = request.directive.payload.thermostatMode.value;
          var action = value !== "OFF" ? "on" : "off";
          response = JSON.parse(JSON.parse(await  turn_smartcoil(action, request)));
        }
        else if (requestNamespace === 'Alexa.ThermostatController' && requestMethod === "SetTargetTemperature") {
          value = request.directive.payload.targetSetpoint.value;
          response = JSON.parse(JSON.parse(await set_smartcoil_temperature(value, request)));
        }
        else if (requestNamespace  === 'Alexa.RangeController' && requestMethod === "SetRangeValue") {
          value = request.directive.payload.rangeValue;
          response = JSON.parse(JSON.parse(await set_smartcoil_speed(value, request)));
        }
        else if (requestNamespace === 'Alexa' && requestMethod === "ReportState") {
          response = JSON.parse(JSON.parse(await get_smartcoil_state(request)));
        }

        context.succeed(response);
    }

    function tell_smartcoil(service, data) {
        var https = require('https');

        var options = {
          hostname: 'abemo.pagekite.me',
          port: 443,
          path: service,
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(data)
          }
        };

        var prom = new Promise((resolve, reject) => {
          const request = https.request(options, (response) => {
            response.setEncoding('utf8');
            let returnData = '';
            if (response.statusCode < 200 || response.statusCode >= 300) {
              reject('server error: ' + response.statusCode);
            }
            response.on('data', (chunk) => {
              returnData += chunk;
            });
            response.on('end', () => {
              resolve(JSON.stringify(returnData));
            });
            response.on('error', (error) => {
              reject('internal error: ' + error);
            });
          });
          request.write(data);
          request.end();
        }
      );

      return prom;
    }

    function turn_smartcoil(action, req) {
        var service = '/turn_smartcoil'
        var data = JSON.stringify({
          token: tok,
          switch: action,
          request: req
        });

        return tell_smartcoil(service, data);
    }

    function set_smartcoil_temperature(temp, req) {
      var service = '/set_smartcoil_temperature'
      var data = JSON.stringify({
        token: tok,
        temperature: temp,
        request: req
      })

      return tell_smartcoil(service, data)
    }

    function set_smartcoil_speed(sp, req) {
      var service = '/set_smartcoil_speed'
      var data = JSON.stringify({
        token: tok,
        speed: sp,
        request: req
      })

      return tell_smartcoil(service, data)
    }

    function get_smartcoil_state(req) {
      var service = '/get_smartcoil_state'
      var data = JSON.stringify({
        token: tok,
        request: req
      })

      return tell_smartcoil(service, data)
    }
};
