#!/usr/bin/env python3
"""
ROI-Based VLA Color Pipeline with ESP32 LED Telemetry
Samples color inside a dedicated bounding box to drive RGB LEDs and tracks horizontal target position.
"""

import sys
import time
import cv2
import numpy as np
import serial

# --- Configuration ---
CAMERA_INDEX = 0         # /dev/video0
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200

# Bounding Box Dimensions (Center of frame)
BOX_SIZE = 100           # 100x100 pixel sampling box
PIXEL_THRESHOLD = 800    # Active color pixel count threshold inside box

def init_serial(port, baud):
    try:
        ser = serial.Serial(port, baud, timeout=1)
        time.sleep(2)
        print(f"[INFO] Serial bridge established on {port} at {baud} baud.")
        return ser
    except Exception as e:
        print(f"[WARN] Serial port open failed ({e}). Running in simulation mode.")
        return None

def analyze_roi_colors(roi_hsv):
    """
    Evaluates the color profile exclusively inside the target bounding box.
    """
    # HSV Ranges
    lower_red1 = np.array([0, 120, 70]); upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 120, 70]); upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([36, 90, 90]); upper_green = np.array([86, 255, 255])
    lower_blue = np.array([94, 80, 80]); upper_blue = np.array([126, 255, 255])

    # Masks
    mask_r1 = cv2.inRange(roi_hsv, lower_red1, upper_red1)
    mask_r2 = cv2.inRange(roi_hsv, lower_red2, upper_red2)
    mask_red = mask_r1 | mask_r2
    mask_green = cv2.inRange(roi_hsv, lower_green, upper_green)
    mask_blue = cv2.inRange(roi_hsv, lower_blue, upper_blue)

    # Pixel Counts inside ROI
    r_count = cv2.countNonZero(mask_red)
    g_count = cv2.countNonZero(mask_green)
    b_count = cv2.countNonZero(mask_blue)

    # Determine dominant state inside box
    r_active = int(r_count > PIXEL_THRESHOLD)
    g_active = int(g_count > PIXEL_THRESHOLD)
    b_active = int(b_count > PIXEL_THRESHOLD)

    return r_active, g_active, b_active

def main():
    print("=" * 60)
    print("Initializing ROI Color Sampling VLA Controller")
    print("=" * 60)

    ser = init_serial(SERIAL_PORT, BAUD_RATE)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[ERROR] Could not open camera on /dev/video{CAMERA_INDEX}.")
        sys.exit(1)

    current_angle = 90
    last_sent_payload = ""

    print("[INFO] Pipeline active. Place colored objects inside the center box. Press 'q' to quit.")
    print("-" * 60)

    try:
        while cap.isOpened():
            start_time = time.time()
            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.flip(frame, 1)
            height, width, _ = frame.shape

            # 1. Define ROI Box Coordinates (Centered)
            box_x1 = (width // 2) - (BOX_SIZE // 2)
            box_y1 = (height // 2) - (BOX_SIZE // 2)
            box_x2 = box_x1 + BOX_SIZE
            box_y2 = box_y1 + BOX_SIZE

            # Extract ROI crop
            roi = frame[box_y1:box_y2, box_x1:box_x2]
            roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

            # 2. Analyze Dominant Color inside ROI
            r, g, b = analyze_roi_colors(roi_hsv)

            # 3. Spatial Tracking (Servo Position)
            gray_channel = frame[:, :, 1]
            column_sums = np.sum(gray_channel, axis=0)
            center_x = int(np.argmax(column_sums))
            target_angle = int(np.interp(center_x, [0, width], [180, 0]))
            current_angle = int(0.2 * target_angle + 0.8 * current_angle)

            # 4. Construct Payload
            payload = f"ANGLES:{current_angle}|LEDS:{r},{g},{b}\n"

            if payload != last_sent_payload:
                last_sent_payload = payload
                if ser and ser.is_open:
                    ser.write(payload.encode('utf-8'))
                    ser.flush()
                print(f"[ROI TELEMETRY] Servo: {current_angle}° | LEDs (R,G,B): ({r},{g},{b})")

            # 5. Visual Rendering
            # Draw ROI Bounding Box (Changes color to match detected object)
            box_color = (0, 255, 0) # Default green box
            if r and not g and not b: box_color = (0, 0, 255)      # Red
            elif g and not r and not b: box_color = (0, 255, 0)    # Green
            elif b and not r and not g: box_color = (255, 0, 0)    # Blue
            elif r and g and b: box_color = (255, 255, 255)        # All

            cv2.rectangle(frame, (box_x1, box_y1), (box_x2, box_y2), box_color, 2)
            cv2.putText(frame, "COLOR SAMPLING ZONE", (box_x1 - 15, box_y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, box_color, 1)

            # HUD Status
            latency_ms = (time.time() - start_time) * 1000
            led_status = f"R:{'ON' if r else 'OFF'} G:{'ON' if g else 'OFF'} B:{'ON' if b else 'OFF'}"
            cv2.putText(frame, f"Servo: {current_angle} deg | {led_status} | Latency: {latency_ms:.1f}ms", 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

            cv2.imshow("VLA Vision Feed", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if ser and ser.is_open:
            ser.close()
        print("[INFO] Engine closed.")

if __name__ == "__main__":
    main()
