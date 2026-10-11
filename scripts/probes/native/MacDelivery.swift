// Disposable synthetic IPC measurement; never issues an approval or writes research.
import Darwin
import Foundation
import Security

let limit = 1024
enum ProbeFailure: Error { case invalid, io, timeout }

func now() -> Double {
    var info = mach_timebase_info_data_t()
    mach_timebase_info(&info)
    return Double(mach_continuous_time()) * Double(info.numer) / Double(info.denom) / 1_000_000_000
}

func output(_ fields: [String: Any]) {
    var value = fields
    value["schema_version"] = 1
    value["authorization_verified"] = false
    let raw = try! JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    print(String(data: raw, encoding: .utf8)!)
    fflush(stdout)
}

func address(_ path: String) throws -> sockaddr_un {
    let bytes = Array(path.utf8)
    guard !bytes.contains(0), bytes.count < 104 else { throw ProbeFailure.invalid }
    var value = sockaddr_un()
    value.sun_family = sa_family_t(AF_UNIX)
    value.sun_len = UInt8(MemoryLayout<sockaddr_un>.size)
    withUnsafeMutableBytes(of: &value.sun_path) { buffer in
        buffer.copyBytes(from: bytes + [0])
    }
    return value
}

func socketFD() throws -> Int32 {
    let fd = socket(AF_UNIX, SOCK_STREAM, 0)
    guard fd >= 0 else { throw ProbeFailure.io }
    var yes: Int32 = 1
    guard fcntl(fd, F_SETFD, FD_CLOEXEC) == 0,
          setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &yes, socklen_t(MemoryLayout.size(ofValue: yes))) == 0 else {
        close(fd); throw ProbeFailure.io
    }
    return fd
}

func waitFor(_ fd: Int32, _ events: Int16, _ deadline: Double) throws {
    while true {
        let remaining = deadline - now()
        guard remaining > 0 else { throw ProbeFailure.timeout }
        var entry = pollfd(fd: fd, events: events, revents: 0)
        let result = poll(&entry, 1, Int32(min(remaining * 1000, 30_000).rounded(.up)))
        if result < 0 && errno == EINTR { continue }
        guard result > 0 else { throw ProbeFailure.timeout }
        guard entry.revents & events != 0 else { throw ProbeFailure.io }
        return
    }
}

func readBytes(_ fd: Int32, _ count: Int, _ deadline: Double) throws -> Data {
    var data = Data()
    while data.count < count {
        try waitFor(fd, Int16(POLLIN), deadline)
        var buffer = [UInt8](repeating: 0, count: count - data.count)
        let size = recv(fd, &buffer, buffer.count, MSG_DONTWAIT)
        if size < 0 && [EINTR, EAGAIN].contains(errno) { continue }
        guard size > 0 else { throw ProbeFailure.io }
        data.append(contentsOf: buffer.prefix(size))
    }
    return data
}

func writeBytes(_ fd: Int32, _ data: Data, _ deadline: Double) throws {
    var offset = 0
    while offset < data.count {
        try waitFor(fd, Int16(POLLOUT), deadline)
        let size = data.withUnsafeBytes { buffer in
            send(fd, buffer.baseAddress!.advanced(by: offset), buffer.count - offset, MSG_DONTWAIT)
        }
        if size < 0 && [EINTR, EAGAIN].contains(errno) { continue }
        guard size > 0 else { throw ProbeFailure.io }
        offset += size
    }
}

func frame(_ data: Data) -> Data {
    var size = UInt32(data.count).bigEndian
    return withUnsafeBytes(of: &size) { Data($0) } + data
}

func readFrame(_ fd: Int32, _ deadline: Double) throws -> Data {
    let header = try readBytes(fd, 4, deadline)
    let count = header.reduce(UInt32(0)) { ($0 << 8) | UInt32($1) }
    guard count > 0, count <= limit else { throw ProbeFailure.invalid }
    return try readBytes(fd, Int(count), deadline)
}

func sendStatus(_ fd: Int32, _ value: String, _ deadline: Double) throws {
    try writeBytes(fd, frame(Data(value.utf8)), deadline)
}

