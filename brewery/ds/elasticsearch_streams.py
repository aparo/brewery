#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ..dq.base import FieldTypeProbe
from .base import DataSource, DataTarget
from ..metadata import expand_record, Field

try:
    from pyes.es import ES
    from pyes.exceptions import TypeMissingException

except ImportError:
    from brewery.utils import MissingPackage
    pyes = MissingPackage("pyes", "ElasticSearch streams", "http://www.elasticsearch.org/")

class ESDataSource(DataSource):
    """
    docstring for ClassName
    """

    def __init__(self, document_type, index=None, host=None, port=None, expand=False, **elasticsearch_args):
        """Creates a ElasticSearch data source stream.

        :Attributes:
            * document_type: elasticsearch document_type name
            * index: index name, default is test
            * host: elasticsearch database server host, default is ``localhost``
            * port: elasticsearch port, default is ``27017``
            * expand: expand dictionary values and treat children as top-level keys with dot '.'
                separated key path to the child..
        """
        super(ESDataSource, self).__init__()
        self.document_type = document_type
        self.index = index or "test"
        self.host = host or "127.0.0.1"
        self.port = port or "9200"
        self.elasticsearch_args = elasticsearch_args
        self.expand = expand
        self.connection = None
        self._fields = None

    def initialize(self):
        """Initialize ElasticSearch source stream:
        """
        args = self.elasticsearch_args.copy()
        server = ""
        if self.host:
            server = self.host
        if self.port:
            server += ":" + self.port

        self.connection = ES(server, **args)
        self.connection.default_indices = self.index
        self.connection.default_types = self.document_type

    def read_fields(self, limit=0, collapse = False):
        keys = []
        probes = {}

        def probe_record(record, parent=None):
            for key, value in record.items():
                if parent:
                    full_key = parent + "." + key
                else:
                    full_key = key

                if self.expand and type(value) == dict:
                    probe_record(value, full_key)
                    continue

                if not full_key in probes:
                    probe = FieldTypeProbe(full_key)
                    probes[full_key] = probe
                    keys.append(full_key)
                else:
                    probe = probes[full_key]
                probe.probe(value)

        for record in self.document_type.find(limit=limit):
            probe_record(record)

        fields = []

        for key in keys:
            probe = probes[key]
            field = Field(probe.field)

            storage_type = probe.unique_storage_type
            if not storage_type:
                field.storage_type = "unknown"
            elif storage_type == "unicode":
                field.storage_type = "string"
            else:
                field.storage_type = "unknown"
                field.concrete_storage_type = storage_type

            # FIXME: Set analytical type

            fields.append(field)

        self._fields = list(fields)
        return self._fields

    def rows(self):
        if not self.connection:
            raise RuntimeError("Stream is not initialized")
        from pyes.query import MatchAllQuery
        fields = self.field_names
        results = self.connection.search(MatchAllQuery(), search_type="scan", timeout="5m", size="200")
        return ESRowIterator(results, fields)

    def records(self):
        if not self.connection:
            raise RuntimeError("Stream is not initialized")
        from pyes.query import MatchAllQuery
        results = self.connection.search(MatchAllQuery(), search_type="scan", timeout="5m", size="200")
        return ESRecordIterator(results, self.expand)

class ESRowIterator(object):
    """Wrapper for ElasticSearch ResultSet to be able to return rows() as tuples and records() as
    dictionaries"""
    def __init__(self, resultset, field_names):
        self.resultset = resultset
        self.field_names = field_names

    def __getitem__(self, index):
        record = self.resultset.__getitem__(index)

        array = []

        for field in self.field_names:
            value = record
            for key in field.split('.'):
                if key in value:
                    value = value[key]
                else:
                    break
            array.append(value)

        return tuple(array)

class ESRecordIterator(object):
    """Wrapper for ElasticSearch ResultSet to be able to return rows() as tuples and records() as
    dictionaries"""
    def __init__(self, resultset, expand=False):
        self.resultset = resultset
        self.expand = expand

    def __getitem__(self, index):
        def expand_record(record, parent=None):
            ret = {}
            for key, value in record.items():
                if parent:
                    full_key = parent + "." + key
                else:
                    full_key = key

                if type(value) == dict:
                    expanded = expand_record(value, full_key)
                    ret.update(expanded)
                else:
                    ret[full_key] = value
            return ret

        record = self.resultset.__getitem__(index)
        if not self.expand:
            return record
        else:
            return expand_record(record)

class ESDataTarget(DataTarget):
    """docstring for ClassName
    """

    def __init__(self, document_type, index="test", host="127.0.0.1", port="9200", truncate=False, expand=False,
                 **elasticsearch_args):
        """Creates a ElasticSearch data target stream.

        :Attributes:
            * document_ElasticSearch elasticsearch document_type name
            * index: database name
            * host: ElasticSearch database server host, default is ``localhost``
            * port: ElasticSearch port, default is ``9200``
            * expand: expand dictionary values and treat children as top-level keys with dot '.'
                separated key path to the child..
            * truncate: delete existing data in the document_type. Default: False
        """
        super(ESDataTarget, self).__init__()
        self.document_type = document_type
        self.index = index
        self.host = host
        self.port = port
        self.elasticsearch_args = elasticsearch_args
        self.expand = expand
        self.truncate = truncate
        self._fields = None

    def initialize(self):
        """
        Initialize ElasticSearch source stream:
        """
        from pyes.es import ES
        from pyes.exceptions import IndexAlreadyExistsException

        args = self.elasticsearch_args.copy()
        server = ""
        if self.host:
            server = self.host
        if self.port:
            server += ":" + self.port

        create = args.pop("create", False)
        replace = args.pop("replace", False)

        self.connection = ES(server, **args)
        self.connection.default_indices = self.index
        self.connection.default_types = self.document_type

        created = False
        if create:
            try:
                self.connection.create_index(self.index)
                self.connection.refresh(self.index)
                created = True
            except IndexAlreadyExistsException:
                pass

        if replace and not created:
            self.connection.delete_index_if_exists(self.index)
            self.connection.refresh(self.index)
            self.connection.create_index(self.index)
            self.connection.refresh(self.index)

        if self.truncate:
            self.connection.delete_mapping(self.index, self.document_type)
            self.connection.refresh(self.index)
        #check mapping
        try:
            self.connection.get_mapping(self.document_type, self.index)
        except TypeMissingException:
            self.connection.put_mapping(self.document_type, self._get_mapping(), self.index)

    def _get_mapping(self):
        """Build an ES optimized mapping for the given fields"""
        from pyes.mappings import DocumentObjectField, IntegerField, StringField, BooleanField, FloatField, DateField

        document = DocumentObjectField(name=self.document_type)
        for field in self.fields:
            st = field.storage_type
            if st == "unknown":
                #lets es detect the type
                continue
            elif st in ["string", "text"]:
                document.add_property(StringField(name=field.name))
            elif st == "integer":
                document.add_property(IntegerField(name=field.name))
            elif st == "boolean":
                document.add_property(BooleanField(name=field.name))
            elif st == "date":
                document.add_property(DateField(name=field.name))
            elif st == "float":
                document.add_property(FloatField(name=field.name))

        return document


    def append(self, obj):
        record = obj
        if not isinstance(obj, dict):
            record = dict(zip(self.field_names, obj))

        if self.expand:
            record = expand_record(record)

        id = record.get('id') or record.get('_id')
        self.connection.index(record, self.index, self.document_type, id, bulk=True)

    def finalize(self):
        self.connection.flush_bulk(forced=True)
