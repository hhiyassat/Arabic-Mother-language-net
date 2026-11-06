"""python3 -m arabic_net_api كَسَرَ [--root كسر] [--form فَعَلَ] [--only hfn,wazn] [--letters]
   python3 -m arabic_net_api --root-only كسر
   python3 -m arabic_net_api --sources"""
import argparse
import json
import sys

from . import root, sources, verb


def main(argv=None):
    ap = argparse.ArgumentParser(prog="arabic_net_api")
    ap.add_argument("word", nargs="?")
    ap.add_argument("--root", default="")
    ap.add_argument("--form", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--letters", action="store_true", help="لا يُستبعد غير المطابق مشكولاً")
    ap.add_argument("--root-only", action="store_true")
    ap.add_argument("--sources", action="store_true")
    a = ap.parse_args(argv)
    inc = set(a.only.split(",")) if a.only else None
    if a.sources:
        r = sources()
    elif a.root_only:
        r = root(a.word, include=inc)
    elif a.word:
        r = verb(a.word, a.root, a.form, include=inc, match="letters" if a.letters else "exact")
    else:
        ap.print_help()
        return 2
    json.dump(r, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
