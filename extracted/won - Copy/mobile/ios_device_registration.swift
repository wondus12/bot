// iOS device registration and fingerprinting
import Foundation
import UIKit
import Security
import CryptoKit
import LocalAuthentication

class IOSDeviceManager {
    
    private let apiBaseURL = "https://your-api-domain.com/api"
    private let keychainService = "com.contentbot.devicekey"
    private let keyTag = "ContentBotDeviceKey"
    
    /**
     * Collect comprehensive device fingerprint
     */
    func collectDeviceFingerprint() -> [String: Any] {
        let device = UIDevice.current
        let screen = UIScreen.main
        let locale = Locale.current
        let timeZone = TimeZone.current
        
        var fingerprint: [String: Any] = [:]
        
        // Device identifiers
        fingerprint["vendor_id"] = device.identifierForVendor?.uuidString ?? ""
        fingerprint["device_model"] = device.model
        fingerprint["device_name"] = device.name
        fingerprint["system_name"] = device.systemName
        fingerprint["system_version"] = device.systemVersion
        
        // Hardware characteristics
        fingerprint["screen_width"] = screen.bounds.width
        fingerprint["screen_height"] = screen.bounds.height
        fingerprint["screen_scale"] = screen.scale
        fingerprint["screen_brightness"] = screen.brightness
        
        // System characteristics
        fingerprint["timezone"] = timeZone.identifier
        fingerprint["language"] = locale.languageCode ?? ""
        fingerprint["country"] = locale.regionCode ?? ""
        fingerprint["calendar"] = locale.calendar.identifier
        
        // App and system info
        fingerprint["bundle_id"] = Bundle.main.bundleIdentifier ?? ""
        fingerprint["app_version"] = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? ""
        
        // Additional entropy
        fingerprint["processor_count"] = ProcessInfo.processInfo.processorCount
        fingerprint["physical_memory"] = ProcessInfo.processInfo.physicalMemory
        
        return fingerprint
    }
    
    /**
     * Generate device-specific keypair in Secure Enclave
     */
    private func generateDeviceKeypair() -> Bool {
        // Delete existing key if present
        deleteDeviceKeypair()
        
        let access = SecAccessControlCreateWithFlags(
            kCFAllocatorDefault,
            kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
            [.privateKeyUsage, .biometryAny], // Require biometric authentication
            nil
        )
        
        guard access != nil else {
            print("Failed to create access control")
            return false
        }
        
        let keyAttributes: [String: Any] = [
            kSecAttrKeyType as String: kSecAttrKeyTypeRSA,
            kSecAttrKeySizeInBits as String: 2048,
            kSecAttrTokenID as String: kSecAttrTokenIDSecureEnclave,
            kSecPrivateKeyAttrs as String: [
                kSecAttrIsPermanent as String: true,
                kSecAttrApplicationTag as String: keyTag.data(using: .utf8)!,
                kSecAttrAccessControl as String: access!
            ]
        ]
        
        var error: Unmanaged<CFError>?
        guard let privateKey = SecKeyCreateRandomKey(keyAttributes as CFDictionary, &error) else {
            print("Failed to generate keypair: \(error?.takeRetainedValue().localizedDescription ?? "Unknown error")")
            return false
        }
        
        return true
    }
    
    /**
     * Get public key from Secure Enclave
     */
    private func getPublicKey() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassKey,
            kSecAttrApplicationTag as String: keyTag.data(using: .utf8)!,
            kSecAttrKeyType as String: kSecAttrKeyTypeRSA,
            kSecReturnRef as String: true
        ]
        
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        
        guard status == errSecSuccess, let privateKey = item else {
            print("Failed to retrieve private key")
            return nil
        }
        
        guard let publicKey = SecKeyCopyPublicKey(privateKey as! SecKey) else {
            print("Failed to get public key")
            return nil
        }
        
        var error: Unmanaged<CFError>?
        guard let publicKeyData = SecKeyCopyExternalRepresentation(publicKey, &error) else {
            print("Failed to export public key: \(error?.takeRetainedValue().localizedDescription ?? "Unknown error")")
            return nil
        }
        
        return (publicKeyData as Data).base64EncodedString()
    }
    
    /**
     * Delete device keypair
     */
    private func deleteDeviceKeypair() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassKey,
            kSecAttrApplicationTag as String: keyTag.data(using: .utf8)!
        ]
        
        SecItemDelete(query as CFDictionary)
    }
    
    /**
     * Register device with backend
     */
    func registerDevice(telegramToken: String) async -> Result<DeviceRegistrationResult, Error> {
        do {
            // Generate keypair if not exists
            guard generateDeviceKeypair() else {
                throw DeviceError.keypairGenerationFailed
            }
            
            // Collect device fingerprint
            let fingerprint = collectDeviceFingerprint()
            
            // Get public key
            guard let publicKey = getPublicKey() else {
                throw DeviceError.publicKeyRetrievalFailed
            }
            
            // Prepare registration data
            let registrationData: [String: Any] = [
                "device_type": "mobile",
                "platform": "ios",
                "device_name": UIDevice.current.name,
                "fingerprint": fingerprint,
                "public_key": publicKey
            ]
            
            // Make API request
            guard let url = URL(string: "\(apiBaseURL)/device/register") else {
                throw DeviceError.invalidURL
            }
            
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.addValue("Bearer \(telegramToken)", forHTTPHeaderField: "Authorization")
            request.addValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONSerialization.data(withJSONObject: registrationData)
            
            let (data, response) = try await URLSession.shared.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw DeviceError.registrationFailed
            }
            
            let result = try JSONSerialization.jsonObject(with: data) as? [String: Any]
            
            guard let deviceId = result?["device_id"] as? String,
                  let success = result?["success"] as? Bool,
                  let message = result?["message"] as? String else {
                throw DeviceError.invalidResponse
            }
            
            return .success(DeviceRegistrationResult(
                deviceId: deviceId,
                success: success,
                message: message
            ))
            
        } catch {
            return .failure(error)
        }
    }
    
    /**
     * Decrypt content key using device private key
     */
    func decryptContentKey(_ encryptedKey: String) -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassKey,
            kSecAttrApplicationTag as String: keyTag.data(using: .utf8)!,
            kSecAttrKeyType as String: kSecAttrKeyTypeRSA,
            kSecReturnRef as String: true
        ]
        
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        
        guard status == errSecSuccess, let privateKey = item else {
            print("Failed to retrieve private key")
            return nil
        }
        
        guard let encryptedData = Data(base64Encoded: encryptedKey) else {
            print("Invalid base64 encrypted key")
            return nil
        }
        
        var error: Unmanaged<CFError>?
        guard let decryptedData = SecKeyCreateDecryptedData(
            privateKey as! SecKey,
            .rsaEncryptionOAEPSHA256,
            encryptedData as CFData,
            &error
        ) else {
            print("Failed to decrypt content key: \(error?.takeRetainedValue().localizedDescription ?? "Unknown error")")
            return nil
        }
        
        return decryptedData as Data
    }
}

