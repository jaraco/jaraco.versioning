import operator
import itertools
from functools import reduce

import packaging.version


def find(pred, items):
    """
    Find the index of the first element in items for which pred returns
    True

    >>> find(lambda x: x > 3, range(100))
    4
    >>> find(lambda x: x < -3, range(100)) is None
    True
    """
    for i, item in enumerate(items):
        if pred(item):
            return i


def rfind(pred, items):
    """
    Find the index of the last element in items for which pred returns
    True. Returns a negative number useful for indexing from the end
    of a list or tuple.

    >>> rfind(lambda x: x > 3, [5,4,3,2,1])
    -4
    """
    return -find(pred, reversed(items)) - 1


class SummableVersion(packaging.version.Version):
    """
    A special version that can be added to another Version.

    >>> SummableVersion('1.1') + packaging.version.Version('2.3')
    <Version('3.4')>
    """

    def __add__(self, other):
        result = SummableVersion('1.0')
        result._version = result._version._replace(
            release=tuple(
                itertools.starmap(
                    operator.add,
                    itertools.zip_longest(
                        self._version.release,
                        other._version.release,
                        fillvalue=0,
                    ),
                ),
            ),
        )
        return SummableVersion(str(result))

    def reset_less_significant(self, significant_version):
        """
        Reset to zero all version info less significant than the
        indicated version.

        >>> ver = SummableVersion('3.1.2')
        >>> ver.reset_less_significant(SummableVersion('0.1'))
        >>> str(ver)
        '3.1'
        """

        def nonzero(x):
            return x != 0

        version_len = len(significant_version._version.release)
        significant_pos = rfind(nonzero, significant_version._version.release)
        significant_pos = version_len + significant_pos + 1
        new_release = self._version.release[:significant_pos] + (0,) * (
            version_len - significant_pos
        )
        self._version = self._version._replace(release=new_release)
        self.__init__(str(self))

    def as_number(self):
        """
        >>> round(SummableVersion('1.9.3').as_number(), 12)
        1.93
        """

        def combine(subver, ver):
            return subver / 10 + ver

        return reduce(combine, reversed(self._version.release))


class VersionManagement:
    """
    Version functions for RepoManager classes
    """

    increment = '0.0.1'

    @staticmethod
    def __versions_from_tags(tags):
        for tag in tags:
            try:
                yield packaging.version.Version(tag)
            except ValueError:
                pass

    @staticmethod
    def __best_version(versions):
        try:
            return max(versions)
        except ValueError:
            pass

    def get_valid_versions(self):
        """
        Return all version tags that can be represented by a Version.
        """
        return self.__versions_from_tags(tag.tag for tag in self.get_repo_tags())

    def get_tagged_version(self):
        """
        Get the version of the local working set as a Version or
        None if no viable tag exists. If the local working set is itself
        the tagged commit and the tip and there are no local
        modifications, use the tag on the parent changeset.
        """
        tags = list(self.get_tags())
        if 'tip' in tags and not self.is_modified():
            tags = self.get_parent_tags('tip')
        versions = self.__versions_from_tags(tags)
        return self.__best_version(versions)

    def get_latest_version(self):
        """
        Determine the latest version ever released of the project in
        the repo (based on tags).
        """
        return self.__best_version(self.get_valid_versions())

    def get_current_version(self, increment=None):
        """
        Return as a string the version of the current state of the
        repository -- a tagged version, if present, or the next version
        based on prior tagged releases.
        """
        ver = (
            self.get_tagged_version() or str(self.get_next_version(increment)) + '.dev0'
        )
        return str(ver)

    def get_next_version(self, increment=None):
        """
        Return the next version based on prior tagged releases.
        """
        increment = increment or self.increment
        return self.infer_next_version(self.get_latest_version(), increment)

    @staticmethod
    def infer_next_version(last_version, increment):
        """
        Given a simple application version (as a Version),
        and an increment (1.0, 0.1, or 0.0.1), guess the next version.

        Set up a shorthand for examples

        >>> def VM_infer(*params):
        ...     return str(VersionManagement.infer_next_version(*params))

        >>> VM_infer('3.2', '0.0.1')
        '3.2.1'
        >>> VM_infer(packaging.version.Version('3.2'), '0.0.1')
        '3.2.1'
        >>> VM_infer('3.2.3', '0.1')
        '3.3'
        >>> VM_infer('3.1.2', '1.0')
        '4.0'

        Subversions never increment parent versions

        >>> VM_infer('3.0.9', '0.0.1')
        '3.0.10'

        If it's a prerelease version, just remove the prerelease.

        >>> VM_infer('3.1a1', '0.0.1')
        '3.1'

        If there is no last version, use the increment itself

        >>> VM_infer(None, '0.1')
        '0.1'
        """
        if last_version is None:
            return increment
        last_version = SummableVersion(str(last_version))
        if last_version.is_prerelease:
            last_version._version = last_version._version._replace(
                pre=None,
                dev=None,
            )
            return str(last_version)
        increment = SummableVersion(increment)
        sum = last_version + increment
        sum.reset_less_significant(increment)
        return sum