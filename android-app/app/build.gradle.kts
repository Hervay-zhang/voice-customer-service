plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android {
    namespace = "com.yunsheng.call"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.yunsheng.call"; minSdk = 26; targetSdk = 35
        versionCode = 1; versionName = "1.0"
        buildConfigField("String", "SERVER_URL", "\"http://10.0.2.2:8000\"")
    }
    buildFeatures { buildConfig = true }
}
dependencies {
    implementation("androidx.core:core-ktx:1.16.0")
    implementation("androidx.appcompat:appcompat:1.7.1")
    implementation("com.google.android.material:material:1.12.0")
    implementation(platform("com.google.firebase:firebase-bom:34.16.0"))
    implementation("com.google.firebase:firebase-messaging")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
}
