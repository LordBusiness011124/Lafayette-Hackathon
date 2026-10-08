#!/bin/bash
# Open the mobile web demo in an available iPhone Simulator, not a native app.
set -euo pipefail
DEMO_URL="${1:-http://127.0.0.1:8000}"
if ! xcrun --find simctl >/dev/null 2>&1; then
  echo 'iOS Simulator is unavailable. Install Xcode and an iOS Simulator runtime first.' >&2
  echo 'Then run: DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer bash scripts/ios-demo.sh' >&2
  exit 1
fi
SIMULATOR_ID="$(xcrun simctl list devices available -j | python3 -c 'import json,sys; devices=[d for ds in json.load(sys.stdin)["devices"].values() for d in ds if d.get("isAvailable") and "iPhone" in d["name"]]; devices.sort(key=lambda d:d["state"]!="Booted"); print(devices[0]["udid"] if devices else "")')"
if [ -z "$SIMULATOR_ID" ]; then
  echo 'No available iPhone runtime. Install one in Xcode Settings > Components.' >&2
  exit 1
fi
if ! xcrun simctl list devices booted -j | python3 -c 'import json,sys; target=sys.argv[1]; sys.exit(not any(d["udid"]==target for ds in json.load(sys.stdin)["devices"].values() for d in ds))' "$SIMULATOR_ID"; then
  xcrun simctl boot "$SIMULATOR_ID"
fi
open -a Simulator
xcrun simctl bootstatus "$SIMULATOR_ID" -b
xcrun simctl openurl "$SIMULATOR_ID" "$DEMO_URL"
