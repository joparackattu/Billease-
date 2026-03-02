# Tapo C210 RTSP – VLC / App not opening stream

If VLC (or the Billease app) cannot open the RTSP URL, work through these in order.

## 1. Use the **Camera Account**, not your Tapo app login

RTSP uses a **camera account** that you create only for this camera:

1. Open **Tapo app** → select the camera.
2. Tap **Settings** (gear) → **Advanced Settings** → **Camera Account**.
3. **Create** a username and password (6–32 characters).  
   Example: username `Billease`, password `12344321`.
4. **Reboot the camera** (power off/on or restart in the app).  
   RTSP often does not work until the camera has been restarted after creating the camera account.

Use this **camera account** in the RTSP URL, not your main Tapo/TP-Link account.

---

## 2. Only two of these can be on at once

Tapo allows only **two** of these at the same time:

- **SD card recording**
- **Tapo Care** (cloud)
- **RTSP/ONVIF**

To use RTSP:

- **Either** remove the SD card or turn off **SD card recording** in the Tapo app,  
- **Or** turn off **Tapo Care** (pause or cancel in the app).

Then try the stream again.

---

## 3. Check network and IP

- Your **PC** (where VLC runs) and the **camera** must be on the **same LAN** (same Wi‑Fi or same router).
- In a terminal on the PC run:  
  `ping 172.20.10.13`  
  If you get no reply, the camera is off, wrong IP, or on a different network. Get the current IP from the Tapo app: **Settings → Device Info**.
- Update the RTSP URL in `main.py` (or your script) if the camera’s IP is different.

---

## 4. URLs to try in VLC

**Media → Open Network Stream** (Ctrl+N), then try in this order:

1. **Standard (high quality)**  
   `rtsp://Billease:12344321@172.20.10.13:554/stream1`

2. **With TCP (often more stable)**  
   `rtsp://Billease:12344321@172.20.10.13:554/stream1?transport=tcp`

3. **Lower quality stream**  
   `rtsp://Billease:12344321@172.20.10.13:554/stream2`

4. **All lowercase user/pass** (if the camera is strict about case):  
   `rtsp://billease:12344321@172.20.10.13:554/stream1`

Replace `Billease`, `12344321`, and `172.20.10.13` with your **camera account** and the camera’s current IP.

---

## 5. VLC options

- In “Open Network Stream”, click **Show more options**.
- Set **Caching** to **1000–3000 ms**.
- If there is a **Protocol** or **Force TCP** option, enable it and try again.

---

## 6. Firewall

- On the **PC**, allow **inbound** for **port 554** (RTSP) if you use a firewall.  
  For VLC you usually only need **outbound** to the camera; the camera does not connect back to the PC for RTSP.

---

## Quick checklist

- [ ] Camera account created in Tapo app (Advanced → Camera Account).
- [ ] Camera **rebooted** after creating the camera account.
- [ ] SD card **removed** or **SD recording off**; or **Tapo Care off**.
- [ ] `ping 172.20.10.13` works from the PC.
- [ ] URL uses **camera account** user/pass and correct IP.
- [ ] Tried `stream1`, `stream2`, and `?transport=tcp` in VLC.

If it still fails, try another device on the same Wi‑Fi (e.g. phone with VLC) to see if the problem is the PC or the camera/account.
