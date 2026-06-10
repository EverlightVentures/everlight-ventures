# OnyxPOS PWA Setup Guide

## Progressive Web App Features

OnyxPOS frontend is now a fully-featured Progressive Web App (PWA) with:

- ✅ **Offline Support** - Works without internet connection
- ✅ **Installable** - Add to home screen on mobile and desktop
- ✅ **Fast Loading** - Service worker caching for instant loads
- ✅ **Mobile-Optimized** - Touch-friendly interface with responsive design
- ✅ **App-Like Experience** - Fullscreen mode, no browser UI
- ✅ **Auto-Updates** - Seamless updates when new versions deploy

## Installation

### 1. Install Dependencies

```bash
cd /home/mgn/Projects/OnyxPOS/frontend
npm install
```

This will install `vite-plugin-pwa` which handles service worker generation and PWA manifest.

### 2. Generate PWA Icons

You need to create the following icon files in `/frontend/public/`:

**Required Icons:**
- `pwa-192x192.png` - Small icon for Android
- `pwa-512x512.png` - Large icon for Android (also used as maskable)
- `apple-touch-icon.png` - 180x180px for iOS
- `favicon-32x32.png` - Standard favicon
- `favicon-16x16.png` - Small favicon
- `masked-icon.svg` - Safari pinned tab icon

**Quick Icon Generation:**

Using ImageMagick (if you have a logo file):
```bash
# From a master logo.png (1024x1024 recommended)
convert logo.png -resize 192x192 public/pwa-192x192.png
convert logo.png -resize 512x512 public/pwa-512x512.png
convert logo.png -resize 180x180 public/apple-touch-icon.png
convert logo.png -resize 32x32 public/favicon-32x32.png
convert logo.png -resize 16x16 public/favicon-16x16.png
```

Or use online tools:
- https://realfavicongenerator.net/ - Complete favicon package
- https://www.pwabuilder.com/imageGenerator - PWA icon generator
- https://maskable.app/ - Maskable icon editor

### 3. Development Mode

```bash
npm run dev
```

PWA features are enabled in development mode. You can test:
- Service worker registration in DevTools > Application > Service Workers
- Manifest in DevTools > Application > Manifest
- Install prompt (may need HTTPS even in dev)

### 4. Production Build

```bash
npm run build
npm run preview
```

The build process will:
1. Generate service worker (`sw.js`)
2. Create workbox config for caching
3. Generate PWA manifest
4. Optimize assets for offline use

## PWA Capabilities

### Offline Mode

The PWA caches:
- **Static Assets**: All JS, CSS, HTML files
- **API Responses**: 5-minute cache for API calls (NetworkFirst strategy)
- **Images & Fonts**: Cached after first load

**Offline Behavior:**
- If online: Fetch from network, cache response
- If offline: Serve from cache
- If cache miss: Show offline fallback (if configured)

### Installation

**Desktop (Chrome/Edge):**
1. Visit the app
2. Look for install icon in address bar
3. Click "Install OnyxPOS"
4. App opens in standalone window

**Mobile (iOS):**
1. Open in Safari
2. Tap Share button
3. Select "Add to Home Screen"
4. Tap "Add"

**Mobile (Android):**
1. Open in Chrome
2. Tap menu (⋮)
3. Select "Install app" or "Add to Home Screen"

### Auto-Updates

Service worker uses `registerType: 'autoUpdate'`:
- Checks for updates on page load
- Downloads new version in background
- Updates automatically on next visit
- No user prompts or interruptions

## Configuration

### Manifest (vite.config.js)

```javascript
manifest: {
  name: 'OnyxPOS - Point of Sale',
  short_name: 'OnyxPOS',
  description: '...',
  theme_color: '#0a0a0a',      // Matches OnyxOS black branding
  background_color: '#0a0a0a',
  display: 'standalone',        // Fullscreen without browser UI
  orientation: 'portrait',      // Lock to portrait on mobile
  start_url: '/',
}
```

### Cache Strategy

**NetworkFirst (API calls):**
- Tries network first
- Falls back to cache if offline
- Cache expires after 5 minutes
- Max 100 cached entries

**CacheFirst (Static assets):**
- Serves from cache immediately
- Updates cache in background
- Perfect for images, fonts, JS bundles

### Touch Optimization

CSS in `index.html` handles:
- **No tap highlight**: Removes default blue flash on tap
- **Smooth scrolling**: `-webkit-overflow-scrolling: touch`
- **No text selection**: Prevents accidental text selection on buttons

## Testing

### 1. Lighthouse PWA Audit

```bash
# Build production version
npm run build
npm run preview

# Open Chrome DevTools
# Navigate to Lighthouse tab
# Run PWA audit
```

