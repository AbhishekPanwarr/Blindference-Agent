import { randomBytes, createCipheriv, createDecipheriv } from 'crypto'

/**
 * Generate a random 256-bit AES key.
 */
export function generateAesKey(): Buffer {
  return randomBytes(32)
}

/**
 * Encrypt plaintext with AES-256-GCM.
 * Returns { iv, authTag, ciphertext }.
 */
export function encryptAesGcm(plaintext: string, key: Buffer): { iv: Buffer; authTag: Buffer; ciphertext: Buffer } {
  const iv = randomBytes(12) // 12-byte IV for GCM (NIST standard)
  const cipher = createCipheriv('aes-256-gcm', key, iv)
  const ciphertext = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()])
  const authTag = cipher.getAuthTag()
  return { iv, authTag, ciphertext }
}

/**
 * Decrypt AES-256-GCM ciphertext.
 */
export function decryptAesGcm(ciphertext: Buffer, key: Buffer, iv: Buffer, authTag: Buffer): string {
  const decipher = createDecipheriv('aes-256-gcm', key, iv)
  decipher.setAuthTag(authTag)
  const plaintext = Buffer.concat([decipher.update(ciphertext), decipher.final()])
  return plaintext.toString('utf8')
}

/**
 * Pack IV + authTag + ciphertext into a single buffer for storage/transmission.
 * Format: [iv (12 bytes)][authTag (16 bytes)][ciphertext (variable)].
 */
export function packAesPayload(iv: Buffer, authTag: Buffer, ciphertext: Buffer): Buffer {
  return Buffer.concat([iv, authTag, ciphertext])
}

/**
 * Unpack a packed AES payload.
 */
export function unpackAesPayload(packed: Buffer): { iv: Buffer; authTag: Buffer; ciphertext: Buffer } {
  if (packed.length < 28) {
    throw new Error('Packed payload too short (must be at least 28 bytes)')
  }
  return {
    iv: packed.subarray(0, 12),
    authTag: packed.subarray(12, 28),
    ciphertext: packed.subarray(28),
  }
}

/**
 * Split a 32-byte AES key into two 16-byte halves for CoFHE uint128 encryption.
 */
export function splitKeyForCofhe(key: Buffer): { high: bigint; low: bigint } {
  if (key.length !== 32) {
    throw new Error(`Key must be 32 bytes, got ${key.length}`)
  }
  const high = BigInt('0x' + key.subarray(0, 16).toString('hex'))
  const low = BigInt('0x' + key.subarray(16, 32).toString('hex'))
  return { high, low }
}

/**
 * Combine two uint128 halves back into a 32-byte AES key.
 */
export function combineKeyHalves(high: bigint, low: bigint): Buffer {
  const key = Buffer.alloc(32)
  key.write(high.toString(16).padStart(32, '0'), 0, 16, 'hex')
  key.write(low.toString(16).padStart(32, '0'), 16, 16, 'hex')
  return key
}

/**
 * Upload encrypted payload to IPFS via Pinata.
 */
export async function uploadToIpfs(data: Buffer, jwt: string, filename = 'blindference-payload.bin'): Promise<string> {
  const FormData = (await import('form-data')).default
  const form = new FormData()
  form.append('file', data, { filename })

  const resp = await fetch('https://api.pinata.cloud/pinning/pinFileToIPFS', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${jwt}`,
      ...form.getHeaders(),
    },
    body: form as any,
  })

  if (!resp.ok) {
    throw new Error(`IPFS upload failed: ${resp.status} ${resp.statusText}`)
  }

  const result = (await resp.json()) as { IpfsHash: string }
  return result.IpfsHash
}

/**
 * Download encrypted payload from IPFS gateway.
 */
export async function downloadFromIpfs(cid: string, gateway = 'https://gateway.pinata.cloud/ipfs'): Promise<Buffer> {
  const resp = await fetch(`${gateway}/${cid}`)
  if (!resp.ok) {
    throw new Error(`IPFS download failed: ${resp.status} ${resp.statusText}`)
  }
  return Buffer.from(await resp.arrayBuffer())
}
