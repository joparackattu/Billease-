# Fixing Safari Access Issues

If you can't access the BILLESE UI from Safari on your phone, follow these steps:

## Step 1: Set Up Windows Firewall

**Run as Administrator:**
```powershell
.\setup_firewall.ps1
```

Or manually add firewall rules:
```powershell
# Run PowerShell as Administrator
netsh advfirewall firewall add rule name="Vite Dev Server Port 3000" dir=in action=allow protocol=TCP localport=3000
netsh advfirewall firewall add rule name="FastAPI Backend Port 8000" dir=in action=allow protocol=TCP localport=8000
```

## Step 2: Verify Network Configuration

1. **Check your computer's IP address:**
   ```powershell
   ipconfig
   ```
   Look for "IPv4 Address" under your Wi-Fi adapter (e.g., `192.168.1.100`)

2. **Ensure phone and computer are on the same Wi-Fi network**

3. **Test connectivity from phone:**
   - Try accessing `http://YOUR_IP:3000` in Safari
   - If it doesn't work, try `http://YOUR_IP:8000/docs` (backend API docs)

## Step 3: Start the Servers

Run the start script:
```powershell
.\start_for_phone.ps1
```

This script will:
- Detect your IP address
- Configure the frontend `.env` file
- Start the backend server on port 8000
- Start the frontend server on port 3000

## Step 4: Access from Safari

1. **On your iPhone/iPad:**
   - Open Safari
   - Navigate to: `http://YOUR_IP:3000`
   - Replace `YOUR_IP` with your computer's IP address

2. **If you see connection errors:**
   - Check that both servers are running
   - Verify the IP address is correct
   - Try accessing from another device on the same network

## Common Issues and Solutions

### Issue: "Safari can't open the page"

**Solution:**
- Make sure Windows Firewall allows port 3000 (run `setup_firewall.ps1`)
- Verify the frontend server is running and shows "Network: http://0.0.0.0:3000"
- Check that your phone and computer are on the same Wi-Fi network

### Issue: "Connection refused" or "Can't connect to server"

**Solution:**
- The server might not be binding to `0.0.0.0` properly
- Restart the frontend server: `cd frontend && npm run dev -- --host 0.0.0.0`
- Check Windows Firewall isn't blocking Node.js

### Issue: "Page loads but API calls fail"

**Solution:**
- Check the `.env` file in `frontend/` has the correct `VITE_API_URL`
- It should be: `VITE_API_URL=http://YOUR_IP:8000`
- Restart the frontend dev server after changing `.env`

### Issue: "Works on Chrome but not Safari"

**Solution:**
- Safari might be caching old data
- Clear Safari cache: Settings → Safari → Clear History and Website Data
- Try a private/incognito window in Safari
- Check Safari's privacy settings aren't blocking local network access

## Verify Server is Accessible

Test from your phone's browser:
1. **Frontend:** `http://YOUR_IP:3000` - Should show the login page
2. **Backend API:** `http://YOUR_IP:8000/docs` - Should show FastAPI documentation

If both work, the servers are accessible. If only one works, check the firewall rules.

## Alternative: Use Your Computer's Hostname

Instead of IP address, you can sometimes use your computer's hostname:
- Find hostname: `hostname` in PowerShell
- Access: `http://HOSTNAME:3000` (e.g., `http://MyPC:3000`)

Note: This may not work on all networks, IP address is more reliable.

## Still Not Working?

1. **Check Windows Defender Firewall:**
   - Go to Windows Security → Firewall & network protection
   - Click "Allow an app through firewall"
   - Ensure Node.js and Python are allowed for Private networks

2. **Check Antivirus:**
   - Some antivirus software blocks local network access
   - Temporarily disable to test

3. **Check Router Settings:**
   - Some routers have "AP Isolation" or "Client Isolation" enabled
   - This prevents devices on the same network from communicating
   - Disable this feature in your router settings

4. **Try Different Port:**
   - If port 3000 is blocked, edit `frontend/vite.config.js` and change `port: 3000` to `port: 3001`
   - Update firewall rules accordingly



