#!/usr/bin/env python3
"""SDK Cloud Publisher — upload pipeline JSON reports to WISE-IoT via DCCS+MQTT.

Uses the WISE-PaaS DataHub Edge Python SDK which handles DCCS authentication
and MQTT broker credential management automatically.

Architecture:
    PC (this script) ──DCCS──▶ get MQTT creds ──MQTT──▶ WISE-EnSaaS/RabbitMQ ──▶ DataHub ──SimpleJson──▶ Dashboard

Usage:
    uv run python scripts/sdk_cloud_publisher.py --report code/data/report.json
    uv run python scripts/sdk_cloud_publisher.py --report code/data/report.json --dry-run

Credentials (from IoTSuite device registration):
    Device ID:    231a82fda93a42999e6d69cacb7f405e
    Device Key:   8934d9aba9d3be278f9495686245a94e
    DCCS API:     https://api-dccs-ensaas.edu.advantech.com.cn/v1/serviceCredentials/
"""

import argparse
import datetime
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from wisepaasdatahubedgesdk.EdgeAgent import EdgeAgent
from wisepaasdatahubedgesdk.Model.Edge import (
    EdgeAgentOptions,
    DCCSOptions,
    EdgeData,
    EdgeTag,
)
import wisepaasdatahubedgesdk.Common.Constants as constant

logger = logging.getLogger("sdk_publisher")

# --- IoTSuite device credentials (from device registration) ---
DEVICE_ID = "231a82fda93a42999e6d69cacb7f405e"
DEVICE_KEY = "8934d9aba9d3be278f9495686245a94e"
DCCS_API = "https://api-dccs-ensaas.edu.advantech.com.cn/v1/serviceCredentials"

# --- Tag name → pipeline property mapping ---
PROPERTY_MAP = {
    "risk_score":       "risk_score",
    "risk_level":       "risk_level",
    "detections_count": "detections",
    "high_risk_count":  "high_risk",
    "peak_score":       "peak_score",
    "avg_score":        "avg_score",
    "fps":              "fps",
    "frame_idx":        "frame_idx",
}


class SDKCloudPublisher:
    """Publishes pipeline frame data to WISE-IoT via DCCS SDK."""

    def __init__(self, device_id: str = DEVICE_ID, device_key: str = DEVICE_KEY,
                 dccs_api: str = DCCS_API) -> None:
        options = EdgeAgentOptions(
            nodeId=device_id,
            deviceId=device_id,
            type=constant.EdgeType["Gateway"],
            heartbeat=60,
            dataRecover=True,
            connectType=constant.ConnectType["DCCS"],
            DCCS=DCCSOptions(
                apiUrl=dccs_api,
                credentialKey=device_key,
            ),
        )
        self._agent = EdgeAgent(options=options)
        self._device_id = device_id
        self._connected = False
        self._published = 0

    def connect(self) -> None:
        logger.info("Connecting via DCCS to %s ...", DCCS_API)
        self._agent.connect()
        # SDK connect is synchronous — wait briefly for connection
        time.sleep(2)
        self._connected = True
        logger.info("Connected via DCCS → MQTT")

    def publish_frame(self, frame_data: dict[str, Any]) -> None:
        data = EdgeData()
        data.timestamp = datetime.datetime.utcnow()
        for key, tag_name in PROPERTY_MAP.items():
            if key in frame_data:
                val = frame_data[key]
                if isinstance(val, float):
                    val = round(val, 2)
                data.tagList.append(EdgeTag(
                    deviceId=self._device_id,
                    tagName=tag_name,
                    value=val,
                ))
        self._agent.sendData(data)
        self._published += 1

    def publish_report(self, report: dict[str, Any]) -> int:
        frames = report.get("frame_details", [])
        if not frames:
            logger.warning("No frame_details in report")
            return 0

        logger.info("Publishing %d frames via DCCS SDK ...", len(frames))
        self._published = 0
        for i, frame in enumerate(frames):
            props = {
                "frame_idx": frame.get("frame_idx", i),
                "risk_score": frame.get("score", 0.0),
                "risk_level": frame.get("level", "low"),
                "detections_count": frame.get("detections_count", 0),
                "high_risk_count": frame.get("high_risk_count", 0),
                "fps": frame.get("fps", 0.0),
            }
            self.publish_frame(props)
            if (i + 1) % 100 == 0:
                logger.info("  %d/%d frames published", i + 1, len(frames))
            time.sleep(0.05)  # throttle

        logger.info("Done: %d frames published", self._published)
        return self._published

    def close(self) -> None:
        self._agent.disconnect()
        logger.info("Disconnected. Total: %d", self._published)


# --- CLI ---

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser(
        description="Publish pipeline JSON reports to WISE-IoT via DCCS SDK"
    )
    ap.add_argument("--report", type=Path, required=True,
                    help="Path to pipeline JSON report")
    ap.add_argument("--dry-run", action="store_true",
                    help="Preview without connecting")
    ap.add_argument("--device-id", default=DEVICE_ID)
    ap.add_argument("--device-key", default=DEVICE_KEY)
    ap.add_argument("--dccs-api", default=DCCS_API)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    with open(args.report, encoding="utf-8") as f:
        report = json.load(f)

    if args.dry_run:
        summary = report.get("summary", {})
        frames = report.get("frame_details", [])
        print(f"=== DRY RUN (SDK) ===")
        print(f"  Device ID: {args.device_id}")
        print(f"  DCCS API:  {args.dccs_api}")
        print(f"  Report:    {json.dumps(summary, indent=2)}")
        print(f"  Frames:    {len(frames)}")
        if frames:
            print(f"  Sample frame 0: {json.dumps(frames[0], indent=2)}")
        print(f"=== End DRY RUN ===")
        return

    publisher = SDKCloudPublisher(
        device_id=args.device_id,
        device_key=args.device_key,
        dccs_api=args.dccs_api,
    )
    try:
        publisher.connect()
        publisher.publish_report(report)
    except Exception as e:
        logger.error("Publishing failed: %s", e)
        raise
    finally:
        publisher.close()


if __name__ == "__main__":
    main()
