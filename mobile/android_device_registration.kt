// Android device registration and fingerprinting
package com.contentbot.security

import android.content.Context
import android.provider.Settings
import android.os.Build
import android.util.DisplayMetrics
import android.telephony.TelephonyManager
import java.security.KeyPairGenerator
import java.security.KeyStore
import javax.crypto.KeyGenerator
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.*

class AndroidDeviceManager(private val context: Context) {
    
    companion object {
        private const val KEYSTORE_ALIAS = "ContentBotDeviceKey"
        private const val API_BASE_URL = "https://your-api-domain.com/api"
    }
    
    /**
     * Collect comprehensive device fingerprint
     */
    fun collectDeviceFingerprint(): JSONObject {
        val displayMetrics = context.resources.displayMetrics
        val telephonyManager = context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
        
        return JSONObject().apply {
            // Hardware identifiers
            put("android_id", Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID))
            put("device_model", Build.MODEL)
            put("device_manufacturer", Build.MANUFACTURER)
            put("device_brand", Build.BRAND)
            put("device_product", Build.PRODUCT)
            
            // OS information
            put("os_version", Build.VERSION.RELEASE)
            put("api_level", Build.VERSION.SDK_INT)
            put("build_id", Build.ID)
            put("build_fingerprint", Build.FINGERPRINT)
            
            // Display characteristics
            put("screen_width", displayMetrics.widthPixels)
            put("screen_height", displayMetrics.heightPixels)
            put("screen_density", displayMetrics.density)
            put("screen_dpi", displayMetrics.densityDpi)
            
            // System characteristics
            put("timezone", TimeZone.getDefault().id)
            put("language", Locale.getDefault().language)
            put("country", Locale.getDefault().country)
            
            // Network info (if available)
            try {
                put("network_operator", telephonyManager.networkOperatorName)
                put("sim_operator", telephonyManager.simOperatorName)
            } catch (e: SecurityException) {
                // Handle permission denial gracefully
            }
            
            // Additional entropy
            put("available_processors", Runtime.getRuntime().availableProcessors())
            put("total_memory", Runtime.getRuntime().totalMemory())
        }
    }
    
    /**
     * Generate device-specific keypair in Android Keystore
     */
    private fun generateDeviceKeypair(): Boolean {
        return try {
            val keyPairGenerator = KeyPairGenerator.getInstance(
                KeyProperties.KEY_ALGORITHM_RSA, 
                "AndroidKeyStore"
            )
            
            val keyGenParameterSpec = KeyGenParameterSpec.Builder(
                KEYSTORE_ALIAS,
                KeyProperties.PURPOSE_DECRYPT or KeyProperties.PURPOSE_ENCRYPT
            )
                .setDigests(KeyProperties.DIGEST_SHA256, KeyProperties.DIGEST_SHA512)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_RSA_OAEP)
                .setKeySize(2048)
                .setUserAuthenticationRequired(false) // Set to true for biometric protection
                .build()
            
            keyPairGenerator.initialize(keyGenParameterSpec)
            keyPairGenerator.generateKeyPair()
            
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }
    
    /**
     * Get public key from Android Keystore
     */
    private fun getPublicKey(): String? {
        return try {
            val keyStore = KeyStore.getInstance("AndroidKeyStore")
            keyStore.load(null)
            
            val publicKey = keyStore.getCertificate(KEYSTORE_ALIAS)?.publicKey
            val publicKeyBytes = publicKey?.encoded
            
            android.util.Base64.encodeToString(publicKeyBytes, android.util.Base64.DEFAULT)
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }
    
    /**
     * Register device with backend
     */
    suspend fun registerDevice(telegramToken: String): Result<DeviceRegistrationResult> {
        return withContext(Dispatchers.IO) {
            try {
                // Generate keypair if not exists
                if (!generateDeviceKeypair()) {
                    return@withContext Result.failure(Exception("Failed to generate device keypair"))
                }
                
                // Collect device fingerprint
                val fingerprint = collectDeviceFingerprint()
                
                // Get public key
                val publicKey = getPublicKey()
                    ?: return@withContext Result.failure(Exception("Failed to get public key"))
                
                // Prepare registration data
                val registrationData = JSONObject().apply {
                    put("device_type", "mobile")
                    put("platform", "android")
                    put("device_name", "${Build.MANUFACTURER} ${Build.MODEL}")
                    put("fingerprint", fingerprint)
                    put("public_key", publicKey)
                }
                
                // Make API request
                val client = OkHttpClient()
                val requestBody = registrationData.toString()
                    .toRequestBody("application/json".toMediaType())
                
                val request = Request.Builder()
                    .url("$API_BASE_URL/device/register")
                    .addHeader("Authorization", "Bearer $telegramToken")
                    .post(requestBody)
                    .build()
                
                val response = client.newCall(request).execute()
                val responseBody = response.body?.string()
                
                if (response.isSuccessful && responseBody != null) {
                    val result = JSONObject(responseBody)
                    Result.success(
                        DeviceRegistrationResult(
                            deviceId = result.getString("device_id"),
                            success = result.getBoolean("success"),
                            message = result.getString("message")
                        )
                    )
                } else {
                    Result.failure(Exception("Registration failed: ${response.code}"))
                }
                
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }
    
    /**
     * Decrypt content key using device private key
     */
    fun decryptContentKey(encryptedKey: String): ByteArray? {
        return try {
            val keyStore = KeyStore.getInstance("AndroidKeyStore")
            keyStore.load(null)
            
            val privateKey = keyStore.getKey(KEYSTORE_ALIAS, null) as java.security.PrivateKey
            val cipher = javax.crypto.Cipher.getInstance("RSA/ECB/OAEPWithSHA-256AndMGF1Padding")
            cipher.init(javax.crypto.Cipher.DECRYPT_MODE, privateKey)
            
            val encryptedBytes = android.util.Base64.decode(encryptedKey, android.util.Base64.DEFAULT)
            cipher.doFinal(encryptedBytes)
            
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }
}

data class DeviceRegistrationResult(
    val deviceId: String,
    val success: Boolean,
    val message: String
)

/**
 * Secure video player with device binding
 */
class SecureVideoPlayer(private val context: Context) {
    
    /**
     * Play encrypted video with device verification
     */
    fun playEncryptedVideo(
        encryptedVideoPath: String,
        contentKey: ByteArray,
        onError: (String) -> Unit
    ) {
        try {
            // Decrypt video in memory (simplified - use streaming decryption in production)
            val decryptedPath = decryptVideoFile(encryptedVideoPath, contentKey)
            
            // Use ExoPlayer with custom data source for secure playback
            // Implement screen recording detection and blocking
            setupSecurePlayback(decryptedPath)
            
        } catch (e: Exception) {
            onError("Failed to play video: ${e.message}")
        }
    }
    
    private fun decryptVideoFile(encryptedPath: String, key: ByteArray): String {
        // Implement AES-GCM decryption
        // Return path to decrypted file (in app's private storage)
        return ""
    }
    
    private fun setupSecurePlayback(videoPath: String) {
        // Configure ExoPlayer with:
        // - Custom data source factory
        // - Screen recording detection
        // - Watermarking overlay
        // - Hardware-accelerated decoding
    }
}

/**
 * Anti-tampering and security measures
 */
class SecurityManager(private val context: Context) {
    
    /**
     * Detect if device is rooted/jailbroken
     */
    fun isDeviceCompromised(): Boolean {
        return isRooted() || isDebuggingEnabled() || isEmulator()
    }
    
    private fun isRooted(): Boolean {
        // Check for common root indicators
        val rootPaths = arrayOf(
            "/system/app/Superuser.apk",
            "/sbin/su",
            "/system/bin/su",
            "/system/xbin/su",
            "/data/local/xbin/su",
            "/data/local/bin/su",
            "/system/sd/xbin/su",
            "/system/bin/failsafe/su",
            "/data/local/su"
        )
        
        return rootPaths.any { java.io.File(it).exists() }
    }
    
    private fun isDebuggingEnabled(): Boolean {
        return (context.applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0
    }
    
    private fun isEmulator(): Boolean {
        return Build.FINGERPRINT.startsWith("generic") ||
                Build.FINGERPRINT.startsWith("unknown") ||
                Build.MODEL.contains("google_sdk") ||
                Build.MODEL.contains("Emulator") ||
                Build.MANUFACTURER.contains("Genymotion")
    }
    
    /**
     * Detect screen recording attempts
     */
    fun detectScreenRecording(): Boolean {
        // Check for screen recording apps
        // Monitor media projection usage
        // Detect accessibility services that might capture screen
        return false // Simplified implementation
    }
}
