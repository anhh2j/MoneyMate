# MoneyMate

Trợ lý tài chính cá nhân Android local-first. T00 chỉ tạo khung build; ứng dụng mở một màn hình “MoneyMate”. Không có parser, DB, capture service, khóa ứng dụng hay chức năng mạng ở task này.

## Yêu cầu và build từ clone sạch

- JDK 17 (`java -version`).
- Android Studio có SDK Manager, hoặc Android command-line tools.
- Cài Android SDK Platform 37.0, Build Tools 37.0.0, Platform Tools; chấp nhận SDK licenses.
- Đặt `ANDROID_HOME` trỏ tới SDK (hoặc cấu hình `sdk.dir` trong `local.properties`, không commit).
- Lần build đầu cần Internet để tải công cụ/dependency; APK không có quyền INTERNET.

```sh
git clone https://github.com/anhh2j/MoneyMate.git
cd MoneyMate
# Khi review T00: git switch feature/T00-project-skeleton
sdkmanager "platforms;android-37.0" "build-tools;37.0.0" "platform-tools"
sdkmanager --licenses
./gradlew ktlintCheck detekt test assembleDebug
./gradlew lintDebug verifyModuleGraph
```

Windows PowerShell: dùng `gradlew.bat` thay cho `./gradlew`; đặt `$env:ANDROID_HOME` tới thư mục SDK. Không cần cài Gradle toàn cục; wrapper pin Gradle và SHA-256.

APK: `app/build/outputs/apk/debug/app-debug.apk`. Khởi động một AVD Android API 26 trở lên từ Android Studio Device Manager, sau đó:

```sh
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -W -n com.app.moneymate/.MainActivity
adb shell uiautomator dump /sdcard/window.xml
adb shell cat /sdcard/window.xml
```

Màn hình phải hiển thị “MoneyMate”. CI tự kiểm text trong UI hierarchy và lưu ảnh chụp.

## Kiểm tra

```sh
./gradlew :parser:dependencies :dedup:dependencies :categorizer:dependencies
./gradlew :app:dependencies
./gradlew :app:processDebugMainManifest :app:processReleaseMainManifest
./gradlew verifyModuleGraph
```

CI ghi dependency report từng module và kiểm merged manifests debug/release. Báo cáo nằm ở `build/reports/`, `<module>/build/reports/`, `<module>/build/test-results/`. Mỗi module có đúng một smoke test: JVM kiểm resource thật đã đóng gói và liên kết core-model; Android library kiểm BuildConfig được sinh; app kiểm nạp launcher Activity. Không dùng smoke test để tạo tỷ lệ coverage giả.

JaCoCo đo coverage cho các module Kotlin/JVM. Ngưỡng 85% ở parser/dedup/categorizer được cấu hình nhưng chưa bật vì chưa có production class; T04 phải bật gate mặc định khi thêm code thật. Có thể chạy thử cấu hình bằng `./gradlew :parser:check :dedup:check :categorizer:check -PenableProductionCoverage=true`; khi chưa có class, không coi kết quả bỏ qua của JaCoCo là đạt coverage. Xem ADR-0001.

## Cấu trúc module

| Module | Loại / trách nhiệm về sau | Phụ thuộc module trực tiếp |
| --- | --- | --- |
| app | Android application, Compose / navigation / DI | tất cả tám module còn lại |
| core-model | Kotlin/JVM, model / interface | không |
| parser | Kotlin/JVM, template engine | core-model |
| dedup | Kotlin/JVM, khử trùng lặp | core-model |
| categorizer | Kotlin/JVM, phân loại | core-model |
| capture | Android library, thu thập | core-model |
| data | Android library, persistence | core-model |
| privacy | Android library, quyền riêng tư | không ở T00 |
| security | Android library, khóa cục bộ | không ở T00 |

Không tạo auth/sync ở MVP. `applicationId`: `com.app.moneymate`; minSdk 26, compileSdk/targetSdk 37 (Android 17 ổn định; không dùng QPR beta).

## Version và phạm vi

Version tạm chỉ khai báo trong `app/build.gradle.kts`, theo DOC-BRIEF-M0 v1.5.0. T00b sẽ gỡ các giá trị tạm và đọc từ version.properties, bổ sung pipeline version/release. T00 không hiển thị version, không ký/phát hành release, không tạo tag. CI chỉ assemble debug; việc xử lý release manifest phục vụ kiểm quyền, không sinh APK release.

Quy tắc làm việc: [AGENTS.md](AGENTS.md). Tài liệu: [docs/README.md](docs/README.md). Quyết định: [ADR-0001](docs/adr/0001-kien-truc-module.md).
