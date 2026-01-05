# BILLESE Mobile Frontend

Mobile-responsive web application for the BILLESE smart billing system.

## Features

- 📷 **Scan Page**: Live camera feed with item scanning
- 💰 **Bill Page**: View current bill and checkout
- 📜 **History Page**: View past bills

## Setup

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure API URL:**
   - Create `.env` file:
     ```
     VITE_API_URL=http://localhost:8000
     ```
   - Or modify `src/api/backend.js` directly

3. **Start development server:**
   ```bash
   npm run dev
   ```

4. **Open in browser:**
   - Desktop: `http://localhost:3000`
   - Mobile: Use your computer's IP address (e.g., `http://192.168.1.100:3000`)

## Build for Production

```bash
npm run build
```

The built files will be in `dist/` folder.

## Mobile Access

### Option 1: Direct IP Access
1. Find your computer's IP address
2. On mobile device, open: `http://YOUR_IP:3000`

### Option 2: PWA (Progressive Web App)
1. Open the app in mobile browser
2. Add to home screen
3. Works like a native app!

## Pages

### Scan Page
- Live camera feed at top
- Weight input
- Scan button
- Shows detected item with OK/Cancel buttons

### Bill Page
- Lists all items in current bill
- Shows total
- Checkout button (saves to history)
- Clear button

### History Page
- Lists all past bills
- Tap to view details
- Shows date, items, and total

## API Integration

The app connects to your FastAPI backend at `http://localhost:8000`.

Make sure your backend is running:
```bash
cd ..
uvicorn main:app --reload --host 0.0.0.0
```

## Troubleshooting

### Camera feed not loading
- Check backend is running
- Check camera is connected
- Verify API URL in `.env`

### CORS errors
- Make sure backend has CORS enabled (already configured)
- Check backend is accessible from mobile device

### Build errors
- Make sure Node.js 16+ is installed
- Delete `node_modules` and reinstall