**Target Scores:**
- PWA: 100/100
- Performance: 90+
- Accessibility: 90+
- Best Practices: 90+

### 2. Manual Testing

**Install Flow:**
- [ ] Desktop install prompt appears
- [ ] Mobile "Add to Home Screen" works
- [ ] App opens in standalone mode
- [ ] No browser UI visible

**Offline Mode:**
- [ ] Turn off network in DevTools
- [ ] Reload page (should load from cache)
- [ ] Navigate between routes (should work)
- [ ] API calls use cached data

**Mobile Touch:**
- [ ] No blue tap highlights
- [ ] Buttons have adequate touch targets (44x44px minimum)
- [ ] Smooth scrolling
- [ ] No accidental text selection

### 3. Browser Compatibility

**Full PWA Support:**
- ✅ Chrome/Edge (Desktop & Mobile)
- ✅ Safari (iOS 11.3+)
- ✅ Firefox (Desktop & Mobile)
- ✅ Samsung Internet

**Limited Support:**
- ⚠️ Safari Desktop (no install, but works as website)
- ⚠️ Older browsers (graceful degradation)

## Deployment

### Vercel / Netlify

PWA works out of the box. The build process generates all necessary files:
- `dist/manifest.webmanifest` - PWA manifest
- `dist/sw.js` - Service worker
- `dist/workbox-*.js` - Workbox runtime

**HTTPS Required:** PWAs require HTTPS in production. Vercel/Netlify provide this automatically.

### Custom Server (Nginx)

Add headers to serve service worker:

```nginx
location /sw.js {
  add_header Cache-Control "no-cache";
  add_header Service-Worker-Allowed "/";
}

location /manifest.webmanifest {
  add_header Content-Type application/manifest+json;
}
```

### Service Worker Updates

When you deploy a new version:
1. Service worker detects update
2. Downloads new assets in background
3. Activates on next page load (or refresh)
4. User sees new version seamlessly

**Force Update:**
```javascript
// In your app code
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then(registrations => {
    registrations.forEach(registration => registration.update())
  })
}
```

## Mobile-Specific Features

### iOS Enhancements

- **Status Bar**: Black translucent for immersive feel
- **App Title**: "OnyxPOS" in app switcher
- **Splash Screen**: Auto-generated from icons
- **Home Screen Icon**: 180x180 with rounded corners

### Android Enhancements

- **Theme Color**: Black matches status bar
- **Maskable Icon**: Safe zone for adaptive icons
- **Shortcuts**: Can add quick actions in manifest
- **Share Target**: Can receive shared content (future)

### Touch Targets

All interactive elements meet WCAG 2.1 guidelines:
- Minimum 44x44px touch target
- Adequate spacing between elements
- Visual feedback on touch

## Performance Optimizations

### Code Splitting

Vite automatically splits:
- Route-based chunks
- Vendor bundles (React, libraries)
- Lazy-loaded components

### Image Optimization

Recommendations:
- Use WebP format for icons
- Compress PNG icons (TinyPNG, ImageOptim)
- Serve responsive images with `srcset`

### Bundle Size

Current build (approximate):
- Main bundle: ~150KB (gzipped)
- Vendor (React): ~130KB (gzipped)
- Total initial: ~280KB

**Target**: Keep under 300KB for fast 3G loads

## Troubleshooting

### Service Worker Not Registering

1. Check HTTPS (required in production)
2. Clear cache and hard reload (Ctrl+Shift+R)
3. Check DevTools > Application > Service Workers for errors

### Install Prompt Not Showing

1. Ensure all manifest fields are valid
2. Check icon files exist at correct paths
3. Visit site at least twice (some browsers delay prompt)
4. Open DevTools > Application > Manifest to verify

### Offline Mode Not Working

1. Verify service worker is active (DevTools > Application)
2. Check cache storage (DevTools > Application > Cache Storage)
3. Ensure API URLs match workbox patterns in vite.config.js

### Icons Not Loading

1. Verify files exist in `/public/` directory
2. Check browser console for 404 errors
3. Ensure correct paths in manifest (no leading `/public/`)

## Next Steps

1. **Generate Icons** - Create all required icon sizes
2. **Test Install** - Verify install flow on mobile and desktop
3. **Lighthouse Audit** - Run and fix any issues
4. **Deploy** - Push to production with HTTPS
5. **Monitor** - Track PWA install metrics in analytics

## Resources

- [PWA Checklist](https://web.dev/pwa-checklist/)
- [Vite PWA Plugin Docs](https://vite-pwa-org.netlify.app/)
- [Workbox Docs](https://developers.google.com/web/tools/workbox)
- [MDN: Progressive Web Apps](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps)
