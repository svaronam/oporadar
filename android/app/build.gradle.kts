plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "es.oporadar.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "es.oporadar.app"
        minSdk = 26
        targetSdk = 34
        versionCode = 3
        versionName = "1.2.0"
    }

    // Firma fija: así cada APK nueva de GitHub Actions se instala encima de la anterior sin desinstalar.
    signingConfigs {
        create("fija") {
            storeFile = file("keystore/oporadar.jks")
            storePassword = System.getenv("KEYSTORE_PASSWORD")
            keyAlias = "oporadar"
            keyPassword = System.getenv("KEYSTORE_PASSWORD")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("fija")
        }
        debug {
            signingConfig = signingConfigs.getByName("fija")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.work:work-runtime-ktx:2.9.1")
}