// No peer-supplied PID/role/path is consulted. Exact audit identity is obtained
// from the connected kernel socket, then resolved to a dynamic SecCode guest.
func trustedPeer(_ fd: Int32, _ requirement: SecRequirement) -> Bool {
    var token = audit_token_t()
    var size = socklen_t(MemoryLayout.size(ofValue: token))
    guard getsockopt(fd, SOL_LOCAL, LOCAL_PEERTOKEN, &token, &size) == 0,
          size == MemoryLayout.size(ofValue: token) else { return false }
    let data = withUnsafeBytes(of: &token) { Data($0) }
    var code: SecCode?
    guard SecCodeCopyGuestWithAttributes(nil, [kSecGuestAttributeAudit as String: data] as CFDictionary,
                                        [], &code) == errSecSuccess, let code,
          SecCodeCheckValidity(code, [], requirement) == errSecSuccess else { return false }
    var information: CFDictionary?
    // SecCode.h explicitly accepts a dynamic SecCode here even though Swift
    // imports the parameter as SecStaticCode. Keep the dynamic object to obtain
    // kSecCodeInfoStatus instead of silently checking only on-disk flags.
    let opaqueCode = unsafeBitCast(code, to: SecStaticCode.self)
    guard SecCodeCopySigningInformation(opaqueCode, SecCSFlags(rawValue: kSecCSSigningInformation | kSecCSDynamicInformation), &information) == errSecSuccess,
          let fields = information as? [String: Any],
          let flags = fields[kSecCodeInfoFlags as String] as? NSNumber,
          let running = fields[kSecCodeInfoStatus as String] as? NSNumber else { return false }
    // CSCommon.h kSecCodeSignatureRuntime and sys/codesign.h CS_RUNTIME.
    let runtime: UInt32 = 0x10000
    return flags.uint32Value & runtime != 0 && running.uint32Value & runtime != 0
}

