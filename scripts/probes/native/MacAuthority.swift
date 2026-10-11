// Disposable R2 experiment. This is not a product authorization broker.
import AppKit
import CryptoKit
import Foundation
import LocalAuthentication
import Security

let reviewText = """
ClaimBranch · macOS 사용자 확인 검증

합성 연구 사례: Pruning과 quantization은 기존 예상과 다르고,
compression은 해당 조건에서만 예상과 일치합니다.

검토할 판단: sensitivity만으로 관찰한 손상을 설명하기 어렵습니다.
이유: 세 관찰을 함께 보존하고 compression의 결과를 일반화하지 않습니다.

이번 동작: 위 내용에 대한 일회용 검증 메시지에 서명합니다.
연구 기록이나 원고는 변경하지 않습니다. 실제 승인 권한도 발급하지 않습니다.

승인 검증을 누르면 이 실험 전용 키를 만들고 macOS 사용자 확인을 요청합니다.
기존 키를 사용하지 않으며, 키를 키체인에 저장하지 않습니다. 종료하면 임시 키 참조를 해제합니다.
"""

func emit(_ value: [String: Any], code: Int32 = 0) -> Never {
    if let data = try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]),
       let line = String(data: data, encoding: .utf8) { print(line) }
    exit(code)
}

func nativeFailureStatus(domain: String, code: Int) -> String {
    if domain == LAError.errorDomain && [LAError.userCancel.rawValue,
        LAError.appCancel.rawValue, LAError.systemCancel.rawValue].contains(code) { return "cancelled" }
    if domain == NSOSStatusErrorDomain && code == Int(errSecUserCanceled) { return "cancelled" }
    return "error"
}

final class ReviewController: NSObject, NSApplicationDelegate, NSWindowDelegate {
    let context = LAContext()
    let deadline = ProcessInfo.processInfo.systemUptime + 90
    var window: NSWindow!
    var button: NSButton!
    var label: NSTextField!
    var timer: Timer?
    var signing = false
    var terminal: String?
    let message: Data
    let reviewDigest: String

    override init() {
        reviewDigest = SHA256.hash(data: Data(reviewText.utf8)).map { String(format: "%02x", $0) }.joined()
        message = Data(("claimbranch:mac-native-probe:v1\n" + reviewDigest + "\n" + UUID().uuidString).utf8)
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 740, height: 570),
                          styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.title = "ClaimBranch · 합성 자료 사용자 확인 검증"
        window.delegate = self
        let scroll = NSScrollView(frame: NSRect(x: 24, y: 136, width: 692, height: 410))
        scroll.hasVerticalScroller = true
        let text = NSTextView(frame: scroll.bounds)
        text.isEditable = false
        text.isSelectable = true
        text.font = NSFont.systemFont(ofSize: 16)
        text.string = reviewText + "\n\n검토 내용 SHA-256: " + reviewDigest
        scroll.documentView = text
        window.contentView?.addSubview(scroll)
        label = NSTextField(wrappingLabelWithString: "90초 이내에 승인 검증 또는 취소를 선택하세요.")
        label.frame = NSRect(x: 24, y: 83, width: 692, height: 40)
        window.contentView?.addSubview(label)
        button = NSButton(title: "승인 검증", target: self, action: #selector(approve))
        button.frame = NSRect(x: 495, y: 25, width: 125, height: 40)
        button.bezelStyle = .rounded
        let cancel = NSButton(title: "취소", target: self, action: #selector(cancelReview))
        cancel.frame = NSRect(x: 625, y: 25, width: 85, height: 40)
        cancel.bezelStyle = .rounded
        window.contentView?.addSubview(button)
        window.contentView?.addSubview(cancel)
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        timer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            if ProcessInfo.processInfo.systemUptime >= self.deadline { self.stop("expired") }
        }
    }

