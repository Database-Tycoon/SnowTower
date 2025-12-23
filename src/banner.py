#!/usr/bin/env python3
"""
SnowTower ASCII Banner

Displays the SnowTower logo and version information.
"""

__version__ = "0.1.0"

BANNER = r"""
  .  *        .       *    .        *   .    *       .   *        .      *
       *  .       *            .     \|/      *   .          *  .
    .        *        .    *      . --*-- .     .    *  .         *     .
                              .      /|\                    .
         .      /\      .          ' | '        /\              *
     *         /  \              '   |   '     /  \     .
       /\     /    \     /\    '     |     '  /    \        /\
   .  /  \   /      \   /  \  '      |      '/      \   .  /  \    *
     /    \_/   *    \_/    \'      /_\     '/   *   \_/    \ \
  __/                       '                '                  \__
 /          *              .                 .          *          \
/___________________________________________________________________________\

                    ╔═══════════════════════════════════╗
                    ║         S N O W T O W E R         ║
                    ║   Enterprise Snowflake Management ║
                    ╚═══════════════════════════════════╝
"""

BANNER_WITH_VERSION = BANNER + f"""
                              Version {__version__}
"""


def show_banner(with_version: bool = True) -> None:
    """Display the SnowTower banner."""
    if with_version:
        print(BANNER_WITH_VERSION)
    else:
        print(BANNER)


def main() -> None:
    """CLI entry point."""
    show_banner(with_version=True)


if __name__ == "__main__":
    main()
