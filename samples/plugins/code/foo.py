"""Rules for writing custom commands.

1. Start with this sample command file, and modify it.
2. Make sure to give your file the same name as your command.
3. The entry point for your command will be "task_runner(args)", which
   is defined below. Do not change this function signature. Most of your
   code will go there, but you may add additional functions/modules as
   desired. The only rule here is that you must use this pre-defined
   entry point.
4. args will be a argparse.Namespace variable that contains all the
   inputs captured on the command line, which are defined by foo_args.py
5. Your code should return None.
5. Each newly defined function must have an associated argument parser,
   defined in {function name}_args.py. See "foo_args.py" in
   banip/samples/argument_parsers
6. Make sure to put this file in banip/src/plugins/code.
"""

import argparse


def task_runner(args: argparse.Namespace) -> None:
    """Do something wonderful.

    This is foo, so by definition it's wonderful!

    Parameters
    ----------
    args : argparse.Namespace
        Arguments passed on the command line.
    """
    total = args.first + args.second
    print(f"The sum of {args.first} and {args.second} is {total}.")
    print("Cool! Right?")
    return


if __name__ == "__main__":
    pass
