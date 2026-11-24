package com.yunsheng.call
import android.app.Application
import android.content.Context
import java.util.UUID
class CallApplication : Application() {
    companion object { fun deviceId(context: Context): String { val prefs=context.getSharedPreferences("call",Context.MODE_PRIVATE); return prefs.getString("deviceId",null) ?: ("phone-"+UUID.randomUUID().toString().take(6)).also{prefs.edit().putString("deviceId",it).apply()} } }
}
