import sys

if sys.version_info[:2] != (3, 13):
    from .runtime import unsupported_runtime
    raise SystemExit(unsupported_runtime(sys.argv[1:]))

from .application.cli import main

raise SystemExit(main())
