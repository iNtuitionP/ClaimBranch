// Exercises only parent-created synthetic resources. Never a provider sandbox.
import Darwin
import Foundation

func fileAttempt(_ path: String, write: Bool) -> [String: Any] {
    errno = 0
    let handle = open(path, write ? O_WRONLY | O_APPEND : O_RDONLY)
    if handle < 0 { return ["allowed": false, "errno": Int(errno)] }
    defer { close(handle) }
    if write {
        let marker = Array("probe-write\n".utf8)
        let count = marker.withUnsafeBytes { Darwin.write(handle, $0.baseAddress!, $0.count) }
        if count != marker.count { return ["allowed": false, "errno": Int(errno)] }
    } else {
        var byte: UInt8 = 0
        if read(handle, &byte, 1) != 1 { return ["allowed": false, "errno": Int(errno)] }
    }
    return ["allowed": true, "errno": 0]
}

let args = Array(CommandLine.arguments.dropFirst())
guard args.count == 2, let port = UInt16(args[1]), port > 0 else { exit(2) }
let connection = socket(AF_INET, SOCK_STREAM, 0)
var network: [String: Any] = ["allowed": false, "errno": Int(errno)]
if connection >= 0 {
    var address = sockaddr_in()
    address.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
    address.sin_family = sa_family_t(AF_INET)
    address.sin_port = port.bigEndian
    address.sin_addr.s_addr = inet_addr("127.0.0.1")
    let result = withUnsafePointer(to: &address) {
        $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
            connect(connection, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
        }
    }
    network = ["allowed": result == 0, "errno": result == 0 ? 0 : Int(errno)]
    close(connection)
}
let data = try JSONSerialization.data(withJSONObject: ["read": fileAttempt(args[0], write: false),
    "write": fileAttempt(args[0], write: true), "network": network], options: [.sortedKeys])
print(String(decoding: data, as: UTF8.self))
