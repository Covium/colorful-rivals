"""Entry point for the source tree and packaged Colorful Rivals application."""
import sys


def main():
    arguments = sys.argv[1:]
    if arguments and arguments[0] == '--self-test':
        import subprocess
        import build
        from paths import resolve_retoc
        build.verify_template()
        subprocess.run([str(resolve_retoc(build.RESOURCE_ROOT)), '--help'], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif arguments and arguments[0] == '--worker':
        sys.argv = [sys.argv[0], *arguments[1:]]
        import build
        build.main()
    elif arguments:
        import build
        build.main()
    else:
        import configure
        configure.main()


if __name__ == '__main__':
    main()
