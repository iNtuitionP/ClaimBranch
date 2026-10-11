// Disposable recovery-mechanism experiment. No OS credential, UI or file access.
// Secrets/payload use pipes only. A successful decrypt never confers authority.
import Foundation
import CryptoKit
import Security
import Darwin

let magic = Data([0x43, 0x42, 0x52, 0x45, 0, 1]) // CBRE v1, experiment only
let info = Data("ClaimBranch recovery experiment v1".utf8)
let maxPlaintext = 270336
let maxCheckpoint = 1024
let overhead = 66 // magic(6), salt(32), nonce(12), tag(16)
enum Rejected: Error { case input, verification, signature }

func readInput(_ limit: Int) throws -> Data {
    var result = Data()
    while true {
        let part = try FileHandle.standardInput.read(upToCount: min(65536, limit + 1 - result.count)) ?? Data()
        if part.isEmpty { return result }
        result.append(part)
        if result.count > limit { throw Rejected.input }
    }
}

func randomSalt() throws -> Data {
    var bytes = [UInt8](repeating: 0, count: 32)
    guard SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes) == errSecSuccess else { throw Rejected.input }
    return Data(bytes)
}

func derive(_ key: Data, _ salt: Data) -> SymmetricKey {
    HKDF<SHA256>.deriveKey(inputKeyMaterial: SymmetricKey(data: key), salt: salt,
                           info: info, outputByteCount: 32)
}

func seal(_ plaintext: Data, _ key: Data) throws -> Data {
    guard !plaintext.isEmpty, plaintext.count <= maxPlaintext else { throw Rejected.input }
    let salt = try randomSalt()
    let header = magic + salt
    let box = try AES.GCM.seal(plaintext, using: derive(key, salt), authenticating: header)
    guard let combined = box.combined, combined.count == plaintext.count + 28 else { throw Rejected.input }
    return header + combined
}

func open(_ archive: Data, _ key: Data) throws -> Data {
    guard archive.count > overhead, archive.count <= maxPlaintext + overhead,
          archive.prefix(magic.count) == magic else { throw Rejected.input }
    let header = Data(archive.prefix(38))
    let salt = Data(header.suffix(32))
    let box = try AES.GCM.SealedBox(combined: Data(archive.dropFirst(38)))
    return try AES.GCM.open(box, using: derive(key, salt), authenticating: header)
}

func hex(_ text: String) -> Data {
    let bytes = Array(text.utf8)
    return Data(stride(from: 0, to: bytes.count, by: 2).map {
        UInt8(String(bytes: bytes[$0..<$0 + 2], encoding: .utf8)!, radix: 16)!
    })
}

func knownAnswers() throws {
    // OpenSSL's evpciph_aes_common.txt AES-256-GCM zero-key/IV vectors.
    let key = SymmetricKey(data: Data(repeating: 0, count: 32))
    let nonce = try AES.GCM.Nonce(data: Data(repeating: 0, count: 12))
    for (size, ciphertext, tag) in [
        (0, "", "530f8afbc74536b9a963b4f1c4cb738b"),
        (16, "cea7403d4d606b6e074ec5d3baf39d18", "d0d1c8a799996bf0265b98b5d48ab919")
    ] {
        let plain = Data(repeating: 0, count: size)
        let box = try AES.GCM.seal(plain, using: key, nonce: nonce)
        guard box.ciphertext == hex(ciphertext), box.tag == hex(tag),
              try AES.GCM.open(box, using: key) == plain else { throw Rejected.verification }
    }
    // RFC 5869 Appendix A.1: independent HKDF-SHA256 expected output.
    let derived = HKDF<SHA256>.deriveKey(inputKeyMaterial: SymmetricKey(data: Data(repeating: 0x0b, count: 22)),
        salt: hex("000102030405060708090a0b0c"), info: hex("f0f1f2f3f4f5f6f7f8f9"), outputByteCount: 42)
    guard derived.withUnsafeBytes({ Data($0) }) == hex(
        "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865")
        else { throw Rejected.verification }
}

func fixtureSignature(_ message: Data) throws -> Data {
    // Software fixture only, never a fallback for a device approval key.
    guard !message.isEmpty,
          let value = try JSONSerialization.jsonObject(with: message) as? [String: Any],
          value["format"] as? String == "claimbranch-recovery-checkpoint/v1",
          value["classification"] as? String == "candidate-history" else { throw Rejected.input }
    let key = P256.Signing.PrivateKey()
    let signature = try key.signature(for: message).derRepresentation
    return key.publicKey.x963Representation + signature
}

func verifyCheckpoint(_ input: Data) throws {
    guard input.count >= 76 else { throw Rejected.input }
    let signatureSize = Int(input[0]) * 256 + Int(input[1])
    let messageOffset = 67 + signatureSize
    guard (8...72).contains(signatureSize), input.count > messageOffset,
          input.count - messageOffset <= maxCheckpoint else { throw Rejected.input }
    do {
        let key = try P256.Signing.PublicKey(x963Representation: Data(input[2..<67]))
        let signature = try P256.Signing.ECDSASignature(derRepresentation: Data(input[67..<messageOffset]))
        guard key.isValidSignature(signature, for: Data(input[messageOffset...])) else { throw Rejected.signature }
    } catch {
        throw Rejected.signature
    }
}

do {
    let arguments = Array(CommandLine.arguments.dropFirst())
    guard arguments.count == 1 else { throw Rejected.input }
    if arguments == ["check"] {
        guard try readInput(0).isEmpty else { throw Rejected.input }
        try knownAnswers()
        try FileHandle.standardOutput.write(contentsOf: Data("recovery-crypto-ok\n".utf8))
    } else if arguments == ["fixture-sign"] {
        let signature = try fixtureSignature(readInput(maxCheckpoint))
        try FileHandle.standardOutput.write(contentsOf: signature)
    } else if arguments == ["verify-checkpoint"] {
        try verifyCheckpoint(readInput(2 + 65 + 72 + maxCheckpoint))
        try FileHandle.standardOutput.write(contentsOf: Data("signature-verified\n".utf8))
    } else {
        guard ["seal", "open"].contains(arguments[0]) else { throw Rejected.input }
        let input = try readInput(32 + maxPlaintext + overhead)
        guard input.count > 32 else { throw Rejected.input }
        let key = Data(input.prefix(32)), payload = Data(input.dropFirst(32))
        let result = try arguments[0] == "seal" ? seal(payload, key) : open(payload, key)
        try FileHandle.standardOutput.write(contentsOf: result)
    }
} catch Rejected.signature {
    try? FileHandle.standardError.write(contentsOf: Data("signature-rejected\n".utf8))
    exit(2)
} catch CryptoKitError.authenticationFailure {
    try? FileHandle.standardError.write(contentsOf: Data("authentication-rejected\n".utf8))
    exit(2)
} catch {
    // No exception, request, key, path or partially decrypted bytes are logged.
    try? FileHandle.standardError.write(contentsOf: Data("recovery-rejected\n".utf8))
    exit(1)
}
