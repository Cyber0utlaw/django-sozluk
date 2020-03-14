from contextlib import suppress

from django.core.paginator import Paginator
from django.utils.functional import cached_property

from ..models import Category
from . import get_category_parameters
from .settings import (NON_DB_CATEGORIES, NON_DB_SLUGS_SAFENAMES, TOPICS_PER_PAGE_DEFAULT, YEAR_RANGE)


class PlainSerializer:
    """A surface-level 'serializer' that creates a dictionary from 'public' methods/attributes {name: return value}"""

    exclude = ()
    """A tuple of names of attributes/methods to be ignored while serializing."""

    def get_serialized(self):
        """Outer dictionary comprehension removes null values from inner dictionary. @formatter:off"""
        return {
            key: value
            for key, value in {
                name: getattr(self, name)
                for name in dir(self)
                if not name.startswith(
                    ("_", "get_serialized", "exclude") + self.exclude
                )
            }.items()
            if value is not None
        }
    # @formatter:on


class PageSerializer(PlainSerializer):
    """Serializes page_obj of Paginator."""

    class _Paginator(PlainSerializer):
        def __init__(self, page_obj):
            self.num_pages = page_obj.paginator.num_pages
            self.page_range = page_obj.paginator.page_range

    def __init__(self, page_obj):
        self.paginator = self._Paginator(page_obj).get_serialized()
        self.object_list = page_obj.object_list
        self.number = page_obj.number
        self.has_previous = page_obj.has_previous()
        self.has_next = page_obj.has_next()
        self.has_other_pages = page_obj.has_other_pages()

        if self.has_previous:
            self.previous_page_number = page_obj.previous_page_number()

        if self.has_next:
            self.next_page_number = page_obj.next_page_number()


class LeftFrame(PlainSerializer):
    """
    An interface for TopicListManager. (for presentation layer)
    Note: Check out PlainSerializer before you append any attribute or method.
    """

    exclude = ("as_context",)

    def __init__(self, manager, page):
        """
        :param manager: An instance of TopicListManager (or a child of TopicListHandler)
        :param page: Integer or string, for Paginator.
        """
        self.slug = manager.slug
        self._page = page
        self._manager = manager

    @property
    def year_range(self):
        return YEAR_RANGE if self.slug == "tarihte-bugun" else None

    @property
    def year(self):
        return self._manager.year

    @property
    def safename(self):
        if self.slug in NON_DB_CATEGORIES:
            return NON_DB_SLUGS_SAFENAMES[self.slug][0]

        with suppress(Category.DoesNotExist):
            return Category.objects.get(slug=self.slug).name

    @property
    def slug_identifier(self):
        return self._manager.slug_identifier

    @property
    def refresh_count(self):
        return self._manager.refresh_count

    @property
    def parameters(self):
        key = self.slug if self.slug in NON_DB_CATEGORIES else "generic"
        return get_category_parameters(key, self.year)

    @cached_property
    def page(self):
        """Get current page_obj via Paginator and serialize it using PageSerializer"""
        user = self._manager.user
        paginate_by = (user.topics_per_page if user.is_authenticated else TOPICS_PER_PAGE_DEFAULT)
        paginator = Paginator(self._manager.serialized, paginate_by)
        return PageSerializer(paginator.get_page(self._page)).get_serialized()

    def as_context(self):
        return self.get_serialized()
