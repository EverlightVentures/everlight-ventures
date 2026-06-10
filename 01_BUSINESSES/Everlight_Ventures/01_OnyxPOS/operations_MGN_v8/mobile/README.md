# OnyxPOS Mobile App

React Native mobile app for OnyxPOS - Built with Expo for iOS and Android.

## Features

- 🔐 **Secure Authentication** - JWT-based auth with auto token refresh
- 📊 **Real-time Dashboard** - Live sales metrics and analytics
- 📱 **Native Performance** - Smooth 60fps on all devices
- 🌙 **Dark Theme** - Premium dark interface matching web app
- 🔄 **Pull to Refresh** - Real-time data updates
- 📦 **Offline Ready** - AsyncStorage for local data persistence

## Tech Stack

- **React Native** - Cross-platform mobile framework
- **Expo** - Development platform and build system
- **React Navigation** - Native navigation
- **Axios** - HTTP client with interceptors
- **AsyncStorage** - Local storage for auth tokens

## Quick Start

### Prerequisites

- Node.js 18+
- Expo CLI: `npm install -g expo-cli`
- iOS Simulator (Mac) or Android Studio (Any OS)
- Expo Go app on your phone (optional)

### Installation

```bash
cd mobile
npm install
```

### Run Development Server

```bash
# Start Expo dev server
npm start

# Run on iOS simulator (Mac only)
npm run ios

# Run on Android emulator
npm run android

# Run in web browser (for quick testing)
npm run web
```

### Testing on Physical Device

1. Install "Expo Go" app from App Store or Play Store
2. Run `npm start` in terminal
3. Scan the QR code with Expo Go app
4. App will load on your device

## Project Structure

```
mobile/
├── src/
│   ├── screens/           # App screens
│   │   ├── LoginScreen.js
│   │   └── DashboardScreen.js
│   ├── navigation/        # Navigation setup
│   │   └── AppNavigator.js
│   ├── context/           # React Context
│   │   └── AuthContext.js
│   ├── utils/             # Utilities
│   │   └── api.js         # API client
│   └── components/        # Reusable components
├── assets/                # Images, fonts
├── App.js                 # Entry point
└── package.json
```

## Configuration

### Backend URL

Update the API base URL in `src/utils/api.js`:

```javascript
// For local development
const API_BASE_URL = 'http://localhost:5000/api/v1';

// For production
const API_BASE_URL = 'https://api.onyxpos.com/api/v1';

// For iOS simulator (local backend)
const API_BASE_URL = 'http://localhost:5000/api/v1';

// For Android emulator (local backend)
const API_BASE_URL = 'http://10.0.2.2:5000/api/v1';

// For physical device (local backend on same network)
const API_BASE_URL = 'http://YOUR_COMPUTER_IP:5000/api/v1';
```

## Building for Production

### iOS (requires Mac + Apple Developer Account)

```bash
# Build standalone app
expo build:ios

# Or use EAS Build (recommended)
npm install -g eas-cli
eas build --platform ios
```

### Android

```bash
# Build APK for testing
expo build:android -t apk

# Build AAB for Play Store
expo build:android -t app-bundle

# Or use EAS Build (recommended)
npm install -g eas-cli
eas build --platform android
```

## Publishing to App Stores

### iOS App Store

1. Build production iOS app with EAS Build
2. Download IPA file
3. Upload to App Store Connect via Transporter app
4. Submit for review

### Google Play Store

1. Build production Android AAB with EAS Build
2. Create app listing in Play Console
3. Upload AAB to production track
4. Submit for review

## Features by Screen

### Login Screen
- Email/password authentication
- Loading states
- Error handling
- Auto-login with stored tokens

### Dashboard Screen
- Real-time metrics (today, week, month)
- Trial countdown banner
- Pull-to-refresh
- Quick action buttons
- Logout functionality

## Next Steps

- [ ] Add Sales Terminal screen
- [ ] Add Inventory Management screen
- [ ] Add Analytics screen
- [ ] Add Settings screen
- [ ] Implement barcode scanning
- [ ] Add receipt printing
- [ ] Offline transaction queue
- [ ] Push notifications

## Development Tips

### Running on Android Emulator with Local Backend

1. Start your backend: `cd backend && python3 app.py`
2. Use `http://10.0.2.2:5000/api/v1` as API URL (10.0.2.2 maps to localhost on emulator)

### Running on iOS Simulator with Local Backend

1. Start your backend: `cd backend && python3 app.py`
2. Use `http://localhost:5000/api/v1` as API URL

### Running on Physical Device with Local Backend

1. Ensure device and computer are on same Wi-Fi
2. Find your computer's local IP: `ipconfig getifaddr en0` (Mac) or `ipconfig` (Windows)
3. Use `http://YOUR_IP:5000/api/v1` as API URL

## Troubleshooting

### "Unable to connect to server"
- Check that backend is running
- Verify API_BASE_URL is correct for your environment
- On Android emulator, use `http://10.0.2.2:5000`
- On physical device, use your computer's local IP

### "Expo Go has stopped working"
- Clear Expo cache: `expo start -c`
- Reinstall node_modules: `rm -rf node_modules && npm install`

### Build failures
- Update Expo SDK: `expo upgrade`
- Check expo-cli version: `expo
