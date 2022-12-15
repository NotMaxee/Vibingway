import asyncio
import logging
import sys

__all__ = ["GitError", "NoRepository", "NoCommits", "Git"]

# prepend SUDO on Linux
if sys.platform == "linux":
    GIT = ("sudo", "git")
else:
    GIT = ("git",)


class GitError(Exception):
    """Base exception for git related errors."""
    pass


class NoRepository(GitError):
    """Exception raised when the working directory is not a valid git repository."""
    pass


class NoCommits(GitError):
    """EXception raised when there are no commits in the repository."""
    pass


class Git:
    """A simple interface for interacting with git.

    Requires the current working directory to be a git repository.

    On windows sytems the event loop must be a
    :class:`asyncio.ProactorEventLoop`.
    """

    def __init__(self):
        self.log = logging.getLogger(__name__)

    async def _run(self, *args):
        """Run a git command and return the results.

        Positional arguments are appended to the ``git`` command.

        Returns
        -------
        str
            The console output.
        """
        process = await asyncio.create_subprocess_exec(
            *GIT,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        stdout = stdout.decode("utf-8").strip()
        stderr = stderr.decode("utf-8").strip()

        if stderr != "" and stderr.startswith("fatal:"):
            stderr = stderr.split("\n")[0]
            cmd = " ".join(GIT + args)
            msg = f"an error occured while running '{cmd}': {stderr}"

            if stderr.startswith("fatal: not a git repository"):
                raise NoRepository(msg)
            elif (
                stderr.startswith("fatal: your current branch") and
                stderr.endswith("does not have any commits yet")
            ):
                raise NoCommits(msg)
            else:
                raise GitError(msg)

        return stdout

    async def get_commit(self, offset=0):
        """Returns a dictionary containing details of the desired commit.

        Parameters
        ----------
        offset: int
            The offset of the commit relative to the most recent one.
            Defaults to ``0``.

        Raises
        ------
        :class:`GitError`
            If an error occurs during command execution.
        :class:`NoRepository`
            If the working directory is not a repository.
        :class:`NoCommits`
            If the repository does not have any commits.

        Returns
        -------
        :class:`dict`
            A dictionary containing the following keys:

            ======== =============================================
            Key      Description
            ======== =============================================
            hash     The short revision hash.
            relative Relative commit time.
            when     Absolute commit time.
            subject  The commit subject.
            message  The commit message.
            ======== =============================================
        """
        pretty = "--pretty=%h%n%cr%n%ct%n%s%n%b"
        date = "--date=format:\"%d.%m.%Y %H:%M:%S\""
        info = await self._run("log", "-1", pretty, date, f"--skip={offset}", "--no-merges")
        sequence = info.split("\n", 4)
        if len(sequence) < 5:
            sequence += [""] * (5 - len(sequence))
        short, relative, when, subject, message = sequence

        return dict(
            hash=short,
            relative=relative,
            when=when,
            subject=subject,
            message=message
        )

    async def get_commit_count(self):
        """Returns the total amount of commits without merge commits.

        Raises
        ------
        :class:`GitError`
            If an error occurs during command execution.

        Returns
        -------
        :class:`int`
            The amount of commits.
        """
        commits = await self._run("rev-list", "--count", "--no-merges", "HEAD")
        return int(commits)

    async def get_branch(self):
        """
        Returns the name of the current branch.

        Raises
        ------
        :class:`GitError`
            If an error occurs during command execution.

        Returns
        -------
        :class:`str`
            The name of the current branch.
        """
        return await self._run("rev-parse", "--abbrev-ref", "HEAD")

    async def is_behind(self):
        """Checks whether the local behind is behind or has diverged from the remote.

        Raises
        ------
        :class:`GitError`
            If an error occurs during execution.

        Returns
        -------
        :class:`bool`
            :obj:`True` when the branch is behind, otherwise :obj:`False`.
        """
        branch = await self._run("rev-parse", "--abbrev-ref", "HEAD")
        await self._run("remote", "update")
        branch_range = f"{branch}..origin/{branch}"
        revisions = await self._run("rev-list", "--count", branch_range)
        return int(revisions) > 0

    async def pull(self):
        """Pull the latest avaiable revision from the remote.

        Raises
        ------
        :class:`GitError`
            If an error occurs during command execution.
        :class:`NoRepository`
            If the working directory is not a repository.
        """
        await self._run("pull", "--ff-only")

    async def in_repo(self):
        """Check whether the current working directory is
        a valid git repository.

        Returns
        -------
        :class:`bool`
            A boolean indicating whether the current working
            directory is a git repository.
        """
        try:
            in_tree = await self._run("rev-parse", "--is-inside-work-tree")
        except GitError:
            return False
        return (in_tree == "true")
