import ast
from pathlib import Path
import unittest


VERSIONS = Path(__file__).parents[1] / "migrations" / "versions"
BASELINE = VERSIONS / "20260928_00_core_schema_baseline.py"
CURRICULUM = VERSIONS / "20260928_01_add_curriculum_structure.py"


def assignments(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                values[target.id] = node.value.value
    return tree, values


class MigrationChainSafetyTest(unittest.TestCase):
    def test_core_baseline_is_root_and_no_op(self):
        tree, values = assignments(BASELINE)
        self.assertEqual(values.get("revision"), "20260928_00")
        self.assertIsNone(values.get("down_revision"))

        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for name in ("upgrade", "downgrade"):
            self.assertIn(name, functions)
            self.assertTrue(
                all(isinstance(stmt, ast.Pass) for stmt in functions[name].body),
                f"{name} must remain a no-op in the core baseline",
            )

    def test_curriculum_revision_follows_core_baseline(self):
        _, values = assignments(CURRICULUM)
        self.assertEqual(values.get("revision"), "20260928_01")
        self.assertEqual(values.get("down_revision"), "20260928_00")


if __name__ == "__main__":
    unittest.main()
