#!/usr/bin/env python
# Mode: -*- python -*-
#
# Copyright (c) 2015-2017, 2019-2020, 2023-2024
# by Rocky Bernstein
# Copyright (c) 2000-2002 by hartmut Goebel <h.goebel@crazy-compilers.com>
#

import os
import sys
import time

from uncompyle6.verify import VerifyCmpError
from uncompyle6.main import main, status_msg
from uncompyle6.version import __version__

program = "uncompyle6"


def usage():
    print(__doc__)
    sys.exit(1)


__doc__ = """
Usage:
  %s [OPTIONS]... [ FILE | DIR]...
  %s [--help | -h | --V | --version]

Examples:
  %s      foo.pyc bar.pyc       # decompile foo.pyc, bar.pyc to stdout
  %s -o . foo.pyc bar.pyc       # decompile to ./foo.pyc_dis and ./bar.pyc_dis
  %s -o /tmp /usr/lib/python1.5 # decompile whole library

Options:
  -o <path>     output decompiled files to this path:
                if multiple input files are decompiled, the common prefix
                is stripped from these names and the remainder appended to
                <path>
                  uncompyle6 -o /tmp bla/fasel.pyc bla/foo.pyc
                    -> /tmp/fasel.pyc_dis, /tmp/foo.pyc_dis
                  uncompyle6 -o /tmp bla/fasel.pyc bar/foo.pyc
                    -> /tmp/bla/fasel.pyc_dis, /tmp/bar/foo.pyc_dis
                  uncompyle6 -o /tmp /usr/lib/python1.5
                    -> /tmp/smtplib.pyc_dis ... /tmp/lib-tk/FixTk.pyc_dis
  --compile | -c <python-file>
                attempts a decompilation after compiling <python-file>
  -d            print timestamps
  -p <integer>  use <integer> number of processes
  -r            recurse directories looking for .pyc and .pyo files
  --fragments   use fragments deparser
  --verify      compare generated source with input byte-code
  --verify-run  compile generated source, run it and check exit code
  --syntax-verify compile generated source
  --linemaps    generated line number correspondencies between byte-code
                and generated source output
  --encoding  <encoding>
                use <encoding> in generated source according to pep-0263
  --help        show this message

Debugging Options:
  --asm     | -a        include byte-code       (disables --verify)
  --grammar | -g        show matching grammar
  --tree={before|after}
  -t {before|after}     include syntax before (or after) tree transformation
                        (disables --verify)
  --tree++ | -T         add template rules to --tree=before when possible

Extensions of generated files:
  '.pyc_dis' '.pyo_dis'   successfully decompiled (and verified if --verify)
    + '_unverified'       successfully decompile but --verify failed
    + '_failed'           decompile failed (contact author for enhancement)
""" % (
    (program,) * 5
)

    ):
        print('Error: %s requires Python 2.4-3.10' % program)
        sys.exit(-1)

    numproc = 0
    out_base = None

    out_base = None
    source_paths = []
    timestamp = False
    timestampfmt = "# %Y.%m.%d %H:%M:%S %Z"
    pyc_paths = files

    try:
        opts, pyc_paths = getopt.getopt(
            sys.argv[1:],
            "hac:gtTdrVo:p:",
            "help asm compile= grammar linemaps recurse "
            "timestamp tree= tree+ "
            "fragments verify verify-run version "
            "syntax-verify "
            "showgrammar encoding=".split(" "),
        )
    except getopt.GetoptError, e:
        sys.stderr.write('%s: %s\n' %
                         (os.path.basename(sys.argv[0]), e))
        sys.exit(-1)

    options = {
        "showasm": None
    }
    for opt, val in opts:
        if opt in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        elif opt in ("-V", "--version"):
            print("%s %s" % (program, __version__))
            sys.exit(0)
        elif opt == "--verify":
            options["do_verify"] = "strong"
        elif opt == "--syntax-verify":
            options["do_verify"] = "weak"
        elif opt == "--fragments":
            options["do_fragments"] = True
        elif opt == "--verify-run":
            options["do_verify"] = "verify-run"
        elif opt == "--linemaps":
            options["do_linemaps"] = True
        elif opt in ("--asm", "-a"):
            if options["showasm"] == None:
                options["showasm"] = "after"
            else:
                options["showasm"] = "both"
            options["do_verify"] = None
        elif opt in ("--tree", "-t"):
            if "showast" not in options:
                options["showast"] = {}
            if val == "before":
                options["showast"][val] = True
            elif val == "after":
                options["showast"][val] = True
            else:
                options["showast"]["before"] = True
            options["do_verify"] = None
        elif opt in ("--tree+", "-T"):
            if "showast" not in options:
                options["showast"] = {}
            options["showast"]["after"] = True
            options["showast"]["before"] = True
            options["do_verify"] = None
        elif opt in ("--grammar", "-g"):
            options["showgrammar"] = True
        elif opt == "-o":
            outfile = val
        elif opt in ("--timestamp", "-d"):
            timestamp = True
        elif opt in ("--compile", "-c"):
            source_paths.append(val)
        elif opt == "-p":
            numproc = int(val)
        elif opt in ("--recurse", "-r"):
            recurse_dirs = True
        elif opt == "--encoding":
            options["source_encoding"] = val
        else:
            sys.stderr.write(opt)
            usage()

    # Expand directory if "recurse" was specified.
    if recurse_dirs:
        expanded_files = []
        for f in pyc_paths:
            if os.path.isdir(f):
                for root, _, dir_files in os.walk(f):
                    for df in dir_files:
                        if df.endswith(".pyc") or df.endswith(".pyo"):
                            expanded_files.append(os.path.join(root, df))
        pyc_paths = expanded_files

    # argl, commonprefix works on strings, not on path parts,
    # thus we must handle the case with files in 'some/classes'
    # and 'some/cmds'
    src_base = os.path.commonprefix(pyc_paths)
    if src_base[-1:] != os.sep:
        src_base = os.path.dirname(src_base)
    if src_base:
        sb_len = len(os.path.join(src_base, ""))
        pyc_paths = [f[sb_len:] for f in pyc_paths]

    if not pyc_paths:
        sys.stderr.write("No files given\n")
        usage()

    if outfile == "-":
        outfile = None  # use stdout
    elif outfile and os.path.isdir(outfile):
        out_base = outfile
        outfile = None
    elif outfile and len(pyc_paths) > 1:
        out_base = outfile
        outfile = None

    # A second -a turns show_asm="after" into show_asm="before"
    if asm_plus or asm:
        asm_opt = "both" if asm_plus else "after"
    else:
        asm_opt = None

    if timestamp:
        print(time.strftime(timestampfmt))

    if numproc <= 1:
        show_ast = {"before": tree or tree_plus, "after": tree_plus}
        try:
            result = main(
                src_base,
                out_base,
                pyc_paths,
                source_paths,
                outfile,
                showasm=asm_opt,
                showgrammar=show_grammar,
                showast=show_ast,
                do_verify=verify,
                do_linemaps=linemaps,
                start_offset=start_offset,
                stop_offset=stop_offset,
            )
            if len(pyc_paths) > 1:
                mess = status_msg(*result)
                print("# " + mess)
                pass
        except ImportError:
            print(str(sys.exc_info()[1]))
            sys.exit(2)
        except KeyboardInterrupt:
            pass
        except VerifyCmpError:
            raise
    else:
        from multiprocessing import Process, Queue

        try:
            from Queue import Empty
        except ImportError:
            from queue import Empty

        fqueue = Queue(len(pyc_paths) + numproc)
        for f in pyc_paths:
            fqueue.put(f)
        for i in range(numproc):
            fqueue.put(None)

        rqueue = Queue(numproc)

        tot_files = okay_files = failed_files = verify_failed_files = 0

        def process_func():
            try:
                (tot_files, okay_files, failed_files, verify_failed_files) = (
                    0,
                    0,
                    0,
                    0,
                )
                while 1:
                    f = fqueue.get()
                    if f is None:
                        break
                    (t, o, f, v) = main(src_base, out_base, [f], [], outfile, **options)
                    tot_files += t
                    okay_files += o
                    failed_files += f
                    verify_failed_files += v
            except (Empty, KeyboardInterrupt):
                pass
            rqueue.put((tot_files, okay_files, failed_files, verify_failed_files))
            rqueue.close()

        try:
            procs = [Process(target=process_func) for i in range(numproc)]
            for p in procs:
                p.start()
            for p in procs:
                p.join()
            try:
                (tot_files, okay_files, failed_files, verify_failed_files) = (
                    0,
                    0,
                    0,
                    0,
                )
                while True:
                    (t, o, f, v) = rqueue.get(False)
                    tot_files += t
                    okay_files += o
                    failed_files += f
                    verify_failed_files += v
            except Empty:
                pass
            print(
                "# decompiled %i files: %i okay, %i failed, %i verify failed"
                % (tot_files, okay_files, failed_files, verify_failed_files)
            )
        except (KeyboardInterrupt, OSError):
            pass

    if timestamp:
        print(time.strftime(timestampfmt))

    return


if __name__ == "__main__":
    main_bin()
