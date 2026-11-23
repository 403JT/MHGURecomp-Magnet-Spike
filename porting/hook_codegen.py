"""Preserve interrupted ARM state around the weapon's injected C callbacks.

The upstream helper still emits and validates the displaced instructions and
main-module return addresses. This adapter replaces only its callback wrapper.
"""


def restore(target='recomp'):
    if target not in ('recomp', 'ryujinx'):
        raise ValueError('Unknown hook runtime target')
    flags = ['    msr     APSR_nzcvqg, r12']
    if target == 'ryujinx':
        # Ryujinx 1.3.3 throws NotImplementedException("APSR_g") for the
        # combined MSR. UADD8 sets GE[i] from each byte's carry without touching
        # NZCVQ. Spread the saved GE nibble into four 0/0x80 bytes, add each
        # byte to itself, then restore NZCVQ with the supported MSR form.
        # r0/r1 remain saved in the integer frame until the final pop.
        flags = [
            '    ubfx    r0, r12, #16, #4',
            '    orr     r0, r0, r0, lsl #14',
            '    movw    r1, #3', '    movt    r1, #3',
            '    and     r0, r0, r1',
            '    orr     r0, r0, r0, lsl #7',
            '    movw    r1, #0x0101', '    movt    r1, #0x0101',
            '    and     r0, r0, r1', '    lsl     r0, r0, #7',
            '    uadd8   r0, r0, r0', '    msr     APSR_nzcvq, r12',
        ]
    return [
        '    vpop    {d16-d31}', '    vpop    {d0-d15}',
        '    pop     {r0, r12}', '    vmsr    fpscr, r0',
        *flags, '    pop     {r0-r5, r12, lr}',
    ]


def trampoline(build, img, name, site, target='recomp'):
    if name in build.REPLACE_HOOKS or name in build.MID_EXIT:
        raise ValueError('This wrapper supports only the standalone weapon hooks')
    original = build.trampoline(img, name, site)
    _, separator, displaced = original.partition('    bxne    lr\n')
    if not separator:
        raise ValueError('Upstream trampoline layout changed')
    prefix = [
        f'    .global {name}_tramp', f'    .hidden {name}_tramp', f'    .hidden {name}_c',
        '    .align 2', f'{name}_tramp:',
        '    push    {r0-r5, r12, lr}', '    mrs     r12, apsr', '    vmrs    r0, fpscr',
        '    push    {r0, r12}', '    vpush   {d0-d15}', '    vpush   {d16-d31}',
        # The C callback receives the same register array as upstream. The
        # stack remains aligned to 8 bytes at the call boundary (296 bytes).
        '    add     r0, sp, #264',
        *(['    mov     r1, r6','    mov     r2, r9','    mov     r3, r7'] if name=='ms_local_world_shape' else []),
        *(['    mov     r1, r8'] if name=='ms_local_cancel_range' else []),
        f'    bl      {name}_c',
        '    cmp     r0, #0', f'    bne     .L{name}_handled',
    ]
    return '\n'.join(prefix + restore(target)) + '\n' + displaced + '\n' + '\n'.join(
        [f'.L{name}_handled:'] + restore(target) + ['    bx      lr']) + '\n'
