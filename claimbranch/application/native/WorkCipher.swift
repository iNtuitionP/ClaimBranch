// Unaccepted work encryption and device data-key wrapping. No signing or file access.
// Secrets/payload use pipes only. A successful decrypt never confers authority.
import Foundation
import CryptoKit
import Security
import Darwin
import LocalAuthentication

let magic = Data([0x43, 0x42, 0x57, 0x4b, 0, 1]) // CBWK v1, unaccepted work only
let info = Data("ClaimBranch unaccepted paper work v1".utf8)
let maxPlaintext = 262144
let overhead = 66 // magic(6), salt(32), nonce(12), tag(16)
enum Rejected: Error { case input, verification }

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

let keyMagic = Data([0x43, 0x42, 0x4b, 0x59, 0, 1]) // CBKY v1
let maxKeyBytes = 16770 // header(234), enclave representation(1...16384), boxes(120), MAC(32)
let devicePurpose = Data("ClaimBranch device work data key v1".utf8)
let recoveryPurpose = Data("ClaimBranch recovery work data key v1".utf8)
let integrityPurpose = Data("ClaimBranch work key envelope integrity v1".utf8)
let contentPurpose = Data("ClaimBranch device-bound work content v1".utf8)

func boundContentKey(_ key: Data, _ binding: Data) -> Data {
    let derived = HKDF<SHA256>.deriveKey(inputKeyMaterial: SymmetricKey(data: key), salt: binding,
                                       info: contentPurpose, outputByteCount: 32)
    return derived.withUnsafeBytes { Data($0) }
}

func envelopeIntegrityKey(_ dataKey: Data, _ salt: Data) -> SymmetricKey {
    HKDF<SHA256>.deriveKey(inputKeyMaterial: SymmetricKey(data: dataKey), salt: salt,
                           info: integrityPurpose, outputByteCount: 32)
}

func recoveryWrappingKey(_ key: Data, _ salt: Data) -> SymmetricKey {
    HKDF<SHA256>.deriveKey(inputKeyMaterial: SymmetricKey(data: key), salt: salt,
                           info: recoveryPurpose, outputByteCount: 32)
}

func noInteraction() -> LAContext {
    let context = LAContext()
    context.interactionNotAllowed = true
    return context
}

func createWorkKey(_ input: Data) throws -> Data {
    guard input.count == 96, SecureEnclave.isAvailable else { throw Rejected.input }
    let binding = Data(input.prefix(32))
    let dataKey = Data(input[32..<64]), recoveryKey = Data(input[64..<96])
    var error: Unmanaged<CFError>?
    guard let access = SecAccessControlCreateWithFlags(nil, kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
            .privateKeyUsage, &error) else { throw Rejected.input }
    // Data access is deliberately distinct from foreground approval signing.
    let device = try SecureEnclave.P256.KeyAgreement.PrivateKey(accessControl: access,
                                                               authenticationContext: noInteraction())
    let representation = device.dataRepresentation
    guard !representation.isEmpty, representation.count <= 16384 else { throw Rejected.input }
    let ephemeral = P256.KeyAgreement.PrivateKey()
    let salt = try randomSalt(), recoverySalt = try randomSalt()
    let length = Data([UInt8(representation.count >> 8), UInt8(representation.count & 255)])
    let header = keyMagic + binding + device.publicKey.x963Representation + ephemeral.publicKey.x963Representation
        + salt + recoverySalt + length + representation
    let shared = try ephemeral.sharedSecretFromKeyAgreement(with: device.publicKey)
    let wrappingKey = shared.hkdfDerivedSymmetricKey(using: SHA256.self, salt: salt,
                                                     sharedInfo: devicePurpose, outputByteCount: 32)
    let recoveryWrapping = recoveryWrappingKey(recoveryKey, recoverySalt)
    let box = try AES.GCM.seal(dataKey, using: wrappingKey, authenticating: header)
    let recoveryBox = try AES.GCM.seal(dataKey, using: recoveryWrapping, authenticating: header)
    guard let combined = box.combined, let recovered = recoveryBox.combined,
          combined.count == 60, recovered.count == 60 else { throw Rejected.input }
    // Verify actual device agreement now; never silently substitute a software device key.
    let deviceShared = try device.sharedSecretFromKeyAgreement(with: ephemeral.publicKey)
    let deviceWrapping = deviceShared.hkdfDerivedSymmetricKey(using: SHA256.self, salt: salt,
                                                              sharedInfo: devicePurpose, outputByteCount: 32)
    guard try AES.GCM.open(box, using: deviceWrapping, authenticating: header) == dataKey,
          try AES.GCM.open(recoveryBox, using: recoveryWrapping, authenticating: header) == dataKey
          else { throw Rejected.verification }
    let envelope = header + combined + recovered
    let authentication = HMAC<SHA256>.authenticationCode(for: envelope,
                                                       using: envelopeIntegrityKey(dataKey, salt))
    return envelope + Data(authentication)
}

