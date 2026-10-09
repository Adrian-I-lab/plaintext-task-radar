"""The commit hooks refuse planted problems, never echo a matched term, and fail closed.

Sensitive-looking strings are assembled at run time so this file passes the hooks itself.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent / "scripts" / "hooks"
TERM = "zz-" + "planted-term-4410"

pytestmark = pytest.mark.skipif(not (shutil.which("bash") and shutil.which("git")),
                                reason="needs bash and git")


@pytest.fixture
def repo(tmp_path):
    work = tmp_path / "repo"
    work.mkdir()
    terms = tmp_path / "terms.txt"
    terms.write_text("# comment line\n\n" + TERM.upper() + "\n")
    env = {**os.environ, "PORTFOLIO_DENYLIST": str(terms), "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1"}
    git = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.org"]
    subprocess.run(git + ["init", "-q"], cwd=work, env=env, check=True)
    subprocess.run(git + ["config", "core.hooksPath", str(HOOKS)], cwd=work, env=env, check=True)

    def commit(name: str, content: str, message: str = "Add a file", **extra: str):
        (work / name).write_text(content)
        subprocess.run(git + ["add", "--", name], cwd=work, env=env, check=True)
        run_env = {**env, **extra}
        if not run_env["PORTFOLIO_DENYLIST"]:
            del run_env["PORTFOLIO_DENYLIST"]
        done = subprocess.run(git + ["commit", "-q", "-m", message], cwd=work, env=run_env,
                              capture_output=True, text=True)
        subprocess.run(git + ["reset", "-q"], cwd=work, env=env, check=False)
        return done.returncode, done.stdout + done.stderr

    return commit


def test_clean_content_passes(repo):
    assert repo("ok.txt", "Plain text. Contact team@example.org or 127.0.0.1.\n")[0] == 0


@pytest.mark.parametrize("content, label", [
    ("server at 192." + "168.1.10\n", "private-ipv4-192"),
    ("server at 10." + "2.3.4\n", "private-ipv4-10"),
    ("server at 172." + "20.0.5\n", "private-ipv4-172"),
    ("peer at 100." + "100.7.8\n", "shared-ipv4-100"),
    ("see /ho" + "me/someone/notes\n", "home-path-unix"),
    ("see /Us" + "ers/someone/notes\n", "home-path-unix"),
    ("key AKIA" + "A" * 16 + "\n", "aws-access-key"),
    ("-----BEGIN RSA " + "PRIVATE KEY-----\n", "private-key-block"),
    ("token ghp_" + "a" * 24 + "\n", "github-token"),
    ("mail someone" + "@" + "corp.invalid\n", "email-address"),
])
def test_secret_patterns_are_refused(repo, content, label):
    code, out = repo("bad.txt", "first line\n" + content)
    assert code == 1
    assert f"bad.txt:2: secret pattern {label}" in out


def test_denylist_hit_in_content_never_prints_the_term(repo):
    code, out = repo("bad.txt", f"one\ntwo {TERM} three\n")
    assert code == 1 and "bad.txt:2: denylist hit" in out
    assert TERM.lower() not in out.lower()


def test_denylist_hit_in_message_is_refused(repo):
    code, out = repo("ok.txt", "fine\n", message=f"Mention {TERM}")
    assert code == 1 and "commit message:1: denylist hit" in out
    assert TERM.lower() not in out.lower()


def test_denylist_hit_in_file_name_hides_the_name(repo):
    code, out = repo(f"{TERM}.txt", "fine\n")
    assert code == 1 and "denylist hit" in out
    assert TERM.lower() not in out.lower()


def test_fails_closed_without_a_term_list(repo, tmp_path):
    code, out = repo("ok.txt", "fine\n", PORTFOLIO_DENYLIST="")
    assert code == 1 and "PORTFOLIO_DENYLIST is not set" in out
    code, out = repo("ok.txt", "fine\n", PORTFOLIO_DENYLIST=str(tmp_path / "missing.txt"))
    assert code == 1 and "does not name a readable file" in out
    empty = tmp_path / "empty.txt"
    empty.write_text("# only a comment\n\n")
    code, out = repo("ok.txt", "fine\n", PORTFOLIO_DENYLIST=str(empty))
    assert code == 1 and "holds no terms" in out
