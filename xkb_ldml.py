from argparse import ArgumentError
from lxml import etree
import sys, os, hashlib
import langcodes

from typing import List, NamedTuple, Optional
class LayoutDetails(NamedTuple):
    """Details combining layout and optional variant"""
    layout: str
    variant: Optional[str]
    brief: Optional[str]
    description: Optional[str]
    iso3166: Optional[List[str]]
    """Countries"""

    iso639: Optional[List[str]]
    """Languages"""

    def xkb_name(self) -> str:
        return f"{self.layout}({self.variant})" if self.variant else self.layout

def language(layout: LayoutDetails) -> str:
    # https://tools.ietf.org/html/bcp47
    if not layout.iso639:
        raise ValueError(f"no language for {layout.xkb_name()}")
    tag = layout.iso639[0]
    if layout.iso3166:
        tag += "-" + layout.iso3166[0]
    return langcodes.standardize_tag(tag)

assert language(LayoutDetails(iso639=["eng"], iso3166=["GB"], layout=None, variant=None, description=None, brief=None)) == "en-GB"
assert language(LayoutDetails(iso639=["fra"], iso3166=["FR"], layout=None, variant=None, description=None, brief=None)) == "fr-FR"
assert language(LayoutDetails(iso639=["epo"], iso3166=[], layout=None, variant=None, description=None, brief=None)) == "eo"

positions_and_codes = []
for line in open("iso-xkb-keynames.csv"):
    parts = [part.strip() for part in line.split(",")]
    iso_position = parts[0]
    code = int(parts[2])
    positions_and_codes.append((iso_position, code))

locale_dir = "/usr/share/X11/locale"
locale_to_compose_file = dict()
import os.path
for line in open(os.path.join(locale_dir, "compose.dir")):
    if line.startswith("#"):
        continue
    parts = line.split()
    if not parts:
        continue
    assert len(parts) == 2, parts
    locale_to_compose_file[parts[-1]] = os.path.join(locale_dir, parts[0].rstrip(":"))

assert locale_to_compose_file['en_GB.UTF-8'] == '/usr/share/X11/locale/en_US.UTF-8/Compose'

def parse_compose(path: str) -> dict[tuple[str], str]:
    """Return a dict of tuple of key names to output character"""
    sequences_to_result = dict()
    for line in open(path):
        if line.startswith("#"):
            line, comment = "", line
        if ":" not in line:
            continue
        first, second = line.split(":", maxsplit=1)
        sequence = tuple(part[1:-1] for part in first.split())
        result = second[2] if second[2] != "\\" else second[3]
        sequences_to_result[sequence] = result
    return sequences_to_result

assert parse_compose("/usr/share/X11/locale/en_US.UTF-8/Compose")

# assert language("gb", "colemak") == "en-GB"
# assert language("ng", "igbo") == "ig-NG"

# How to represent dead_tilde? An obvious idea is to use ~, but we don't want the non-dead tilde key to participate in transforms. We could set transform="no" on the non-dead tilde, but this would break sequences such as <Multi_key> <asciitilde> <A>
dead_keys_to_unicode = {"dead_abovecomma": "\u0313","dead_abovedot": "\u0307","dead_abovereversedcomma": "\u0314","dead_abovering": "\u030a","dead_aboveverticalline": "\u030D","dead_acute": "\u0301","dead_belowbreve": "\u032E","dead_belowcircumflex": "\u032D","dead_belowcomma": "\u0326","dead_belowdiaeresis": "\u0324","dead_belowdot": "\u0323","dead_belowmacron": "\u0331","dead_belowring": "\u0325","dead_belowtilde": "\u0330","dead_belowverticalline": "\u0329","dead_breve": "\u0306","dead_caron": "\u030c","dead_cedilla": "\u0327","dead_circumflex": "\u0302","dead_diaeresis": "\u0308","dead_doubleacute": "\u030b","dead_doublegrave": "\u030F","dead_grave": "\u0300","dead_hook": "\u0309","dead_horn": "\u031B","dead_invertedbreve": "\u0311", "dead_iota": "\u0345","dead_longsolidusoverlay": "\u0338","dead_lowline": "\u0332","dead_macron": "\u0304","dead_ogonek": "\u0328","dead_semivoiced_sound": "\u309a","dead_tilde": "\u0303","dead_voiced_sound": "\u3099", "dead_stroke": "\u0338"}

import unicodedata
def ldml_escape_if_necessary(char: str) -> str:
    if len(char) != 1:
        return char
    if unicodedata.category(char) == "Cc":
        return ldml_escape(char)
    return char

def ldml_escape(char: str) -> str:
    return '\\u{' + str(hex(ord(char)))[2:].zfill(4) + '}'

from xkbcommon import xkb
if os.environ.get("XKB_CONFIG_ROOT"):
    xkb_context = xkb.Context(no_default_includes=True)
    xkb_context.include_path_append(os.environ.get("XKB_CONFIG_ROOT"))
else:
    xkb_context = xkb.Context()

