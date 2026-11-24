# 云声电话 Android App

用 Android Studio 打开本目录并安装 Android SDK 35。`app/build.gradle.kts` 的 `SERVER_URL` 默认适用于模拟器；真机需改成电脑局域网地址，跨网络正式环境必须使用 HTTPS 域名。

后台来电需要在 Firebase 创建包名 `com.yunsheng.call` 的应用，将 `google-services.json` 放入 `android-app/app/`，添加 Google Services 插件，并在服务端 `.env` 设置 `FIREBASE_CREDENTIALS`。前台打开 App 时不依赖 Firebase。

当前使用公共 STUN。生产环境必须部署 TURN，否则部分运营商或企业网络无法建立通话。
