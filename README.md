xkb_ldml
========

LDML keyboard mappings for XKB layouts.

## Background

Unicode's [Common Locale Data Repository](http://cldr.unicode.org/) (CLDR) collects locale data for all countries and languages, including [keyboard layouts in LDML format](https://github.com/unicode-org/cldr/tree/master/keyboards). In particular, there are some [useful charts](https://unicode-org.github.io/cldr-staging/charts/latest/keyboards/layouts/en). These cover Windows, Mac, Android and Chrome OS layouts, but are missing Linux layouts.

## Results

I generated LDML and charts for Linux from XKB data version 2.29.

* LDML https://github.com/hickford/xkb_ldml/tree/cldr-keyboards-linux
* Charts https://hickford.github.io/xkb_ldml/layouts/

## Developer instructions

### Generate LDML

    xkbcli list > xkbcli-list.yaml
    python3 xkb_ldml.py

### Create charts

Download CLDR data and tools from http://cldr.unicode.org/index/downloads . Extract data.

    java -DCLDR_DIR=cldr -DCLDR_TMP_DIR=tmp -jar cldr-tools-40.0.jar showkeyboards
