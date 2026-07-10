# SFProBrows (SafetyFastProfessionalBrowser)
SFProBrows is a modern web browser project focused on delivering high performance and tight security boundaries.

This project is actively developed and maintained by PyNetCoder Software Corporation to contribute to the open-source community.

🚀 Features
- **High Performance:** Optimized for fast page loading times with minimal resource consumption.
- **Security-Oriented:** A secure browsing infrastructure that prioritizes user privacy.
- **Intelligent AdBlocker (New):** Native Python-level network interception targeting trackers, intrusive ads, and malicious third-party scripts.
- **Advanced Logging (New):** Integrated with Loguru and Icecream for seamless debug tracking and local automated logs stored in `AppData/Local/SFProBrows`.
- **Windows Integration:** Fully compatible with the Windows default browser selection ecosystem via Registry optimizations.

🗺️ 1.2.0 Security Roadmap (Upcoming)
The following core security mitigations are currently in development for the next minor release:
1. **Malware/Spyware Domain Blacklist:** Implementing network-level blocking for known high-risk domains (e.g., untrusted third-party game launchers, automated malicious APK downloaders).
2. **Drive-by Download Interception:** Automatic termination of stealth background downloads attempting to drop executable payloads without explicit user consent.
3. **SHA-256 Hash Verification:** Built-in cryptographic integrity checks for downloaded artifacts to guard against local system compromise and file-tampering.
4. **Brotli Compression Evaluation:** Assessing the native `br` compression stack integration for faster data transmission overhead.
s.

🛠️ How to Run
### Running the Executable
This project is distributed as a standalone Windows executable. You do not need to install Python or any external dependencies to run it.

1. Navigate to the latest release on GitHub.
2. Launch SFProBrows.exe directly to start the browser.

📦 Deployment (For Developers)
Stable production releases for Windows users are compiled and packaged into a professional installation wizard (.exe) using Inno Setup. Future production-ready setups and installers will be available under the Releases section of this repository.

📄 License
This project is licensed under the Apache License 2.0. For more details, please refer to the LICENSE file located in the root directory of this repository.

Copyright (c) 2026 PyNetCoder
