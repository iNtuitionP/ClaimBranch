// Independent R2 custody measurement. Foreground review is explicit only.
import AppKit
import CryptoKit
import Darwin
import Foundation
import LocalAuthentication
import Security

let arguments = Array(CommandLine.arguments.dropFirst())
let mode = arguments.first ?? "invalid"
let blobName = "enclave-key.bin"

func emit(_ status: String, _ fields: [String: Any] = [:], code: Int32 = 0) -> Never {
    var value: [String: Any] = ["schema_version": 1, "mode": mode, "status": status,
        "process_id": Int(getpid()), "authorization_verified": false, "product_custody_verified": false]
    value.merge(fields) { _, new in new }
    let data = try! JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    print(String(data: data, encoding: .utf8)!)
    exit(code)
}

func failure(_ code: Int32 = errno) -> NSError { NSError(domain: NSPOSIXErrorDomain, code: Int(code)) }
func sha256(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }

func directory() throws -> Int32 {
    let fd = open(".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
    guard fd >= 0 else { throw failure() }
    var info = stat()
    guard fstat(fd, &info) == 0, info.st_uid == geteuid(), info.st_mode & 0o077 == 0 else {
        close(fd); throw failure(EACCES)
    }
    return fd
}

func writeBlob(_ data: Data) throws {
    guard !data.isEmpty && data.count <= 16_384 else { throw failure(EFBIG) }
    let dir = try directory()
    defer { close(dir) }
    let fd = openat(dir, blobName, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
    guard fd >= 0 else { throw failure() }
    let file = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
    try file.write(contentsOf: data)
    try file.synchronize()
    try file.close()
    guard fsync(dir) == 0 else { throw failure() }
}

func readBlob() throws -> Data {
    let dir = try directory()
    defer { close(dir) }
    let fd = openat(dir, blobName, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
    guard fd >= 0 else { throw failure() }
    let file = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
    defer { try? file.close() }
    var info = stat()
    guard fstat(fd, &info) == 0, info.st_uid == geteuid(), info.st_nlink == 1,
          info.st_mode & S_IFMT == S_IFREG, info.st_mode & 0o777 == 0o600,
          info.st_size > 0 && info.st_size <= 16_384 else { throw failure(EACCES) }
    let data = try file.read(upToCount: 16_385) ?? Data()
    guard data.count == info.st_size else { throw failure(EIO) }
    return data
}

func details(_ error: Error) -> [String: Any] {
    let e = error as NSError
    return ["error_domain": e.domain, "error_code": e.code]
}

func interactionError(_ error: Error) -> NSError? {
    var current: NSError? = error as NSError
    for _ in 0..<4 {
        guard let e = current else { return nil }
        if (e.domain == NSOSStatusErrorDomain && e.code == Int(errSecInteractionNotAllowed)) ||
           (e.domain == LAError.errorDomain && e.code == LAError.notInteractive.rawValue) { return e }
        current = e.userInfo[NSUnderlyingErrorKey] as? NSError
    }
    return nil
}

func createKey(_ context: LAContext) throws -> SecureEnclave.P256.Signing.PrivateKey {
    var error: Unmanaged<CFError>?
    guard let access = SecAccessControlCreateWithFlags(nil, kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
            [.privateKeyUsage, .userPresence], &error) else {
        if let error { throw error.takeRetainedValue() }
        throw failure(EINVAL)
    }
    return try SecureEnclave.P256.Signing.PrivateKey(accessControl: access, authenticationContext: context)
}

let preparationText = """
ClaimBranch · 실험용 승인 키 준비

1단계: ‘테스트 키 만들기’를 누르면 이 검증만을 위한 새 Secure Enclave 키를 만듭니다.
macOS가 본인 확인을 요청하면 직접 진행하세요. 기존 키나 연구 자료는 사용하지 않습니다.

키의 암호화된 표현을 실험용 임시 폴더에 저장한 뒤 이 프로세스는 종료됩니다.
다음 프로세스에서 같은 키를 다시 열고, 별도 검토 창에서 서명 내용을 확인합니다.

지금은 연구 판단을 승인하거나 원고를 수정하는 단계가 아닙니다.
취소하거나 90초가 지나면 후속 검토로 넘어가지 않습니다.
실험을 마치면 임시 폴더와 키 자료를 정리합니다.
"""

let reviewText = """
ClaimBranch · 재시작 후 승인 키 검증

이번 검증은 첫 프로세스에서 만든 실험 전용 키를 새 프로세스에서 다시 열어 사용합니다.

검토할 동작: 지금 표시된 내용과 이번 요청값을 묶은 일회용 메시지에 서명합니다.
아래 공개키 식별값은 키를 만들었던 프로세스의 식별값과 같아야 합니다.

‘승인 검증’을 누르면 macOS에 이번 검토를 위한 본인 확인을 명시적으로 요청합니다.
이 요청이 성공한 경우에만 같은 인증 컨텍스트로 보호된 키의 서명을 시도합니다.
취소하거나 90초가 지나면 서명 결과를 사용하지 않습니다.

실제 연구 기록과 원고는 변경하지 않습니다. 제품의 승인 권한도 발급하지 않습니다.
실험용 키 자료는 검증을 마치면 임시 폴더와 함께 정리됩니다.
"""

func validDigest(_ value: String) -> Bool {
    value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
}

struct ReviewBinding {
    let publicDigest: String
    let representationDigest: String
    let nonce: String
    var reviewDigest: String { sha256(Data(reviewText.utf8)) }
    var message: Data {
        Data(("claimbranch:key-reopen-review:v1\n" + [reviewDigest, publicDigest, representationDigest, nonce].joined(separator: "\n")).utf8)
    }
    var fields: [String: Any] {
        ["public_key_digest": publicDigest, "representation_digest": representationDigest,
         "review_digest": reviewDigest, "challenge_digest": sha256(message)]
    }
}

// mach_continuous_time advances across system sleep, unlike an uptime-only timer.
func reviewNow() -> Double {
    var info = mach_timebase_info_data_t()
    mach_timebase_info(&info)
    return Double(mach_continuous_time()) * Double(info.numer) / Double(info.denom) / 1_000_000_000
}

func cancelledAuthentication(_ error: NSError) -> Bool {
    (error.domain == LAError.errorDomain && [LAError.userCancel.rawValue, LAError.appCancel.rawValue,
        LAError.systemCancel.rawValue].contains(error.code)) ||
    (error.domain == NSOSStatusErrorDomain && error.code == Int(errSecUserCanceled))
}

func cancellationFields(_ trigger: String?, _ error: [String: Any]) -> [String: Any] {
    let domain = error["error_domain"] as? String
    let code = error["error_code"] as? Int
    let nativeUserCancel = (domain == LAError.errorDomain && code == LAError.userCancel.rawValue) ||
        (domain == NSOSStatusErrorDomain && code == Int(errSecUserCanceled))
    // An explicit native user-cancel is more specific than a simultaneous app
    // close. Keep both observations; a UI origin cannot be inferred from a
    // terminal gate alone. No error contents/reason strings are exposed.
    return ["cancel_source": nativeUserCancel || trigger == nil ? "native" : "review",
            "cancel_trigger": trigger ?? "native_callback",
            "cancel_error_domain": domain as Any? ?? NSNull(),
            "cancel_error_code": code as Any? ?? NSNull()]
}

struct ReviewGate {
    let deadline: Double
    private(set) var started = false
    private(set) var terminal: String?
    private(set) var finished = false
    private(set) var authenticationSucceeded = false
    private(set) var signingStarted = false

    mutating func begin(_ now: Double) -> Bool {
        guard !finished && !started && terminal == nil else { return false }
        if now >= deadline { terminal = "expired"; return false }
        started = true
        return true
    }
    mutating func stop(_ reason: String) {
        if !finished && terminal == nil { terminal = reason }
    }
    mutating func allowSigning(_ authenticated: Bool, _ now: Double) -> Bool {
        guard started && !finished && terminal == nil && !signingStarted else { return false }
        if now >= deadline { terminal = "expired"; return false }
        guard authenticated else { return false }
        authenticationSucceeded = true
        signingStarted = true
        return true
    }
    mutating func finish(_ observed: String, _ now: Double) -> String? {
        guard !finished else { return nil }
        if terminal == nil && now >= deadline { terminal = "expired" }
        finished = true
        if let terminal { return terminal }
        if observed == "matched" && !signingStarted { return "error" }
        return started && ["matched", "created", "cancelled", "error"].contains(observed) ? observed : "error"
    }
}

func gateChecks() -> [String: Bool] {
    var a = ReviewGate(deadline: 10)
    a.stop("cancelled")
    let before = !a.begin(1) && a.finish("matched", 2) == "cancelled"
    var b = ReviewGate(deadline: 10)
    let first = b.begin(1)
    let once = !b.begin(2)
    let signing = b.allowSigning(true, 2)
    b.stop("cancelled")
    let during = b.finish("matched", 3) == "cancelled"
    var c = ReviewGate(deadline: 10)
    _ = c.begin(1)
    let late = c.finish("matched", 10) == "expired"
    var d = ReviewGate(deadline: 10)
    _ = d.begin(1)
    _ = d.allowSigning(true, 2)
    let matched = d.finish("matched", 9) == "matched"
    var e = ReviewGate(deadline: 10)
    _ = e.begin(1)
    e.stop("cancelled")
    var f = ReviewGate(deadline: 10)
    _ = f.begin(1)
    var g = ReviewGate(deadline: 10)
    _ = g.begin(1)
    var h = ReviewGate(deadline: 10)
    _ = h.begin(1)
    let noAuthentication = h.finish("matched", 2) == "error" && !h.signingStarted
    var i = ReviewGate(deadline: 10)
    _ = i.begin(1)
    let failedAuthentication = !i.allowSigning(false, 2) && !i.signingStarted
    var j = ReviewGate(deadline: 10)
    _ = j.begin(1)
    j.stop("cancelled")
    let cancelledBeforeSigning = !j.allowSigning(true, 2) && !j.signingStarted
    var k = ReviewGate(deadline: 10)
    _ = k.begin(1)
    let lateAuthentication = !k.allowSigning(true, 10) && !k.signingStarted && k.finish("matched", 10) == "expired"
    var l = ReviewGate(deadline: 10)
    _ = l.begin(1)
    let callbackOnce = l.allowSigning(true, 2) && !l.allowSigning(true, 3)
    let nativeCancel = cancellationFields("window_close", ["error_domain": LAError.errorDomain, "error_code": -2])
    let invalidated = cancellationFields("review_button", ["error_domain": LAError.errorDomain, "error_code": -9])
    let noCallback = cancellationFields("application_terminate", [:])
    return ["cancel_before_start": before, "cancel_during_signing": first && signing && during,
        "late_success": late, "single_start": once, "finish_once": d.finish("matched", 9) == nil,
        "success_before_deadline": matched,
        "native_cancel": cancelledAuthentication(NSError(domain: LAError.errorDomain, code: -2)) &&
            cancelledAuthentication(NSError(domain: NSOSStatusErrorDomain, code: -128)),
        "wrong_error_domain": !cancelledAuthentication(NSError(domain: "unrelated", code: -2)),
        "cancelled_creation": e.finish("created", 2) == "cancelled",
        "late_creation": f.finish("created", 10) == "expired",
        "creation_before_deadline": g.finish("created", 9) == "created",
        "unauthenticated_success_rejected": noAuthentication,
        "failed_authentication_does_not_sign": failedAuthentication,
        "cancelled_authentication_does_not_sign": cancelledBeforeSigning,
        "late_authentication_does_not_sign": lateAuthentication,
        "authentication_callback_once": callbackOnce,
        "native_cancel_survives_close_race": nativeCancel["cancel_source"] as? String == "native",
        "app_invalidation_is_not_native_user_cancel": invalidated["cancel_source"] as? String == "review",
        "missing_callback_is_not_invented": noCallback["cancel_error_code"] is NSNull]
}

func verifyPublicSignature(_ binding: ReviewBinding) -> Never {
    var fields = binding.fields
    fields["signature_verified"] = false
    do {
        let input = try FileHandle.standardInput.read(upToCount: 4097) ?? Data()
        guard input.count <= 4096,
              let value = try JSONSerialization.jsonObject(with: input) as? [String: String],
              Set(value.keys) == ["public_key_x963", "signature_der"],
              let publicData = Data(base64Encoded: value["public_key_x963"]!), publicData.count == 65,
              let signatureData = Data(base64Encoded: value["signature_der"]!), (8...72).contains(signatureData.count),
              sha256(publicData) == binding.publicDigest else { emit("rejected", fields) }
        let key = try P256.Signing.PublicKey(x963Representation: publicData)
        let signature = try P256.Signing.ECDSASignature(derRepresentation: signatureData)
        let verified = key.isValidSignature(signature, for: binding.message)
        fields["signature_verified"] = verified
        emit(verified ? "verified" : "rejected", fields)
    } catch { emit("rejected", fields) }
}

final class ReopenReviewController: NSObject, NSApplicationDelegate, NSWindowDelegate {
    let binding: ReviewBinding?
    let context = LAContext()
    var gate = ReviewGate(deadline: reviewNow() + 90)
    var window: NSWindow!
    var button: NSButton!
    var label: NSTextField!
    var timer: Timer?
    var cancelTrigger: String?

    init(_ binding: ReviewBinding?) {
        self.binding = binding
        super.init()
        context.interactionNotAllowed = true
        context.touchIDAuthenticationAllowableReuseDuration = 0
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 760, height: 630),
                          styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.title = binding == nil ? "ClaimBranch · 실험용 키 준비" : "ClaimBranch · 재시작 후 키 검증 (합성 자료)"
        window.delegate = self
        let scroll = NSScrollView(frame: NSRect(x: 24, y: 128, width: 712, height: 478))
        scroll.hasVerticalScroller = true
        let text = NSTextView(frame: scroll.bounds)
        text.isEditable = false
        text.isSelectable = true
        text.isVerticallyResizable = true
        text.autoresizingMask = [.width]
        text.textContainer?.widthTracksTextView = true
        text.textContainer?.containerSize = NSSize(width: scroll.contentSize.width, height: .greatestFiniteMagnitude)
        text.font = NSFont.systemFont(ofSize: 15)
        text.string = preparationText
        if let binding {
            text.string = reviewText + "\n\n공개키 SHA-256: " + binding.publicDigest +
                "\n검토 내용 SHA-256: " + binding.reviewDigest + "\n이번 요청 SHA-256: " + sha256(binding.message)
        }
        scroll.documentView = text
        window.contentView?.addSubview(scroll)
        label = NSTextField(wrappingLabelWithString: binding == nil ?
                            "90초 이내에 테스트 키 만들기 또는 취소를 선택하세요." : "90초 이내에 승인 검증 또는 취소를 선택하세요.")
        label.frame = NSRect(x: 24, y: 76, width: 712, height: 40)
        window.contentView?.addSubview(label)
        button = NSButton(title: binding == nil ? "테스트 키 만들기" : "승인 검증", target: self, action: #selector(approve))
        button.frame = NSRect(x: 505, y: 24, width: 130, height: 40)
        button.bezelStyle = .rounded
        let cancel = NSButton(title: "취소", target: self, action: #selector(cancelReview))
        cancel.frame = NSRect(x: 641, y: 24, width: 90, height: 40)
        cancel.bezelStyle = .rounded
        window.contentView?.addSubview(button)
        window.contentView?.addSubview(cancel)
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        timer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] _ in
            guard let self else { return }
            if reviewNow() >= self.gate.deadline { self.stop("expired", trigger: "deadline") }
        }
    }
    @objc func approve() {
        guard gate.begin(reviewNow()) else {
            if gate.terminal != nil { finish("error") }
            return
        }
        button.isEnabled = false
        label.stringValue = "macOS에서 확인하세요. 취소·만료 후의 결과는 버립니다."
        context.interactionNotAllowed = false
        context.localizedReason = binding == nil ? "ClaimBranch 재시작 검증에 쓸 새 실험용 승인 키 준비" :
            "ClaimBranch에 표시된 재시작 후 합성 검토 메시지에 서명"
        if binding != nil {
            // Explicit evaluation has its own cancellation result. Never infer a
            // displayed prompt from an implicit CryptoKit/Keychain operation.
            context.evaluatePolicy(.deviceOwnerAuthentication, localizedReason: context.localizedReason) { [self] success, error in
                DispatchQueue.main.async { [self] in
                    guard gate.allowSigning(success && error == nil, reviewNow()) else {
                        let cancelled = error.map { cancelledAuthentication($0 as NSError) } ?? false
                        finish(cancelled ? "cancelled" : "error", error.map(details) ?? [:])
                        return
                    }
                    // Keep key access control authoritative. Only this evaluated
                    // context may sign, with further implicit interaction denied.
                    context.interactionNotAllowed = true
                    performKeyOperation()
                }
            }
        } else {
            performKeyOperation()
        }
    }
    func performKeyOperation() {
        guard binding == nil || gate.signingStarted else { finish("error"); return }
        DispatchQueue.global(qos: .userInitiated).async { [self] in
            var status = "error"
            var fields: [String: Any] = [:]
            var preparedBlob: Data?
            do {
                if let binding {
                    let blob = try readBlob()
                    guard sha256(blob) == binding.representationDigest else { throw failure(EINVAL) }
                    let key = try SecureEnclave.P256.Signing.PrivateKey(dataRepresentation: blob, authenticationContext: context)
                    let publicData = key.publicKey.x963Representation
                    guard sha256(publicData) == binding.publicDigest else { throw failure(EINVAL) }
                    let signature = try key.signature(for: binding.message)
                    guard key.publicKey.isValidSignature(signature, for: binding.message) else { throw failure(EIO) }
                    status = "matched"
                    fields = ["signature_verified": true, "public_key_x963": publicData.base64EncodedString(),
                              "signature_der": signature.derRepresentation.base64EncodedString()]
                } else {
                    let key = try createKey(context)
                    let blob = key.dataRepresentation
                    // Persist only after the main thread accepts a timely completion.
                    preparedBlob = blob
                    status = "created"
                    fields = ["public_key_digest": sha256(key.publicKey.x963Representation), "representation_digest": sha256(blob)]
                }
            } catch {
                status = cancelledAuthentication(error as NSError) ? "cancelled" : "error"
                fields = details(error)
            }
            DispatchQueue.main.async { [self, status, fields, preparedBlob] in finish(status, fields, preparedBlob: preparedBlob) }
        }
    }
    @objc func cancelReview() { stop("cancelled", trigger: "review_button") }
    func stop(_ reason: String, trigger: String) {
        if gate.terminal == nil { cancelTrigger = trigger }
        gate.stop(reason)
        context.invalidate()
        button?.isEnabled = false
        label?.stringValue = "검증을 중단하고 실험용 키를 정리하고 있습니다."
        if !gate.started { finish("error") }
    }
    func windowShouldClose(_ sender: NSWindow) -> Bool { stop("cancelled", trigger: "window_close"); return false }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        stop("cancelled", trigger: "application_terminate")
        return .terminateCancel
    }
    func finish(_ observed: String, _ raw: [String: Any] = [:], preparedBlob: Data? = nil) {
        guard let status = gate.finish(observed, reviewNow()) else { return }
        timer?.invalidate()
        context.invalidate()
        if status == "error" { emit("error", raw.isEmpty ? ["error_domain": "ClaimBranchProbe", "error_code": 2] : raw, code: 1) }
        if status == "created" {
            guard binding == nil, let preparedBlob else {
                emit("error", ["error_domain": "ClaimBranchProbe", "error_code": 6], code: 1)
            }
            do { try writeBlob(preparedBlob) }
            catch { emit("error", details(error), code: 1) }
            if reviewNow() >= gate.deadline { emit("expired") }
            emit("created", raw)
        }
        var fields = binding?.fields ?? [:]
        if binding != nil {
            fields["signature_verified"] = status == "matched"
            fields["explicit_authentication_succeeded"] = gate.authenticationSucceeded
            fields["signing_started"] = gate.signingStarted
        }
        if status == "matched" { fields.merge(raw) { _, new in new } }
        if status == "cancelled" { fields.merge(cancellationFields(cancelTrigger, raw)) { _, new in new } }
        emit(status, fields)
    }
}

if arguments == ["gate-check"] { emit("checked", ["checks": gateChecks()]) }
if arguments == ["prepare"] {
    guard SecureEnclave.isAvailable else { emit("error", ["error_domain": "ClaimBranchProbe", "error_code": 4], code: 1) }
    let app = NSApplication.shared
    let controller = ReopenReviewController(nil)
    app.delegate = controller
    app.run()
    emit("error", ["error_domain": "ClaimBranchProbe", "error_code": 5], code: 1)
}
if ["review", "verify"].contains(mode) {
    guard arguments.count == 4 && arguments.dropFirst().allSatisfy(validDigest) else {
        emit("error", ["error_domain": "ClaimBranchProbe", "error_code": 3], code: 1)
    }
    let binding = ReviewBinding(publicDigest: arguments[1], representationDigest: arguments[2], nonce: arguments[3])
    if mode == "verify" { verifyPublicSignature(binding) }
    guard SecureEnclave.isAvailable else { emit("error", ["error_domain": "ClaimBranchProbe", "error_code": 4], code: 1) }
    let app = NSApplication.shared
    let controller = ReopenReviewController(binding)
    app.delegate = controller
    app.run()
    emit("error", ["error_domain": "ClaimBranchProbe", "error_code": 5], code: 1)
}

if arguments == ["check"] {
    emit(SecureEnclave.isAvailable ? "available" : "unavailable", ["secure_enclave_available": SecureEnclave.isAvailable])
}
guard arguments.count == 1, ["create", "reopen", "deny"].contains(mode), SecureEnclave.isAvailable else {
    emit("error", ["error_domain": "ClaimBranchProbe", "error_code": 1], code: 1)
}

let context = LAContext()
context.interactionNotAllowed = true
context.touchIDAuthenticationAllowableReuseDuration = 0
do {
    let key: SecureEnclave.P256.Signing.PrivateKey
    let blob: Data
    if mode == "create" {
        key = try createKey(context)
        blob = key.dataRepresentation
        try writeBlob(blob)
    } else {
        blob = try readBlob()
        do {
            key = try SecureEnclave.P256.Signing.PrivateKey(dataRepresentation: blob, authenticationContext: context)
        } catch {
            emit("key_rejected", details(error), code: 1)
        }
    }
    let identity: [String: Any] = ["public_key_digest": sha256(key.publicKey.x963Representation), "representation_digest": sha256(blob)]
    if mode == "deny" {
        do {
            // Fixed synthetic challenge only. A signature here is a failed gate.
            _ = try key.signature(for: Data("claimbranch:noninteractive-custody-test:v1".utf8))
            emit("signature_without_interaction", identity, code: 1)
        } catch {
            if let denied = interactionError(error) {
                emit("interaction_denied", identity.merging(details(denied)) { _, new in new })
            }
            emit("error", details(error), code: 1)
        }
    }
    emit(mode == "create" ? "created" : "reopened", identity)
} catch {
    emit("error", details(error), code: 1)
}
