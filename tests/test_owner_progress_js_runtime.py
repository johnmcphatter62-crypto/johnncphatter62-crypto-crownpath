"""Exercise the Owner progress renderer in a disposable JavaScript DOM stub."""
from pathlib import Path
import shutil
import subprocess
import pytest


def test_owner_progress_refresh_renders_and_handles_failure():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is unavailable")
    source = (Path(__file__).resolve().parents[1] / "frontend" / "app.js").read_text(encoding="utf-8")
    start = source.index("async function loadOwnerLearnerProgress()")
    end = source.index("async function loadInstructorRequests()", start)
    handler = source[start:end]
    harness = r"""
const assert = require('node:assert/strict');
const list = {
  children: [],
  replaceChildren() { this.children = []; },
  append(node) { this.children.push(node); }
};
const message = {textContent: ''};
const document = {
  querySelector(selector) {
    if (selector === '#ownerLearnerProgressList') return list;
    if (selector === '#learnerProgressMessage') return message;
    throw new Error('Unexpected selector: ' + selector);
  },
  createElement(tag) {
    return {
      tag, textContent: '', children: [],
      append(...nodes) { this.children.push(...nodes); }
    };
  }
};
let response = {learners: [{name: '<script>alert(1)</script>', role: 'COSMETOLOGY_PRO', lessons_completed: 1, lessons_total: 4, overall_progress: 25}]};
async function jsonRequest(path) {
  assert.equal(path, '/api/owner/learner-progress');
  if (response instanceof Error) throw response;
  return response;
}
""" + handler + r"""
(async () => {
  await loadOwnerLearnerProgress();
  assert.equal(list.children.length, 1);
  assert.equal(list.children[0].children[0].textContent, '<script>alert(1)</script> — COSMETOLOGY PRO');
  assert.match(list.children[0].children[1].textContent, /1 of 4 lessons complete/);
  assert.equal(message.textContent, '1 learner(s) loaded.');
  response = {learners: []};
  await loadOwnerLearnerProgress();
  assert.equal(list.children.length, 0);
  assert.equal(message.textContent, 'No learners to report yet.');
  response = new Error('Offline');
  await loadOwnerLearnerProgress();
  assert.equal(message.textContent, 'Offline');
  response = {};
  await loadOwnerLearnerProgress();
  assert.equal(message.textContent, 'Student progress report is unavailable.');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
    result = subprocess.run([node, "-e", harness], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
