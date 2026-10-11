// Finite proposal ingress. No provider launcher, tool execution or accepted writer.
import Foundation
import Security
import CryptoKit
import Darwin

let identity = "org.claimbranch.local-proposal-worker"
enum WorkerError: Error { case invalid, io }
func encoded(_ value: Any) throws -> Data {
    try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .withoutEscapingSlashes])
}
func hash(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
func inspect() throws -> [String: Any] {
    var code: SecCode?
    guard SecCodeCopySelf([], &code) == errSecSuccess, let code,
          SecCodeCheckValidity(code, [], nil) == errSecSuccess else { throw WorkerError.invalid }
    var information: CFDictionary?
    guard SecCodeCopySigningInformation(unsafeBitCast(code, to: SecStaticCode.self),
              SecCSFlags(rawValue: kSecCSSigningInformation | kSecCSDynamicInformation), &information) == errSecSuccess,
          let fields = information as? [String: Any],
          fields[kSecCodeInfoIdentifier as String] as? String == identity,
          let unique = fields[kSecCodeInfoUnique as String] as? Data, unique.count == 20,
          let flags = fields[kSecCodeInfoFlags as String] as? NSNumber,
          let running = fields[kSecCodeInfoStatus as String] as? NSNumber,
          flags.uint32Value & 0x10000 != 0, running.uint32Value & 0x10000 != 0,
          let rights = fields[kSecCodeInfoEntitlementsDict as String] as? [String: Any],
          Set(rights.keys) == ["com.apple.security.app-sandbox"],
          let sandbox = rights["com.apple.security.app-sandbox"] as? NSNumber,
          CFGetTypeID(sandbox) == CFBooleanGetTypeID(), sandbox.boolValue else { throw WorkerError.invalid }
    return ["schema": "claimbranch.proposal-worker-check/v1", "identifier": identity,
            "code_hash": unique.map { String(format: "%02x", $0) }.joined(),
            "running_hardened": true, "sandbox_entitled": true, "authorization_verified": false]
}
func input() throws -> Data {
    var info = stat()
    guard fstat(STDIN_FILENO, &info) == 0, info.st_mode & S_IFMT == S_IFIFO else { throw WorkerError.invalid }
    var raw = Data()
    // Parent owns the wall-clock deadline and kills/reaps the entire child group.
    while true {
        var bytes = [UInt8](repeating: 0, count: 4096)
        let count = read(STDIN_FILENO, &bytes, bytes.count)
        if count < 0 && errno == EINTR { continue }
        guard count >= 0, raw.count + count <= 65536 else { throw WorkerError.invalid }
        if count == 0 { return raw }
        raw.append(contentsOf: bytes.prefix(count))
    }
}
func result(_ raw: Data) throws -> [String: Any] {
    guard let value = try JSONSerialization.jsonObject(with: raw) as? [String: Any],
          Set(value.keys) == ["schema", "status", "text"],
          value["schema"] as? String == "claimbranch.provider-result/v1",
          let status = value["status"] as? String, ["ok", "refused", "failed"].contains(status),
          try encoded(value) == raw else { throw WorkerError.invalid }
    if status == "ok" {
        guard let text = value["text"] as? String, text.utf8.count <= 16384,
              !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { throw WorkerError.invalid }
        // Python owns the canonical Unicode version. Preserve its exact bytes;
        // Foundation may know newer combining sequences than Python 3.13.
    } else if !(value["text"] is NSNull) { throw WorkerError.invalid }
    return ["schema": "claimbranch.proposal-worker-result/v1", "input_digest": hash(raw),
            "result": value, "authorization_verified": false]
}
func fileAccess(_ path: String, _ writing: Bool) -> [String: Any] {
    let fd = open(path, (writing ? O_WRONLY : O_RDONLY) | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
    let error = fd < 0 ? Int(errno) : 0
    if fd >= 0 { close(fd) } // Never read, truncate, or write diagnostic targets.
    return ["allowed": fd >= 0, "errno": error]
}
func connectAccess(_ address: UnsafePointer<sockaddr>, _ count: socklen_t, _ family: Int32) -> [String: Any] {
    let fd = socket(family, SOCK_STREAM, 0)
    guard fd >= 0 else { return ["allowed": false, "errno": Int(errno)] }
    defer { close(fd) }
    guard fcntl(fd, F_SETFL, O_NONBLOCK) == 0 else { throwlessFailure() }
    let result = connect(fd, address, count)
    var error = result == 0 ? 0 : errno
    if error == EINPROGRESS {
        var waiting = pollfd(fd: fd, events: Int16(POLLOUT), revents: 0)
        if poll(&waiting, 1, 1000) > 0 {
            var size = socklen_t(MemoryLayout<Int32>.size)
            if getsockopt(fd, SOL_SOCKET, SO_ERROR, &error, &size) != 0 { error = errno }
        } else { error = ETIMEDOUT }
    }
    return ["allowed": error == 0, "errno": Int(error)]
}
func throwlessFailure() -> Never { exit(2) }
func boundary(_ raw: Data) throws -> [String: Any] {
    guard raw.count <= 8192, let value = try JSONSerialization.jsonObject(with: raw) as? [String: Any],
          Set(value.keys) == ["schema", "files", "socket", "port", "nonce"],
          value["schema"] as? String == "claimbranch.worker-boundary/v1",
          let files = value["files"] as? [String], (1...8).contains(files.count),
          files.allSatisfy({ $0.hasPrefix("/") && !$0.contains("\0") && $0.utf8.count <= 1024 }),
          let path = value["socket"] as? String, path.hasPrefix("/"), !path.contains("\0"), path.utf8.count < 104,
          let number = value["port"] as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID(),
          (1...65535).contains(number.intValue), number.doubleValue == Double(number.intValue),
          let nonce = value["nonce"] as? String, nonce.utf8.count == 64,
          nonce.allSatisfy({ "0123456789abcdef".contains($0) }), try encoded(value) == raw else { throw WorkerError.invalid }
    var local = sockaddr_un()
    local.sun_family = sa_family_t(AF_UNIX)
    local.sun_len = UInt8(MemoryLayout<sockaddr_un>.size)
    let bytes = Array(path.utf8) + [0]
    withUnsafeMutableBytes(of: &local.sun_path) { $0.copyBytes(from: bytes) }
    let ipc = withUnsafePointer(to: &local) { $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
        connectAccess($0, socklen_t(MemoryLayout<sockaddr_un>.size), AF_UNIX)
    } }
    var network = sockaddr_in()
    network.sin_len = UInt8(MemoryLayout<sockaddr_in>.size); network.sin_family = sa_family_t(AF_INET)
    network.sin_port = UInt16(number.intValue).bigEndian; network.sin_addr.s_addr = inet_addr("127.0.0.1")
    let tcp = withUnsafePointer(to: &network) { $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
        connectAccess($0, socklen_t(MemoryLayout<sockaddr_in>.size), AF_INET)
    } }
    return ["schema": "claimbranch.worker-boundary-result/v1", "nonce": nonce,
            "files": files.map { ["read": fileAccess($0, false), "write": fileAccess($0, true)] },
            "socket": ipc, "network": tcp, "authorization_verified": false]
}
func custody(_ raw: Data) throws -> [String: Any] {
    guard raw.count <= 16384, let value = try JSONSerialization.jsonObject(with: raw) as? [String: Any],
          Set(value.keys) == ["schema", "files", "nonce"], value["schema"] as? String == "claimbranch.worker-custody/v1",
          let files = value["files"] as? [String], files.count == 3,
          files.allSatisfy({ $0.hasPrefix("/") && !$0.contains("\0") && $0.utf8.count <= 4096 }),
          let nonce = value["nonce"] as? String, nonce.count == 64,
          nonce.allSatisfy({ "0123456789abcdef".contains($0) }), try encoded(value) == raw else { throw WorkerError.invalid }
    func observed(_ result: Int32) -> [String: Any] {
        ["allowed": result == 0, "errno": result == 0 ? 0 : Int(errno)]
    }
    let attempts: [[String: Any]] = files.map { path in
        let directory = URL(fileURLWithPath: path).deletingLastPathComponent().path
        let prefix = directory + "/.cb-denial-" + nonce
        let created = open(prefix + "-created", O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        let createResult = observed(created >= 0 ? 0 : -1)
        if created >= 0 { close(created) }
        let renameResult = observed(rename(prefix + "-canary", prefix + "-renamed"))
        var listResult: [String: Any]
        if let dir = opendir(directory) {
            errno = 0
            _ = readdir(dir)
            listResult = observed(errno == 0 ? 0 : -1)
            closedir(dir)
        } else { listResult = observed(-1) }
        return ["read": fileAccess(path, false), "write": fileAccess(path, true),
                "create": createResult, "rename": renameResult, "list": listResult]
    }
    return ["schema": "claimbranch.worker-custody-result/v1", "nonce": nonce, "attempts": attempts,
            "authorization_verified": false]
}
do {
    guard CommandLine.arguments.count == 2 else { throw WorkerError.invalid }
    let mode = CommandLine.arguments[1]
    let value: [String: Any]
    switch mode {
    case "check": value = try inspect()
    case "result": _ = try inspect(); value = try result(input())
    case "boundary": _ = try inspect(); value = try boundary(input())
    case "custody": _ = try inspect(); value = try custody(input())
    default: throw WorkerError.invalid
    }
    FileHandle.standardOutput.write(try encoded(value))
} catch { exit(2) }