func unwrapWorkKey(_ envelope: Data, _ binding: Data, recoveryKey: Data? = nil) throws -> Data {
    guard envelope.count >= 387, envelope.count <= maxKeyBytes,
          envelope.prefix(6) == keyMagic, Data(envelope[6..<38]) == binding else { throw Rejected.input }
    let count = Int(envelope[232]) * 256 + Int(envelope[233])
    let headerSize = 234 + count
    guard (1...16384).contains(count), envelope.count == headerSize + 152 else { throw Rejected.input }
    let header = Data(envelope.prefix(headerSize))
    let key: SymmetricKey
    let boxStart: Int
    if let recoveryKey {
        guard recoveryKey.count == 32 else { throw Rejected.input }
        key = recoveryWrappingKey(recoveryKey, Data(envelope[200..<232]))
        boxStart = headerSize + 60
    } else {
        guard SecureEnclave.isAvailable else { throw Rejected.input }
        let device = try SecureEnclave.P256.KeyAgreement.PrivateKey(
            dataRepresentation: Data(envelope[234..<headerSize]), authenticationContext: noInteraction())
        guard device.publicKey.x963Representation == Data(envelope[38..<103]) else { throw Rejected.input }
        let ephemeral = try P256.KeyAgreement.PublicKey(x963Representation: Data(envelope[103..<168]))
        let shared = try device.sharedSecretFromKeyAgreement(with: ephemeral)
        key = shared.hkdfDerivedSymmetricKey(using: SHA256.self, salt: Data(envelope[168..<200]),
                                             sharedInfo: devicePurpose, outputByteCount: 32)
        boxStart = headerSize
    }
    let box = try AES.GCM.SealedBox(combined: Data(envelope[boxStart..<boxStart + 60]))
    let result = try AES.GCM.open(box, using: key, authenticating: header)
    guard result.count == 32,
          HMAC<SHA256>.isValidAuthenticationCode(Data(envelope.suffix(32)),
            authenticating: Data(envelope.dropLast(32)),
            using: envelopeIntegrityKey(result, Data(envelope[168..<200]))) else { throw Rejected.verification }
    return result
}

do {
    let arguments = Array(CommandLine.arguments.dropFirst())
    guard arguments.count == 1 else { throw Rejected.input }
    if arguments == ["check"] {
        guard try readInput(0).isEmpty else { throw Rejected.input }
        try knownAnswers()
        try FileHandle.standardOutput.write(contentsOf: Data("work-crypto-ok\n".utf8))
    } else if ["work-seal-bound", "work-open-bound"].contains(arguments[0]) {
        let input = try readInput(64 + maxPlaintext + overhead)
        guard input.count > 64 else { throw Rejected.input }
        let key = boundContentKey(Data(input[32..<64]), Data(input.prefix(32)))
        let payload = Data(input.dropFirst(64))
        let output = try arguments[0] == "work-seal-bound" ? seal(payload, key) : open(payload, key)
        try FileHandle.standardOutput.write(contentsOf: output)
    } else if arguments == ["key-create"] {
        let output = try createWorkKey(readInput(96))
        try FileHandle.standardOutput.write(contentsOf: output)
    } else if arguments == ["key-open"] {
        let input = try readInput(32 + maxKeyBytes)
        guard input.count > 32 else { throw Rejected.input }
        let key = try unwrapWorkKey(Data(input.dropFirst(32)), Data(input.prefix(32)))
        try FileHandle.standardOutput.write(contentsOf: key)
    } else if arguments == ["key-recover"] {
        let input = try readInput(64 + maxKeyBytes)
        guard input.count > 64 else { throw Rejected.input }
        let key = try unwrapWorkKey(Data(input.dropFirst(64)), Data(input.prefix(32)),
                                   recoveryKey: Data(input[32..<64]))
        try FileHandle.standardOutput.write(contentsOf: key)
    } else {
        guard ["seal", "open"].contains(arguments[0]) else { throw Rejected.input }
        let input = try readInput(32 + maxPlaintext + overhead)
        guard input.count > 32 else { throw Rejected.input }
        let key = Data(input.prefix(32)), payload = Data(input.dropFirst(32))
        let result = try arguments[0] == "seal" ? seal(payload, key) : open(payload, key)
        try FileHandle.standardOutput.write(contentsOf: result)
    }
} catch {
    try? FileHandle.standardError.write(contentsOf: Data("work-crypto-rejected\n".utf8))
    exit(2)
}
