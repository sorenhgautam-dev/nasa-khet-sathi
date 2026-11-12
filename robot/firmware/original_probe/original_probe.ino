#include <OneWire.h>
#include <DallasTemperature.h>

// ESP32 pins connected to the sensors
const int MOISTURE_PIN = 34;  // Connect to AOUT on the soil sensor
const int TEMP_PIN = 4;       // Connect to S on the temperature sensor

// Adjust these two numbers if your percentage needs fine-tuning
const int DRY_VALUE = 2467;   // Reading when the sensor is completely dry (0%)
const int WET_VALUE = 660;   // Reading when the sensor is in water (100%)

OneWire oneWire(TEMP_PIN);
DallasTemperature tempSensor(&oneWire);

void setup() {
  Serial.begin(115200);
  tempSensor.begin();
}

void loop() {
  // Get temperature in Celsius
  tempSensor.requestTemperatures();
  float temperature = tempSensor.getTempCByIndex(0);

  // Get soil moisture and convert it to a 0% - 100% scale
  int sensorReading = analogRead(MOISTURE_PIN);
  int moisturePercent = map(sensorReading, DRY_VALUE, WET_VALUE, 0, 100);
  moisturePercent = constrain(moisturePercent, 0, 100);

  // Print temperature first, then moisture percentage
  Serial.print("Temperature: ");
  if (temperature == DEVICE_DISCONNECTED_C) {
    Serial.print("Check wiring");
  } else {
    Serial.print(temperature, 1);
    Serial.print(" °C");
  }

  Serial.print("  |  Moisture: ");
  Serial.print(moisturePercent);
  Serial.println("%");

  delay(2000); // Update every 2 seconds
}
