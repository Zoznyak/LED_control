import network
import socket
import machine
import neopixel
import time
import json

# Alapértelmezett értékek
SSID = ""
PASSWORD = ""
LED_PIN_NUM = 5  # D1 pin az ESP8266-on
NUM_LEDS = 10   # Kanapé 120, TV 180 
LED_STEP = 2
LISTEN_PORT = 80
CONFIG_FILE = 'config.json'

# --- Konfiguráció betöltése ---
try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        # A 'get' metódus biztonságos: ha a kulcs létezik, az értékét adja,
        # ha nem, akkor a második argumentumként megadott alapértelmezett értéket.
        SSID = config.get('SSID', SSID)
        PASSWORD = config.get('PASSWORD', PASSWORD)
        LED_PIN_NUM = config.get('LED_PIN_NUM', LED_PIN_NUM)
        NUM_LEDS = config.get('NUM_LEDS', NUM_LEDS)
        LED_STEP = config.get('LED_STEP', LED_STEP)
        LISTEN_PORT = config.get('LISTEN_PORT', LISTEN_PORT)
        
    print(f"Sikeresen betöltve a {CONFIG_FILE} fájlból.")
    print(f"SSID: {SSID}")
    print(f"LED Pin: {LED_PIN_NUM}, LED Count: {NUM_LEDS}, LED Step: {LED_STEP}")

except OSError:
    print(f"Figyelem: A {CONFIG_FILE} nem található. Alapértelmezett értékek használata.")
except (ValueError, KeyError) as e:
    print(f"Hiba: A {CONFIG_FILE} sérült vagy hiányos: {e}. Alapértelmezett értékek használata.")

# --- Globális Változók ---
# LED szalag inicializálása
led_pin = machine.Pin(LED_PIN_NUM)
np = neopixel.NeoPixel(led_pin, NUM_LEDS)

# A NeoPixel lib nem kezeli a globális fényerőt, mint a FastLED.
# Ezt manuálisan kell alkalmaznunk a színek beállításakor.
# Tároljuk az "alap" színt és a fényerőt külön.
global_brightness = 128  # Kezdő fényerő (0-255)
current_color = (0, 0, 0) # Jelenlegi "tiszta" szín

# --- LED Vezérlő Függvények ---

def apply_color_and_brightness():
    """
    Segédfüggvény: Alkalmazza a 'current_color'-t a 'global_brightness'-szel skálázva.
    A FastLED ezt automatikusan csinálja, a neopixel-nél nekünk kell.
    """
    global current_color, global_brightness, np
    
    # Fényerő skálázása (0.0 - 1.0)
    scale = global_brightness / 255.0
    
    r, g, b = current_color
    
    # Színek skálázása a fényerővel
    scaled_r = int(r * scale)
    scaled_g = int(g * scale)
    scaled_b = int(b * scale)
    
    scaled_color = (scaled_r, scaled_g, scaled_b)
    # 1. Először kikapcsolunk MINDEN LED-et.
    #    Ez biztosítja, hogy a köztes LED-ek (amiket nem akarunk használni) sötétek maradjanak.
    np.fill((0, 0, 0))
    # 2. Végigmegyünk a szalagon, és csak minden LED_STEP-edik ledet állítjuk be.
    # A range(start, stop, step) tökéletes erre.
    for i in range(0, NUM_LEDS, LED_STEP):
        np[i] = scaled_color
    # 3. Adatküldés a szalagnak
    np.write()

def led_on():
    global current_color, global_brightness
    print("LED On")
    current_color = (250, 110, 40)
    global_brightness = 130
    apply_color_and_brightness()

def led_off():
    global current_color, global_brightness
    print("LED Off")
    current_color = (0, 0, 0)
    # A fényerő 0-ra állítása is kikapcsolja
    global_brightness = 0
    apply_color_and_brightness()

def set_color(r, g, b):
    """Beállít egy új színt, megtartva az aktuális fényerőt."""
    global current_color
    print(f"Set Color: R={r}, G={g}, B={b}")
    # Biztosítjuk, hogy az értékek 0-255 között legyenek
    current_color = (max(0, min(255, r)),
                     max(0, min(255, g)),
                     max(0, min(255, b)))
    apply_color_and_brightness()

