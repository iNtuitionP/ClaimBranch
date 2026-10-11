// Source-built role identity, unaccepted review transport, explicit new-key
// preparation and private foreground signing. No accepted research writes.
import Foundation
import Security
import Darwin
import CryptoKit
import AppKit
import LocalAuthentication

#if CLAIMBRANCH_BROKER
let role = "broker"
#elseif CLAIMBRANCH_GATEWAY
let role = "gateway"
#else
#error("A fixed runtime role is required")
#endif

func inspect() -> [String: Any]? {
    var code: SecCode?
    guard SecCodeCopySelf([], &code) == errSecSuccess, let code,
          SecCodeCheckValidity(code, [], nil) == errSecSuccess else { return nil }
    var information: CFDictionary?
    // The C API accepts dynamic code; preserve it for the running status.
    let dynamic = unsafeBitCast(code, to: SecStaticCode.self)
    guard SecCodeCopySigningInformation(dynamic,
            SecCSFlags(rawValue: kSecCSSigningInformation | kSecCSDynamicInformation),
            &information) == errSecSuccess,
          let fields = information as? [String: Any],
          let identifier = fields[kSecCodeInfoIdentifier as String] as? String,
          identifier == "org.claimbranch.local-runtime." + role,
          let unique = fields[kSecCodeInfoUnique as String] as? Data,
          unique.count == 20,
          let signed = fields[kSecCodeInfoFlags as String] as? NSNumber,
          let running = fields[kSecCodeInfoStatus as String] as? NSNumber,
          signed.uint32Value & 0x10000 != 0,
          running.uint32Value & 0x10000 != 0 else { return nil }
    return ["schema": "claimbranch.native-runtime-check/v1", "role": role,
            "identifier": identifier,
            "code_hash": unique.map { String(format: "%02x", $0) }.joined(),
            "running_hardened": true, "authorization_verified": false,
            "protected_acceptance_available": false]
}

enum DeliveryError: Error { case invalid, io, timeout, peer }
let deliveryLimit = 262176 // 32-byte exchange nonce plus bounded canonical review.

func continuousNow() -> Double {
    var scale = mach_timebase_info_data_t()
    mach_timebase_info(&scale)
    return Double(mach_continuous_time()) * Double(scale.numer) / Double(scale.denom) / 1_000_000_000
}

func waitReady(_ fd: Int32, _ events: Int16, _ deadline: Double) throws {
    while true {
        let remaining = deadline - continuousNow()
        guard remaining > 0 else { throw DeliveryError.timeout }
        var value = pollfd(fd: fd, events: events, revents: 0)
        let count = poll(&value, 1, Int32(min(remaining * 1000, 10000).rounded(.up)))
        if count < 0 && errno == EINTR { continue }
        if count == 0 { continue } // A polling slice is not the sealed deadline.
        guard count > 0 else { throw DeliveryError.io }
        guard value.revents & (events | Int16(POLLHUP)) != 0 else { throw DeliveryError.io }
        return
    }
}

func inputReview(_ deadline: Double, _ limit: Int = deliveryLimit) throws -> Data {
    var info = stat()
    guard fstat(STDIN_FILENO, &info) == 0, info.st_mode & S_IFMT == S_IFIFO else { throw DeliveryError.invalid }
    let previous = fcntl(STDIN_FILENO, F_GETFL)
    guard previous >= 0, fcntl(STDIN_FILENO, F_SETFL, previous | O_NONBLOCK) == 0 else { throw DeliveryError.io }
    defer { _ = fcntl(STDIN_FILENO, F_SETFL, previous) }
    var result = Data()
    while true {
        try waitReady(STDIN_FILENO, Int16(POLLIN), deadline)
        var buffer = [UInt8](repeating: 0, count: 4096)
        let count = read(STDIN_FILENO, &buffer, buffer.count)
        if count < 0 && [EINTR, EAGAIN].contains(errno) { continue }
        guard count >= 0 else { throw DeliveryError.io }
        if count == 0 { break }
        guard result.count + count <= limit else { throw DeliveryError.invalid }
        result.append(contentsOf: buffer.prefix(count))
    }
    guard result.count >= 33 else { throw DeliveryError.invalid }
    return result
}

func socketAddress(_ path: String) throws -> sockaddr_un {
    let bytes = Array(path.utf8)
    guard path.hasPrefix("/"), !bytes.contains(0), bytes.count < 104 else { throw DeliveryError.invalid }
    var value = sockaddr_un()
    value.sun_family = sa_family_t(AF_UNIX)
    value.sun_len = UInt8(MemoryLayout<sockaddr_un>.size)
    withUnsafeMutableBytes(of: &value.sun_path) { $0.copyBytes(from: bytes + [0]) }
    return value
}

func configureSocket(_ fd: Int32) throws {
    var yes: Int32 = 1
    guard fcntl(fd, F_SETFD, FD_CLOEXEC) == 0,
          fcntl(fd, F_SETFL, O_NONBLOCK) == 0,
          setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &yes, socklen_t(MemoryLayout.size(ofValue: yes))) == 0
    else { throw DeliveryError.io }
}

func readExact(_ fd: Int32, _ count: Int, _ deadline: Double) throws -> Data {
    var result = Data()
    while result.count < count {
        try waitReady(fd, Int16(POLLIN), deadline)
        var buffer = [UInt8](repeating: 0, count: min(count - result.count, 4096))
        let size = recv(fd, &buffer, buffer.count, MSG_DONTWAIT)
        if size < 0 && [EINTR, EAGAIN].contains(errno) { continue }
        guard size > 0 else { throw DeliveryError.io }
        result.append(contentsOf: buffer.prefix(size))
    }
    return result
}

func writeAll(_ fd: Int32, _ bytes: Data, _ deadline: Double) throws {
    var offset = 0
    while offset < bytes.count {
        try waitReady(fd, Int16(POLLOUT), deadline)
        let count = bytes.withUnsafeBytes {
            send(fd, $0.baseAddress!.advanced(by: offset), $0.count - offset, MSG_DONTWAIT)
        }
        if count < 0 && [EINTR, EAGAIN].contains(errno) { continue }
        guard count > 0 else { throw DeliveryError.io }
        offset += count
    }
}

func framed(_ bytes: Data) -> Data {
    var count = UInt32(bytes.count).bigEndian
    return withUnsafeBytes(of: &count) { Data($0) } + bytes
}

func readFrame(_ fd: Int32, _ deadline: Double, _ limit: Int = deliveryLimit) throws -> Data {
    let header = try readExact(fd, 4, deadline)
    let count = header.reduce(UInt32(0)) { ($0 << 8) | UInt32($1) }
    guard count > 0, count <= limit else { throw DeliveryError.invalid }
    return try readExact(fd, Int(count), deadline)
}

func requirePeer(_ fd: Int32, _ hash: String) throws {
    let expectedRole = role == "broker" ? "gateway" : "broker"
    var uid: uid_t = 0
    var gid: gid_t = 0
    var token = audit_token_t()
    var size = socklen_t(MemoryLayout.size(ofValue: token))
    guard getpeereid(fd, &uid, &gid) == 0, uid == geteuid(),
          getsockopt(fd, SOL_LOCAL, LOCAL_PEERTOKEN, &token, &size) == 0,
          size == MemoryLayout.size(ofValue: token) else { throw DeliveryError.peer }
    let data = withUnsafeBytes(of: &token) { Data($0) }
    var guest: SecCode?
    var requirement: SecRequirement?
    let text = "identifier \"org.claimbranch.local-runtime.\(expectedRole)\" and cdhash H\"\(hash)\""
    guard SecRequirementCreateWithString(text as CFString, [], &requirement) == errSecSuccess,
          let requirement,
          SecCodeCopyGuestWithAttributes(nil, [kSecGuestAttributeAudit as String: data] as CFDictionary,
                                        [], &guest) == errSecSuccess, let guest,
          SecCodeCheckValidity(guest, [], requirement) == errSecSuccess else { throw DeliveryError.peer }
    var information: CFDictionary?
    // SecCode.h accepts the dynamic object, even though Swift imports a static type.
    guard SecCodeCopySigningInformation(unsafeBitCast(guest, to: SecStaticCode.self),
          SecCSFlags(rawValue: kSecCSSigningInformation | kSecCSDynamicInformation), &information) == errSecSuccess,
          let fields = information as? [String: Any],
          let flags = fields[kSecCodeInfoFlags as String] as? NSNumber,
          let running = fields[kSecCodeInfoStatus as String] as? NSNumber,
          flags.uint32Value & 0x10000 != 0, running.uint32Value & 0x10000 != 0
    else { throw DeliveryError.peer }
}

