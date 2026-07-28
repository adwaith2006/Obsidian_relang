#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monocypher CLI — Python reimplementation.
Reads function name + hex params from stdin, writes hex results to stdout.
Protocol: <function_name>\n then <hex_param>:\n per param.
Output: <hex_result>:\n per result.
"""
import sys
import hashlib
import hmac as _hmac
import struct
from typing import Callable

# ── I/O helpers ───────────────────────────────────────────────────────────────

def read_line() -> str:
    line = sys.stdin.readline()
    if not line:
        sys.stderr.write("unexpected EOF\n"); sys.exit(1)
    return line.rstrip('\n\r').rstrip(':').rstrip()

def read_hex() -> bytes:
    line = read_line()
    if line == '': return b''
    if len(line) % 2 != 0:
        sys.stderr.write(f"odd hex len: {line}\n"); sys.exit(1)
    return bytes.fromhex(line)

def print_hex(data: bytes) -> None:
    sys.stdout.write(data.hex() + ':\n')

def print_u64_le(v: int) -> None:
    print_hex(v.to_bytes(8, 'little'))

def load64_le(b: bytes) -> int: return int.from_bytes(b[:8], 'little')
def load32_le(b: bytes) -> int: return int.from_bytes(b[:4], 'little')

# ── Constant-time comparison ──────────────────────────────────────────────────

def _ct_compare(a: bytes, b: bytes) -> int:
    if len(a) != len(b): return 0xff
    diff = 0
    for x, y in zip(a, b): diff |= x ^ y
    return 0 if diff == 0 else 0xff

def do_crypto_verify16():
    a=read_hex(); b=read_hex()
    res = _ct_compare(a[:16], b[:16])
    sys.stdout.write("00:\n" if res == 0 else "ffffffff:\n")

def do_crypto_verify32():
    a=read_hex(); b=read_hex()
    res = _ct_compare(a[:32], b[:32])
    sys.stdout.write("00:\n" if res == 0 else "ffffffff:\n")

def do_crypto_verify64():
    a=read_hex(); b=read_hex()
    res = _ct_compare(a[:64], b[:64])
    sys.stdout.write("00:\n" if res == 0 else "ffffffff:\n")
def do_crypto_wipe():
    data=read_hex(); print_hex(bytes(len(data)))

# ── ChaCha20 ──────────────────────────────────────────────────────────────────

_M32 = 0xFFFFFFFF
def _r32(v,n): return ((v<<n)|(v>>(32-n)))&_M32

def _qr(a,b,c,d):
    a=(a+b)&_M32; d^=a; d=_r32(d,16)
    c=(c+d)&_M32; b^=c; b=_r32(b,12)
    a=(a+b)&_M32; d^=a; d=_r32(d, 8)
    c=(c+d)&_M32; b^=c; b=_r32(b, 7)
    return a,b,c,d

def _chacha20_block(state: list) -> bytes:
    x = list(state)
    for _ in range(10):
        x[0],x[4],x[8], x[12]=_qr(x[0],x[4],x[8], x[12])
        x[1],x[5],x[9], x[13]=_qr(x[1],x[5],x[9], x[13])
        x[2],x[6],x[10],x[14]=_qr(x[2],x[6],x[10],x[14])
        x[3],x[7],x[11],x[15]=_qr(x[3],x[7],x[11],x[15])
        x[0],x[5],x[10],x[15]=_qr(x[0],x[5],x[10],x[15])
        x[1],x[6],x[11],x[12]=_qr(x[1],x[6],x[11],x[12])
        x[2],x[7],x[8], x[13]=_qr(x[2],x[7],x[8], x[13])
        x[3],x[4],x[9], x[14]=_qr(x[3],x[4],x[9], x[14])
    out=bytearray(64)
    for i in range(16):
        struct.pack_into('<I',out,i*4,(x[i]+state[i])&_M32)
    return bytes(out)

def _init_djb(key,nonce,ctr):
    c=[0x61707865,0x3320646e,0x79622d32,0x6b206574]
    k=struct.unpack('<8I',key[:32]); n=struct.unpack('<2I',nonce[:8])
    return [c[0],c[1],c[2],c[3],k[0],k[1],k[2],k[3],k[4],k[5],k[6],k[7],
            ctr&_M32,(ctr>>32)&_M32,n[0],n[1]]

def _init_ietf(key,nonce,ctr):
    c=[0x61707865,0x3320646e,0x79622d32,0x6b206574]
    k=struct.unpack('<8I',key[:32]); n=struct.unpack('<3I',nonce[:12])
    return [c[0],c[1],c[2],c[3],k[0],k[1],k[2],k[3],k[4],k[5],k[6],k[7],
            ctr&_M32,n[0],n[1],n[2]]

def chacha20_djb(pt,key,nonce,ctr):
    st=_init_djb(key,nonce,ctr); out=bytearray()
    lo=ctr&_M32; hi=(ctr>>32)&_M32
    for i in range(0,len(pt),64):
        blk=_chacha20_block(st); chunk=pt[i:i+64]
        out.extend(a^b for a,b in zip(chunk,blk))
        lo=(lo+1)&_M32
        if lo==0: hi=(hi+1)&_M32
        st[12]=lo; st[13]=hi
    return bytes(out), lo|(hi<<32)

def chacha20_ietf(pt,key,nonce,ctr):
    st=_init_ietf(key,nonce,ctr); out=bytearray(); c=ctr&_M32
    for i in range(0,len(pt),64):
        blk=_chacha20_block(st); chunk=pt[i:i+64]
        out.extend(a^b for a,b in zip(chunk,blk))
        c=(c+1)&_M32; st[12]=c
    return bytes(out), c

def chacha20_h(key,inp):
    c=[0x61707865,0x3320646e,0x79622d32,0x6b206574]
    k=struct.unpack('<8I',key[:32]); n=struct.unpack('<4I',inp[:16])
    st=[c[0],c[1],c[2],c[3],k[0],k[1],k[2],k[3],k[4],k[5],k[6],k[7],n[0],n[1],n[2],n[3]]
    x=list(st)
    for _ in range(10):
        x[0],x[4],x[8], x[12]=_qr(x[0],x[4],x[8], x[12])
        x[1],x[5],x[9], x[13]=_qr(x[1],x[5],x[9], x[13])
        x[2],x[6],x[10],x[14]=_qr(x[2],x[6],x[10],x[14])
        x[3],x[7],x[11],x[15]=_qr(x[3],x[7],x[11],x[15])
        x[0],x[5],x[10],x[15]=_qr(x[0],x[5],x[10],x[15])
        x[1],x[6],x[11],x[12]=_qr(x[1],x[6],x[11],x[12])
        x[2],x[7],x[8], x[13]=_qr(x[2],x[7],x[8], x[13])
        x[3],x[4],x[9], x[14]=_qr(x[3],x[4],x[9], x[14])
    out=bytearray(32)
    for i,idx in enumerate([0,1,2,3,12,13,14,15]):
        struct.pack_into('<I',out,i*4,x[idx]&_M32)
    return bytes(out)

def chacha20_x(pt,key,nonce,ctr):
    sub=chacha20_h(key,nonce[:16])
    nn=nonce[16:24]
    return chacha20_djb(pt,sub,nn,ctr)

def do_crypto_chacha20_h():
    print_hex(chacha20_h(read_hex(),read_hex()))
def do_crypto_chacha20_djb():
    key=read_hex(); nonce=read_hex(); pt=read_hex(); cb=read_hex()
    ct,nc=chacha20_djb(pt,key,nonce,load64_le(cb))
    print_hex(ct); print_u64_le(nc)
def do_crypto_chacha20_ietf():
    key=read_hex(); nonce=read_hex(); pt=read_hex(); cb=read_hex()
    ct,nc=chacha20_ietf(pt,key,nonce,load32_le(cb))
    print_hex(ct); print_hex((nc&_M32).to_bytes(4,'little'))
def do_crypto_chacha20_x():
    key=read_hex(); nonce=read_hex(); pt=read_hex(); cb=read_hex()
    ct,nc=chacha20_x(pt,key,nonce,load64_le(cb))
    print_hex(ct); print_u64_le(nc)

# ── Poly1305 ──────────────────────────────────────────────────────────────────

_POLYP = (1<<130)-5

def poly1305(msg,key):
    r=int.from_bytes(key[:16],'little')&0x0ffffffc0ffffffc0ffffffc0fffffff
    s=int.from_bytes(key[16:32],'little'); acc=0
    for i in range(0,len(msg),16):
        blk=msg[i:i+16]
        n=int.from_bytes(blk,'little')+(1<<(8*len(blk)))
        acc=r*(acc+n)%_POLYP
    return ((acc+s)&((1<<128)-1)).to_bytes(16,'little')

def do_crypto_poly1305():
    key=read_hex(); msg=read_hex(); print_hex(poly1305(msg,key))

# ── AEAD (XChaCha20-Poly1305) ─────────────────────────────────────────────────

def _pad16(d): r=len(d)%16; return d+(b'\x00'*(16-r)) if r else d

def _mac(poly_key,ad,ct):
    data=_pad16(ad)+_pad16(ct)+len(ad).to_bytes(8,'little')+len(ct).to_bytes(8,'little')
    return poly1305(data,poly_key)

def aead_lock(pt,key,nonce,ad):
    sub=chacha20_h(key,nonce[:16]); sn=b'\x00'*4+nonce[16:24]
    pkey=_chacha20_block(_init_djb(sub,sn,0))[:32]
    ct,_=chacha20_djb(pt,sub,sn,1)
    return ct, _mac(pkey,ad,ct)

def aead_unlock(ct,mac,key,nonce,ad):
    sub=chacha20_h(key,nonce[:16]); sn=b'\x00'*4+nonce[16:24]
    pkey=_chacha20_block(_init_djb(sub,sn,0))[:32]
    if _ct_compare(mac,_mac(pkey,ad,ct))!=0: return b'',-1
    pt,_=chacha20_djb(ct,sub,nonce[16:24],1); return pt,0

def do_crypto_aead_lock():
    key=read_hex(); nonce=read_hex(); ad=read_hex(); pt=read_hex()
    ct,mac=aead_lock(pt,key,nonce,ad); print_hex(ct); print_hex(mac)

def do_crypto_aead_unlock():
    key=read_hex(); nonce=read_hex(); ad=read_hex(); ct=read_hex(); mac=read_hex()
    pt,r=aead_unlock(ct,mac,key,nonce,ad)
    if r==0: print_hex(pt)
    sys.stdout.write(f"{'00' if r==0 else 'ff'}:\n")

# AEAD streaming context
# C struct crypto_aead_ctx layout: key[32] + counter[8] + nonce[8] = 48 bytes
def do_crypto_aead_init_x():
    key=read_hex(); nonce=read_hex()
    sub=chacha20_h(key,nonce[:16])
    print_hex((0).to_bytes(8,'little') + sub + nonce[16:24])

def do_crypto_aead_init_djb():
    key=read_hex(); nonce=read_hex()
    print_hex((0).to_bytes(8,'little') + key + nonce[:8])

def do_crypto_aead_init_ietf():
    key=read_hex(); nonce=read_hex()
    ctr = (0).to_bytes(4,'little') + nonce[:4]
    print_hex(ctr + key + nonce[4:12])

def do_crypto_aead_write():
    key=read_hex(); nonce=read_hex(); ad=read_hex(); pt=read_hex()
    # init_ietf:
    ctx_key = key
    ctx_ctr = load32_le(nonce[:4]) << 32
    ctx_nonce = nonce[4:12]
    # write:
    auth_key, _ = chacha20_djb(bytes(64), ctx_key, ctx_nonce, ctx_ctr)
    ct, _ = chacha20_djb(pt, ctx_key, ctx_nonce, ctx_ctr + 1)
    mac = _mac(auth_key[:32], ad, ct)
    print_hex(ct); print_hex(mac)

# ── BLAKE2b ───────────────────────────────────────────────────────────────────

def do_crypto_blake2b():
    msg=read_hex(); print_hex(hashlib.blake2b(msg,digest_size=64).digest())

def do_crypto_blake2b_keyed():
    msg=read_hex(); key=read_hex(); ks=min(len(key),64)
    print_hex(hashlib.blake2b(msg,digest_size=64,key=key[:ks]).digest())

# ── SHA-512, HMAC, HKDF ───────────────────────────────────────────────────────

def _sha512(*parts):
    h=hashlib.sha512()
    for p in parts: h.update(p)
    return h.digest()

def _hmac512(key,msg):
    return _hmac.new(key,msg,hashlib.sha512).digest()

def do_crypto_sha512():
    print_hex(_sha512(read_hex()))

def do_crypto_sha512_hmac():
    key=read_hex(); msg=read_hex(); print_hex(_hmac512(key,msg))

def do_crypto_sha512_hkdf():
    ikm=read_hex(); salt=read_hex(); info=read_hex(); okm_ph=read_hex()
    okm_size=len(okm_ph)
    if not salt: salt=bytes(64)
    prk=_hmac512(salt,ikm)
    okm=b''; prev=b''; i=1
    while len(okm)<okm_size:
        prev=_hmac512(prk,prev+info+bytes([i])); okm+=prev; i+=1
    print_hex(okm[:okm_size])

# ── Argon2 ────────────────────────────────────────────────────────────────────

ARGON2_VERSION = 0x13
_U64 = (1<<64)-1

def _b2long(data, length):
    lb = length.to_bytes(4,'little')
    if length <= 64:
        return hashlib.blake2b(lb+data, digest_size=length).digest()
    out=bytearray()
    a=hashlib.blake2b(lb+data, digest_size=64).digest()
    out.extend(a[:32]); rem=length-32
    while rem>64:
        a=hashlib.blake2b(a,digest_size=64).digest()
        out.extend(a[:32]); rem-=32
    out.extend(hashlib.blake2b(a,digest_size=rem).digest())
    return bytes(out)

def _gb(a,b,c,d):
    a=(a+b+2*(a&0xFFFFFFFF)*(b&0xFFFFFFFF))&_U64
    d=d^a; d=((d>>32)|(d<<32))&_U64
    c=(c+d+2*(c&0xFFFFFFFF)*(d&0xFFFFFFFF))&_U64
    b=b^c; b=((b>>24)|(b<<40))&_U64
    a=(a+b+2*(a&0xFFFFFFFF)*(b&0xFFFFFFFF))&_U64
    d=d^a; d=((d>>16)|(d<<48))&_U64
    c=(c+d+2*(c&0xFFFFFFFF)*(d&0xFFFFFFFF))&_U64
    b=b^c; b=((b>>63)|(b<<1))&_U64
    return a,b,c,d

def _argon2_G(X,Y):
    R=[X[i]^Y[i] for i in range(128)]; Z=list(R)
    def gb(v,a,b,c,d): v[a],v[b],v[c],v[d]=_gb(v[a],v[b],v[c],v[d])
    for i in range(8):
        b=i*16
        gb(Z,b+0,b+4,b+8, b+12); gb(Z,b+1,b+5,b+9, b+13)
        gb(Z,b+2,b+6,b+10,b+14); gb(Z,b+3,b+7,b+11,b+15)
        gb(Z,b+0,b+5,b+10,b+15); gb(Z,b+1,b+6,b+11,b+12)
        gb(Z,b+2,b+7,b+8, b+13); gb(Z,b+3,b+4,b+9, b+14)
    for i in range(16):
        ii=[i+16*j for j in range(8)]
        gb(Z,ii[0],ii[1],ii[2],ii[3]); gb(Z,ii[4],ii[5],ii[6],ii[7])
        gb(Z,ii[0],ii[4],ii[2],ii[6]); gb(Z,ii[1],ii[5],ii[3],ii[7])
    return [Z[i]^R[i] for i in range(128)]

def crypto_argon2(hash_size,password,salt,key,ad,algo,m_cost,t_cost,lanes):
    SP=4
    seg=max(m_cost//(lanes*SP),1); ll=seg*SP; mem=lanes*ll
    h0_in=(lanes.to_bytes(4,'little')+hash_size.to_bytes(4,'little')+
            m_cost.to_bytes(4,'little')+t_cost.to_bytes(4,'little')+
            ARGON2_VERSION.to_bytes(4,'little')+algo.to_bytes(4,'little')+
            len(password).to_bytes(4,'little')+password+
            len(salt).to_bytes(4,'little')+salt+
            len(key).to_bytes(4,'little')+key+
            len(ad).to_bytes(4,'little')+ad)
    h0=hashlib.blake2b(h0_in,digest_size=64).digest()
    blocks=[[0]*128 for _ in range(mem)]
    for l in range(lanes):
        for b2 in range(2):
            seed=h0+b2.to_bytes(4,'little')+l.to_bytes(4,'little')
            blocks[l*ll+b2]=list(struct.unpack('<128Q',_b2long(seed,1024)))
    for t in range(t_cost):
        for s in range(SP):
            for l in range(lanes):
                start=2 if (t==0 and s==0) else (0 if s==0 else 1)
                for bi in range(start,seg):
                    ci=l*ll+s*seg+bi
                    pi=ci-1
                    if s==0 and bi==0: pi=l*ll+ll-1
                    pb=blocks[pi]; J1=pb[0]; J2=(pb[1]>>32)&_U64
                    if t==0 and s<=1: rl=l
                    else: rl=int(J2)%lanes
                    if rl==l:
                        rs=(s*seg+bi-1) if t==0 else (ll-seg+bi-1 if s==0 else 3*seg+bi-1)
                    else:
                        rs=s*seg-(1 if bi==0 else 0) if t==0 else 3*seg-(1 if bi==0 else 0)
                    if rs<=0: rs=1
                    y=(J1*J1)>>32; z=(rs*y)>>32
                    ref_pos=rs-1-z
                    sp=0 if t==0 else (((s+1)*seg)%ll if s!=3 else 0)
                    ri=(sp+int(ref_pos))%ll
                    rb=rl*ll+ri
                    nb=_argon2_G(pb,blocks[rb])
                    if t==0: blocks[ci]=nb
                    else: blocks[ci]=[blocks[ci][i]^nb[i] for i in range(128)]
    fin=list(blocks[ll-1])
    for l in range(1,lanes):
        idx=l*ll+ll-1
        for i in range(128): fin[i]^=blocks[idx][i]
    return _b2long(struct.pack('<128Q',*fin),hash_size)

def do_crypto_argon2():
    algo_b=read_hex(); blk_b=read_hex(); pass_b=read_hex(); lane_b=read_hex()
    pw=read_hex(); salt=read_hex(); key=read_hex(); ad=read_hex(); hp=read_hex()
    print_hex(crypto_argon2(len(hp),pw,salt,key,ad,
        load32_le(algo_b),load32_le(blk_b),load32_le(pass_b),load32_le(lane_b)))

# ── X25519 / Curve25519 ───────────────────────────────────────────────────────

_P = (1<<255)-19

def _finv(n): return pow(n,_P-2,_P)
def _fsqrt(n): return pow(n,(_P+3)//8,_P)

def _clamp(sk):
    s=bytearray(sk[:32]); s[0]&=248; s[31]&=127; s[31]|=64
    return int.from_bytes(s,'little')

def _ladder(u,k):
    a24=121665; x1=u; x2,z2=1,0; x3,z3=u,1; sw=0
    for t in range(254,-1,-1):
        bit=(k>>t)&1; sw^=bit
        if sw: x2,x3=x3,x2; z2,z3=z3,z2
        sw=bit
        A=(x2+z2)%_P; AA=A*A%_P; B=(x2-z2)%_P; BB=B*B%_P; E=(AA-BB)%_P
        C=(x3+z3)%_P; D=(x3-z3)%_P; DA=D*A%_P; CB=C*B%_P
        x3=pow(DA+CB,2,_P); z3=x1*pow(DA-CB,2,_P)%_P
        x2=AA*BB%_P; z2=E*(AA+a24*E)%_P
    if sw: x2,x3=x3,x2; z2,z3=z3,z2
    return x2*_finv(z2)%_P

_BU=9

def do_crypto_x25519():
    sk=read_hex(); pk=read_hex()
    u=int.from_bytes(pk[:32],'little')%_P
    print_hex(_ladder(u,_clamp(sk)).to_bytes(32,'little'))

def do_crypto_x25519_public_key():
    sk=read_hex()
    print_hex(_ladder(_BU,_clamp(sk)).to_bytes(32,'little'))

def do_crypto_x25519_inverse():
    sk=read_hex(); pt=read_hex()
    k=int.from_bytes(sk[:32],'little')
    u=int.from_bytes(pt[:32],'little')%_P
    print_hex(_ladder(u,k).to_bytes(32,'little'))

def do_crypto_x25519_dirty_small():
    sk=read_hex(); k=int.from_bytes(sk[:32],'little')
    k&=~7; k|=(1<<254)
    print_hex(_ladder(_BU,k).to_bytes(32,'little'))

def do_crypto_x25519_dirty_fast():
    sk=read_hex(); k=int.from_bytes(sk[:32],'little')
    k&=~7; k|=(1<<254)
    print_hex(_ladder(_BU,k).to_bytes(32,'little'))

# ── Edwards curve (Ed25519 / EdDSA) ──────────────────────────────────────────

_Q=2**252+27742317777372353535851937790883648493
_GX=15112221349535400772501151409588531511454012693041857206046113283949847762202
_GY=46316835694926478169428394003475163141307993866256225615783033603165251855960
_d=37095705934669439343138083508754565189542113879843219016388785533085940283555

def _ed_add(P,Q):
    X1,Y1,Z1,T1=P; X2,Y2,Z2,T2=Q
    A=(Y1-X1)*(Y2-X2)%_P; B=(Y1+X1)*(Y2+X2)%_P
    C=T1*2*_d*T2%_P; D=Z1*2*Z2%_P
    E=B-A; F=D-C; G=D+C; H=B+A
    return E*F%_P, G*H%_P, F*G%_P, E*H%_P

def _ed_dbl(P):
    X1,Y1,Z1,T1=P
    A=X1*X1%_P; B=Y1*Y1%_P; C=2*Z1*Z1%_P
    E=((X1+Y1)*(X1+Y1)-A-B)%_P
    G=(B-A)%_P; F=(G-C)%_P; H=(-A-B)%_P
    return E*F%_P, G*H%_P, F*G%_P, E*H%_P

_BASE=(_GX%_P, _GY%_P, 1, _GX*_GY%_P)
_ID=(0,1,1,0)

def _smul(P,k):
    R=_ID
    while k:
        if k&1: R=_ed_add(R,P)
        P=_ed_dbl(P); k>>=1
    return R

def _compress(P):
    X,Y,Z,T=P; zi=_finv(Z); x=X*zi%_P; y=Y*zi%_P
    r=bytearray(y.to_bytes(32,'little')); r[31]^=(x&1)<<7; return bytes(r)

def _decompress(b32):
    b=bytearray(b32[:32]); sign=(b[31]>>7)&1; b[31]&=0x7f
    y=int.from_bytes(b,'little')
    if y>=_P: return None
    y2=y*y%_P; u=(y2-1)%_P; v=(_d*y2+1)%_P
    x=_fsqrt(u*_finv(v)%_P)
    if (x*x*v-u)%_P!=0:
        x=x*pow(2,(_P-1)//4,_P)%_P
    if (x*x*v-u)%_P!=0: return None
    if x==0 and sign==1: return None
    if x&1!=sign: x=_P-x
    return (x,y,1,x*y%_P)

def _chk_eq(SB,RkA):
    return SB[0]*RkA[2]%_P==RkA[0]*SB[2]%_P and SB[1]*RkA[2]%_P==RkA[1]*SB[2]%_P

# ── Monocypher EdDSA (Blake2b) ────────────────────────────────────────────────

def _bh(*parts):
    h=hashlib.blake2b(digest_size=64)
    for p in parts: h.update(p)
    return h.digest()

def _trim(s):
    b=bytearray(s[:32]); b[0]&=248; b[31]&=127; b[31]|=64
    return int.from_bytes(b,'little')

def _eddsa_kp(seed):
    h=_bh(seed); a=_trim(h[:32]); pk=_compress(_smul(_BASE,a))
    return seed[:32]+pk, pk

def _eddsa_sign(sk64,msg):
    h=_bh(sk64[:32]); a=_trim(h[:32]); pk=sk64[32:64]
    r=int.from_bytes(_bh(h[32:],msg),'little')%_Q
    R=_compress(_smul(_BASE,r))
    k=int.from_bytes(_bh(R,pk,msg),'little')%_Q
    S=(r+k*a)%_Q
    return R+S.to_bytes(32,'little')

def _eddsa_chk(sig,pk,msg):
    R=sig[:32]; S=int.from_bytes(sig[32:64],'little')
    if S>=_Q: return 0xff
    Rp=_decompress(R); Ap=_decompress(pk)
    if Rp is None or Ap is None: return 0xff
    k=int.from_bytes(_bh(R,pk,msg),'little')%_Q
    if _chk_eq(_smul(_BASE,S),_ed_add(Rp,_smul(Ap,k))): return 0
    return 0xff

def do_crypto_eddsa_key_pair():
    seed=read_hex(); sk,pk=_eddsa_kp(seed); print_hex(sk); print_hex(pk)

def do_crypto_eddsa_sign():
    sk=read_hex(); pk=read_hex(); msg=read_hex()
    print_hex(_eddsa_sign(sk[:32]+pk,msg))

def do_crypto_eddsa_check():
    sig=read_hex(); pk=read_hex(); msg=read_hex()
    sys.stdout.write(f"{_eddsa_chk(sig,pk,msg):02x}:\n")

def do_crypto_eddsa_trim_scalar():
    inp=read_hex(); b=bytearray(inp[:32])
    b[0]&=248; b[31]&=127; b[31]|=64; print_hex(bytes(b))

def do_crypto_eddsa_reduce():
    expanded=read_hex()
    print_hex((int.from_bytes(expanded[:64],'little')%_Q).to_bytes(32,'little'))

def do_crypto_eddsa_mul_add():
    a=read_hex(); b=read_hex(); c=read_hex()
    r=(int.from_bytes(a[:32],'little')*int.from_bytes(b[:32],'little')+
       int.from_bytes(c[:32],'little'))%_Q
    print_hex(r.to_bytes(32,'little'))

def do_crypto_eddsa_scalarbase():
    s=read_hex(); k=int.from_bytes(s[:32],'little')%_Q
    print_hex(_compress(_smul(_BASE,k)))

def do_crypto_eddsa_check_equation():
    sig=read_hex(); pk=read_hex(); hram=read_hex()
    R=sig[:32]; S=int.from_bytes(sig[32:64],'little')
    if S>=_Q: sys.stdout.write("ff:\n"); return
    Rp=_decompress(R); Ap=_decompress(pk)
    if Rp is None or Ap is None: sys.stdout.write("ff:\n"); return
    k=int.from_bytes(hram[:32],'little')%_Q
    rv=0 if _chk_eq(_smul(_BASE,S),_ed_add(Rp,_smul(Ap,k))) else 0xff
    sys.stdout.write(f"{rv:02x}:\n")

# ── Ed25519 (standard, SHA-512) ───────────────────────────────────────────────

def _sh(*parts):
    h=hashlib.sha512()
    for p in parts: h.update(p)
    return h.digest()

def _ed25519_kp(seed):
    a=_sh(seed[:32])
    sc=bytearray(a[:32]); sc[0]&=248; sc[31]&=127; sc[31]|=64
    pk=_compress(_smul(_BASE,int.from_bytes(sc,'little')))
    return seed[:32]+pk, pk

def _ed25519_sign(sk64,msg,dom=b''):
    a=_sh(sk64[:32])
    sc=bytearray(a[:32]); sc[0]&=248; sc[31]&=127; sc[31]|=64
    sc_val=int.from_bytes(sc,'little')
    pk=sk64[32:64]
    r_hash=_sh(dom,a[32:64],msg)
    r=int.from_bytes(r_hash[:64],'little')%_Q
    R=_compress(_smul(_BASE,r))
    h_hash=_sh(dom,R,pk,msg)
    h=int.from_bytes(h_hash[:64],'little')%_Q
    S=(r+h*sc_val)%_Q
    return R+S.to_bytes(32,'little')

def _ed25519_chk(sig,pk,msg,dom=b''):
    R=sig[:32]; S=int.from_bytes(sig[32:64],'little')
    if S>=_Q: return 0xff
    Rp=_decompress(R); Ap=_decompress(pk)
    if Rp is None or Ap is None: return 0xff
    h_hash=_sh(dom,R,pk,msg)
    h=int.from_bytes(h_hash[:64],'little')%_Q
    if _chk_eq(_smul(_BASE,S),_ed_add(Rp,_smul(Ap,h))): return 0
    return 0xff

def do_crypto_ed25519_key_pair():
    seed=read_hex(); sk,pk=_ed25519_kp(seed); print_hex(sk); print_hex(pk)

def do_crypto_ed25519_sign():
    sk=read_hex(); pk=read_hex(); msg=read_hex()
    print_hex(_ed25519_sign(sk[:32]+pk,msg))

def do_crypto_ed25519_check():
    sig=read_hex(); pk=read_hex(); msg=read_hex()
    sys.stdout.write(f"{_ed25519_chk(sig,pk,msg):02x}:\n")

_ED25519_PH_PREFIX=b'SigEd25519 no Ed25519 collisions\x01\x00'

def do_crypto_ed25519_ph_sign():
    sk=read_hex(); pk=read_hex(); hv=read_hex()
    print_hex(_ed25519_sign(sk[:32]+pk,hv,_ED25519_PH_PREFIX))

def do_crypto_ed25519_ph_check():
    sig=read_hex(); pk=read_hex(); hv=read_hex()
    sys.stdout.write(f"{_ed25519_chk(sig,pk,hv,_ED25519_PH_PREFIX):02x}:\n")

# ── Elligator 2 ───────────────────────────────────────────────────────────────

_A25519=486662
_SQRT_M1=pow(2,(_P-1)//4,_P)

def _invsqrt(x):
    x=x%_P
    if x==0: return True, 0
    t0=pow(x,(_P-5)//8,_P)
    quartic=(t0*t0%_P*x)%_P
    p1=(quartic==1); m1=(quartic==_P-1); ms=(quartic==(_P-_SQRT_M1)%_P)
    if m1 or ms: isr=(t0*_SQRT_M1)%_P
    else: isr=t0
    return bool(p1 or m1), isr

def do_crypto_elligator_map():
    hid=read_hex(); b=bytearray(hid[:32]); b[31]&=0x3f
    r=int.from_bytes(b,'little')
    v=(1+2*r*r)%_P; vi=_finv(v)
    u=(-_A25519*vi)%_P
    rhs=(u*u*u + _A25519*u*u + u)%_P
    is_sq, _ = _invsqrt(rhs)
    if not is_sq:
        u=(-u-_A25519)%_P
    print_hex(u.to_bytes(32,'little'))

def do_crypto_elligator_rev():
    pt=read_hex(); tl=read_line(); tweak=int(tl,16) if tl else 0
    b=bytearray(pt[:32]); b[31]&=0x7f
    u=int.from_bytes(b,'little')%_P
    t2=(u+_A25519)%_P; t3=(-2*u*t2)%_P
    is_sq, isr = _invsqrt(t3)
    if not is_sq:
        sys.stdout.write("ff:\n")
        return
    t1=t2 if (tweak&1) else u
    t3=(t1*isr)%_P; t1=(2*t3)%_P; t2=(-t3)%_P
    if t1&1: t3=t2
    hidden=bytearray(t3.to_bytes(32,'little'))
    hidden[31]|=(tweak&0xc0)
    print_hex(bytes(hidden))
    sys.stdout.write("00:\n")

def do_crypto_elligator_key_pair():
    seed=read_hex()
    buf=bytearray(64)
    buf[32:64]=seed[:32]
    while True:
        out64, _ = chacha20_djb(bytes(64), buf[32:64], bytes(8), 0)
        buf[:64] = out64
        sk_b = bytearray(buf[:32])
        sk_b[0] &= 248; sk_b[31] &= 127; sk_b[31] |= 64
        k = int.from_bytes(sk_b, 'little')
        u = _ladder(_BU, k)

        tweak = buf[32]
        b = bytearray(u.to_bytes(32, 'little')); b[31] &= 0x7f
        u_val = int.from_bytes(b, 'little') % _P
        t2 = (u_val + _A25519) % _P
        t3 = (-2 * u_val * t2) % _P
        is_sq, isr = _invsqrt(t3)
        if is_sq:
            t1 = t2 if (tweak & 1) else u_val
            t3 = (t1 * isr) % _P; t1_check = (2 * t3) % _P; t2_neg = (-t3) % _P
            if t1_check & 1: t3 = t2_neg
            hidden = bytearray(t3.to_bytes(32, 'little'))
            hidden[31] |= (tweak & 0xc0)
            print_hex(bytes(hidden))
            print_hex(bytes(buf[:32]))
            break

# ── Curve conversions ─────────────────────────────────────────────────────────

def do_crypto_eddsa_to_x25519():
    ep=read_hex(); b=bytearray(ep[:32]); b[31]&=0x7f
    y=int.from_bytes(b,'little')%_P
    u=(1+y)*_finv((1-y)%_P)%_P
    print_hex(u.to_bytes(32,'little'))

def do_crypto_x25519_to_eddsa():
    xp=read_hex(); b=bytearray(xp[:32]); b[31]&=0x7f
    u=int.from_bytes(b,'little')%_P
    y=(u-1)*_finv((u+1)%_P)%_P
    print_hex(y.to_bytes(32,'little'))

# ── Dispatch ──────────────────────────────────────────────────────────────────

DISPATCH={
    "crypto_verify16":             do_crypto_verify16,
    "crypto_verify32":             do_crypto_verify32,
    "crypto_verify64":             do_crypto_verify64,
    "crypto_wipe":                 do_crypto_wipe,
    "crypto_chacha20_h":           do_crypto_chacha20_h,
    "crypto_chacha20_djb":         do_crypto_chacha20_djb,
    "crypto_chacha20_ietf":        do_crypto_chacha20_ietf,
    "crypto_chacha20_x":           do_crypto_chacha20_x,
    "crypto_poly1305":             do_crypto_poly1305,
    "crypto_aead_lock":            do_crypto_aead_lock,
    "crypto_aead_unlock":          do_crypto_aead_unlock,
    "crypto_blake2b":              do_crypto_blake2b,
    "crypto_blake2b_keyed":        do_crypto_blake2b_keyed,
    "crypto_sha512":               do_crypto_sha512,
    "crypto_sha512_hmac":          do_crypto_sha512_hmac,
    "crypto_sha512_hkdf":          do_crypto_sha512_hkdf,
    "crypto_argon2":               do_crypto_argon2,
    "crypto_x25519":               do_crypto_x25519,
    "crypto_x25519_public_key":    do_crypto_x25519_public_key,
    "crypto_x25519_inverse":       do_crypto_x25519_inverse,
    "crypto_x25519_dirty_small":   do_crypto_x25519_dirty_small,
    "crypto_x25519_dirty_fast":    do_crypto_x25519_dirty_fast,
    "crypto_eddsa_key_pair":       do_crypto_eddsa_key_pair,
    "crypto_eddsa_sign":           do_crypto_eddsa_sign,
    "crypto_eddsa_check":          do_crypto_eddsa_check,
    "crypto_eddsa_trim_scalar":    do_crypto_eddsa_trim_scalar,
    "crypto_eddsa_reduce":         do_crypto_eddsa_reduce,
    "crypto_eddsa_mul_add":        do_crypto_eddsa_mul_add,
    "crypto_eddsa_scalarbase":     do_crypto_eddsa_scalarbase,
    "crypto_eddsa_check_equation": do_crypto_eddsa_check_equation,
    "crypto_ed25519_key_pair":     do_crypto_ed25519_key_pair,
    "crypto_ed25519_sign":         do_crypto_ed25519_sign,
    "crypto_ed25519_check":        do_crypto_ed25519_check,
    "crypto_ed25519_ph_sign":      do_crypto_ed25519_ph_sign,
    "crypto_ed25519_ph_check":     do_crypto_ed25519_ph_check,
    "crypto_elligator_map":        do_crypto_elligator_map,
    "crypto_elligator_rev":        do_crypto_elligator_rev,
    "crypto_elligator_key_pair":   do_crypto_elligator_key_pair,
    "crypto_eddsa_to_x25519":      do_crypto_eddsa_to_x25519,
    "crypto_x25519_to_eddsa":      do_crypto_x25519_to_eddsa,
    "crypto_aead_init_x":          do_crypto_aead_init_x,
    "crypto_aead_init_djb":        do_crypto_aead_init_djb,
    "crypto_aead_init_ietf":       do_crypto_aead_init_ietf,
    "crypto_aead_write":           do_crypto_aead_write,
}

def main():
    fn=sys.stdin.readline()
    if not fn: sys.stderr.write("empty input\n"); sys.exit(1)
    fn=fn.strip()
    h=DISPATCH.get(fn)
    if h is None: sys.stderr.write(f"unknown function: {fn}\n"); sys.exit(1)
    h()

if __name__=="__main__":
    main()