import types
import typing

import packaging.version

from jaraco import versioning


class Versioned(versioning.Versioned, types.SimpleNamespace):
    def is_modified(self):
        return False


class TestVersioning:
    def test_tag_versions(self):
        """
        Versioning should only choose relevant tags (versions)
        """
        mgr = Versioned(get_tags=lambda: tags)
        tags = {'foo', 'bar', '3.0'}
        assert mgr.get_tagged_version() == packaging.version.Version('3.0')
        tags = set()
        assert mgr.get_tagged_version() is None
        tags = {'foo', 'bar'}
        assert mgr.get_tagged_version() is None

    def test_tag_priority(self):
        """
        Since Mercurial provides tags in arbitrary order, the versioning
        support should infer the precedence (choose latest).
        """
        mgr = Versioned(get_tags=lambda: tags)
        tags = {'1.0', '1.1'}
        assert mgr.get_tagged_version() == packaging.version.Version('1.1')
        tags = {'0.10', '0.9'}
        assert mgr.get_tagged_version() == packaging.version.Version('0.10')

    def test_defer_to_parent_tag(self):
        """
        Use the parent tag if on the tip
        """
        mgr = Versioned(
            get_tags=lambda rev=None: {'tip'},
            get_parent_tags=lambda rev=None: {'1.0'},
        )
        assert mgr.get_tagged_version() == packaging.version.Version('1.0')

    def test_get_next_version(self):
        mgr = Versioned(get_repo_tags=lambda: set())
        assert mgr.get_next_version() == '0.0.1'

    def test_local_revision_not_tagged(self):
        """
        When no tags are available, use the greatest tag and add the increment
        """
        mgr = Versioned(
            get_tags=lambda rev=None: set(),
            get_repo_tags=lambda: {
                typing.NamedTuple('Tag', [('tag', str)])(var)
                for var in ['foo', 'bar', '1.0']
            },
        )
        assert mgr.get_tagged_version() is None
        assert mgr.get_next_version() == packaging.version.Version('1.0.1')
        assert mgr.get_current_version() == '1.0.1.dev0'