    @objc func approve() {
        guard !signing && terminal == nil else { return }
        if ProcessInfo.processInfo.systemUptime >= deadline { stop("expired"); return }
        signing = true
        button.isEnabled = false
        label.stringValue = "macOS에서 본인을 확인하세요. 취소하거나 시간이 지나면 결과를 버립니다."
        context.localizedReason = "ClaimBranch에 표시된 합성 검토 내용에 대한 일회용 검증 서명"
        context.touchIDAuthenticationAllowableReuseDuration = 0
        DispatchQueue.global(qos: .userInitiated).async { [self] in
            var output: [String: Any] = ["status": "error", "presence_verified": false,
                "signature_verified": false, "private_export_denied": false,
                "authorization_verified": false, "review_digest": reviewDigest]
            var error: Unmanaged<CFError>?
            if let control = SecAccessControlCreateWithFlags(nil, kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
                                                            [.privateKeyUsage, .userPresence], &error) {
                let attrs: [CFString: Any] = [kSecAttrKeyType: kSecAttrKeyTypeECSECPrimeRandom,
                    kSecAttrKeySizeInBits: 256, kSecAttrTokenID: kSecAttrTokenIDSecureEnclave,
                    kSecPrivateKeyAttrs: [kSecAttrIsPermanent: false, kSecAttrAccessControl: control],
                    kSecUseAuthenticationContext: context]
                if let key = SecKeyCreateRandomKey(attrs as CFDictionary, &error) {
                    var exportError: Unmanaged<CFError>?
                    let export = SecKeyCopyExternalRepresentation(key, &exportError)
                    output["private_export_denied"] = export == nil
                    if let signature = SecKeyCreateSignature(key, .ecdsaSignatureMessageX962SHA256,
                                                             message as CFData, &error),
                       let publicKey = SecKeyCopyPublicKey(key) {
                        let verified = SecKeyVerifySignature(publicKey, .ecdsaSignatureMessageX962SHA256,
                                                             message as CFData, signature, &error)
                        output["signature_verified"] = verified
                        output["presence_verified"] = verified && export == nil
                        output["status"] = verified && export == nil ? "matched" : "error"
                        if let bytes = SecKeyCopyExternalRepresentation(publicKey, &error) {
                            output["public_key_x963"] = (bytes as Data).base64EncodedString()
                            output["signature_der"] = (signature as Data).base64EncodedString()
                            output["message"] = message.base64EncodedString()
                        } else { output["status"] = "error" }
                    }
                }
            }
            if let failure = error?.takeRetainedValue() {
                let code = CFErrorGetCode(failure)
                let domain = CFErrorGetDomain(failure) as String
                output["native_error_code"] = code
                output["native_error_domain"] = domain
                output["status"] = nativeFailureStatus(domain: domain, code: code)
            }
            DispatchQueue.main.async { [self, output] in finish(output) }
        }
    }

    @objc func cancelReview() { stop("cancelled") }

    func stop(_ reason: String) {
        if terminal == nil { terminal = reason }
        context.invalidate()
        button?.isEnabled = false
        label?.stringValue = "검증을 중단하고 실험 전용 키를 정리하고 있습니다."
        if !signing { finish(["status": terminal!, "presence_verified": false,
                              "signature_verified": false, "authorization_verified": false]) }
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool { stop("cancelled"); return false }

    func finish(_ raw: [String: Any]) {
        timer?.invalidate()
        var output = raw
        if ProcessInfo.processInfo.systemUptime >= deadline && terminal == nil { terminal = "expired" }
        if terminal == nil && raw["status"] as? String == "cancelled" { terminal = "cancelled" }
        if let reason = terminal {
            output["status"] = reason
            output["presence_verified"] = false
            output["signature_verified"] = false
            for key in ["signature_der", "public_key_x963", "message"] { output.removeValue(forKey: key) }
        }
        output["key_storage"] = "ephemeral"
        output["persistent_custody_verified"] = false
        output["authorization_verified"] = false
        emit(output, code: ["matched", "cancelled", "expired"].contains(output["status"] as? String ?? "") ? 0 : 1)
    }
}

let args = Array(CommandLine.arguments.dropFirst())
if args == ["--check"] {
    let context = LAContext()
    var ownerError: NSError?
    let owner = context.canEvaluatePolicy(.deviceOwnerAuthentication, error: &ownerError)
    var bioError: NSError?
    let bio = context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &bioError)
    emit(["status": owner && SecureEnclave.isAvailable ? "available" : "unavailable",
          "owner_available": owner, "biometry_available": bio,
          "secure_enclave_available": SecureEnclave.isAvailable,
          "owner_error_code": ownerError?.code as Any? ?? NSNull(),
          "biometry_error_code": bioError?.code as Any? ?? NSNull(),
          "cancellation_mapping_verified": nativeFailureStatus(domain: LAError.errorDomain, code: -2) == "cancelled"
            && nativeFailureStatus(domain: NSOSStatusErrorDomain, code: -128) == "cancelled"
            && nativeFailureStatus(domain: "unrelated-domain", code: -2) == "error",
          "authorization_verified": false])
}
if args == ["--review"] {
    let app = NSApplication.shared
    let controller = ReviewController()
    app.delegate = controller
    app.run()
}
emit(["status": "invalid_arguments", "authorization_verified": false], code: 2)