func withReviewPeer(_ path: String, _ peerHash: String, _ deadline: Double, _ exchange: (Int32) throws -> Void) throws {
    var fd = socket(AF_UNIX, SOCK_STREAM, 0)
    guard fd >= 0 else { throw DeliveryError.io }
    defer { close(fd) }
    try configureSocket(fd)
    var address = try socketAddress(path)
#if CLAIMBRANCH_GATEWAY
    guard URL(fileURLWithPath: path).lastPathComponent == "s" else { throw DeliveryError.invalid }
    let directory = open(URL(fileURLWithPath: path).deletingLastPathComponent().path,
                         O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
    guard directory >= 0 else { throw DeliveryError.io }
    defer { close(directory) }
    var parent = stat()
    guard fstat(directory, &parent) == 0, parent.st_uid == geteuid(),
          parent.st_mode & 0o777 == 0o700 else { throw DeliveryError.invalid }
    umask(0o077)
    let bound = withUnsafePointer(to: &address) {
        $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { bind(fd, $0, socklen_t(MemoryLayout<sockaddr_un>.size)) }
    }
    guard bound == 0 else { throw DeliveryError.io }
    var original = stat()
    guard fstatat(directory, "s", &original, AT_SYMLINK_NOFOLLOW) == 0,
          original.st_mode & S_IFMT == S_IFSOCK else { throw DeliveryError.io }
    defer {
        var current = stat()
        if fstatat(directory, "s", &current, AT_SYMLINK_NOFOLLOW) == 0,
           current.st_dev == original.st_dev, current.st_ino == original.st_ino {
            unlinkat(directory, "s", 0)
        }
    }
    guard listen(fd, 1) == 0 else { throw DeliveryError.io }
    try waitReady(fd, Int16(POLLIN), deadline)
    let peer = accept(fd, nil, nil)
    guard peer >= 0 else { throw DeliveryError.io }
    defer { close(peer) }
    try configureSocket(peer)
    try requirePeer(peer, peerHash)
    try exchange(peer)
#else
    while true {
        guard continuousNow() < deadline else { throw DeliveryError.timeout }
        let connected = withUnsafePointer(to: &address) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { connect(fd, $0, socklen_t(MemoryLayout<sockaddr_un>.size)) }
        }
        if connected == 0 { break }
        var error = errno
        if error == EINPROGRESS {
            try waitReady(fd, Int16(POLLOUT), deadline)
            var size = socklen_t(MemoryLayout.size(ofValue: error))
            guard getsockopt(fd, SOL_SOCKET, SO_ERROR, &error, &size) == 0 else { throw DeliveryError.io }
            if error == 0 { break }
        }
        // The inode can exist before listen(). Retry only readiness errors on
        // a fresh socket, within the original deadline, before any peer/data use.
        guard [ENOENT, ECONNREFUSED].contains(error) else { throw DeliveryError.io }
        close(fd)
        fd = socket(AF_UNIX, SOCK_STREAM, 0)
        guard fd >= 0 else { throw DeliveryError.io }
        try configureSocket(fd)
        usleep(10000)
    }
    try requirePeer(fd, peerHash)
    try exchange(fd)
#endif
    guard continuousNow() < deadline else { throw DeliveryError.timeout }
}

func deliver(_ path: String, _ peerHash: String, _ bytes: Data, _ deadline: Double) throws {
    let digest = Data(SHA256.hash(data: bytes))
    try withReviewPeer(path, peerHash, deadline) { fd in
#if CLAIMBRANCH_GATEWAY
        try writeAll(fd, framed(digest), deadline)
        guard try readFrame(fd, deadline) == bytes else { throw DeliveryError.invalid }
        try writeAll(fd, framed(digest), deadline)
#else
        guard try readFrame(fd, deadline) == digest else { throw DeliveryError.invalid }
        try writeAll(fd, framed(bytes), deadline)
        guard try readFrame(fd, deadline) == digest else { throw DeliveryError.invalid }
#endif
    }
}

func deliveryResult() throws -> [String: Any] {
    let args = Array(CommandLine.arguments.dropFirst())
    guard args.count == 3,
          args[0] == (role == "gateway" ? "receive-review" : "send-review"),
          args[2].utf8.count == 40, args[2].utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) })
    else { throw DeliveryError.invalid }
    let deadline = continuousNow() + 8
    let bytes = try inputReview(deadline)
    try deliver(args[1], args[2], bytes, deadline)
    return ["schema": "claimbranch.native-review-delivery/v1", "role": role,
            "status": "delivered-unaccepted-review", "exchange_digest": SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined(),
            "byte_count": bytes.count, "peer_verified": true,
            "authorization_verified": false, "protected_acceptance_available": false]
}

