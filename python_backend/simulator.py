import sys
import io

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import json
import math
import os
import random
import time
import argparse
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "factory/machine1/telemetry")


def generate_telemetry(anomaly: bool = False) -> dict:
    """Generates synthetic telemetry data representing normal or anomalous industrial machine operation."""
    if not anomaly:
        # --- Normal Operating State ---
        acc_rms = round(random.uniform(0.25, 0.45), 3)
        acc_std = round(acc_rms * random.uniform(0.65, 0.85), 3)
        acc_peak = round(acc_rms * random.uniform(1.4, 1.8), 3)
        acc_p2p = round(acc_peak * 2 * random.uniform(0.9, 1.1), 3)
        crest_factor = round(acc_peak / acc_rms if acc_rms > 0 else 0, 3)
        skewness = round(random.uniform(-0.15, 0.15), 3)
        kurtosis = round(random.uniform(2.8, 3.2), 3)

        fft_dom_freq = round(random.uniform(25.0, 30.0), 2)  # ~1600-1800 RPM motor
        fft_max_amp = round(random.uniform(0.2, 0.5), 3)
        spectral_centroid = round(random.uniform(28.0, 35.0), 2)

        temperature = round(random.uniform(22.0, 26.0), 1)
        humidity = round(random.uniform(45.0, 55.0), 1)
        pressure = round(random.uniform(1010.0, 1015.0), 1)
        distance = random.randint(148, 152)

    else:
        # --- Abnormal / Fault Operating State (Bearing/Unbalance Anomaly) ---
        acc_rms = round(random.uniform(1.8, 3.5), 3)
        acc_std = round(acc_rms * random.uniform(0.7, 0.9), 3)
        acc_peak = round(acc_rms * random.uniform(2.5, 4.0), 3)
        acc_p2p = round(acc_peak * 2 * random.uniform(0.95, 1.15), 3)
        crest_factor = round(acc_peak / acc_rms if acc_rms > 0 else 0, 3)
        skewness = round(random.uniform(0.4, 1.2), 3)
        kurtosis = round(random.uniform(5.5, 9.5), 3)  # Heavy tailed impact distribution

        fft_dom_freq = round(random.uniform(75.0, 120.0), 2)  # High frequency fault harmonics
        fft_max_amp = round(random.uniform(1.8, 3.5), 3)
        spectral_centroid = round(random.uniform(60.0, 95.0), 2)

        temperature = round(random.uniform(48.0, 65.0), 1)  # Overheating machine
        humidity = round(random.uniform(35.0, 42.0), 1)
        pressure = round(random.uniform(1008.0, 1012.0), 1)
        distance = random.randint(130, 170)  # Mechanical wobbling

    return {
        "acc_rms": acc_rms,
        "acc_std": acc_std,
        "acc_peak": acc_peak,
        "acc_p2p": acc_p2p,
        "crest_factor": crest_factor,
        "skewness": skewness,
        "kurtosis": kurtosis,
        "fft_dom_freq": fft_dom_freq,
        "fft_max_amp": fft_max_amp,
        "spectral_centroid": spectral_centroid,
        "temperature": temperature,
        "humidity": humidity,
        "pressure": pressure,
        "distance": distance,
    }


def main():
    parser = argparse.ArgumentParser(description="IoT Industrial Maintenance Vibration Simulator")
    parser.add_argument(
        "--mode",
        choices=["normal", "anomaly", "toggle"],
        default="normal",
        help="Simulation mode: normal operation, continuous anomaly, or periodic toggling",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Publishing interval in seconds (default: 1.0s)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Number of telemetry messages to publish (0 for infinite loop)",
    )
    args = parser.parse_args()

    client = mqtt.Client(CallbackAPIVersion.VERSION2)

    print(f" Connecting to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}...")
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        print(f" Successfully connected! Publishing to topic: '{MQTT_TOPIC}'")
    except Exception as e:
        print(f" Failed to connect to MQTT broker: {e}")
        return

    published_count = 0
    current_anomaly_state = (args.mode == "anomaly")

    try:
        while True:
            published_count += 1
            if args.mode == "toggle":
                # Toggle anomaly mode every 15 samples
                current_anomaly_state = (published_count // 15) % 2 == 1

            payload = generate_telemetry(anomaly=current_anomaly_state)
            payload_json = json.dumps(payload)

            res = client.publish(MQTT_TOPIC, payload_json)
            if res.rc == mqtt.MQTT_ERR_SUCCESS:
                status_label = "⚠️ ANOMALY" if current_anomaly_state else "🟢 NORMAL"
                print(
                    f"[{published_count:04d}] Sent payload ({status_label}): "
                    f"RMS={payload['acc_rms']:.2f}g | DomFreq={payload['fft_dom_freq']:.1f}Hz | "
                    f"Temp={payload['temperature']:.1f}°C"
                )
            else:
                print(f"[{published_count:04d}] Failed to publish message to topic '{MQTT_TOPIC}'")

            if args.count > 0 and published_count >= args.count:
                print(f" Reached requested message count ({args.count}). Exiting.")
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n Stopped simulator.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