func server(_ path: String, _ requirement: SecRequirement, _ count: Int, _ binding: Data, _ expired: Bool) throws {
    // Python supplies a new owned directory. Pin its descriptor; never replace
    // an existing socket or unlink an object we did not create.
    guard URL(fileURLWithPath: path).lastPathComponent == "s" else { throw ProbeFailure.invalid }
    let parent = URL(fileURLWithPath: path).deletingLastPathComponent().path
    let dir = open(parent, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
    guard dir >= 0 else { throw ProbeFailure.io }
    defer { close(dir) }
    var info = stat()
    guard fstat(dir, &info) == 0, info.st_uid == geteuid(), info.st_mode & 0o777 == 0o700 else { throw ProbeFailure.invalid }
    let fd = try socketFD()
    defer { close(fd) }
    umask(0o077)
    var addr = try address(path)
    let bound = withUnsafePointer(to: &addr) {
        $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { bind(fd, $0, socklen_t(MemoryLayout<sockaddr_un>.size)) }
    }
    guard bound == 0 else { throw ProbeFailure.io }
    var socketInfo = stat()
    guard fstatat(dir, "s", &socketInfo, AT_SYMLINK_NOFOLLOW) == 0,
          socketInfo.st_mode & S_IFMT == S_IFSOCK else { throw ProbeFailure.invalid }
    defer {
        var current = stat()
        if fstatat(dir, "s", &current, AT_SYMLINK_NOFOLLOW) == 0,
           current.st_dev == socketInfo.st_dev, current.st_ino == socketInfo.st_ino {
            unlinkat(dir, "s", 0)
        }
    }
    guard listen(fd, 8) == 0 else { throw ProbeFailure.io }
    let lifetime = now() + 20
    let reviewDeadline = expired ? now() - 1 : lifetime
    var consumed = 0
    var cancelled = false
    var outcomes: [String] = []
    output(["status": "ready"])
    for _ in 0..<count {
        try waitFor(fd, Int16(POLLIN), lifetime)
        let peer = accept(fd, nil, nil)
        guard peer >= 0 else { throw ProbeFailure.io }
        defer { close(peer) }
        var yes: Int32 = 1
        guard setsockopt(peer, SOL_SOCKET, SO_NOSIGPIPE, &yes, socklen_t(MemoryLayout.size(ofValue: yes))) == 0 else { throw ProbeFailure.io }
        let deadline = min(lifetime, now() + 3)
        guard trustedPeer(peer, requirement) else {
            try? sendStatus(peer, "peer_rejected", deadline)
            outcomes.append("peer_rejected")
            continue
        }
        var status = "input_rejected"
        do {
            try sendStatus(peer, "ready", deadline)
            let request = try readFrame(peer, deadline)
            if request.dropFirst() != binding || ![UInt8(1), UInt8(2)].contains(request.first!) {
                status = "binding_rejected"
            } else if now() >= reviewDeadline {
                status = "expired"
            } else if consumed != 0 {
                status = "replay_rejected"
            } else if cancelled {
                status = "cancelled"
            } else if request.first == 2 {
                cancelled = true
                status = "cancelled"
            } else {
                // Exact current binding, from the expected native peer, once.
                consumed = 1
                status = "received"
            }
        } catch { status = "input_rejected" }
        try? sendStatus(peer, status, deadline)
        outcomes.append(status)
    }
    output(["status": "completed", "outcomes": outcomes, "consumed": consumed])
}

func client(_ path: String, _ requirement: SecRequirement, _ mode: String, _ binding: Data) throws {
    let fd = try socketFD()
    defer { close(fd) }
    var addr = try address(path)
    let connected = withUnsafePointer(to: &addr) {
        $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { connect(fd, $0, socklen_t(MemoryLayout<sockaddr_un>.size)) }
    }
    guard connected == 0 else { throw ProbeFailure.io }
    guard trustedPeer(fd, requirement) else {
        output(["status": "peer_rejected", "peer_verified": false, "binding_sent": false]); return
    }
    let deadline = now() + 4
    let hello = try readFrame(fd, deadline)
    if hello == Data("peer_rejected".utf8) {
        output(["status": "peer_rejected", "peer_verified": true, "binding_sent": false]); return
    }
    guard hello == Data("ready".utf8) else { throw ProbeFailure.invalid }
    var value = binding
    if mode == "wrong-project" {
        // Change only the project bytes. Re-encoding via a different JSON
        // implementation could also alter slash escaping and weaken this case.
        let marker = Data("\"project\":\"synthetic-project\"".utf8)
        guard let range = value.range(of: marker) else { throw ProbeFailure.invalid }
        value.replaceSubrange(range, with: Data("\"project\":\"another-project\"".utf8))
    } else if mode == "changed" {
        value[value.count - 1] ^= 1
    }
    let request = frame(Data([mode == "cancel" ? 2 : 1]) + value)
    if mode == "oversized" {
        try writeBytes(fd, Data([0, 0, 4, 1]), deadline)
    } else if mode == "truncated" {
        try writeBytes(fd, request.prefix(7), deadline)
        shutdown(fd, SHUT_WR)
    } else {
        try writeBytes(fd, request, deadline)
    }
    let reply = try readFrame(fd, deadline)
    let status = String(data: reply, encoding: .utf8) ?? "invalid"
    guard ["received", "binding_rejected", "replay_rejected", "cancelled", "expired", "input_rejected"].contains(status) else { throw ProbeFailure.invalid }
    output(["status": status, "peer_verified": true, "binding_sent": true])
}

do {
    let args = Array(CommandLine.arguments.dropFirst())
    guard args.count == 5, ["server", "client"].contains(args[0]), args[2].utf8.count <= 256 else { throw ProbeFailure.invalid }
    var requirement: SecRequirement?
    guard SecRequirementCreateWithString(args[2] as CFString, [], &requirement) == errSecSuccess,
          let requirement else { throw ProbeFailure.invalid }
    let input = try FileHandle.standardInput.read(upToCount: limit + 1) ?? Data()
    guard (1...512).contains(input.count) else { throw ProbeFailure.invalid }
    if args[0] == "server" {
        guard let count = Int(args[3]), (1...16).contains(count), ["current", "expired"].contains(args[4]) else { throw ProbeFailure.invalid }
        try server(args[1], requirement, count, input, args[4] == "expired")
    } else {
        guard ["valid", "changed", "wrong-project", "cancel", "stale", "oversized", "truncated"].contains(args[3]), args[4] == "synthetic" else { throw ProbeFailure.invalid }
        try client(args[1], requirement, args[3], input)
    }
} catch {
    output(["status": "error"])
    exit(1)
}
