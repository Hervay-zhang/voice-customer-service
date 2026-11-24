package com.yunsheng.call
import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.os.Bundle
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    private lateinit var webView: WebView
    private val permissions=registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()){}
    @SuppressLint("SetJavaScriptEnabled") override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        permissions.launch(arrayOf(Manifest.permission.RECORD_AUDIO,Manifest.permission.POST_NOTIFICATIONS))
        webView=WebView(this).apply {
            settings.javaScriptEnabled=true; settings.domStorageEnabled=true; settings.mediaPlaybackRequiresUserGesture=false; settings.mixedContentMode=WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            webChromeClient=object:WebChromeClient(){override fun onPermissionRequest(request:PermissionRequest){if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED)runOnUiThread{request.grant(request.resources)}else request.deny()}}
        }
        setContentView(webView)
        webView.loadUrl("${BuildConfig.SERVER_URL}/mobile?device=${CallApplication.deviceId(this)}")
    }
    @Deprecated("Deprecated in Java") override fun onBackPressed(){if(webView.canGoBack())webView.goBack()else super.onBackPressed()}
}
