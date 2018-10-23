import argparse
import sys
import unittest

import lookout.style.format.__main__ as main
from lookout.style.format.tests.test_quality_report import Capturing


class MainTests(unittest.TestCase):
    def test_handlers(self):
        action2handler = {
            "eval": "quality_report",
            "vis": "visualize",
            "rule": "print_rules_report",
            "robust-eval": "style_robustness_report",
            "pr-curve": "plot_pr_curve",
            "gen-smoke-dataset": "generate_smoke_entry",
        }
        parser = main.create_parser()
        subcommands = set([x.dest for x in parser._subparsers._actions[2]._choices_actions])
        set_action2handler = set(action2handler)
        self.assertFalse(len(subcommands - set_action2handler),
                         "You forgot to add to this test {} subcommand(s) check".format(
                             subcommands - set_action2handler))

        self.assertFalse(len(set_action2handler - subcommands),
                         "You cover unexpected subcommand(s) {}".format(
                             set_action2handler - subcommands))

        called_actions = []
        args_save = sys.argv
        error_save = argparse.ArgumentParser.error
        try:
            argparse.ArgumentParser.error = lambda self, message: None

            for action, handler in action2handler.items():
                def handler_append(*args, **kwargs):
                    called_actions.append(action)
                handler_save = getattr(main, handler)
                try:
                    setattr(main, handler, handler_append)
                    sys.argv = [main.__file__, action]
                    main.main()
                finally:
                    setattr(main, handler, handler_save)
        finally:
            sys.argv = args_save
            argparse.ArgumentParser.error = error_save

        set_called_actions = set(called_actions)
        set_actions = set(action2handler)
        self.assertEqual(set_called_actions, set_actions)
        self.assertEqual(len(set_called_actions), len(called_actions))


    def test_empty(self):
        args = sys.argv
        error = argparse.ArgumentParser.error
        try:
            argparse.ArgumentParser.error = lambda self, message: None

            sys.argv = [main.__file__]
            with Capturing() as  output:
                main.main()
        finally:
            sys.argv = args
            argparse.ArgumentParser.error = error
        self.assertIn("usage:", output[0])


if __name__ == "__main__":
    unittest.main()
