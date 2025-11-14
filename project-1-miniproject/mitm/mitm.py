import subprocess
import time
import os
import glob
from collections import defaultdict
import requests

# --- Config ---
GEMINI_API_KEY = "XXX"

CAP_DIR = "/home/XXX"
INTERFACE = "XXX"               
ROTATE_SECONDS = 60             
ALERT_COOLDOWN = 120            
TCPDUMP_BIN = "tcpdump"
MERGECAP_BIN = "mergecap"       

os.makedirs(CAP_DIR, exist_ok=True)


def run_tcpdump(filename):
    """Run tcpdump for ROTATE_SECONDS seconds, saving to filename."""
    cmd = [
        "sudo", TCPDUMP_BIN,
        "-i", INTERFACE,
        "-w", filename,
        "-G", str(ROTATE_SECONDS),
        "-W", "1",       # capture one file only
        "-n", "-s", "0"
    ]
    print(f"[+] Capturing to {filename} for {ROTATE_SECONDS}s...")
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def check_arp_duplicates():
    """Detect duplicate MAC addresses in ARP table."""
    out = subprocess.check_output(["arp", "-n"]).decode(errors="ignore")
    mac_count = defaultdict(int)
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            mac = parts[2]
            mac_count[mac] += 1
    dups = {m: c for m, c in mac_count.items() if c > 1}
    if dups:
        print(f"[!] ALERT: Duplicate MACs detected: {dups}")
        return True
    return False


def convert_pcap_to_json(pcap_path):
    """Convert merged pcap to JSON using tshark."""
    json_path = pcap_path.replace(".pcap", ".json")
    cmd = ["tshark", "-r", pcap_path, "-T", "json"]

    print(f"[+] Converting {pcap_path} → {json_path} ...")
    try:
        with open(json_path, "w") as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.DEVNULL)
        print(f"[✓] JSON file created: {json_path}")
        return json_path
    except Exception as e:
        print(f"[x] Failed to convert pcap to JSON: {e}")
        return None


def merge_captures():
    """Merge the two most recent captures and convert to JSON."""
    files = sorted(glob.glob(os.path.join(CAP_DIR, "capture-*.pcap")))
    files = [f for f in files if os.path.basename(f) in ("capture-1.pcap", "capture-2.pcap")]
    if not files:
        print("[!] No capture files to merge.")
        return
    output = os.path.join(CAP_DIR, "capture-merged.pcap")

    try:
        cmd = [MERGECAP_BIN, "-w", output] + files
        subprocess.check_call(cmd)
        print(f"[✓] Merged captures → {output}")
    except Exception as e:
        print(f"[x] mergecap failed ({e}). Copying instead.")
        for i, f in enumerate(files):
            backup = f"{output}.part{i}"
            subprocess.call(["cp", f, backup])
            print(f"    Copied {f} -> {backup}")

    # --- Convert merged file to JSON ---
    convert_pcap_to_json(output)
    fffile=open("capture-merged.json", "r")
    prompt = (
        f"Analyze this pcap dump in json format for arp spoofing:  Give output in only Valid Attack/Not Valid Attack\n\n"
        f"{fffile.read()}"
    )
    print("\nGemini AI analysis of pcap file : ")
    start=time.time()
    ai_result = call_gemini_api(prompt)
    end=time.time()
    print(ai_result)
    print(f"Execution time: {end-start:.6f} seconds")

def call_gemini_api(prompt, model="gemini-2.0-flash", temperature=0.0):
    """
    Sends a text prompt to Gemini API and returns the text output.
    (currently not used automatically)
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature}
    }

    resp = requests.post(url, headers=headers, json=body)
    if resp.status_code == 429:
        return "⚠️ Rate limit hit (429 Too Many Requests). Try again later."
    resp.raise_for_status()
    data = resp.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return str(data)


def main_loop():
    alert_active = False
    last_alert_time = 0
    index = 1

    try:
        while True:
            filename = os.path.join(CAP_DIR, f"capture-{index}.pcap")

            run_tcpdump(filename)

            duplicates = check_arp_duplicates()
            now = time.time()

            if duplicates and not alert_active:
                merge_captures()
                alert_active = True
                last_alert_time = now
                print(f"[→] Alert active. Cooldown started ({ALERT_COOLDOWN}s).")

            elif alert_active:
                # Reset alert if no duplicates for ALERT_COOLDOWN
                if not duplicates and (now - last_alert_time) >= ALERT_COOLDOWN:
                    alert_active = False
                    print("[✓] Alert reset (no duplicates for cooldown).")
                elif duplicates:
                    last_alert_time = now

            # Alternate between capture-1.pcap and capture-2.pcap
            index = 1 if index == 2 else 2

    except KeyboardInterrupt:
        print("\n[!] Stopping capture monitor...")


if __name__ == "__main__":
    main_loop()