let keyFile = "key-registration.json"
let keyPurpose = Data("ClaimBranch synthetic key registration v1\n".utf8)
func hashHex(_ bytes: Data) -> String { SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined() }
func encoded(_ value: Any) throws -> Data {
    // Foundation's sortedKeys uses localized ordering (for example, it places
    // _CodeSignature before Info.plist). The portable contract sorts key bytes.
    func encode(_ value: Any, _ depth: Int) throws -> Data {
        guard depth <= 16 else { throw DeliveryError.invalid }
        if let object = value as? [String: Any] {
            var result = Data("{".utf8)
            let keys = object.keys.sorted { $0.utf8.lexicographicallyPrecedes($1.utf8) }
            for (index, key) in keys.enumerated() {
                if index > 0 { result.append(Data(",".utf8)) }
                result.append(try encode(key, depth + 1))
                result.append(Data(":".utf8))
                result.append(try encode(object[key]!, depth + 1))
            }
            result.append(Data("}".utf8)); return result
        }
        if let array = value as? [Any] {
            var result = Data("[".utf8)
            for (index, item) in array.enumerated() {
                if index > 0 { result.append(Data(",".utf8)) }
                result.append(try encode(item, depth + 1))
            }
            result.append(Data("]".utf8)); return result
        }
        return try JSONSerialization.data(withJSONObject: value, options: [.fragmentsAllowed, .withoutEscapingSlashes])
    }
    return try encode(value, 0)
}
func hexText(_ value: String, _ count: Int) -> Bool {
    value.utf8.count == count && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
}
let signingLimit = 294912
let signingPurpose = Data("ClaimBranch synthetic review attestation v1\n".utf8)
func finiteJSON(_ value: Any, _ depth: Int = 0) -> Bool {
    guard depth <= 16 else { return false }
    if value is NSNull { return true }
    if let text = value as? String {
        return text.utf8.count <= 16384 && text.utf8.elementsEqual(text.precomposedStringWithCanonicalMapping.utf8)
    }
    if let number = value as? NSNumber {
        if CFGetTypeID(number) == CFBooleanGetTypeID() { return true }
        return !["f", "d"].contains(String(cString: number.objCType)) && abs(number.doubleValue) <= 9007199254740991
    }
    if let array = value as? [Any] { return array.count <= 128 && array.allSatisfy { finiteJSON($0, depth + 1) } }
    if let object = value as? [String: Any] {
        return object.count <= 128 && object.allSatisfy { finiteJSON($0.key, depth + 1) && finiteJSON($0.value, depth + 1) }
    }
    return false
}
func nativeFalse(_ value: Any?) -> Bool {
    guard let number = value as? NSNumber else { return false }
    return CFGetTypeID(number) == CFBooleanGetTypeID() && !number.boolValue
}
func signingReviewVersion(_ review: [String: Any]) -> Bool {
    let keys: Set<String> = ["schema", "operation", "operation_digest", "assessment", "decision", "lineages", "source_judgments", "preparation", "manuscript_digest", "session_nonce", "sealed_at", "expires_at", "parent_review_digest", "authority", "authorization_verified", "acceptance_available"]
    switch review["schema"] as? String {
    case "claimbranch.paper-operation-review/v1":
        return Set(review.keys) == keys
    case "claimbranch.paper-operation-review/v2":
        guard Set(review.keys) == keys.union(["origin_registry_digest"]),
              let commitment = review["origin_registry_digest"] as? String, hexText(commitment, 64),
              let operation = review["operation"] as? [String: Any],
              operation["action"] as? String == "record-interpretation" else { return false }
        return true
    default: return false
    }
}
func initialIdentifier(_ value: Any?) -> Bool {
    guard let text = value as? String, (1...128).contains(text.utf8.count) else { return false }
    return text.range(of: "^[A-Za-z0-9][A-Za-z0-9._:-]*\\z", options: .regularExpression) != nil
}
func initialNumber(_ value: Any?) -> Bool {
    guard let text = value as? String, (1...24).contains(text.utf8.count) else { return false }
    return text.range(of: "^(0|[1-9][0-9]*)\\z", options: .regularExpression) != nil
}
func initialIdentity(_ value: Any?) -> Bool {
    guard let object = value as? [String: Any], Set(object.keys) == ["device", "inode"] else { return false }
    return initialNumber(object["device"]) && initialNumber(object["inode"])
}
func initialPath(_ value: Any?) -> Bool {
    guard let text = value as? String, (2...8192).contains(text.utf8.count), text.utf8.count % 2 == 0 else { return false }
    return hexText(text, text.utf8.count)
}
func initializationOperation(_ review: [String: Any]) throws -> [String: Any] {
    guard Set(review.keys) == ["schema", "seed", "association", "initial_head", "evidence_watermark", "operation_count", "session_nonce", "sealed_at", "expires_at", "authority", "authorization_verified", "acceptance_available", "source_fidelity_verified"],
          review["schema"] as? String == "claimbranch.project-initialization-review/v1",
          review["authority"] as? String == "unaccepted-initialization-review",
          nativeFalse(review["authorization_verified"]), nativeFalse(review["acceptance_available"]), nativeFalse(review["source_fidelity_verified"]),
          let count = review["operation_count"] as? NSNumber, CFGetTypeID(count) != CFBooleanGetTypeID(), count.intValue == 0,
          let watermark = review["evidence_watermark"] as? NSNumber, CFGetTypeID(watermark) != CFBooleanGetTypeID(), watermark.intValue == 0,
          initialIdentifier(review["session_nonce"]),
          let seed = review["seed"] as? [String: Any], Set(seed.keys) == ["schema_version", "project_id", "paper_title", "claim_id", "claim_statement", "anchor_id"],
          let version = seed["schema_version"] as? NSNumber, CFGetTypeID(version) != CFBooleanGetTypeID(), version.intValue == 3,
          initialIdentifier(seed["project_id"]), initialIdentifier(seed["claim_id"]), initialIdentifier(seed["anchor_id"]),
          seed["claim_id"] as? String != seed["anchor_id"] as? String,
          let title = seed["paper_title"] as? String, !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
          let thesis = seed["claim_statement"] as? String, !thesis.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
          review["initial_head"] as? String == "root-" + (try hashHex(encoded(seed))),
          let association = review["association"] as? [String: Any], Set(association.keys) == ["schema", "source", "workspace", "workspace_identity"],
          association["schema"] as? String == "claimbranch.project-association-preview/v1",
          initialPath(association["workspace"]), initialIdentity(association["workspace_identity"]),
          let source = association["source"] as? [String: Any], Set(source.keys) == ["root", "root_identity", "git_dir", "git_identity", "git_common_dir", "git_common_identity", "manuscript", "anchor_id", "file_identity", "size", "mtime_ns", "ctime_ns", "source_digest"],
          ["root", "git_dir", "git_common_dir", "manuscript"].allSatisfy({ initialPath(source[$0]) }),
          ["root_identity", "git_identity", "git_common_identity", "file_identity"].allSatisfy({ initialIdentity(source[$0]) }),
          ["size", "mtime_ns", "ctime_ns"].allSatisfy({ initialNumber(source[$0]) }),
          source["anchor_id"] as? String == seed["anchor_id"] as? String,
          let sourceDigest = source["source_digest"] as? String, hexText(sourceDigest, 64) else { throw DeliveryError.invalid }
    return ["action": "initialize-project", "project_id": seed["project_id"]!, "seed": seed,
            "association": association, "initial_head": review["initial_head"]!]
}
func signingOperation(_ review: [String: Any]) throws -> [String: Any] {
    if review["schema"] as? String == "claimbranch.project-initialization-review/v1" {
        return try initializationOperation(review)
    }
    guard signingReviewVersion(review), review["authority"] as? String == "unaccepted-review",
          nativeFalse(review["authorization_verified"]), nativeFalse(review["acceptance_available"]),
          let operation = review["operation"] as? [String: Any], operation["schema"] as? String == "claimbranch.paper-operation/v1",
          let action = operation["action"] as? String, ["record-interpretation", "apply-selected-merge"].contains(action),
          review["operation_digest"] as? String == (try hashHex(encoded(operation))),
          let decision = review["decision"] as? [String: Any], let disposition = decision["disposition"] as? String,
          ["not-required", "answered", "deferred"].contains(disposition) else { throw DeliveryError.invalid }
    return operation
}
func visibleReviewText(_ text: String) -> String {
    text.unicodeScalars.map { scalar in
        let hidden = [.format, .control, .lineSeparator, .paragraphSeparator].contains(scalar.properties.generalCategory) ||
                     [0x115F, 0x1160, 0x3164, 0xFFA0].contains(scalar.value)
        return hidden && scalar.value != 10 ? "\\u{\(String(scalar.value, radix: 16))}" : String(scalar)
    }.joined()
}
struct ReviewSigningRequest {
    let packet: Data
    let header: [String: Any]
    let keyRequest: [String: String]
    let review: [String: Any]
    let operation: [String: Any]
    let publicKey: P256.Signing.PublicKey
    let sealedAt: Double
    let expiresAt: Double
    let enrollment: NativeEnrollment?
    var digest: Data { Data(SHA256.hash(data: packet)) }
    var message: Data { (enrollment == nil ? signingPurpose : Data("ClaimBranch enrolled review v1\n".utf8)) + digest }
    init(_ packet: Data, enrollment: NativeEnrollment? = nil) throws {
        guard packet.count > 4, packet.count <= signingLimit else { throw DeliveryError.invalid }
        let count = Int(packet.prefix(4).reduce(UInt32(0)) { ($0 << 8) | UInt32($1) })
        guard (1...4096).contains(count), packet.count > count + 4, packet.count - count - 4 <= 262144 else { throw DeliveryError.invalid }
        let head = Data(packet[4..<(4 + count)])
        let raw = Data(packet[(4 + count)...])
        guard let header = try JSONSerialization.jsonObject(with: head) as? [String: Any],
              Set(header.keys) == Set(["schema", "key_request", "registration_digest", "public_key_x963", "review_digest", "operation_digest", "nonce"] + (enrollment == nil ? [] : ["local_id"])),
              header["schema"] as? String == (enrollment == nil ? "claimbranch.review-signing-request/v1" : "claimbranch.enrolled-review-signing-request/v1"),
              finiteJSON(header), try encoded(header) == head,
              let keyRequest = header["key_request"] as? [String: String],
              Set(keyRequest.keys) == ["schema", "project_id", "build_pin", "broker_code_hash", "gateway_code_hash", "nonce", "directory_identity"],
              keyRequest["schema"] == "claimbranch.key-preparation/v1",
              let project = keyRequest["project_id"], project.utf8.count <= 128,
              project.range(of: "^[A-Za-z0-9][A-Za-z0-9._:-]*\\z", options: .regularExpression) != nil,
              hexText(keyRequest["build_pin"]!, 64), hexText(keyRequest["nonce"]!, 64),
              hexText(keyRequest["broker_code_hash"]!, 40), hexText(keyRequest["gateway_code_hash"]!, 40),
              let directory = keyRequest["directory_identity"], directory.utf8.count <= 64,
              directory.range(of: "^[0-9]+:[0-9]+\\z", options: .regularExpression) != nil,
              let own = inspect(),
              (enrollment == nil ? own["code_hash"] as? String == keyRequest[role + "_code_hash"] : enrollment!.accepts(header, keyRequest)),
              let registration = header["registration_digest"] as? String, hexText(registration, 64),
              let nonce = header["nonce"] as? String, hexText(nonce, 64),
              let publicText = header["public_key_x963"] as? String,
              let publicBytes = Data(base64Encoded: publicText), publicBytes.count == 65,
              publicBytes.base64EncodedString() == publicText,
              let review = try JSONSerialization.jsonObject(with: raw) as? [String: Any],
              finiteJSON(review), try encoded(review) == raw,
              review["schema"] as? String != "claimbranch.project-initialization-review/v1" || enrollment != nil,
              header["review_digest"] as? String == hashHex(raw),
              case let operation = try signingOperation(review),
              operation["project_id"] as? String == project,
              let operationDigest = header["operation_digest"] as? String,
              try hashHex(encoded(operation)) == operationDigest,
              let sealed = review["sealed_at"] as? NSNumber, CFGetTypeID(sealed) != CFBooleanGetTypeID(),
              let expires = review["expires_at"] as? NSNumber, CFGetTypeID(expires) != CFBooleanGetTypeID(),
              sealed.doubleValue >= 0, expires.doubleValue > sealed.doubleValue,
              expires.doubleValue <= sealed.doubleValue + 300 else { throw DeliveryError.invalid }
        self.packet = packet; self.header = header; self.keyRequest = keyRequest
        self.enrollment = enrollment
        self.review = review; self.operation = operation
        self.publicKey = try P256.Signing.PublicKey(x963Representation: publicBytes)
        self.sealedAt = sealed.doubleValue; self.expiresAt = expires.doubleValue
    }
    func fresh() throws {
        let now = Date().timeIntervalSince1970
        guard sealedAt <= now, now < expiresAt else { throw DeliveryError.timeout }
    }
    func verifiedReply(_ raw: Data) throws -> (String, String?) {
        guard raw.count <= 4096, let value = try JSONSerialization.jsonObject(with: raw) as? [String: String],
              try encoded(value) == raw, let status = value["status"] else { throw DeliveryError.invalid }
        if status == "signed-unaccepted-review" {
            guard Set(value.keys) == ["status", "signature_der"], let text = value["signature_der"],
                  let bytes = Data(base64Encoded: text), (8...72).contains(bytes.count),
                  bytes.base64EncodedString() == text else { throw DeliveryError.invalid }
            try fresh()
            guard publicKey.isValidSignature(try P256.Signing.ECDSASignature(derRepresentation: bytes), for: message)
            else { throw DeliveryError.invalid }
            return (status, nil)
        }
        guard Set(value.keys) == ["status", "stop_source"], let source = value["stop_source"],
              (status == "cancelled" && ["review-window", "os-authentication"].contains(source)) ||
              (status == "expired" && source == "deadline") else { throw DeliveryError.invalid }
        return (status, source)
    }
    func observation(_ outcome: (String, String?)) -> [String: Any] {
        let (status, source) = outcome
        var value: [String: Any] = ["schema": "claimbranch.native-review-signing/v1", "role": role,
            "status": status, "exchange_digest": hashHex(packet), "review_digest": header["review_digest"]!,
            "operation_digest": header["operation_digest"]!, "peer_verified": true,
            "signature_verified": status == "signed-unaccepted-review", "authorization_verified": false,
            "protected_acceptance_available": false]
        if let source { value["stop_source"] = source }
        if let enrollment { value["local_id"] = enrollment.id; value["enrollment_verified"] = true }
        return value
    }
}
// CLAIMBRANCH_INITIAL_SOURCE_SUPPORT
func signingResult() throws -> [String: Any] {
    let args = Array(CommandLine.arguments.dropFirst())
    let enrolledMode = args.first == (role == "broker" ? "sign-enrolled-review" : "receive-enrolled-review")
    guard args.count == 3,
          enrolledMode || args[0] == (role == "broker" ? "sign-review" : "receive-signed-review"),
          hexText(args[2], enrolledMode ? 64 : 40) else { throw DeliveryError.invalid }
    let enrollment = enrolledMode ? try loadEnrollment(args[2]) : nil
    let peer = enrollment?.body[role == "broker" ? "gateway_hash" : "broker_hash"] ?? args[2]
    let deadline = continuousNow() + 98
    let request = try ReviewSigningRequest(inputReview(continuousNow() + 8, signingLimit), enrollment: enrollment)
    guard enrolledMode || peer == request.keyRequest[(role == "broker" ? "gateway" : "broker") + "_code_hash"] else { throw DeliveryError.invalid }
    try request.fresh()
    try request.checkInitialSource()
    var reply = Data()
    var outcome: (String, String?)?
    try withReviewPeer(args[1], peer, deadline) { fd in
#if CLAIMBRANCH_GATEWAY
        try writeAll(fd, framed(request.digest), deadline)
        guard try readFrame(fd, deadline, signingLimit) == request.packet else { throw DeliveryError.invalid }
        try writeAll(fd, framed(request.digest), deadline)
        reply = try readFrame(fd, deadline, 4096)
        outcome = try request.verifiedReply(reply)
        try requirePeer(fd, peer)
        try writeAll(fd, framed(Data(SHA256.hash(data: reply))), deadline)
#else
        guard try readFrame(fd, deadline) == request.digest else { throw DeliveryError.invalid }
        try writeAll(fd, framed(request.packet), deadline)
        guard try readFrame(fd, deadline) == request.digest else { throw DeliveryError.invalid }
        try request.fresh()
        reply = try reviewAndSign(request, deadline)
        outcome = try request.verifiedReply(reply)
        if outcome!.0 == "signed-unaccepted-review" { try request.checkInitialSource(); try request.fresh() }
        try requirePeer(fd, peer)
        try writeAll(fd, framed(reply), deadline)
        guard try readFrame(fd, deadline) == Data(SHA256.hash(data: reply)) else { throw DeliveryError.invalid }
#endif
    }
    guard let outcome else { throw DeliveryError.invalid }
    try enrollment?.unchanged()
    if outcome.0 == "signed-unaccepted-review" { try request.checkInitialSource(); try request.fresh() }
    return request.observation(outcome)
}

