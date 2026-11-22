Source: https://github.com/jackoalan/gc-dspadpcm-encode
Revision: 039712baa1291fbd77a1390e0496757122efd81b
License: MIT (LICENSE retained).

Local change to grok.c: return zero predictor coefficients if coefficient fitting
finds no usable records. This avoids division by zero for silence/degenerate PCM.
The Windows adapter is ../../codec/dsp_encode.c. It pads the final DSP frame,
starts with zero history, and keeps the exact input sample count in GU's header.
