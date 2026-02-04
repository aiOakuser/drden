# GlobalDesignerHub – iPhone App

React Native (Expo) app for Global Designer Hub: designers, collections, events, and account.

## Prerequisites

- Node.js 18+
- iOS Simulator (Xcode on Mac) or [Expo Go](https://expo.dev/go) on your iPhone
- Backend running at `http://127.0.0.1:8002` (or set `API_BASE_URL` in `src/config.ts`)

## Setup

```bash
cd mobile
npm install
```

## Run

```bash
npm start
```

Then press **i** for iOS Simulator, or scan the QR code with Expo Go on your device.

**Physical device:** If the app cannot reach the API, set `API_BASE_URL` in `src/config.ts` to your machine’s LAN IP (e.g. `http://192.168.1.100:8002`).

## Features

- **Home** – Shortcuts to Designers, Collections, Events
- **Designers** – List and search; tap for profile (bio, location, links)
- **Collections** – List and search; tap for collection detail and looks
- **Events** – List and search; tap for event detail (date, venue, description)
- **Account** – Sign in / Sign up; when signed in: profile and “My designs”, Sign out

## API

The app uses the Django mobile API under `/api/mobile/` (see backend `designer_portfolio/mobile_api.py`).
