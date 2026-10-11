// Local trust comes from native foreground creation in this fixed namespace,
// never from an imported self-signature. Unrestricted same-user code is outside
// this confined-worker boundary. No accepted scientific operation is written.
let enrollmentPurpose = Data("ClaimBranch local enrollment v1\n".utf8)
let revocationPurpose = Data("ClaimBranch local enrollment revocation v1\n".utf8)
let enrollmentFields: Set<String> = ["schema", "local_id", "project_id", "runtime_directory", "runtime_pin",
    "broker_hash", "gateway_hash", "worker_directory", "worker_pin", "worker_hash", "key_directory",
    "key_identity", "registration_digest", "public_key_x963", "protected_identity"]

func enrollmentHome() throws -> String {
    var user = passwd(), found: UnsafeMutablePointer<passwd>?
    var buffer = [CChar](repeating: 0, count: 16384)
    guard getpwuid_r(geteuid(), &user, &buffer, buffer.count, &found) == 0,
          found != nil, let home = user.pw_dir else { throw DeliveryError.invalid }
    return String(cString: home)
}
func enrollmentRoot() throws -> String {
    try enrollmentHome() + "/Library/Application Support/ClaimBranch/enrollments-v1"
}
func localDirectory(_ path: String, _ privateMode: Bool = true) throws -> Int32 {
    guard path.hasPrefix("/"), !path.contains("\0"), path.utf8.count <= 4096,
          let resolved = realpath(path, nil) else { throw DeliveryError.invalid }
    defer { free(resolved) }
    // Foundation rewrites /private/var to /var on this host; use the same POSIX
    // canonical path as the Python owner without accepting linked components.
    guard String(cString: resolved) == path else { throw DeliveryError.invalid }
    var ancestor = URL(fileURLWithPath: path)
    while true {
        var info = stat()
        guard lstat(ancestor.path, &info) == 0, info.st_mode & S_IFMT == S_IFDIR,
              [uid_t(0), geteuid()].contains(info.st_uid),
              (info.st_mode & 0o022 == 0 || (info.st_uid == 0 && info.st_mode & S_ISVTX != 0)),
              !FileManager.default.fileExists(atPath: ancestor.appendingPathComponent(".git").path),
              !(FileManager.default.fileExists(atPath: ancestor.appendingPathComponent("HEAD").path) &&
                FileManager.default.fileExists(atPath: ancestor.appendingPathComponent("objects").path) &&
                FileManager.default.fileExists(atPath: ancestor.appendingPathComponent("refs").path)) else { throw DeliveryError.invalid }
        if ancestor.path == "/" { break }
        ancestor.deleteLastPathComponent()
    }
    let fd = open(path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
    guard fd >= 0 else { throw DeliveryError.io }
    var info = stat()
    guard fstat(fd, &info) == 0, info.st_uid == geteuid(),
          !privateMode || info.st_mode & 0o777 == 0o700 else { close(fd); throw DeliveryError.invalid }
    return fd
}
func localIdentity(_ fd: Int32) throws -> String {
    var info = stat()
    guard fstat(fd, &info) == 0 else { throw DeliveryError.io }
    return "\(info.st_dev):\(info.st_ino):\(info.st_birthtimespec.tv_sec):\(info.st_birthtimespec.tv_nsec)"
}
func localRead(_ path: String, _ mode: mode_t = 0o600, _ limit: Int = 65536) throws -> Data {
    let parent = try localDirectory(URL(fileURLWithPath: path).deletingLastPathComponent().path)
    defer { close(parent) }
    let name = URL(fileURLWithPath: path).lastPathComponent
    let fd = openat(parent, name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
    guard fd >= 0 else { throw DeliveryError.io }
    defer { close(fd) }
    var a = stat(), b = stat(), c = stat()
    guard fstat(fd, &a) == 0, a.st_mode & S_IFMT == S_IFREG, a.st_mode & 0o777 == mode,
          a.st_uid == geteuid(), a.st_nlink == 1, a.st_size > 0, a.st_size <= limit else { throw DeliveryError.invalid }
    let bytes = try FileHandle(fileDescriptor: fd, closeOnDealloc: false).read(upToCount: limit + 1) ?? Data()
    guard bytes.count == a.st_size, fstat(fd, &b) == 0, fstatat(parent, name, &c, AT_SYMLINK_NOFOLLOW) == 0,
          sameKeyFile(a, b), sameKeyFile(b, c) else { throw DeliveryError.invalid }
    return bytes
}
func localCreate(_ directory: Int32, _ name: String, _ raw: Data) throws {
    let fd = openat(directory, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
    guard fd >= 0 else { throw DeliveryError.io }
    defer { close(fd) }
    guard fchmod(fd, 0o600) == 0 else { throw DeliveryError.io }
    try FileHandle(fileDescriptor: fd, closeOnDealloc: false).write(contentsOf: raw)
    guard fsync(fd) == 0, fsync(directory) == 0 else { throw DeliveryError.io }
}
func publishEnrollment(_ directory: Int32, _ raw: Data, _ mayCommit: () -> Bool) throws {
    try localCreate(directory, "pending", raw)
    guard mayCommit(), renameatx_np(directory, "pending", directory, "entry.json", UInt32(RENAME_EXCL)) == 0,
          fsync(directory) == 0 else { throw DeliveryError.io }
}
func custodyScratch(_ name: String) -> Bool {
    name.range(of: "^\\.cb-denial-[0-9a-f]{64}-(canary|renamed|created)\\z", options: .regularExpression) != nil
}
func localInventory(_ path: String) throws -> Set<String> {
    let fd = try localDirectory(path); defer { close(fd) }
    let names = try FileManager.default.contentsOfDirectory(atPath: path)
    guard names.count <= 4096 else { throw DeliveryError.invalid }
    var kept = Set<String>()
    for name in names {
        if custodyScratch(name) {
            var info = stat()
            if fstatat(fd, name, &info, AT_SYMLINK_NOFOLLOW) != 0 {
                if errno == ENOENT { continue } // Concurrent diagnostic cleanup.
                throw DeliveryError.io
            }
            guard info.st_mode & S_IFMT == S_IFREG,
                  info.st_uid == geteuid(), info.st_mode & 0o077 == 0,
                  info.st_nlink == 1, info.st_size <= 128 else { throw DeliveryError.invalid }
        } else { kept.insert(name) }
    }
    return kept
}
// Read-only initial target precondition. Enrollment remains the source of the
// path/identity/id; a caller's empty directory or imported binding is not trust.
func initialProtectedEmpty(_ path: String, _ identity: String, _ id: String) throws {
    guard hexText(id,64) else { throw DeliveryError.invalid }
    let fd = try localDirectory(path); defer { close(fd) }
    guard try localIdentity(fd) == identity,
          try localInventory(path) == ["binding"],
          try localRead(path + "/binding",0o600,64) == Data(id.utf8),
          try localInventory(path) == ["binding"] else { throw DeliveryError.invalid }
    let current = try localDirectory(path); defer { close(current) }
    guard try localIdentity(current) == identity else { throw DeliveryError.invalid }
}
func enrollmentWriter() throws -> Int32 {
    let root = try localDirectory(enrollmentRoot()); defer { close(root) }
    let fd = openat(root, "writer.lock", O_RDWR | O_CREAT | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC, 0o600)
    guard fd >= 0 else { throw DeliveryError.io }
    var info = stat()
    guard fstat(fd, &info) == 0, info.st_uid == geteuid(), info.st_mode & S_IFMT == S_IFREG,
          info.st_mode & 0o777 == 0o600, info.st_nlink == 1, info.st_size == 0,
          flock(fd, LOCK_EX | LOCK_NB) == 0 else { close(fd); throw DeliveryError.io }
    return fd
}
func localObject(_ raw: Data) throws -> [String: Any] {
    guard raw.count <= 65536, let value = try JSONSerialization.jsonObject(with: raw) as? [String: Any],
          finiteJSON(value), try encoded(value) == raw else { throw DeliveryError.invalid }
    return value
}
func localCode(_ path: String, _ identifier: String, _ sandboxed: Bool = false) throws -> String {
    var code: SecStaticCode?, requirement: SecRequirement?, information: CFDictionary?
    guard SecStaticCodeCreateWithPath(URL(fileURLWithPath: path) as CFURL, [], &code) == errSecSuccess, let code,
          SecRequirementCreateWithString("identifier \"\(identifier)\"" as CFString, [], &requirement) == errSecSuccess,
          SecStaticCodeCheckValidity(code, [], requirement) == errSecSuccess,
          SecCodeCopySigningInformation(code, SecCSFlags(rawValue: kSecCSSigningInformation), &information) == errSecSuccess,
          let fields = information as? [String: Any], let unique = fields[kSecCodeInfoUnique as String] as? Data,
          unique.count == 20, let flags = fields[kSecCodeInfoFlags as String] as? NSNumber,
          flags.uint32Value & 0x10000 != 0 else { throw DeliveryError.invalid }
    if sandboxed {
        guard let rights = fields[kSecCodeInfoEntitlementsDict as String] as? [String: Any],
              Set(rights.keys) == ["com.apple.security.app-sandbox"],
              let enabled = rights["com.apple.security.app-sandbox"] as? NSNumber,
              CFGetTypeID(enabled) == CFBooleanGetTypeID(), enabled.boolValue else { throw DeliveryError.invalid }
    } else if let rights = fields[kSecCodeInfoEntitlementsDict as String] as? [String: Any], !rights.isEmpty {
        throw DeliveryError.invalid
    }
    return unique.map { String(format: "%02x", $0) }.joined()
}
func localRuntime(_ path: String) throws -> (String, String, String) {
    let raw = try localRead(path + "/runtime.json", 0o600, 8192), value = try localObject(raw)
    guard Set(value.keys) == ["schema", "source_sha256", "broker", "gateway", "authorization_verified", "protected_acceptance_available"],
          value["schema"] as? String == "claimbranch.mac-runtime-build/v1",
          nativeFalse(value["authorization_verified"]), nativeFalse(value["protected_acceptance_available"]),
          Set(try FileManager.default.contentsOfDirectory(atPath: path)) == ["runtime.json", "broker", "gateway"] else { throw DeliveryError.invalid }
    var hashes = [String]()
    for name in ["broker", "gateway"] {
        guard let entry = value[name] as? [String: String], Set(entry.keys) == ["binary_sha256", "code_hash"] else { throw DeliveryError.invalid }
        let bytes = try localRead(path + "/" + name, 0o700, 4 * 1024 * 1024)
        let code = try localCode(path + "/" + name, "org.claimbranch.local-runtime." + name)
        guard entry["binary_sha256"] == hashHex(bytes), entry["code_hash"] == code else { throw DeliveryError.invalid }
        hashes.append(code)
    }
    guard let own = inspect(), own["code_hash"] as? String == hashes[role == "broker" ? 0 : 1] else { throw DeliveryError.invalid }
    return (hashHex(raw), hashes[0], hashes[1])
}
func localWorker(_ path: String, _ pin: String) throws -> String {
    let raw = try localRead(path + "/worker.json", 0o600, 8192), value = try localObject(raw)
    let names: Set<String> = ["Worker.app/Contents/Info.plist", "Worker.app/Contents/MacOS/worker", "Worker.app/Contents/_CodeSignature/CodeResources"]
    guard hashHex(raw) == pin, Set(value.keys) == ["schema", "source_sha256", "code_hash", "files", "authorization_verified"],
          value["schema"] as? String == "claimbranch.proposal-worker-build/v1", nativeFalse(value["authorization_verified"]),
          let files = value["files"] as? [String: String], Set(files.keys) == names else { throw DeliveryError.invalid }
    for name in names {
        guard try hashHex(localRead(path + "/" + name, name.hasSuffix("/worker") ? 0o700 : 0o600, 4 * 1024 * 1024)) == files[name] else { throw DeliveryError.invalid }
    }
    let code = try localCode(path + "/Worker.app", "org.claimbranch.local-proposal-worker", true)
    guard value["code_hash"] as? String == code else { throw DeliveryError.invalid }
    return code
}
struct NativeEnrollment {
    let body: [String: String]
    let bytes: Data
    let keyRequest: [String: String]
    var id: String { body["local_id"]! }
    var directory: String { get throws { try enrollmentRoot() + "/" + id } }
    func accepts(_ header: [String: Any], _ key: [String: String]) -> Bool {
        header["local_id"] as? String == id && header["registration_digest"] as? String == body["registration_digest"] &&
        header["public_key_x963"] as? String == body["public_key_x963"] && key == keyRequest
    }
    func unchanged(forRevocation: Bool = false) throws {
        guard try loadEnrollment(id, forRevocation: forRevocation).bytes == bytes else { throw DeliveryError.invalid }
    }
    func status() throws -> [String: Any] {
        ["schema": "claimbranch.enrollment-status/v1", "status": "enrolled", "binding": body,
         "registry_directory": try directory, "entry_digest": hashHex(bytes),
         "enrollment_verified": true, "authorization_verified": false, "protected_acceptance_available": false]
    }
}
func enrollmentRecord(_ raw: Data, revoked: Bool = false) throws -> [String: String] {
    let value = try localObject(raw)
    guard Set(value.keys) == ["schema", "body", "signature_der"],
          value["schema"] as? String == (revoked ? "claimbranch.local-enrollment-revocation/v1" : "claimbranch.local-enrollment/v1"),
          let body = value["body"] as? [String: String], Set(body.keys) == enrollmentFields,
          body["schema"] == "claimbranch.local-enrollment-body/v1", hexText(body["local_id"]!, 64),
          let publicBytes = Data(base64Encoded: body["public_key_x963"]!), publicBytes.count == 65,
          let signatureText = value["signature_der"] as? String, let signature = Data(base64Encoded: signatureText),
          signature.base64EncodedString() == signatureText, (8...72).contains(signature.count),
          try P256.Signing.PublicKey(x963Representation: publicBytes).isValidSignature(
            P256.Signing.ECDSASignature(derRepresentation: signature), for: (revoked ? revocationPurpose : enrollmentPurpose) + encoded(body)) else { throw DeliveryError.invalid }
    return body
}
func loadEnrollment(_ id: String, forRevocation: Bool = false) throws -> NativeEnrollment {
    guard hexText(id, 64) else { throw DeliveryError.invalid }
    let root = try enrollmentRoot(), directory = root + "/" + id
    let rootFD = try localDirectory(root); defer { close(rootFD) }
    let dir = try localDirectory(directory); defer { close(dir) }
    let inventory = try localInventory(directory)
    guard !inventory.contains("revoked"), inventory == ["entry.json", "protected", "keys"] else { throw DeliveryError.invalid }
    let raw = try localRead(directory + "/entry.json"), body = try enrollmentRecord(raw)
    guard body["local_id"] == id, body["key_directory"] == directory + "/keys" else { throw DeliveryError.invalid }
    let protected = try localDirectory(directory + "/protected"); defer { close(protected) }
    guard try localIdentity(protected) == body["protected_identity"],
          try localRead(directory + "/protected/binding") == Data(id.utf8) else { throw DeliveryError.invalid }
    if !forRevocation {
        let runtime = try localRuntime(body["runtime_directory"]!)
        guard runtime.0 == body["runtime_pin"], runtime.1 == body["broker_hash"], runtime.2 == body["gateway_hash"],
              try localWorker(body["worker_directory"]!, body["worker_pin"]!) == body["worker_hash"] else { throw DeliveryError.invalid }
    }
    let keyDir = try localDirectory(body["key_directory"]!); defer { close(keyDir) }
    guard try localInventory(body["key_directory"]!) == [keyFile] else { throw DeliveryError.invalid }
    let keyRaw = try readKeyRecord(keyDir), record = try localObject(keyRaw)
    guard hashHex(keyRaw) == body["registration_digest"], try localIdentity(keyDir) == body["key_identity"],
          let keyBody = record["body"] as? [String: Any], let request = keyBody["request"] as? [String: String],
          request["project_id"] == body["project_id"] else { throw DeliveryError.invalid }
    let (representation, publicBytes) = try checkedKeyRecord(keyRaw, request)
    guard publicBytes.base64EncodedString() == body["public_key_x963"] else { throw DeliveryError.invalid }
    let context = LAContext(); context.interactionNotAllowed = true
    defer { context.invalidate() }
    let key = try SecureEnclave.P256.Signing.PrivateKey(dataRepresentation: representation, authenticationContext: context)
    guard key.publicKey.x963Representation == publicBytes else { throw DeliveryError.invalid }
    return NativeEnrollment(body: body, bytes: raw, keyRequest: request)
}

#if CLAIMBRANCH_BROKER
func sweepEnrollment(_ id: String) throws -> [String: Any] {
    let lock = try enrollmentWriter(); defer { close(lock) }
    let entry = try loadEnrollment(id), directory = try entry.directory
    for path in [directory, directory + "/keys", directory + "/protected"] {
        _ = try localInventory(path)
        let fd = try localDirectory(path); defer { close(fd) }
        for name in try FileManager.default.contentsOfDirectory(atPath: path) where custodyScratch(name) {
            guard unlinkat(fd, name, 0) == 0 else { throw DeliveryError.io }
        }
        guard fsync(fd) == 0 else { throw DeliveryError.io }
    }
    try entry.unchanged()
    return try entry.status()
}
func enrollmentRuntimeDirectory() throws -> String {
    // proc_info.h defines PROC_PIDPATHINFO_MAXSIZE as 4 * MAXPATHLEN (4096);
    // that compound C macro is not imported by this Swift SDK.
    var bytes = [CChar](repeating: 0, count: 4096)
    guard proc_pidpath(getpid(), &bytes, UInt32(bytes.count)) > 0 else { throw DeliveryError.invalid }
    return URL(fileURLWithPath: String(cString: bytes)).deletingLastPathComponent().path
}
func newEnrollmentID() throws -> String {
    var bytes = [UInt8](repeating: 0, count: 32)
    guard SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes) == errSecSuccess else { throw DeliveryError.invalid }
    return bytes.map { String(format: "%02x", $0) }.joined()
}
func prepareRegistry() throws -> String {
    let support = try enrollmentHome() + "/Library/Application Support"
    let parent = try localDirectory(support, false); defer { close(parent) }
    for suffix in ["ClaimBranch", "ClaimBranch/enrollments-v1"] {
        let path = support + "/" + suffix
        if mkdir(path, 0o700) != 0 && errno != EEXIST { throw DeliveryError.io }
        let checked = try localDirectory(path); defer { close(checked) }
        let enclosing = try localDirectory(URL(fileURLWithPath: path).deletingLastPathComponent().path, false)
        defer { close(enclosing) }
        guard fsync(checked) == 0, fsync(enclosing) == 0 else { throw DeliveryError.io }
    }
    return try enrollmentRoot()
}
final class EnrollmentController: NSObject, NSApplicationDelegate, NSWindowDelegate {
    let request: [String: String]
    var body: [String: String]
    let keyRaw: Data
    let representation: Data
    let publicBytes: Data
    let context = LAContext()
    var gate = KeyPreparationGate(deadline: continuousNow() + 90)
    var window: NSWindow!, button: NSButton!, timer: Timer?
    var pendingStop: (String, String)?
    var preparedDirectory: String?
    var writerLock: Int32 = -1
    var revoking: NativeEnrollment?
    init(_ raw: Data, revoking: NativeEnrollment? = nil) throws {
        guard raw.count <= 8192, let request = try JSONSerialization.jsonObject(with: raw) as? [String: String],
              Set(request.keys) == ["schema", "project_id", "key_directory", "registration_digest", "worker_directory", "worker_pin"],
              request["schema"] == "claimbranch.enrollment-request/v1", try encoded(request) == raw,
              hexText(request["registration_digest"]!, 64), hexText(request["worker_pin"]!, 64) else { throw DeliveryError.invalid }
        self.request = request
        let keyDir = try localDirectory(request["key_directory"]!); defer { close(keyDir) }
        let keyRaw = try readKeyRecord(keyDir), record = try localObject(keyRaw)
        guard hashHex(keyRaw) == request["registration_digest"], let keyBody = record["body"] as? [String: Any],
              let keyRequest = keyBody["request"] as? [String: String], keyRequest["project_id"] == request["project_id"] else { throw DeliveryError.invalid }
        let (representation, publicBytes) = try checkedKeyRecord(keyRaw, keyRequest)
        self.keyRaw = keyRaw; self.representation = representation; self.publicBytes = publicBytes
        let runtimePath = try enrollmentRuntimeDirectory(), runtime = try localRuntime(runtimePath)
        let worker: String
        if let revoking { worker = revoking.body["worker_hash"]! }
        else { worker = try localWorker(request["worker_directory"]!, request["worker_pin"]!) }
        body = ["schema": "claimbranch.local-enrollment-body/v1", "local_id": try newEnrollmentID(),
                "project_id": request["project_id"]!, "runtime_directory": runtimePath, "runtime_pin": runtime.0,
                "broker_hash": runtime.1, "gateway_hash": runtime.2,
                "worker_directory": request["worker_directory"]!, "worker_pin": request["worker_pin"]!, "worker_hash": worker,
                "key_directory": request["key_directory"]!, "key_identity": try localIdentity(keyDir),
                "registration_digest": request["registration_digest"]!, "public_key_x963": publicBytes.base64EncodedString(),
                "protected_identity": "pending-new-resource"]
        super.init()
        if let revoking { self.body = revoking.body; self.revoking = revoking }
        context.interactionNotAllowed = true
        context.touchIDAuthenticationAllowableReuseDuration = 0
    }
    convenience init(revoking id: String) throws {
        let entry = try loadEnrollment(id, forRevocation: true), body = entry.body
        try self.init(encoded(["schema": "claimbranch.enrollment-request/v1", "project_id": body["project_id"]!,
            "key_directory": body["key_directory"]!, "registration_digest": body["registration_digest"]!,
            "worker_directory": body["worker_directory"]!, "worker_pin": body["worker_pin"]!]), revoking: entry)
    }
    func recheck() throws {
        if let revoking { try revoking.unchanged(forRevocation: true); return }
        let runtime = try localRuntime(body["runtime_directory"]!)
        guard runtime.0 == body["runtime_pin"], runtime.1 == body["broker_hash"], runtime.2 == body["gateway_hash"],
              try localWorker(body["worker_directory"]!, body["worker_pin"]!) == body["worker_hash"] else { throw DeliveryError.invalid }
        let keyDir = try localDirectory(body["key_directory"]!); defer { close(keyDir) }
        guard try localIdentity(keyDir) == body["key_identity"], try readKeyRecord(keyDir) == keyRaw else { throw DeliveryError.invalid }
    }
    func reserve() throws {
        try recheck()
        let root = try prepareRegistry()
        writerLock = try enrollmentWriter()
        if let revoking {
            try revoking.unchanged(forRevocation: true); preparedDirectory = try revoking.directory; return
        }
        let entries = try FileManager.default.contentsOfDirectory(atPath: root).filter { $0 != "writer.lock" }
        guard entries.count <= 4096 else { throw DeliveryError.invalid }
        var established = 0
        for id in entries {
            guard hexText(id, 64) else { continue } // Foreign names are retained, never adopted.
            let entryDir = try localDirectory(root + "/" + id); defer { close(entryDir) }
            let inventory = try localInventory(root + "/" + id)
            if inventory != ["entry.json", "protected", "keys"] && inventory != ["entry.json", "protected", "keys", "revoked"] {
                continue // Retain indeterminate publication without granting trust.
            }
            var info = stat()
            if fstatat(entryDir, "entry.json", &info, AT_SYMLINK_NOFOLLOW) != 0 {
                guard errno == ENOENT else { throw DeliveryError.io }
                continue // Incomplete reservations are retained, never adopted.
            }
            let previous = try enrollmentRecord(localRead(root + "/" + id + "/entry.json"))
            guard previous["public_key_x963"] != body["public_key_x963"] else { throw DeliveryError.invalid }
            established += 1
        }
        guard established < 128 else { throw DeliveryError.invalid }
        let path = root + "/" + body["local_id"]!
        guard mkdir(path, 0o700) == 0 else { throw DeliveryError.io }
        preparedDirectory = path
        let dir = try localDirectory(path); defer { close(dir) }
        guard mkdirat(dir, "protected", 0o700) == 0 else { throw DeliveryError.io }
        let protected = try localDirectory(path + "/protected"); defer { close(protected) }
        body["protected_identity"] = try localIdentity(protected)
        try localCreate(protected, "binding", Data(body["local_id"]!.utf8))
        guard mkdirat(dir, "keys", 0o700) == 0 else { throw DeliveryError.io }
        let keys = try localDirectory(path + "/keys"); defer { close(keys) }
        try localCreate(keys, keyFile, keyRaw)
        body["key_directory"] = path + "/keys"
        body["key_identity"] = try localIdentity(keys)
        guard fsync(dir) == 0 else { throw DeliveryError.io }
    }
    func finish(_ value: [String: Any]) -> Never {
        context.invalidate(); timer?.invalidate()
        guard let bytes = try? encoded(value) else { exit(2) }
        FileHandle.standardOutput.write(bytes); exit(0)
    }
    func stop(_ status: String, _ source: String) {
        guard gate.phase != .terminal else { return }
        let authenticating = gate.phase == .authenticating
        _ = gate.stop(); context.invalidate(); timer?.invalidate()
        if preparedDirectory != nil { fail() }
        if authenticating && source != "os-authentication" {
            pendingStop = (status, source)
            DispatchQueue.main.asyncAfter(deadline: .now() + 1) { [self] in cancelled(status, source) }
        } else { cancelled(status, source) }
    }
    func cancelled(_ status: String, _ source: String) -> Never {
        finish(["schema": "claimbranch.enrollment-stop/v1", "status": status, "stop_source": source,
                "authorization_verified": false, "protected_acceptance_available": false])
    }
    func fail() -> Never {
        context.invalidate()
        fputs("Enrollment outcome indeterminate; inspect native registration before retrying.\n", stderr)
        exit(2)
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 760, height: 550), styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.title = revoking == nil ? "ClaimBranch · 프로젝트 승인 키 등록 (합성 프로젝트)" : "ClaimBranch · 로컬 승인 연결 해제"
        window.delegate = self
        let scroll = NSScrollView(frame: NSRect(x: 20, y: 80, width: 720, height: 450)); scroll.hasVerticalScroller = true
        let text = NSTextView(frame: scroll.bounds); text.isEditable = false; text.isSelectable = true
        text.isVerticallyResizable = true; text.autoresizingMask = [.width]; text.textContainer?.widthTracksTextView = true
        text.font = NSFont.systemFont(ofSize: 14)
        let registrationText = """
        이 기기에서 아래 프로젝트의 승인 키와 실행 코드를 등록합니다.
        새로운 빈 보호 저장소를 만듭니다. 기존 연구·원고는 변경하지 않습니다.
        승인 키의 기기 전용 암호화 표현도 새 등록 폴더에 보관합니다. 원본 후보 파일은 남깁니다.
        가져온 파일의 서명만으로는 이 등록을 대신할 수 없습니다.

        프로젝트: \(body["project_id"]!)
        공개키 지문: \(hashHex(publicBytes))
        새 로컬 연결: \(body["local_id"]!)
        새 저장 위치: \((try? enrollmentRoot()) ?? "unavailable")/\(body["local_id"]!)/protected
        승인 프로그램: \(body["broker_hash"]!)
        검증 프로그램: \(body["gateway_hash"]!)
        제안 처리기: \(body["worker_hash"]!)

        코드·키·저장소가 달라지면 재개를 거부합니다. 자동 재등록하지 않습니다.
        등록은 연구 판단에 대한 승인이 아닙니다. 실제 수용과 저장은 아직 비활성입니다.
        ‘이 연결 등록’을 누르면 이번 등록에 대해 macOS 본인 확인을 요청합니다.
        취소하면 등록하지 않습니다. 중단된 예약은 덮어쓰거나 신뢰하지 않습니다.
        """
        let revocationText = """
        이 로컬 프로젝트의 승인 연결을 해제합니다.
        프로젝트: \(body["project_id"]!)
        로컬 연결: \(body["local_id"]!)
        공개키 지문: \(hashHex(publicBytes))

        기존 기록과 키 파일은 남습니다. 이 연결을 사용하는 새 서명은 거부합니다.
        이전 연구 판단이나 서명을 지우거나 다시 쓰지 않습니다.
        이 동작은 되돌리지 않습니다. 계속 사용하려면 별도의 새 등록이 필요합니다.
        ‘이 연결 해제’를 누르면 macOS 본인 확인을 요청합니다. 취소하면 변경하지 않습니다.
        """
        text.string = visibleReviewText(revoking == nil ? registrationText : revocationText)
        scroll.documentView = text; window.contentView?.addSubview(scroll)
        button = NSButton(title: revoking == nil ? "이 연결 등록" : "이 연결 해제", target: self, action: #selector(enroll)); button.bezelStyle = .rounded
        button.frame = NSRect(x: 450, y: 20, width: 145, height: 40); window.contentView?.addSubview(button)
        let cancel = NSButton(title: "취소", target: self, action: #selector(cancelReview)); cancel.bezelStyle = .rounded
        cancel.frame = NSRect(x: 605, y: 20, width: 130, height: 40); window.contentView?.addSubview(cancel)
        window.center(); window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
        timer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] _ in
            if let self, continuousNow() >= gate.deadline { stop("expired", "deadline") }
        }
        RunLoop.main.add(timer!, forMode: .common)
    }
    @objc func enroll() {
        guard gate.begin(continuousNow()) else { return }
        button.isEnabled = false; context.interactionNotAllowed = false
        context.evaluatePolicy(.deviceOwnerAuthentication, localizedReason: revoking == nil ? "ClaimBranch의 이 합성 프로젝트 승인 키와 실행 코드 등록" : "ClaimBranch의 이 프로젝트 승인 연결 해제") { [self] success, error in
            DispatchQueue.main.async { [self] in
                if let pendingStop {
                    let stop = resolvedKeyStop(pendingStop.0, pendingStop.1, userCancelledKeyAuthentication(error))
                    cancelled(stop.0, stop.1)
                }
                guard gate.phase == .authenticating else { return }
                guard continuousNow() < gate.deadline else { stop("expired", "deadline"); return }
                guard success, error == nil else {
                    if cancelledKeyAuthentication(error) { stop("cancelled", "os-authentication") } else { fail() }
                    return
                }
                guard gate.authenticated(true, continuousNow()) else { fail() }
                context.interactionNotAllowed = true
                do { try reserve() } catch { fail() }
                let statement = body
                DispatchQueue.global(qos: .userInitiated).async { [self] in
                    let result = Result { () throws -> Data in
                        let key = try SecureEnclave.P256.Signing.PrivateKey(dataRepresentation: representation, authenticationContext: context)
                        guard key.publicKey.x963Representation == publicBytes else { throw DeliveryError.invalid }
                        let signature = try key.signature(for: (revoking == nil ? enrollmentPurpose : revocationPurpose) + encoded(statement))
                        return try encoded(["schema": revoking == nil ? "claimbranch.local-enrollment/v1" : "claimbranch.local-enrollment-revocation/v1", "body": statement,
                                            "signature_der": signature.derRepresentation.base64EncodedString()])
                    }
                    DispatchQueue.main.async { [self] in complete(result) }
                }
            }
        }
    }
    func complete(_ result: Result<Data, Error>) {
        guard gate.mayPersist(continuousNow()), let path = preparedDirectory else { fail() }
        do {
            let raw = try result.get(); guard try enrollmentRecord(raw, revoked: revoking != nil) == body else { throw DeliveryError.invalid }
            try recheck()
            let dir = try localDirectory(path); defer { close(dir) }
            if let revoking {
                try revoking.unchanged(forRevocation: true)
                try localCreate(dir, "revoked", raw)
                guard gate.stop() else { throw DeliveryError.invalid }
                finish(["schema": "claimbranch.enrollment-revoked/v1", "status": "revoked", "local_id": revoking.id,
                        "authorization_verified": false, "protected_acceptance_available": false])
            }
            try publishEnrollment(dir, raw) { gate.mayPersist(continuousNow()) }
            let root = try localDirectory(enrollmentRoot()); defer { close(root) }
            guard fsync(root) == 0 else { throw DeliveryError.io }
            let enrolled = try loadEnrollment(body["local_id"]!)
            guard enrolled.bytes == raw, gate.stop() else { throw DeliveryError.invalid }
            finish(try enrolled.status())
        } catch { fail() }
    }
    @objc func cancelReview() { stop("cancelled", "review-window") }
    func windowShouldClose(_ sender: NSWindow) -> Bool { cancelReview(); return false }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply { cancelReview(); return .terminateCancel }
}
#endif