struct DeviceRegistrationResult {
    let deviceId: String
    let success: Bool
    let message: String
}

enum DeviceError: Error {
    case keypairGenerationFailed
    case publicKeyRetrievalFailed
    case invalidURL
    case registrationFailed
    case invalidResponse
}

/**
 * Secure video player with device binding
 */
class SecureVideoPlayer: NSObject {
    
    /**
     * Play encrypted video with device verification
     */
    func playEncryptedVideo(
        encryptedVideoURL: URL,
        contentKey: Data,
        completion: @escaping (Result<Void, Error>) -> Void
    ) {
        do {
            // Decrypt video file
            let decryptedURL = try decryptVideoFile(encryptedVideoURL, contentKey: contentKey)
            
            // Setup secure playback with AVPlayer
            setupSecurePlayback(decryptedURL, completion: completion)
            
        } catch {
            completion(.failure(error))
        }
    }
    
    private func decryptVideoFile(_ encryptedURL: URL, contentKey: Data) throws -> URL {
        // Implement AES-GCM decryption
        // Save decrypted file to app's private documents directory
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let decryptedURL = documentsPath.appendingPathComponent("decrypted_video.mp4")
        
        // Decrypt file using CryptoKit
        let encryptedData = try Data(contentsOf: encryptedURL)
        
        // Extract IV and tag (first 12 bytes IV, last 16 bytes tag)
        let iv = encryptedData.prefix(12)
        let tag = encryptedData.suffix(16)
        let ciphertext = encryptedData.dropFirst(12).dropLast(16)
        
        let sealedBox = try AES.GCM.SealedBox(
            nonce: AES.GCM.Nonce(data: iv),
            ciphertext: ciphertext,
            tag: tag
        )
        
        let symmetricKey = SymmetricKey(data: contentKey)
        let decryptedData = try AES.GCM.open(sealedBox, using: symmetricKey)
        
        try decryptedData.write(to: decryptedURL)
        return decryptedURL
    }
    
    private func setupSecurePlayback(_ videoURL: URL, completion: @escaping (Result<Void, Error>) -> Void) {
        // Configure AVPlayer with security measures:
        // - Disable AirPlay
        // - Add screen recording detection
        // - Add watermarking overlay
        // - Use hardware-accelerated decoding
        
        completion(.success(()))
    }
}

/**
 * Anti-tampering and security measures
 */
class SecurityManager {
    
    /**
     * Detect if device is jailbroken
     */
    func isDeviceCompromised() -> Bool {
        return isJailbroken() || isDebuggingEnabled() || isSimulator()
    }
    
    private func isJailbroken() -> Bool {
        // Check for common jailbreak indicators
        let jailbreakPaths = [
            "/Applications/Cydia.app",
            "/Library/MobileSubstrate/MobileSubstrate.dylib",
            "/bin/bash",
            "/usr/sbin/sshd",
            "/etc/apt",
            "/private/var/lib/apt/"
        ]
        
        for path in jailbreakPaths {
            if FileManager.default.fileExists(atPath: path) {
                return true
            }
        }
        
        // Try to write to system directory
        do {
            let testString = "jailbreak test"
            try testString.write(toFile: "/private/test.txt", atomically: true, encoding: .utf8)
            try FileManager.default.removeItem(atPath: "/private/test.txt")
            return true
        } catch {
            // Normal behavior - cannot write to system directory
        }
        
        return false
    }
    
    private func isDebuggingEnabled() -> Bool {
        var info = kinfo_proc()
        var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, getpid()]
        var size = MemoryLayout<kinfo_proc>.stride
        
        let result = sysctl(&mib, u_int(mib.count), &info, &size, nil, 0)
        
        return result == 0 && (info.kp_proc.p_flag & P_TRACED) != 0
    }
    
    private func isSimulator() -> Bool {
        return TARGET_OS_SIMULATOR != 0
    }
    
    /**
     * Detect screen recording
     */
    func detectScreenRecording() -> Bool {
        if #available(iOS 11.0, *) {
            return UIScreen.main.isCaptured
        }
        return false
    }
    
    /**
     * Add screen recording observer
     */
    func addScreenRecordingObserver(_ observer: @escaping (Bool) -> Void) {
        if #available(iOS 11.0, *) {
            NotificationCenter.default.addObserver(
                forName: UIScreen.capturedDidChangeNotification,
                object: UIScreen.main,
                queue: .main
            ) { _ in
                observer(UIScreen.main.isCaptured)
            }
        }
    }
}
