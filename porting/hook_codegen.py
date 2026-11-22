"""Preserve interrupted ARM state around the weapon's injected C callbacks.

The upstream helper still emits and validates the displaced instructions and
main-module return addresses. This adapter replaces only its callback wrapper.
"""


def restore():
    return [
        '    vpop    {d16-d31}', '    vpop    {d0-d15}',
        '    pop     {r0, r12}', '    vmsr    fpscr, r0',
        '    msr     APSR_nzcvqg, r12', '    pop     {r0-r5, r12, lr}',
    ]


def trampoline(build, img, name, site):
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
    return '\n'.join(prefix + restore()) + '\n' + displaced + '\n' + '\n'.join(
        [f'.L{name}_handled:'] + restore() + ['    bx      lr']) + '\n'
