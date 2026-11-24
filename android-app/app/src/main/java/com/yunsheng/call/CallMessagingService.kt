package com.yunsheng.call
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

class CallMessagingService:FirebaseMessagingService(){
    override fun onNewToken(token:String){val device=CallApplication.deviceId(this);val json="""{"device_id":"$device","push_token":"$token"}""";val req=Request.Builder().url("${BuildConfig.SERVER_URL}/api/calls/devices").post(json.toRequestBody("application/json".toMediaType())).build();Thread{runCatching{OkHttpClient().newCall(req).execute().close()}}.start()}
    override fun onMessageReceived(message:RemoteMessage){if(message.data["type"]!="incoming_call")return;val id="incoming_calls";val manager=getSystemService(NotificationManager::class.java);manager.createNotificationChannel(NotificationChannel(id,"来电",NotificationManager.IMPORTANCE_HIGH).apply{description="电脑端语音来电";enableVibration(true)});val intent=Intent(this,MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP);val pending=PendingIntent.getActivity(this,1,intent,PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE);val note=NotificationCompat.Builder(this,id).setSmallIcon(android.R.drawable.sym_call_incoming).setContentTitle("云声电话来电").setContentText("${message.data["callerId"]?:"电脑端"} 正在呼叫").setPriority(NotificationCompat.PRIORITY_MAX).setCategory(NotificationCompat.CATEGORY_CALL).setFullScreenIntent(pending,true).setAutoCancel(true).build();manager.notify(1001,note)}
}
