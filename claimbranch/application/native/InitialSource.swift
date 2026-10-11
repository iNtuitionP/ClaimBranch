func initialQuoted(_ text: String) -> String {
    guard let raw = try? JSONSerialization.data(withJSONObject: text, options: [.fragmentsAllowed, .withoutEscapingSlashes]) else { return "unavailable" }
    return visibleReviewText(String(decoding: raw, as: UTF8.self))
}
func initialDisplayedPath(_ value: Any?) -> String {
    guard let text = value as? String, initialPath(text) else { return "unavailable" }
    let bytes = Array(text.utf8)
    var data = Data()
    for index in stride(from: 0, to: bytes.count, by: 2) {
        guard let byte = UInt8(String(decoding: bytes[index..<(index+2)], as: UTF8.self), radix: 16) else { return "unavailable" }
        data.append(byte)
    }
    guard let decoded = String(data: data, encoding: .utf8) else { return "원래 경로 바이트 (hex): " + text }
    return initialQuoted(decoded)
}
// Independent read-only initial association checks. No scientific fidelity,
// receipt, accepted genesis, file mutation or filesystem compare-and-swap.
func initialSigningAllowance(_ expires: Double, _ peer: Double, _ monotonic: Double, _ wall: Double) -> Double {
    min(90,peer-monotonic-11,expires-wall-21)
}
func initialExactPath(_ value: Any?, relative: Bool = false) throws -> Data {
    guard let text = value as? String, initialPath(text) else { throw DeliveryError.invalid }
    let hex = Array(text.utf8)
    let raw = Data(stride(from: 0, to: hex.count, by: 2).map {
        UInt8(String(decoding: hex[$0..<($0+2)], as: UTF8.self), radix:16)!
    })
    guard !raw.contains(0), !raw.contains(10), !raw.contains(13),
          (raw.first == 47) != relative else { throw DeliveryError.invalid }
    let parts = raw.split(separator:47, omittingEmptySubsequences:false)
    let components = relative ? parts : Array(parts.dropFirst())
    guard components.allSatisfy({ !$0.isEmpty && $0 != Data(".".utf8) && $0 != Data("..".utf8) }),
          !relative || (raw.suffix(4) == Data(".tex".utf8) && components.last!.count > 4 && components.allSatisfy {
              $0.map { (65...90).contains($0) ? $0+32 : $0 } != Array(".git".utf8)
          }) else { throw DeliveryError.invalid }
    return raw
}
func initialCPath<T>(_ raw: Data, _ body: (UnsafePointer<CChar>) throws -> T) rethrows -> T {
    try (raw.map { CChar(bitPattern:$0) } + [0]).withUnsafeBufferPointer { try body($0.baseAddress!) }
}
func initialCanonicalPath(_ raw: Data) throws -> Data {
    try initialCPath(raw) { path in
        guard let resolved = realpath(path,nil) else { throw DeliveryError.invalid }
        defer { free(resolved) }
        return Data(bytes:resolved,count:strlen(resolved))
    }
}
func initialOpenDirectory(_ raw: Data) throws -> Int32 {
    guard try initialCanonicalPath(raw) == raw else { throw DeliveryError.invalid }
    var fd = open("/",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC)
    guard fd >= 0 else { throw DeliveryError.io }
    do {
        for component in raw.split(separator:47) {
            let child = initialCPath(Data(component)) { openat(fd,$0,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC) }
            guard child >= 0 else { throw DeliveryError.invalid }
            close(fd); fd = child
        }
        return fd
    } catch { close(fd); throw error }
}
func initialStat(_ fd: Int32) throws -> stat {
    var info = stat()
    guard fstat(fd,&info) == 0 else { throw DeliveryError.io }
    return info
}
func initialIdentityMatches(_ info: stat, _ value: Any?) -> Bool {
    guard let expected = value as? [String:String] else { return false }
    return expected == ["device":String(info.st_dev),"inode":String(info.st_ino)]
}
func initialStamp(_ info: stat) throws -> [String:String] {
    func nanos(_ stamp: timespec) throws -> String {
        let (seconds, overflow) = Int64(stamp.tv_sec).multipliedReportingOverflow(by:1_000_000_000)
        let (result, addition) = seconds.addingReportingOverflow(Int64(stamp.tv_nsec))
        guard !overflow, !addition, result >= 0 else { throw DeliveryError.invalid }
        return String(result)
    }
    return ["size":String(info.st_size),"mtime_ns":try nanos(info.st_mtimespec),"ctime_ns":try nanos(info.st_ctimespec)]
}
func initialExists(_ fd: Int32, _ name: String) throws -> Bool {
    var info = stat()
    if fstatat(fd,name,&info,AT_SYMLINK_NOFOLLOW) == 0 { return true }
    guard errno == ENOENT else { throw DeliveryError.io }
    return false
}
func initialGitLocations(_ root: Data) throws -> [Data] {
    // No shell, hooks, filters, global/system Git configuration or input.
    // Repository-local config/includes remain subject to the discovery deadline.
    guard let path = String(data:root,encoding:.utf8) else { throw DeliveryError.invalid }
    let process = Process(), output = Pipe()
    process.executableURL = URL(fileURLWithPath:"/usr/bin/git")
    process.arguments = ["-C",path,"rev-parse","--show-toplevel","--absolute-git-dir","--git-common-dir"]
    process.environment = ["PATH":"/usr/bin:/bin","GIT_CONFIG_NOSYSTEM":"1",
        "GIT_CONFIG_GLOBAL":"/dev/null","GIT_OPTIONAL_LOCKS":"0"]
    process.standardInput = FileHandle.nullDevice; process.standardError = FileHandle.nullDevice
    process.standardOutput = output
    try process.run()
    defer {
        if process.isRunning { kill(process.processIdentifier,SIGKILL) }
        process.waitUntilExit()
        try? output.fileHandleForReading.close(); try? output.fileHandleForWriting.close()
    }
    try output.fileHandleForWriting.close()
    let fd = output.fileHandleForReading.fileDescriptor
    guard fcntl(fd,F_SETFL,O_NONBLOCK) == 0 else { throw DeliveryError.io }
    let deadline = ProcessInfo.processInfo.systemUptime + 5
    var raw = Data(), buffer = [UInt8](repeating:0,count:4096)
    while true {
        let count = read(fd,&buffer,buffer.count)
        if count > 0 { raw.append(contentsOf:buffer.prefix(count)); guard raw.count <= 12288 else { throw DeliveryError.invalid } }
        else if count == 0 { break }
        else if errno != EAGAIN && errno != EINTR { throw DeliveryError.io }
        guard ProcessInfo.processInfo.systemUptime < deadline else { throw DeliveryError.timeout }
        if count < 0 { usleep(1000) }
    }
    while process.isRunning {
        guard ProcessInfo.processInfo.systemUptime < deadline else { throw DeliveryError.timeout }
        usleep(1000)
    }
    guard process.terminationStatus == 0, raw.last == 10 else { throw DeliveryError.invalid }
    let lines = raw.dropLast().split(separator:10,omittingEmptySubsequences:false)
    guard lines.count == 3 else { throw DeliveryError.invalid }
    return try lines.map { line in
        let value = Data(line)
        guard !value.isEmpty, !value.contains(0), !value.contains(13) else { throw DeliveryError.invalid }
        return try initialCanonicalPath(value.first == 47 ? value : root + Data([47]) + value)
    }
}
func initialOutsideGit(_ workspace: Data) throws {
    var ancestor = workspace
    while !ancestor.isEmpty {
        let fd = try initialOpenDirectory(ancestor); defer { close(fd) }
        guard !(try initialExists(fd,".git")),
              !(try initialExists(fd,"HEAD") && initialExists(fd,"objects") && initialExists(fd,"refs")) else { throw DeliveryError.invalid }
        if ancestor == Data([47]) { break }
        guard let slash = ancestor.lastIndex(of:47) else { throw DeliveryError.invalid }
        ancestor = slash == 0 ? Data([47]) : Data(ancestor[..<slash])
    }
}
func initialNotContained(_ child: Int32, _ other: Int32) throws {
    let target = try initialStat(other)
    var current = dup(child)
    guard current >= 0 else { throw DeliveryError.io }
    defer { close(current) }
    for _ in 0..<4096 {
        let info = try initialStat(current)
        guard info.st_dev != target.st_dev || info.st_ino != target.st_ino else { throw DeliveryError.invalid }
        let parent = openat(current,"..",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC)
        guard parent >= 0 else { throw DeliveryError.io }
        let parentInfo: stat
        do { parentInfo = try initialStat(parent) } catch { close(parent); throw error }
        close(current); current = parent
        if info.st_dev == parentInfo.st_dev && info.st_ino == parentInfo.st_ino { return }
    }
    throw DeliveryError.invalid
}
func initialCheckAssociation(_ association: [String:Any]) throws {
    guard let source = association["source"] as? [String:Any], let anchor = source["anchor_id"] as? String,
          initialIdentifier(anchor) else { throw DeliveryError.invalid }
    let paths = try ["root","git_dir","git_common_dir"].map { try initialExactPath(source[$0]) }
    guard try initialGitLocations(paths[0]) == paths else { throw DeliveryError.invalid }
    var directories = [Int32]()
    defer { directories.forEach { close($0) } }
    for (index,key) in ["root_identity","git_identity","git_common_identity"].enumerated() {
        let fd = try initialOpenDirectory(paths[index]); directories.append(fd)
        guard initialIdentityMatches(try initialStat(fd),source[key]) else { throw DeliveryError.invalid }
    }
    let workspace = try initialExactPath(association["workspace"])
    guard paths.allSatisfy({ workspace != $0 && !workspace.starts(with:$0+Data([47])) && !$0.starts(with:workspace+Data([47])) }) else { throw DeliveryError.invalid }
    let work = try initialOpenDirectory(workspace); directories.append(work)
    let privateInfo = try initialStat(work)
    guard initialIdentityMatches(privateInfo,association["workspace_identity"]), privateInfo.st_uid == geteuid(),
          privateInfo.st_mode & 0o777 == 0o700 else { throw DeliveryError.invalid }
    for repo in directories.prefix(3) {
        try initialNotContained(repo,work); try initialNotContained(work,repo)
    }
    try initialOutsideGit(workspace)
    let relative = try initialExactPath(source["manuscript"],relative:true)
    let pieces = relative.split(separator:47)
    var parent = directories[0], entries = [(Int32,Data,Int32)]()
    for piece in pieces.dropLast() {
        let name = Data(piece)
        let fd = initialCPath(name) { openat(parent,$0,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC) }
        guard fd >= 0 else { throw DeliveryError.invalid }
        directories.append(fd); entries.append((parent,name,fd));parent = fd
        guard !(try initialExists(fd,".git")) else { throw DeliveryError.invalid }
    }
    let name = Data(pieces.last!)
    let file = initialCPath(name) { openat(parent,$0,O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC) }
    guard file >= 0 else { throw DeliveryError.invalid }
    defer { close(file) }
    entries.append((parent,name,file))
    let before = try initialStat(file)
    guard before.st_mode & S_IFMT == S_IFREG, before.st_nlink == 1, (0...65536).contains(before.st_size),
          initialIdentityMatches(before,source["file_identity"]),
          try initialStamp(before).allSatisfy({ source[$0.key] as? String == $0.value }) else { throw DeliveryError.invalid }
    var bytes = Data(), buffer = [UInt8](repeating:0,count:4096)
    while true {
        let count = read(file,&buffer,buffer.count)
        if count == 0 { break }
        guard count > 0, bytes.count + count <= 65536 else { throw DeliveryError.invalid }
        bytes.append(contentsOf:buffer.prefix(count))
    }
    let after = try initialStat(file)
    guard try initialStamp(after) == initialStamp(before), initialIdentityMatches(after,source["file_identity"]),
          hashHex(bytes) == source["source_digest"] as? String, String(data:bytes,encoding:.utf8) != nil else { throw DeliveryError.invalid }
    let lines = bytes.split(separator:10,omittingEmptySubsequences:false)
    let starts = lines.indices.filter { $0 < lines.count-1 && lines[$0] == Data("% claimbranch:start id=\(anchor)".utf8) }
    let ends = lines.indices.filter { $0 < lines.count-1 && lines[$0] == Data("% claimbranch:end id=\(anchor)".utf8) }
    guard starts.count == 1, ends.count == 1, starts[0] < ends[0] else { throw DeliveryError.invalid }
    for (owner,name,held) in entries {
        var current = stat()
        guard initialCPath(name,{ fstatat(owner,$0,&current,AT_SYMLINK_NOFOLLOW) }) == 0,
              initialIdentityMatches(current,["device":String((try initialStat(held)).st_dev),"inode":String((try initialStat(held)).st_ino)]),
              current.st_mode & S_IFMT != S_IFLNK else { throw DeliveryError.invalid }
    }
    // Reopen named directories so a held old inode cannot vouch for a replaced path.
    for (index,key) in ["root_identity","git_identity","git_common_identity","workspace_identity"].enumerated() {
        let path = index == 3 ? workspace : paths[index]
        let fd = try initialOpenDirectory(path); defer { close(fd) }
        let value = index == 3 ? association[key] : source[key]
        let info = try initialStat(fd)
        guard initialIdentityMatches(info,value),
              index != 3 || (info.st_uid == geteuid() && info.st_mode & 0o777 == 0o700) else { throw DeliveryError.invalid }
    }
    try initialOutsideGit(workspace)
    guard try initialGitLocations(paths[0]) == paths else { throw DeliveryError.invalid }
    for repo in directories.prefix(3) {
        try initialNotContained(repo,work); try initialNotContained(work,repo)
    }
}
extension ReviewSigningRequest {
    func checkInitialSource() throws {
        guard operation["action"] as? String == "initialize-project" else { return }
        guard let association = operation["association"] as? [String:Any], let enrollment,
              let identity = enrollment.body["protected_identity"] else { throw DeliveryError.invalid }
        try initialProtectedEmpty(try enrollment.directory + "/protected",identity,enrollment.id)
        try initialCheckAssociation(association)
        try initialProtectedEmpty(try enrollment.directory + "/protected",identity,enrollment.id)
    }
}
