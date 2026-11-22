/* Adapter for jackoalan/gc-dspadpcm-encode (MIT; license in third_party).
 * Input is mono PCM16, history starts at zero. No sample-rate conversion. */
#include <stdint.h>
#include <string.h>
void DSPCorrelateCoefs(const short *, int, short *);
void DSPEncodeFrame(short [16], int, unsigned char [8], const short [8][2]);
__declspec(dllexport) int ms_dsp_encode(const int16_t *pcm, int count,
                                     int16_t coefs[16], uint8_t *out) {
    if (!pcm || !coefs || !out || count < 1 || count > 48000 * 30) return -1;
    memset(coefs, 0, 32);
    /* The reference coefficient fitter divides by recordCount on silence.
     * Silence/tiny inputs use the exact zero predictor instead. */
    int energetic = 0;
    for (int i = 0; i < count; i++) if (pcm[i] > 16 || pcm[i] < -16) { energetic = 1; break; }
    if (count >= 28 && energetic) DSPCorrelateCoefs(pcm, count, coefs);
    short frame[16] = {0};
    for (int i = 0; i < count; i += 14) {
        int n = count - i < 14 ? count - i : 14;
        memset(frame + 2, 0, 28);
        memcpy(frame + 2, pcm + i, n * 2);
        DSPEncodeFrame(frame, 14, out + (i / 14) * 8, (const short (*)[2])coefs);
        frame[0] = frame[14]; frame[1] = frame[15];
    }
    return 0;
}
