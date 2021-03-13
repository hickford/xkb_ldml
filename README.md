xkb_ldml
========

LDML keyboard mappings for XKB layouts.

## Background

Unicode's [Common Locale Data Repository](http://cldr.unicode.org/) (CLDR) collects locale data for all countries and languages, including [keyboard layouts in LDML format](https://github.com/unicode-org/cldr/tree/master/keyboards). In particular, there are some [useful charts](https://unicode-org.github.io/cldr-staging/charts/latest/keyboards/layouts/en). These cover Windows, Mac, Android and Chrome OS layouts, but are missing Linux layouts.

## XKB data

I generated LDML and charts for Linux from XKB data.

* LDML https://github.com/hickford/xkb_ldml/tree/cldr-keyboards-linux
* Charts https://hickford.github.io/xkb_ldml/layouts/

## How these were generated

The LDML:

    python3 xkb_ldml.py

The charts:

    java -DCLDR_DIR=cldr -DCLDR_TMP_DIR=tmp -jar cldr-tools-38.1.jar showkeyboards