func keyDirectory(_ request: [String: String]) throws -> Int32 {
    let fd = open(".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
    guard fd >= 0 else { throw DeliveryError.io }
    var info = stat()
    guard fstat(fd, &info) == 0, info.st_uid == geteuid(), info.st_mode & 0o777 == 0o700,
          request["directory_identity"] == "\(info.st_dev):\(info.st_ino)" else {
        close(fd); throw DeliveryError.invalid
    }
    return fd
}
func keyRequest(_ raw: Data) throws -> [String: String] {
    guard raw.count <= 4096,
          let value = try JSONSerialization.jsonObject(with: raw) as? [String: String],
          Set(value.keys) == ["schema", "project_id", "build_pin", "broker_code_hash", "gateway_code_hash", "nonce", "directory_identity"],
          value["schema"] == "claimbranch.key-preparation/v1",
          let project = value["project_id"], project.utf8.count <= 128,
          project.range(of: "^[A-Za-z0-9][A-Za-z0-9._:-]*\\z", options: .regularExpression) != nil,
          hexText(value["build_pin"]!, 64), hexText(value["nonce"]!, 64),
          hexText(value["broker_code_hash"]!, 40), hexText(value["gateway_code_hash"]!, 40),
          let own = inspect(), own["code_hash"] as? String == value["broker_code_hash"],
          try encoded(value) == raw else { throw DeliveryError.invalid }
    let dir = try keyDirectory(value)
    close(dir)
    return value
}
func keyOutput(_ status: String, _ request: Data, _ extra: [String: Any] = [:]) -> Never {
    var value: [String: Any] = ["schema": "claimbranch.key-preparation-result/v1", "status": status,
        "request_digest": hashHex(request), "authorization_verified": false, "product_custody_verified": false]
    value.merge(extra) { _, new in new }
    if let raw = try? encoded(value) { FileHandle.standardOutput.write(raw) }
    exit(0)
}
func signingDenied(_ error: Error) -> Bool {
    var current: NSError? = error as NSError
    for _ in 0..<4 {
        guard let error = current else { return false }
        if (error.domain == NSOSStatusErrorDomain && error.code == Int(errSecInteractionNotAllowed)) ||
           (error.domain == LAError.errorDomain && error.code == LAError.notInteractive.rawValue) { return true }
        current = error.userInfo[NSUnderlyingErrorKey] as? NSError
    }
    return false
}
func cancelledKeyAuthentication(_ error: Error?) -> Bool {
    guard let error = error as NSError? else { return false }
    return (error.domain == LAError.errorDomain && [LAError.userCancel.rawValue, LAError.appCancel.rawValue,
            LAError.systemCancel.rawValue].contains(error.code)) ||
           (error.domain == NSOSStatusErrorDomain && error.code == Int(errSecUserCanceled))
}
func userCancelledKeyAuthentication(_ error: Error?) -> Bool {
    guard let error = error as NSError? else { return false }
    return (error.domain == LAError.errorDomain && error.code == LAError.userCancel.rawValue) ||
           (error.domain == NSOSStatusErrorDomain && error.code == Int(errSecUserCanceled))
}
func registrationBytes(_ request: [String: String], _ context: LAContext) throws -> Data {
    guard SecureEnclave.isAvailable else { throw DeliveryError.invalid }
    var error: Unmanaged<CFError>?
    guard let access = SecAccessControlCreateWithFlags(nil, kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        [.privateKeyUsage, .userPresence], &error) else { throw DeliveryError.invalid }
    let key = try SecureEnclave.P256.Signing.PrivateKey(accessControl: access, authenticationContext: context)
    let representation = key.dataRepresentation
    guard !representation.isEmpty, representation.count <= 8192 else { throw DeliveryError.invalid }
    let body: [String: Any] = ["schema": "claimbranch.key-registration-body/v1", "request": request,
        "public_key_x963": key.publicKey.x963Representation.base64EncodedString(),
        "representation_digest": hashHex(representation)]
    let message = keyPurpose + (try encoded(body))
    let signature = try key.signature(for: message)
    guard key.publicKey.isValidSignature(signature, for: message) else { throw DeliveryError.invalid }
    return try encoded(["schema": "claimbranch.key-registration/v1", "body": body,
        "representation": representation.base64EncodedString(), "signature_der": signature.derRepresentation.base64EncodedString(),
        "authority": "unaccepted-key-registration"])
}
func checkedKeyRecord(_ raw: Data, _ request: [String: String]) throws -> (Data, Data) {
    guard raw.count <= 24576,
          let value = try JSONSerialization.jsonObject(with: raw) as? [String: Any],
          Set(value.keys) == ["schema", "body", "representation", "signature_der", "authority"],
          value["schema"] as? String == "claimbranch.key-registration/v1",
          value["authority"] as? String == "unaccepted-key-registration",
          let body = value["body"] as? [String: Any],
          Set(body.keys) == ["schema", "request", "public_key_x963", "representation_digest"],
          body["schema"] as? String == "claimbranch.key-registration-body/v1",
          body["request"] as? [String: String] == request,
          let publicText = body["public_key_x963"] as? String,
          let publicBytes = Data(base64Encoded: publicText), publicBytes.count == 65, publicBytes.first == 4,
          publicBytes.base64EncodedString() == publicText,
          let representationText = value["representation"] as? String,
          let representation = Data(base64Encoded: representationText), (1...8192).contains(representation.count),
          representation.base64EncodedString() == representationText,
          body["representation_digest"] as? String == hashHex(representation),
          let signatureText = value["signature_der"] as? String,
          let signatureBytes = Data(base64Encoded: signatureText), (8...72).contains(signatureBytes.count),
          signatureBytes.base64EncodedString() == signatureText,
          try encoded(value) == raw else { throw DeliveryError.invalid }
    let publicKey = try P256.Signing.PublicKey(x963Representation: publicBytes)
    let signature = try P256.Signing.ECDSASignature(derRepresentation: signatureBytes)
    guard publicKey.isValidSignature(signature, for: keyPurpose + (try encoded(body))) else { throw DeliveryError.invalid }
    return (representation, publicBytes)
}
func readKeyRecord(_ dir: Int32) throws -> Data {
    let fd = openat(dir, keyFile, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
    guard fd >= 0 else { throw DeliveryError.io }
    defer { close(fd) }
    var before = stat()
    guard fstat(fd, &before) == 0, before.st_mode & S_IFMT == S_IFREG, before.st_nlink == 1,
          before.st_uid == geteuid(), before.st_mode & 0o777 == 0o600,
          before.st_size > 0, before.st_size <= 24576 else { throw DeliveryError.invalid }
    let file = FileHandle(fileDescriptor: fd, closeOnDealloc: false)
    let raw = try file.read(upToCount: 24577) ?? Data()
    var after = stat(), current = stat()
    guard raw.count == before.st_size, fstat(fd, &after) == 0,
          fstatat(dir, keyFile, &current, AT_SYMLINK_NOFOLLOW) == 0,
          sameKeyFile(before, after), sameKeyFile(after, current) else { throw DeliveryError.invalid }
    return raw
}
func sameKeyFile(_ a: stat, _ b: stat) -> Bool {
    a.st_dev == b.st_dev && a.st_ino == b.st_ino && a.st_size == b.st_size &&
    a.st_mode == b.st_mode && a.st_uid == b.st_uid && a.st_nlink == b.st_nlink &&
    a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec && a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec &&
    a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec && a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec
}
func reopenKey(_ requestRaw: Data, _ expected: String) throws -> Never {
    guard hexText(expected, 64) else { throw DeliveryError.invalid }
    let request = try keyRequest(requestRaw)
    let dir = try keyDirectory(request)
    defer { close(dir) }
    let raw = try readKeyRecord(dir)
    guard hashHex(raw) == expected else { throw DeliveryError.invalid }
    let (representation, publicBytes) = try checkedKeyRecord(raw, request)
    let context = LAContext()
    context.interactionNotAllowed = true
    context.touchIDAuthenticationAllowableReuseDuration = 0
    defer { context.invalidate() }
    let key = try SecureEnclave.P256.Signing.PrivateKey(dataRepresentation: representation, authenticationContext: context)
    guard key.publicKey.x963Representation == publicBytes else { throw DeliveryError.invalid }
    var denied = false
    do { _ = try key.signature(for: Data("ClaimBranch key registration noninteractive denial v1".utf8)) }
    catch { denied = signingDenied(error) }
    guard denied, try readKeyRecord(dir) == raw else { throw DeliveryError.invalid }
    keyOutput("reopened", requestRaw, ["registration_digest": expected, "public_key_digest": hashHex(publicBytes),
        "noninteractive_signing_denied": true])
}

#if CLAIMBRANCH_BROKER
struct KeyPreparationGate {
    enum Phase { case reviewing, authenticating, generating, terminal }
    let deadline: Double
    private(set) var phase = Phase.reviewing
    mutating func begin(_ now: Double) -> Bool {
        guard now < deadline, phase == .reviewing else { return false }
        phase = .authenticating
        return true
    }
    mutating func authenticated(_ success: Bool, _ now: Double) -> Bool {
        guard now < deadline, phase == .authenticating, success else { return false }
        phase = .generating
        return true
    }
    func mayPersist(_ now: Double) -> Bool { now < deadline && phase == .generating }
    mutating func stop() -> Bool {
        guard phase != .terminal else { return false }
        phase = .terminal
        return true
    }
}
func resolvedKeyStop(_ status: String, _ source: String, _ nativeUserCancel: Bool) -> (String, String) {
    // macOS may request app termination while reporting its authentication
    // cancellation. Keep the explicit native user-cancel observation when both
    // arrive; it must not be mislabeled as the review window's cancel button.
    (status, status == "cancelled" && nativeUserCancel ? "os-authentication" : source)
}

final class KeyPreparationController: NSObject, NSApplicationDelegate, NSWindowDelegate {
    let requestRaw: Data
    let request: [String: String]
    let directory: Int32
    let reserved: Int32
    let context = LAContext()
    var gate = KeyPreparationGate(deadline: continuousNow() + 90)
    var window: NSWindow!
    var button: NSButton!
    var timer: Timer?
    var pendingStop: (String, String)?
    init(_ raw: Data) throws {
        guard SecureEnclave.isAvailable else { throw DeliveryError.invalid }
        requestRaw = raw
        request = try keyRequest(raw)
        directory = try keyDirectory(request)
        reserved = openat(directory, keyFile, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        guard reserved >= 0 else { close(directory); throw DeliveryError.io }
        guard fchmod(reserved, 0o600) == 0 else { close(reserved); close(directory); throw DeliveryError.io }
        super.init()
        context.interactionNotAllowed = true
        context.touchIDAuthenticationAllowableReuseDuration = 0
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 740, height: 500),
                          styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.title = "ClaimBranch · 새 승인 키 연결 준비 (합성 검증)"
        window.delegate = self
        let scroll = NSScrollView(frame: NSRect(x: 20, y: 85, width: 700, height: 395))
        scroll.hasVerticalScroller = true
        let text = NSTextView(frame: scroll.bounds)
        text.isEditable = false
        text.isSelectable = true
        text.isVerticallyResizable = true
        text.autoresizingMask = [.width]
        text.textContainer?.widthTracksTextView = true
        text.textContainer?.containerSize = NSSize(width: 700, height: CGFloat.greatestFiniteMagnitude)
        text.font = NSFont.systemFont(ofSize: 14)
        text.string = """
        이 프로젝트와 실행 코드에 연결할 새 기기 키를 준비합니다.
        기존 키나 연구 자료는 사용하지 않습니다. 연구 승인 권한은 발급하지 않습니다.

        프로젝트: \(request["project_id"]!)
        실행 코드 묶음: \(request["build_pin"]!)
        저장 위치: \(FileManager.default.currentDirectoryPath)

        ‘새 키 준비’를 누르면 macOS에 이번 동작의 본인 확인을 요청합니다.
        성공한 경우에만 Secure Enclave 키를 만들고 위 연결 정보에 서명합니다.
        개인 키 원문은 내보내지 않으며, 이 기기에서만 열리는 암호화 표현을 저장합니다.
        재시작해도 같은 공개키인지 확인할 수 있습니다.

        이것은 제품 등록 전 합성 검증입니다. 원고와 연구 판단은 변경되지 않습니다.
        취소·만료·중단 시 승인 권한이 생기지 않습니다. 불완전한 파일이 남으면 덮어쓰지 않습니다.
        90초 안에 선택하세요.
        """
        scroll.documentView = text
        window.contentView?.addSubview(scroll)
        button = NSButton(title: "새 키 준비", target: self, action: #selector(prepare))
        button.frame = NSRect(x: 455, y: 25, width: 130, height: 40)
        button.bezelStyle = .rounded
        let cancel = NSButton(title: "취소", target: self, action: #selector(cancelReview))
        cancel.frame = NSRect(x: 595, y: 25, width: 125, height: 40)
        cancel.bezelStyle = .rounded
        window.contentView?.addSubview(button)
        window.contentView?.addSubview(cancel)
        window.center(); window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
        timer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] _ in
            if let self, continuousNow() >= self.gate.deadline { self.stop("expired") }
        }
        RunLoop.main.add(timer!, forMode: .common)
    }
    @objc func prepare() {
        guard gate.begin(continuousNow()) else { return }
        button.isEnabled = false
        context.interactionNotAllowed = false
        context.evaluatePolicy(.deviceOwnerAuthentication,
            localizedReason: "ClaimBranch 합성 프로젝트에 새 기기 승인 키 연결 준비") { [self] success, error in
            DispatchQueue.main.async { [self] in
                if let pendingStop {
                    let outcome = resolvedKeyStop(pendingStop.0, pendingStop.1, userCancelledKeyAuthentication(error))
                    keyOutput(outcome.0, requestRaw, ["stop_source": outcome.1])
                }
                guard gate.phase == .authenticating else { return }
                guard continuousNow() < gate.deadline else { stop("expired"); return }
                guard success, error == nil else {
                    if cancelledKeyAuthentication(error) { stop("cancelled", source: "os-authentication") }
                    else { fail() }
                    return
                }
                guard gate.authenticated(true, continuousNow()) else { stop("expired"); return }
                context.interactionNotAllowed = true
                DispatchQueue.global(qos: .userInitiated).async { [self] in
                    let result = Result { try registrationBytes(request, context) }
                    DispatchQueue.main.async { [self] in complete(result) }
                }
            }
        }
    }
    func complete(_ result: Result<Data, Error>) {
        guard gate.phase == .generating else { return }
        guard gate.mayPersist(continuousNow()) else { stop("expired"); return }
        do {
            let raw = try result.get()
            let (_, publicBytes) = try checkedKeyRecord(raw, request)
            let dir = try keyDirectory(request); close(dir)
            var original = stat(), current = stat()
            guard fstat(reserved, &original) == 0, fstatat(directory, keyFile, &current, AT_SYMLINK_NOFOLLOW) == 0,
                  original.st_dev == current.st_dev, original.st_ino == current.st_ino,
                  original.st_nlink == 1, original.st_size == 0, original.st_mode & 0o777 == 0o600 else { throw DeliveryError.invalid }
            let file = FileHandle(fileDescriptor: reserved, closeOnDealloc: false)
            try file.write(contentsOf: raw)
            guard fsync(reserved) == 0, fsync(directory) == 0 else { throw DeliveryError.io }
            // A write/flush crossing the deadline leaves an incomplete attempt,
            // never a normal cancellation/expiry with an apparently usable file.
            guard gate.mayPersist(continuousNow()), try readKeyRecord(directory) == raw else { fail() }
            guard gate.stop() else { return }
            context.invalidate(); timer?.invalidate()
            keyOutput("prepared", requestRaw, ["registration_digest": hashHex(raw), "public_key_digest": hashHex(publicBytes)])
        } catch { fail() }
    }
    func fail() -> Never {
        context.invalidate()
        fputs("Native key preparation failed; no authority was granted.\n", stderr)
        exit(2)
    }
    func stop(_ status: String, source: String = "deadline") {
        let awaitingAuthentication = gate.phase == .authenticating
        guard gate.stop() else { return }
        pendingStop = (status, source)
        context.invalidate(); timer?.invalidate()
        if awaitingAuthentication && source != "os-authentication" {
            // Deny all later generation immediately; wait at most one second
            // only to classify the native callback before exiting.
            DispatchQueue.main.asyncAfter(deadline: .now() + 1) { [self] in
                keyOutput(status, requestRaw, ["stop_source": source])
            }
            return
        }
        keyOutput(status, requestRaw, ["stop_source": source])
    }
    @objc func cancelReview() { stop("cancelled", source: "review-window") }
    func windowShouldClose(_ sender: NSWindow) -> Bool { cancelReview(); return false }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply { cancelReview(); return .terminateCancel }
}
func reviewKeyMaterial(_ request: ReviewSigningRequest) throws -> Data {
    try request.checkInitialSource()
    let rawRequest = try encoded(request.keyRequest)
    let checked = request.enrollment == nil ? try keyRequest(rawRequest) : request.keyRequest
    try request.enrollment?.unchanged()
    let dir: Int32
    if let enrolled = request.enrollment { dir = try localDirectory(enrolled.body["key_directory"]!) }
    else { dir = try keyDirectory(checked) }
    defer { close(dir) }
    let raw = try readKeyRecord(dir)
    guard hashHex(raw) == request.header["registration_digest"] as? String else { throw DeliveryError.invalid }
    let (representation, publicBytes) = try checkedKeyRecord(raw, checked)
    guard publicBytes == request.publicKey.x963Representation else { throw DeliveryError.invalid }
    return representation
}
final class ReviewSigningController: NSObject, NSApplicationDelegate, NSWindowDelegate {
    let request: ReviewSigningRequest
    let representation: Data
    let context = LAContext()
    var gate: KeyPreparationGate
    var response: Data?
    var pendingStop: (String, String)?
    var window: NSWindow!
    var button: NSButton!
    var timer: Timer?
    let content: String
    init(_ request: ReviewSigningRequest, _ deadline: Double) throws {
        try request.fresh()
        self.request = request
        self.representation = try reviewKeyMaterial(request)
        try request.fresh()
        let remaining = request.operation["action"] as? String == "initialize-project"
            ? initialSigningAllowance(request.expiresAt, deadline, continuousNow(), Date().timeIntervalSince1970)
            : min(90, deadline - continuousNow() - 1, request.expiresAt - Date().timeIntervalSince1970)
        guard remaining > 0 else { throw DeliveryError.timeout }
        self.gate = KeyPreparationGate(deadline: continuousNow() + remaining)
        if request.operation["action"] as? String == "initialize-project" {
            guard let seed = request.operation["seed"] as? [String: Any],
                  let association = request.operation["association"] as? [String: Any],
                  let source = association["source"] as? [String: Any] else { throw DeliveryError.invalid }
            let detail = try JSONSerialization.data(withJSONObject: request.review,
                options: [.sortedKeys, .prettyPrinted, .withoutEscapingSlashes])
            self.content = visibleReviewText("""
            초기 프로젝트 검토의 기기 서명을 확인합니다 (합성 검증).
            이 동작은 프로젝트를 확정하거나 연구 기록·원고를 저장하지 않습니다.

            대상: \(request.keyRequest["project_id"]!) · 프로젝트 초기 상태
            등록된 로컬 연결: \(request.enrollment!.id)
            대상 저장소: \(try request.enrollment!.directory)/protected
            제목: \(initialQuoted(seed["paper_title"] as? String ?? ""))
            이미 작성한 중심 주장 (아직 검증되지 않음):
                \((seed["claim_statement"] as? String ?? "").replacingOccurrences(of: "\n", with: "\n    "))

            논문 위치: \(initialDisplayedPath(source["root"]))
            원고: \(initialDisplayedPath(source["manuscript"]))
            별도 연구 저장 위치: \(initialDisplayedPath(association["workspace"]))
            기록할 초기 이력: 근거 0 · 연산 0
            초기 상태 식별값: \(request.operation["initial_head"] ?? "")
            원고 식별값: \(source["source_digest"] ?? "")
            검토 식별값: \(request.header["review_digest"]!)

            원고 바이트와 연결 위치는 앱과 네이티브 역할에서 다시 확인합니다. 과학적 원본 확인이나 연구 승인은 성립하지 않습니다.
            ‘이 검토에 서명’을 누르면 macOS 본인 확인을 요청합니다.
            제목과 중심 주장을 다시 작성할 필요는 없습니다. 취소·만료 시 성공하지 않습니다.

            전체 초기 검토 내용:
            \(String(decoding: detail, as: UTF8.self))
            """)
        } else {
        guard let effect = request.operation["effect"] as? [String: Any],
              let judgment = effect["judgment"] as? [String: Any],
              let text = judgment["text"] as? String, let reason = judgment["rationale"] as? String,
              let assessment = request.review["assessment"] as? [String: Any],
              let decision = request.review["decision"] as? [String: Any] else { throw DeliveryError.invalid }
        let detail = try JSONSerialization.data(withJSONObject: request.review,
            options: [.sortedKeys, .prettyPrinted, .withoutEscapingSlashes])
        let action = request.operation["action"] as? String == "apply-selected-merge" ? "선택한 논증 변경 병합" : "해석 기록"
        let localBinding: String
        if let enrolled = request.enrollment {
            localBinding = "등록된 로컬 연결: \(enrolled.id)\n대상 저장소: \(try enrolled.directory)/protected"
        } else { localBinding = "미등록 합성 키: 연구 승인 권한 없음" }
        let originBinding = request.review["origin_registry_digest"] == nil ? "" :
            "선택에서 제외된 초안 이력은 식별값으로 결합되어 있습니다. 그 이력의 내용과 출처는 이 창에서 확인되지 않습니다."
        self.content = visibleReviewText("""
        정확한 연구 검토의 기기 서명을 확인합니다 (합성 검증).
        이 동작은 연구 기록을 확정하거나 원고를 수정하지 않습니다.

        대상: \(request.keyRequest["project_id"]!) · \(action)
        \(localBinding)
        \(originBinding)
        연구자의 판단:
        \(text)

        이미 작성한 이유:
        \(reason)

        설명 처리: \(decision["disposition"] ?? "")
        이해 부채: \(decision["understanding_debt"] ?? "") (실제 수용 시에만 적용)
        AI 영향: \(nativeFalse(assessment["ai_influenced"]) ? "없음" : "있음")
        검토 식별값: \(request.header["review_digest"]!)
        원고 식별값: \(request.review["manuscript_digest"] ?? "")

        아래 전체 내용에는 선택·필수·제외 변경, 출처와 기여 이력,
        연구 상태, 설명 답변/보류가 포함됩니다. 다른 내용에는 서명하지 않습니다.
        ‘이 검토에 서명’을 누르면 macOS 본인 확인을 요청합니다.
        취소·만료·변경 시 성공하지 않습니다. 새 이유나 설명을 다시 작성할 필요는 없습니다.

        전체 검토 내용:
        \(String(decoding: detail, as: UTF8.self))
        """)
        }
        super.init()
        context.interactionNotAllowed = true
        context.touchIDAuthenticationAllowableReuseDuration = 0
    }
    var timely: Bool {
        continuousNow() < gate.deadline && Date().timeIntervalSince1970 >= request.sealedAt && Date().timeIntervalSince1970 < request.expiresAt
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 850, height: 650),
                          styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: false)
        window.title = "ClaimBranch · 연구 검토 서명 (합성 검증)"; window.delegate = self
        let scroll = NSScrollView(frame: NSRect(x: 20, y: 85, width: 810, height: 545))
        scroll.autoresizingMask = [.width, .height]; scroll.hasVerticalScroller = true
        let text = NSTextView(frame: scroll.bounds)
        text.isEditable = false; text.isSelectable = true; text.isVerticallyResizable = true
        text.autoresizingMask = [.width]; text.textContainer?.widthTracksTextView = true
        text.textContainer?.containerSize = NSSize(width: 810, height: CGFloat.greatestFiniteMagnitude)
        text.font = NSFont.systemFont(ofSize: 14); text.string = content
        scroll.documentView = text; window.contentView?.addSubview(scroll)
        button = NSButton(title: "이 검토에 서명", target: self, action: #selector(approve))
        button.frame = NSRect(x: 515, y: 25, width: 175, height: 40); button.bezelStyle = .rounded
        let cancel = NSButton(title: "취소", target: self, action: #selector(cancelReview))
        cancel.frame = NSRect(x: 700, y: 25, width: 130, height: 40); cancel.bezelStyle = .rounded
        window.contentView?.addSubview(button); window.contentView?.addSubview(cancel)
        window.center(); window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
        timer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] _ in
            if let self, !self.timely { self.stop("expired", "deadline") }
        }
        RunLoop.main.add(timer!, forMode: .common)
    }
    @objc func approve() {
        guard timely else { stop("expired", "deadline"); return }
        guard gate.begin(continuousNow()) else { return }
        button.isEnabled = false; context.interactionNotAllowed = false
        context.evaluatePolicy(.deviceOwnerAuthentication, localizedReason: "ClaimBranch에 표시된 정확한 합성 연구 검토에 서명") { [self] success, error in
            DispatchQueue.main.async { [self] in
                if let pendingStop {
                    let result = resolvedKeyStop(pendingStop.0, pendingStop.1, userCancelledKeyAuthentication(error))
                    end(try? encoded(["status": result.0, "stop_source": result.1])); return
                }
                guard gate.phase == .authenticating else { return }
                guard timely else { stop("expired", "deadline"); return }
                guard success, error == nil else {
                    if cancelledKeyAuthentication(error) { stop("cancelled", "os-authentication") }
                    else { end(nil) }
                    return
                }
                guard gate.authenticated(true, continuousNow()) else { stop("expired", "deadline"); return }
                context.interactionNotAllowed = true
                DispatchQueue.global(qos: .userInitiated).async { [self] in
                    let result = Result { () throws -> Data in
                        try request.fresh()
                        guard try reviewKeyMaterial(request) == representation else { throw DeliveryError.invalid }
                        let key = try SecureEnclave.P256.Signing.PrivateKey(dataRepresentation: representation, authenticationContext: context)
                        guard key.publicKey.x963Representation == request.publicKey.x963Representation else { throw DeliveryError.invalid }
                        let signature = try key.signature(for: request.message)
                        guard try reviewKeyMaterial(request) == representation else { throw DeliveryError.invalid }
                        return try encoded(["status": "signed-unaccepted-review", "signature_der": signature.derRepresentation.base64EncodedString()])
                    }
                    DispatchQueue.main.async { [self] in
                        guard gate.phase == .generating else { return }
                        guard timely else { stop("expired", "deadline"); return }
                        do {
                            let reply = try result.get()
                            _ = try request.verifiedReply(reply)
                            end(reply)
                        } catch { end(nil) }
                    }
                }
            }
        }
    }
    func end(_ reply: Data?) {
        // The terminal gate also covers errors; output stays confined to the
        // already authenticated socket, never stdout or a persistent file.
        _ = gate.stop(); response = reply
        context.invalidate(); timer?.invalidate(); window?.orderOut(nil)
        NSApp.stop(nil)
        if let event = NSEvent.otherEvent(with: .applicationDefined, location: .zero,
            modifierFlags: [], timestamp: 0, windowNumber: 0, context: nil, subtype: 0, data1: 0, data2: 0) {
            NSApp.postEvent(event, atStart: true)
        }
    }
    func stop(_ status: String, _ source: String) {
        let awaiting = gate.phase == .authenticating
        guard gate.stop() else { return }
        pendingStop = (status, source); context.invalidate(); timer?.invalidate(); button?.isEnabled = false
        if awaiting && source != "os-authentication" {
            DispatchQueue.main.asyncAfter(deadline: .now() + 1) { [self] in
                if response == nil { end(try? encoded(["status": status, "stop_source": source])) }
            }
        } else { end(try? encoded(["status": status, "stop_source": source])) }
    }
    @objc func cancelReview() { stop("cancelled", "review-window") }
    func windowShouldClose(_ sender: NSWindow) -> Bool { cancelReview(); return false }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply { cancelReview(); return .terminateCancel }
}
func reviewAndSign(_ request: ReviewSigningRequest, _ deadline: Double) throws -> Data {
    guard freopen("/dev/null", "w", stderr) != nil else { throw DeliveryError.io }
    let controller = try ReviewSigningController(request, deadline)
    let app = NSApplication.shared; app.delegate = controller
    withExtendedLifetime(controller) { app.run() }
    guard let reply = controller.response else { throw DeliveryError.invalid }
    return reply
}

