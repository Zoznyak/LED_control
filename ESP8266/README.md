# ESP8266

## Flashelés

### Szükséges programok

1. ESPFlasher: https://github.com/nodemcu/nodemcu-flasher/tree/master/Win64/Release
2. Bináris: ESP8266_GENERIC-20250911-v1.26.1.bin 
3. VS Code
4. VS Code extension: 
    * MicroPico 4.3.3
    * Serial Monitor

### Flashelés lépései

#### Alap firmware flashelése

1. Az ESPFlasher megnyitása
2. Board csatlakoztatása
3. Port kiválasztása
4. Config fülön be kell tallozni a binárist (Pl. ESP8266_GENERIC-20250911-v1.26.1.bin )
5. Flash

#### Saját projekt feltöltése
1. VS Code megnyitása
2. Board csatlakoztatása
3. Terminal-ban látni kell, hogy csatlakozott "MicroPython v1.26.1 on 2025-09-11; ESP module with ESP8266"
4. Alsó sávban "Pico connected"
5. Alsó sávban "All commands" -> "Upload project to pico"
6. Ha minden jól megy megjelenik a VS Code-ban, hogy sikeres
7. Disconnect
8. RST gomb a boardon

#### Flash törlése
1. Szükséges tool-ok installálása:
    * pip install esptool
    * pip install setuptools
    * python -m esptool
2. Flash gomb nyomása a boardon és
    * python -m esptool --chip esp8266 erase_flash
3. Ha elindult el lehet engedni a gombot

### Debug
A serial monitor telepítése után a VS Code-on belül lehet monitorozni a kommunikációt. Ehhez disconnectelni kell a Picot, majd a "Serial monitor" fülön a Baud rate: 115200 és a megfelelő port(5).

## API
* POST /color?v=255.100.0 (R.G.B 0-255)
* POST /brightness?v=150 (0-255)
* POST /on
* POST /off

## Konfiguráció
A config.json tartalmazza a különböző konfigurációs értékeket. Ezt lokálisan kell létrehozni, a gitbe érzékeny adatok miatt nem kerül fel.
* "SSID": wifi neve
* "PASSWORD": wifi jelszó
* "LED_PIN_NUM": a boardon a LED-ekre vezérlésére használt pin száma (D1: 5)
* "NUM_LEDS": vezérelni kívánt LED-ek darabszáma
* "LED_STEP": ha nem akarjuk az összes LED-et vezérelni akkor itt adható meg minden hányadik LED legyen vezérelve
* "LISTEN_PORT"