def ldml(layout: LayoutDetails, rules=None, model=None, options=None) -> etree.ElementTree:
    # https://unicode.org/reports/tr35/tr35-keyboards.html
    xkb_keymap = xkb_context.keymap_new_from_names(rules, model, layout.layout, layout.variant, options)
    keyboard = etree.Element("keyboard")
    # https://unicode.org/reports/tr35/tr35-keyboards.html#Keyboard_IDs
    # https://unicode.org/reports/tr35/tr35.html#Identifiers
    lang = language(layout)
    locale = f"{lang}-t-k0-linux"
    if layout.variant:
        variant_subtag = layout.variant if 5 <= len(layout.variant) <= 8 and layout.variant.isalnum() else hashlib.sha1(layout.variant.encode('utf8')).hexdigest()[:8]
        locale += f"-{variant_subtag}"
    keyboard.set("locale", locale)
    tree = etree.ElementTree(keyboard)
    version = etree.SubElement(keyboard, "version")
    version.set("platform", "0")
    version.set("number", "$Revision$")
    names = etree.SubElement(keyboard, "names")
    etree.SubElement(names, "name").set("value", layout.description)
    etree.SubElement(names, "name").set("value", layout.xkb_name())
    settings = etree.SubElement(keyboard, "settings")
    settings.set("transformFailure","omit")
    settings.set("transformPartial","hide")
    sym_names_seen = set()
    def populate_keymap(keymap, xkb_state):
        for iso_position, code in positions_and_codes:
            sym = xkb_state.key_get_one_sym(code)
            # idea from https://www.cl.cam.ac.uk/~mgk25/ucs/keysyms.txt
            # https://github.com/xkbcommon/libxkbcommon/blob/master/xkbcommon/xkbcommon-keysyms.h#L385
            char = xkb.keysym_to_string(sym)
            sym_name = xkb.keysym_get_name(sym)
            if sym_name in ("NoSymbol", "VoidSymbol"):
                continue
            if char == None:
                char = dead_keys_to_unicode.get(sym_name)
                if char is not None:
                    char = ldml_escape(char)
            if char != None:
                sym_names_seen.add(sym_name)
                map_element = etree.SubElement(keymap, "map")
                map_element.set("iso", iso_position)
                # print(char.encode('raw_unicode_escape'))
                map_element.set("to", ldml_escape_if_necessary(char))
            else:
                pass
                # print(f"warning layout {layout.xkb_name()}: unsupported symbol {sym_name} ", file=sys.stderr)


    empty_state = xkb_keymap.state_new()
    populate_keymap(etree.SubElement(keyboard, "keyMap"), empty_state)
    shift_state = xkb_keymap.state_new()
    assert shift_state.update_key(50, xkb.XKB_KEY_DOWN)
    shift_map = etree.SubElement(keyboard, "keyMap")
    shift_map.set("modifiers", "shift")
    populate_keymap(shift_map, shift_state)
    ralt_state = xkb_keymap.state_new()
    assert ralt_state.update_key(108, xkb.XKB_KEY_DOWN)
    ralt_map = etree.SubElement(keyboard, "keyMap")
    ralt_map.set("modifiers", "altR")
    populate_keymap(ralt_map, ralt_state)
    ralt_and_shift_state = xkb_keymap.state_new()
    assert ralt_and_shift_state.update_key(108, xkb.XKB_KEY_DOWN)
    assert ralt_and_shift_state.update_key(50, xkb.XKB_KEY_DOWN)
    ralt_and_shift_map = etree.SubElement(keyboard, "keyMap")
    ralt_and_shift_map.set("modifiers", "altR+shift")
    populate_keymap(ralt_and_shift_map, ralt_and_shift_state)

    locale = f"{lang.replace('-','_')}.UTF-8"
    compose_file = locale_to_compose_file.get(locale)
    if compose_file:
        sequences_to_result = parse_compose(compose_file)

        transforms = etree.SubElement(keyboard, "transforms")
        transforms.set("type", "simple")
        for sequence, result in sequences_to_result.items():
            if set(sequence).issubset(sym_names_seen):
                transform = etree.SubElement(transforms, "transform")
                def translate(sym_name: str) -> str:
                    if sym_name in dead_keys_to_unicode:
                        return ldml_escape(dead_keys_to_unicode[sym_name])
                    s = xkb.keysym_to_string(xkb.keysym_from_name(sym_name))
                    if not s:
                        raise ValueError(f"unknown symname {sym_name}")
                    return s
                transform.set("from", "".join(translate(sym_name) for sym_name in sequence))
                transform.set("to", result)
        if len(transforms) == 0:
            keyboard.remove(transforms)

    return tree

def write_to_cldr(doc):
    os.makedirs("cldr/keyboards/linux", exist_ok=True)
    locale = doc.getroot().get('locale')
    path = "cldr/keyboards/linux/{}.xml".format(locale)
    with open(path, 'w') as f:
        doctype = '<!DOCTYPE keyboard SYSTEM "../dtd/ldmlKeyboard.dtd">'
        print(etree.tostring(doc, pretty_print=True, encoding="unicode", doctype=doctype), file=f)
    # validate
    assert etree.parse(path, etree.XMLParser(dtd_validation=True))


def layouts_from_yaml_path(path: str) -> List[LayoutDetails]:
    import ruamel.yaml
    return [LayoutDetails(**layout) for layout in ruamel.yaml.safe_load(open(path))['layouts']]


if __name__ == "__main__":
    yaml_path = sys.argv[1] if sys.argv[1:] else "xkbcli-list.yaml"
    for layout in layouts_from_yaml_path(yaml_path):
        if layout.layout in ["custom", "brai"]:
            continue
        if layout.variant == "e2":
            continue
        try:
            doc = ldml(layout=layout)
            write_to_cldr(doc)
        except Exception as e:
            print(f"problem with layout {layout.xkb_name()}: {e}", file=sys.stderr)
            continue
    #  subprocess.run(["java", "-DCLDR_DIR=cldr", "-DCLDR_TMP_DIR=tmp", "-jar", "cldr-tools-38.1.jar" , "showkeyboards" ,"-i", ".*linux.*"]).check_returncode()