def set_brightness(brightness_val):
    global global_brightness
    print(f"Set Brightness: {brightness_val}")
    # Biztosítjuk, hogy 0-255 között maradjon
    global_brightness = max(0, min(255, brightness_val))
    apply_color_and_brightness() # Alkalmazzuk az új fényerőt a régi színre

# --- WiFi Kapcsolódás ---
def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f"Connecting to {ssid}...")
        wlan.connect(ssid, password)
        max_wait = 10
        while max_wait > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            max_wait -= 1
            print(".")
            time.sleep(1)
            
    if wlan.isconnected():
        print("WiFi connected.")
        print("IP address:", wlan.ifconfig()[0])
        print("MAC address:", ':'.join(f'{b:02x}' for b in wlan.config('mac')))
    else:
        print("WiFi connection failed.")

# --- Web Szerver Helper ---
def get_query_param(request_str, param_name):
    """
    Kinyeri egy query paraméter értékét (pl. ?v=... vagy ?params=...)
    Az eredeti aREST kód valószínűleg a 'params' vagy 'v' változót várta.
    Mi a ?v=... formátumot implementáljuk.
    """
    param = param_name + '='
    try:
        # Keresd meg '...param='
        start = request_str.find(param)
        if start == -1:
            return None
        start += len(param)
        
        # Keresd meg az érték végét (az első ' ' vagy '&' karakter)
        end_space = request_str.find(' ', start)
        end_amp = request_str.find('&', start)

        if end_space == -1 and end_amp == -1: # Ha ez az utolsó paraméter
            return request_str[start:]
        
        end = -1
        if end_space != -1:
            end = end_space
        if end_amp != -1 and (end == -1 or end_amp < end):
            end = end_amp
            
        return request_str[start:end]
    except Exception:
        return None

# --- Web Szerver Fő Ciklus ---
def start_server():
    addr = socket.getaddrinfo('0.0.0.0', LISTEN_PORT)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Port újrafelhasználás
    s.bind(addr)
    s.listen(1)
    print(f"Server listening on port {LISTEN_PORT}...")

    while True:
        try:
            conn, addr = s.accept()
            print('Connection from', addr)
            request_bytes = conn.recv(1024)
            request = str(request_bytes, 'utf-8')
            print('Request:', request.split('\r\n')[0]) # Csak az első sort írjuk ki

            # --- Kérés Feldolgozása ---
            # Standard HTTP válasz fejléce
            response_header = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n"
            json_response = '{ "status": "ok" }'

            if 'POST /on' in request:
                led_on()
            elif 'POST /off' in request:
                led_off()
            elif 'POST /color' in request:
                # Az eredeti kód 'R.G.B' formátumot várt. Ezt várjuk a 'v' paraméterben.
                # Pl: http://[IP]/color?v=255.100.0
                color_val = get_query_param(request, 'v')
                if color_val:
                    try:
                        r, g, b = map(int, color_val.split('.'))
                        set_color(r, g, b)
                    except Exception as e:
                        print(f"Invalid color format: {e}")
                        json_response = '{ "status": "error", "message": "Invalid color format. Use ?v=R.G.B" }'
                else:
                    json_response = '{ "status": "error", "message": "Missing color value. Use ?v=R.G.B" }'

            elif 'POST /brightness' in request:
                # Pl: http://[IP]/brightness?v=150
                bright_val = get_query_param(request, 'v')
                if bright_val:
                    try:
                        set_brightness(int(bright_val))
                    except Exception as e:
                        print(f"Invalid brightness format: {e}")
                        json_response = '{ "status": "error", "message": "Invalid brightness. Use ?v=NNN" }'
                else:
                    json_response = '{ "status": "error", "message": "Missing brightness. Use ?v=NNN" }'
            
            else:
                json_response = '{ "status": "not_found", "message": "Endpoint not found" }'

            # Válasz küldése és kapcsolat bontása
            conn.sendall(response_header + json_response)
            conn.close()

        except OSError as e:
            conn.close()
            print('Connection closed with error', e)
        except Exception as e:
            print(f"An error occurred: {e}")
            try:
                conn.close() # Próbáljuk meg bezárni, ha még nyitva van
            except:
                pass # A kapcsolat már lehet, hogy bezárult

# --- Program Indítása ---
print("Starting script...")
connect_wifi(SSID, PASSWORD)
led_off() # Kezdéskor kapcsold ki a LED-eket
start_server() # Indítsd a webszervert