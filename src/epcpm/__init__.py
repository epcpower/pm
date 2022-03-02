import epcpm._build
import subprocess


def get_git_revision_hash() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("ascii").strip()


__version__ = "0.0.0"
__sha__ = get_git_revision_hash()

__version_tag__ = "v{}".format(__version__)
__build_tag__ = epcpm._build.job_id
