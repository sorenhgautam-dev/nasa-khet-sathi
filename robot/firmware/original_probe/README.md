# The probe's own sketch (USB only), unchanged

The robot teammate's working sketch, as the owner sent it on 2026-11-12. It is kept here byte for byte as
the reference for build step 10b (Wi-Fi and Firebase are added around it in `../khet_probe/`, without
changing how it reads or calibrates) and as the USB-only firmware to fall back to.

- Board: ESP32. Serial at 115200 baud, one line every 2 seconds:
  `Temperature: 23.1 °C  |  Moisture: 45%`, or `Temperature: Check wiring  |  Moisture: 45%`.
- Moisture: capacitive soil sensor on GPIO34 (an ADC1 pin, so it still reads while Wi-Fi is on).
  Raw reading mapped linearly from 2467 (dry, 0 %) to 660 (in water, 100 %), then limited to 0-100.
- Temperature: DS18B20 on GPIO4 (OneWire and DallasTemperature libraries), one decimal, deg C.
- No secrets in it.

`robot/bridge.py` reads these lines over USB (`tests/test_probe_bridge.py` checks the parser against the
print statements in this file).
