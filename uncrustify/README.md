# Uncrustify

`citus_indent` wraps [`uncrustify`][1], a popular C source code beautifier. When invoked, it immediately applies Citus C style on any git-tracked C files under the current working directory, though a `--check` flag is implemented to check style without modifying any files.

## Getting Started

`citus_indent` requires `uncrustify` v0.68 or greater.

`make install` to install the script, the Citus style configuration file, and a man page. `man citus_indent` for more details.

## Usage

Apply the `citus-style` git attribute to any files that need the Citus C style applied. After that, just ensure you're within the project's directory hierarchy and run `citus_indent` to format all files. Add style changes with `git add -p`.

`citus_indent --check` is useful for scripts: it will not modify any files and simply exits with a non-zero status if any files marked with `citus-style` are non-compliant.

[1]: http://uncrustify.sourceforge.net
