import network
import ujson
import urequests
import utime
import urandom


WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""

BACKEND_URL = "http://filtering-town-tee-regarded.trycloudflare.com/telemetria-sensores"

ID_SENSOR = 99
INTERVALO_DE_ENVIO = 2
WIFI_CONNECT_TIMEOUT_S = 15
WIFI_RETRY_DELAY_S = 3
HTTP_MAX_RETRIES = 3
HTTP_RETRY_DELAY_S = 2

HTTP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Connection": "close",
    "User-Agent": "PicoW-MicroPython/1.0",
}

ANALOG_SENSORS = (
    ("temperatura", 18.0, 36.0),
    ("umidade", 30.0, 90.0),
    ("luminosidade", 100.0, 1000.0),
    ("vibracao", 0.0, 12.0),
)

DIGITAL_SENSORS = (
    ("presenca", ("presenca", "ausencia")),
    ("porta", ("aberto", "fechado")),
    ("bomba", ("ligado", "desligado")),
    ("alarme", ("ligado", "desligado")),
)

wifi = network.WLAN(network.STA_IF)

def escolha_aleatoria(items):
    return items[urandom.getrandbits(16) % len(items)]


def gera_numero(min_value, max_value):
    scaled_min = int(min_value * 100)
    scaled_max = int(max_value * 100)
    value = scaled_min + (urandom.getrandbits(16) % (scaled_max - scaled_min + 1))
    return "{:.2f}".format(value / 100)


def connect_wifi():
    if wifi.isconnected():
        print("Wi-Fi already connected:", wifi.ifconfig())
        return True

    print("Connecting to Wi-Fi:", WIFI_SSID)
    wifi.active(True)
    wifi.connect(WIFI_SSID, WIFI_PASSWORD)

    deadline = utime.time() + WIFI_CONNECT_TIMEOUT_S
    while not wifi.isconnected() and utime.time() < deadline:
        utime.sleep_ms(250)
        print(".", end="")

    print("")

    if wifi.isconnected():
        print("Wi-Fi connected:", wifi.ifconfig())
        return True

    print("Wi-Fi connection timeout")
    try:
        wifi.disconnect()
    except OSError:
        pass
    return False


def ensure_wifi():
    if wifi.isconnected():
        return True

    while not connect_wifi():
        print("Retrying Wi-Fi in", WIFI_RETRY_DELAY_S, "seconds")
        utime.sleep(WIFI_RETRY_DELAY_S)

    return True


def gera_payload_analogico():
    sensor_name, min_value, max_value = escolha_aleatoria(ANALOG_SENSORS)
    return {
        "idDispositivo": ID_SENSOR,
        "tipoSensor": sensor_name,
        "naturezaLeitura": "analogica",
        "valorColetado": gera_numero(min_value, max_value),
    }


def gera_payload_digital():
    sensor_name, states = escolha_aleatoria(DIGITAL_SENSORS)
    return {
        "idDispositivo": ID_SENSOR,
        "tipoSensor": sensor_name,
        "naturezaLeitura": "discreta",
        "valorColetado": escolha_aleatoria(states),
    }


def gera_payload():
    if urandom.getrandbits(1) == 0:
        return gera_payload_analogico()
    return gera_payload_digital()


def envia_req(payload):
    for attempt in range(1, HTTP_MAX_RETRIES + 1):
        ensure_wifi()
        response = None

        try:
            body = ujson.dumps(payload).encode("utf-8")
            response = urequests.post(BACKEND_URL, data=body, headers=HTTP_HEADERS)
            status_code = response.status_code
            response_text = response.text

            if status_code == 202:
                print("Telemetria aceita:", response_text)
                return True

            print("Unexpected HTTP status:", status_code, repr(response_text))
        except Exception as error:
            print("HTTP send failed on attempt", attempt, ":", error)
            try:
                wifi.disconnect()
            except OSError:
                pass
        finally:
            if response is not None:
                response.close()

        if attempt < HTTP_MAX_RETRIES:
            print("Retrying HTTP in", HTTP_RETRY_DELAY_S, "seconds")
            utime.sleep(HTTP_RETRY_DELAY_S)

    return False


def main():
    ensure_wifi()

    while True:
        payload = gera_payload()
        print("Payload gerado:", payload)

        if envia_req(payload):
            print("Enviado com sucesso")
        else:
            print("Envio falhou")

        utime.sleep(INTERVALO_DE_ENVIO)


main()
