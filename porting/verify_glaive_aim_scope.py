"""Prove that only the authorized aim functions differ from original alpha.3."""
import json
import re
import struct
from build_module import HERE, MS, UPMOD, sha
from feedback_session import files
from prepare_glaive_aim_build import STAGE, BASE

LEX = re.compile(r'/\*[\s\S]*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_][A-Za-z_0-9]*|\d+(?:\.\d*)?|[^\s]')


def tokens(source):
    return [m.group() for m in LEX.finditer(source) if not m.group().startswith(('/*', '//'))]


def without_functions(text, names):
    spans = []
    for name in names:
        found = list(re.finditer(r'(?m)^(?:static )?(?:void|int|float|uint32_t) ' + name + r'\([^;{}]*\)\s*\{', text))
        if not found: continue
        assert len(found) == 1
        first = found[0]
        depth = 1
        for token in LEX.finditer(text, first.end()):
            if token.group() == '{': depth += 1
            if token.group() == '}': depth -= 1
            if depth == 0:
                spans.append((first.start(), token.end()))
                break
        else: raise AssertionError('Unterminated function: ' + name)
    for start, end in reversed(sorted(spans)): text = text[:start] + text[end:]
    return text


def ips_layout(path):
    data = path.read_bytes()
    assert data[:5] == b'IPS32'
    at, records = 5, []
    while data[at:at + 4] != b'EEOF':
        site, size = struct.unpack_from('>IH', data, at)
        assert size
        records.append((site, size))
        at += 6 + size
    assert at + 4 == len(data)
    return records


def main():
    base_ms = BASE / 'repo/porting' / MS.relative_to(HERE)
    old = (base_ms / 'module/ms_act.c').read_text(encoding='utf-8')
    new = (STAGE / 'weapon/module/ms_act.c').read_text(encoding='utf-8')
    names = ('aim_look', 'aim_view', 'ms_aim_cursor', 'ms_after_update')
    outside_old = without_functions(old, names)
    outside_old, removed = re.subn(r'(?m)^#define AIM_(?:YAW_STEP|PITCH_STEP|PITCH_MAX)\s+[0-9.]+f\s*', '', outside_old)
    assert removed == 3
    outside_new = without_functions(new, names)
    checks = {'all_other_action_code_token_identical': tokens(outside_old) == tokens(outside_new)}
    old_cls = (base_ms / 'module/ms_class.c').read_text(encoding='utf-8')
    new_cls = (STAGE / 'weapon/module/ms_class.c').read_text(encoding='utf-8')
    addition = '    vt_fn(342, ms_aim_cursor);'
    assert new_cls.count(addition) == 1
    checks['class_change_only_native_cursor_slot_342'] = tokens(old_cls) == tokens(new_cls.replace(addition, ''))
    old_h = (base_ms / 'module/ms.h').read_text(encoding='utf-8')
    new_h = (STAGE / 'weapon/module/ms.h').read_text(encoding='utf-8')
    declaration = 'int ms_aim_cursor(uint8_t *p);'
    assert new_h.count(declaration) == 1
    checks['header_only_new_declaration_state_layout_preserved'] = tokens(old_h) == tokens(new_h.replace(declaration, ''))
    baseline = json.loads((STAGE / 'baseline.json').read_text(encoding='utf-8'))
    checks['all_other_weapon_sources_identical'] = all(
        files(STAGE / 'weapon/module')[n] == h for n, h in baseline['source_files_before'].items()
        if n not in ('ms.h', 'ms_act.c', 'ms_class.c'))
    checks['all_local_module_sources_identical'] = files(STAGE / 'module') == baseline['local_module_before']
    for p in UPMOD.iterdir():
        if p.is_file() and p.suffix in ('.c', '.h', '.S', '.ld', '.py'):
            original = BASE / 'repo/porting' / p.relative_to(HERE)
            assert p.read_bytes().replace(b'\r\n', b'\n') == original.read_bytes().replace(b'\r\n', b'\n'), p.name
    checks['upstream_common_module_sources_identical'] = True
    payload = STAGE / 'output/magnet-spike-experimental'
    current = files(payload)
    checks['same_56_payload_paths'] = current.keys() == baseline['base_payload'].keys() and len(current) == 56
    checks['all_54_assets_identical'] = all(current[n] == h for n, h in baseline['base_payload'].items() if n.startswith('romfs/'))
    checks['executable_patch_sites_lengths_preserved'] = ips_layout(next((payload / 'exefs').glob('*.ips'))) == ips_layout(
        next((STAGE / 'baseline-payload/exefs').glob('*.ips')))
    checks['all_action_tables_identical'] = files(STAGE / 'weapon/gen') == files(MS / 'gen')
    proof = {'all_passed': all(checks.values()), 'checks': checks,
             'allowed_functions': list(names), 'payload_files': current,
             'weapon_source_files': files(STAGE / 'weapon/module'), 'local_source_files': files(STAGE / 'module')}
    (STAGE / 'source-scope.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'all_passed': proof['all_passed'], 'checks': checks}))
    assert proof['all_passed']


if __name__ == '__main__': main()