#endif

// CLAIMBRANCH_ENROLLMENT_SUPPORT

do {
    umask(0o077)
#if CLAIMBRANCH_BROKER
    if CommandLine.arguments.count == 3, CommandLine.arguments[1] == "enrollment-sweep" {
        FileHandle.standardOutput.write(try encoded(sweepEnrollment(CommandLine.arguments[2])))
        exit(0)
    } else if CommandLine.arguments.count == 3, CommandLine.arguments[1] == "revoke-enrollment" {
        guard freopen("/dev/null", "w", stderr) != nil else { throw DeliveryError.io }
        let controller = try EnrollmentController(revoking: CommandLine.arguments[2])
        let app = NSApplication.shared; app.delegate = controller
        withExtendedLifetime(controller) { app.run() }
        throw DeliveryError.invalid
    } else if CommandLine.arguments == [CommandLine.arguments[0], "enroll-project"] {
        let raw = try inputReview(continuousNow() + 8, 8192)
        guard freopen("/dev/null", "w", stderr) != nil else { throw DeliveryError.io }
        let controller = try EnrollmentController(raw)
        let app = NSApplication.shared; app.delegate = controller
        withExtendedLifetime(controller) { app.run() }
        throw DeliveryError.invalid
    } else if CommandLine.arguments == [CommandLine.arguments[0], "prepare-key"] {
        let raw = try inputReview(continuousNow() + 8)
        // AppKit/IME can emit unrelated framework diagnostics. Exit status and
        // closed stdout remain the protocol; never forward framework messages.
        guard freopen("/dev/null", "w", stderr) != nil else { throw DeliveryError.io }
        let controller = try KeyPreparationController(raw)
        let app = NSApplication.shared
        app.delegate = controller
        withExtendedLifetime(controller) { app.run() }
        throw DeliveryError.invalid
    } else if CommandLine.arguments.count == 3, CommandLine.arguments[1] == "reopen-key" {
        try reopenKey(inputReview(continuousNow() + 8), CommandLine.arguments[2])
    }
#endif
    let value: [String: Any]
    if CommandLine.arguments.count == 3, CommandLine.arguments[1] == "enrollment-status" {
        value = try loadEnrollment(CommandLine.arguments[2]).status()
    } else if CommandLine.arguments == [CommandLine.arguments[0], "check"] {
        guard let checked = inspect() else { throw DeliveryError.invalid }
        value = checked
    } else if CommandLine.arguments.count > 1 && ["sign-review", "receive-signed-review", "sign-enrolled-review", "receive-enrolled-review"].contains(CommandLine.arguments[1]) {
        value = try signingResult()
    } else {
        value = try deliveryResult()
    }
    let data = try encoded(value)
    FileHandle.standardOutput.write(data)
} catch {
    fputs("Native runtime operation failed; no authority was granted.\n", stderr)
    exit(2)
}
