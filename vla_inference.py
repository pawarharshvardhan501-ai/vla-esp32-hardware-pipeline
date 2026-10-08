#!/usr/bin/env python3
"""
Robust Brightness / Light Centroid Tracker
Bypasses OpenCV cascades and broken C-extension modules.
"""

import sys
import time
import cv2
import numpy as np
import serial

CAMERA_INDEX = 0  # /dev/video0
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200

def init_serial(port, baud):
    try:
        ser = serial.Serial(port, baud, timeout=1)
        time.sleep(2)
        print(f"[INFO] Serial bridge established on {port} at {baud} baud.")
        return ser
    except Exception as e:
        print(f"[WARN] Serial port open failed ({e}). Running in simulation mode.")
        return None

def main():
    print("=" * 60)
    print("Initializing Robust Direct Frame Tracker")
    print("=" * 60)

    ser = init_serial(SERIAL_PORT, BAUD_RATE)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[ERROR] Could not open camera on /dev/video{CAMERA_INDEX}.")
        sys.exit(1)

    current_angle = 90
    last_sent_angle = 90

    print("[INFO] Pipeline online. Track bright region / object. Press 'q' to quit.")
    print("-" * 60)

    try:
        while cap.isOpened():
            start_time = time.time()
            ret, frame = cap.read()
            if not ret:
                continue

            # Mirror frame horizontally
            frame = cv2.flip(frame, 1)
            height, width, _ = frame.shape

            # Compute horizontal spatial mean weight directly via numpy array
            gray = frame[:, :, 1]  # Green channel matrix
            column_sums = np.sum(gray, axis=0)
            center_x = int(np.argmax(column_sums))

            # Draw visual tracking line
            cv2.line(frame, (center_x, 0), (center_x, height), (0, 255, 0), 2)

            # Map horizontal position (0 -> width) to Servo Angle (180 -> 0)
            target_angle = int(np.interp(center_x, [0, width], [180, 0]))
            current_angle = int(0.2 * target_angle + 0.8 * current_angle)

            if abs(current_angle - last_sent_angle) >= 2:
                last_sent_angle = current_angle
                payload = f"ANGLES:{last_sent_angle},{last_sent_angle},{last_sent_angle},{last_sent_angle},{last_sent_angle}\n"

                if ser and ser.is_open:
                    ser.write(payload.encode('utf-8'))
                    ser.flush()

                print(f"[TRACKING] Position X: {center_x} | Target Angle: {last_sent_angle}° | Payload: {payload.strip()}")

            latency_ms = (time.time() - start_time) * 1000

            cv2.putText(frame, f"Servo: {last_sent_angle} deg | Latency: {latency_ms:.1f}ms", 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow("VLA Vision Feed", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user.")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if ser:
            ser.close()
        print("[INFO] Engine closed.")

if __name__ == "__main__":
    main()
