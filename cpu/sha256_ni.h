/* SHA-256 compression with SHA-NI, explicit midstate. state[] is in standard word order
 * (a..h); block is 64 bytes in message byte order. Based on the Intel SHA extensions
 * reference sequence. */
#pragma once
#include <immintrin.h>
#include <stdint.h>

static inline void sha256_compress_ni(uint32_t state[8], const uint8_t block[64]) {
    const __m128i MASK = _mm_set_epi64x(0x0c0d0e0f08090a0bULL, 0x0405060700010203ULL);
    __m128i tmp = _mm_loadu_si128((const __m128i *)&state[0]);
    __m128i st1 = _mm_loadu_si128((const __m128i *)&state[4]);
    tmp = _mm_shuffle_epi32(tmp, 0xB1);                /* CDAB */
    st1 = _mm_shuffle_epi32(st1, 0x1B);                /* EFGH */
    __m128i st0 = _mm_alignr_epi8(tmp, st1, 8);        /* ABEF */
    st1 = _mm_blend_epi16(st1, tmp, 0xF0);             /* CDGH */
    __m128i abef = st0, cdgh = st1, msg, m0, m1, m2, m3;

    m0 = _mm_shuffle_epi8(_mm_loadu_si128((const __m128i *)(block + 0)), MASK);
    m1 = _mm_shuffle_epi8(_mm_loadu_si128((const __m128i *)(block + 16)), MASK);
    m2 = _mm_shuffle_epi8(_mm_loadu_si128((const __m128i *)(block + 32)), MASK);
    m3 = _mm_shuffle_epi8(_mm_loadu_si128((const __m128i *)(block + 48)), MASK);

#define RND4(mA, k1, k0)                                                   \
    msg = _mm_add_epi32(mA, _mm_set_epi64x(k1, k0));                       \
    st1 = _mm_sha256rnds2_epu32(st1, st0, msg);                            \
    msg = _mm_shuffle_epi32(msg, 0x0E);                                    \
    st0 = _mm_sha256rnds2_epu32(st0, st1, msg);
#define SCHED(mA, mB, mC, mD)                                              \
    tmp = _mm_alignr_epi8(mD, mC, 4);                                      \
    mA = _mm_add_epi32(_mm_sha256msg1_epu32(mA, mB), tmp);                 \
    mA = _mm_sha256msg2_epu32(mA, mD);

    RND4(m0, 0xE9B5DBA5B5C0FBCFULL, 0x71374491428A2F98ULL)
    RND4(m1, 0xAB1C5ED5923F82A4ULL, 0x59F111F13956C25BULL)
    RND4(m2, 0x550C7DC3243185BEULL, 0x12835B01D807AA98ULL)
    RND4(m3, 0xC19BF1749BDC06A7ULL, 0x80DEB1FE72BE5D74ULL)
    SCHED(m0, m1, m2, m3) RND4(m0, 0x240CA1CC0FC19DC6ULL, 0xEFBE4786E49B69C1ULL)
    SCHED(m1, m2, m3, m0) RND4(m1, 0x76F988DA5CB0A9DCULL, 0x4A7484AA2DE92C6FULL)
    SCHED(m2, m3, m0, m1) RND4(m2, 0xBF597FC7B00327C8ULL, 0xA831C66D983E5152ULL)
    SCHED(m3, m0, m1, m2) RND4(m3, 0x1429296706CA6351ULL, 0xD5A79147C6E00BF3ULL)
    SCHED(m0, m1, m2, m3) RND4(m0, 0x53380D134D2C6DFCULL, 0x2E1B213827B70A85ULL)
    SCHED(m1, m2, m3, m0) RND4(m1, 0x92722C8581C2C92EULL, 0x766A0ABB650A7354ULL)
    SCHED(m2, m3, m0, m1) RND4(m2, 0xC76C51A3C24B8B70ULL, 0xA81A664BA2BFE8A1ULL)
    SCHED(m3, m0, m1, m2) RND4(m3, 0x106AA070F40E3585ULL, 0xD6990624D192E819ULL)
    SCHED(m0, m1, m2, m3) RND4(m0, 0x34B0BCB52748774CULL, 0x1E376C0819A4C116ULL)
    SCHED(m1, m2, m3, m0) RND4(m1, 0x682E6FF35B9CCA4FULL, 0x4ED8AA4A391C0CB3ULL)
    SCHED(m2, m3, m0, m1) RND4(m2, 0x8CC7020884C87814ULL, 0x78A5636F748F82EEULL)
    SCHED(m3, m0, m1, m2) RND4(m3, 0xC67178F2BEF9A3F7ULL, 0xA4506CEB90BEFFFAULL)
#undef RND4
#undef SCHED

    st0 = _mm_add_epi32(st0, abef);
    st1 = _mm_add_epi32(st1, cdgh);
    tmp = _mm_shuffle_epi32(st0, 0x1B);                /* FEBA */
    st1 = _mm_shuffle_epi32(st1, 0xB1);                /* DCHG */
    st0 = _mm_blend_epi16(tmp, st1, 0xF0);             /* DCBA */
    st1 = _mm_alignr_epi8(st1, tmp, 8);                /* ABEF -> HGFE */
    _mm_storeu_si128((__m128i *)&state[0], st0);
    _mm_storeu_si128((__m128i *)&state[4], st1);
}
