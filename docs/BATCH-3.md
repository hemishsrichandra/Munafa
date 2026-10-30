# Batch 3: mobile PWA and shared Android shell

## Completion report

**Implemented after Batch 2 in the existing React 19/Vite product.** No stock/sales/dues modules, forecasts or IndexedDB synchronization were added. The original supplier workflow remains the working core.

### Scope, files and contracts

- `frontend/src/App.jsx` and existing components now expose Home, Purchases and More on phones. Daily Business Brief uses actual existing case balances/overdue follow-ups, with synthetic-store labels. Recovery remains under Purchases; no dead future-module tabs were introduced.
- `styles.css` extends the existing design with stacked mobile cards, readable totals, safe-area spacing, horizontal bottom navigation, 44px controls, focus states and reduced motion. Existing desktop layout remains.
- `session.jsx`, `pwa.jsx`, `api.js` and shared UI cover sign-in, roles, loading, errors, offline notices, install/update controls, dialogs and toasts. The phone receiving editor sends exact decimal strings; backend-calculated paise remain authoritative.
- English/Hindi/Kannada selection is a navigation-label preview. The UI explicitly discloses that full workflow translations have not been reviewed.
- `frontend/public/manifest.webmanifest`, `sw.js` and project-owned icons define `/` scope/start, standalone display and shell-only caching. `scripts/build-pwa.cjs` injects a content-derived version and static asset list after Vite build.
- `capacitor.config.json`, `android/` and root npm scripts wrap the same `frontend/dist`; no Android business screens or rules were duplicated. Core/CLI/Android use Capacitor 7.6.10. Filesystem 7.1.9 and Share 7.0.4 support authenticated private-file downloads through temporary app-cache files and an explicit OS share sheet. No external-storage permission is needed.
- Batch 3 adds no application database tables or new merchant APIs. Android login can receive a memory-only bearer session; verified native file requests use that token, never a token embedded in a URL. Server authorization and approval still apply.

### Offline, updates and privacy

First web installation/cache warm-up requires connectivity and a secure context (HTTPS or loopback). The service worker caches public application assets only. It bypasses `/api`, attachments and authenticated records; account logout discards workspace memory and purges non-shell caches. Server logout/revocation still requires connectivity. The packaged Android shell launches without a service worker.

Offline sign-in, records, AI and Paytm calls do not work. Pending writes are neither accepted nor queued in this batch. Existing in-memory records can become stale while disconnected; the global offline indicator makes that limitation visible. No browser localStorage/IndexedDB application persistence exists yet.

A waiting worker activates only after the merchant confirms reload; the prompt explicitly warns about unsaved input. Cancelling leaves the current form in place. No automatic reload discards a draft.

### Validation and evidence

| Check                                        | Result                                                                                                                                                           |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `npm run build`                              | Pass: Vite production build and 12 public PWA assets                                                                                                             |
| `npm run test:e2e`                           | **8 pass** against isolated PostgreSQL schemas                                                                                                                   |
| Phone viewports                              | 360×800, 390×844, 430×932, narrow 320×740, rotated 800×360                                                                                                       |
| Phone assertions                             | No horizontal overflow; usable navigation; 44px nav targets; bounded dialogs and keyboard dismissal                                                              |
| Original workflow                            | Desktop A-104 → reviewed ₹80 → approval → manual sharing confirmation → promise → documented recovery → approved CSV; PNG download checked                       |
| Fractional phone workflow                    | Manual 1.25kg billed/0.75kg received at ₹25.50 → ₹12.75 → approval/message/promise/proof → verified recovery                                                     |
| PWA                                          | Manifest metadata, worker/controller registration, shell cache, API exclusion and offline reload after warm-up pass                                              |
| `npm run android:sync`                       | Pass; both native file plugins registered                                                                                                                        |
| `npm run android:check`                      | Pass installed-project checks; restricted-network latest-version lookup returned unknown                                                                         |
| Gradle `assembleDebug lintDebug --no-daemon` | **BUILD SUCCESSFUL**; Android app lint: 0 errors, 28 warnings (including generated template/icon density/duplicate warnings); no lint suppression/baseline added |
| APK signature                                | `apksigner verify --verbose` succeeds with debug v1/v2 signatures; metadata warnings remain; no release signing claimed                                          |
| APK permissions                              | INTERNET and AndroidX’s app-scoped receiver permission only; no camera/microphone/location/contacts/storage permission                                           |
| APK source parity                            | Every packaged `assets/public` file byte-compared with current `frontend/dist`: pass                                                                             |
| Backend                                      | **52 PostgreSQL tests pass**; Ruff and schema-drift check pass                                                                                                   |

Browser screenshots are generated in ignored `test-results/`: `phone-360x800.png`, `phone-390x844.png`, `phone-430x932.png`, `phone-320x740.png`, `phone-800x360.png`, `case-mobile.png`, `fractional-recovery-mobile.png` and `overview-desktop.png`. The 390px screenshot was visually inspected; bottom navigation remains horizontal and clear of content.

### Exact build and install commands

```sh
npm ci
npm run android:sync
npm run android:check
export JAVA_HOME=/path/to/jdk-21/Contents/Home
export ANDROID_HOME=/path/to/android-sdk
cd android
./gradlew assembleDebug lintDebug --no-daemon
# Only on an explicitly connected development device:
"$ANDROID_HOME/platform-tools/adb" install -r app/build/outputs/apk/debug/app-debug.apk
```

This run used Node 20.20.2, Temurin **21.0.13+9**, Gradle **8.11.1**, compile/target SDK **35**, min SDK **23**, and SDK Build Tools 34/35. Google’s SDK license was accepted only after explicit owner approval. The installed Java 25 initially failed Gradle compatibility; Java 21 resolved it. Dependency/tool warnings are not claimed to be absent.

Temporary tools used locally:

```sh
export JAVA_HOME=/private/tmp/munafa-jdk21/jdk-21.0.13+9/Contents/Home
export ANDROID_HOME=/private/tmp/munafa-android-sdk
```

These temporary tools are not part of the repository. Install permanent local Android Studio/SDK/JDK tools for continued development.

### APK artifact and limits

The generated APK is `android/app/build/outputs/apk/debug/app-debug.apk`, copied to ignored `artifacts/munafa-debug.apk` (**4,378,899 bytes**). SHA-256:

```text
0085c1508b6a0ca6abc20d9df98ff19d579cab48c1a40dcd48ba343bfbe0363d
```

This artifact contains the bundled offline shell. **No hosted HTTPS backend was provided**, so connected sign-in/data features deliberately report a missing backend configuration. To build a connected APK, supply public `VITE_API_BASE=https://YOUR_HOST/api`, allow the exact native origin `https://localhost` on that backend, and rebuild/sync. No credential belongs in a VITE variable.

No physical Android device, emulator, native camera/file picker/share sheet, Android Back behavior, iOS installation or release-signed distribution was tested. Browser offline simulation verifies the PWA shell, not those native behaviors. No live Sarvam or Paytm integration has been verified. GitHub CI is configured but not executed remotely. These are explicit remaining validation items rather than working integration claims.

### Handoff

Batch 2 and Batch 3 are complete within the validated local scope above. Changes remain local/uncommitted. Review these reports, run a real-device acceptance pass and select a hosted HTTPS endpoint before a connected APK demonstration. Batch 4 requires separate approval; no durable outbox, offline financial mutation or future merchant module was started.
