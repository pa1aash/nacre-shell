"""`nacre figs`: regenerate every figure from figures/src/figN.py."""


def _figs(args):
    from nacre import _util
    from nacre.figs import build
    root = _util.repo_root()
    records, failures = build.run(root, mock=args.mock, only=args.only, tiff=args.tiff, cvd=not args.no_cvd)
    print("figs: %d built, %d failure(s)%s" % (len(records), len(failures), " (mock data)" if args.mock else ""))
    return 1 if failures else 0


def register(subparsers):
    p = subparsers.add_parser("figs", help="regenerate the preprint figures, schematics and structures at RSC widths")
    p.add_argument("--mock", action="store_true", help="build from figures/src/mock/*.json into figures/out/mock/")
    p.add_argument("--only", nargs="+", metavar="figN", help="build only these (figN, a schematic id, or rdkit)")
    p.add_argument("--tiff", action="store_true", help="also write 600 dpi TIFF (the RSC supply format)")
    p.add_argument("--no-cvd", action="store_true", help="skip the colour-vision-deficiency simulations")
    p.set_defaults(func=_figs)
