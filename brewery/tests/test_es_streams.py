# -*- coding: utf-8 -*-

import unittest
from brewery.ds.elasticsearch_streams import ESDataSource, ESDataTarget
from brewery.metadata import FieldList

class ESStreamsTestCase(unittest.TestCase):
    def setUp(self):
        self.fields = FieldList([
                            ("category", "string"),
                            ("category_label", "string"),
                            ("subcategory", "string"),
                            ("subcategory_label", "string"),
                            ("line_item", "string"),
                            ("year", "integer"),
                            ("amount", "integer")])
        self.example_row = ["cat", "Category", "scat", "Sub-category", "foo", 2012, 100]

#    def test_fields(self):
#        stream = ESDataSource("users")
#
#        fields = stream.fields
#
#        self.assertEqual(4, len(fields))

    def test_target_create_table(self):
        stream = ESDataTarget("test", create=True)
        # Should raise an exception, because no fields are specified
        #self.assertRaises(Exception, stream.initialize)

        stream.fields = self.fields
        stream.initialize()

        stream.finalize()

#    def test_target_replace_table(self):
#        table = Table('test', self.metadata,
#                    Column('id', Integer, primary_key=True),
#                    Column('login', String(32)),
#                    Column('full_name', String(255)),
#                    Column('profile', Text)
#                )
#
#        self.metadata.create_all(self.engine)
#
#        stream = ds.SQLDataTarget(connection=self.engine, table="test",
#                                    create=True, replace = False)
#
#        stream.fields = self.fields
#        self.assertRaises(Exception, stream.initialize)
#
#        stream = ds.SQLDataTarget(connection=self.engine, table="test",
#                                    create=True, replace = True)
#        stream.fields = self.fields
#        stream.initialize()
#        cnames = [str(c) for c in stream.table.columns]
#        fnames = ["test."+f.name for f in self.fields]
#        self.assertEqual(fnames, cnames)
#        stream.finalize()
#
#    def test_target_concrete_type_map(self):
#        ctm = {"string": String(123)}
#        stream = ds.SQLDataTarget(connection=self.engine, table="test",
#                                  create=True,
#                                  fields=self.fields,
#                                  concrete_type_map=ctm)
#        stream.initialize()
#
#        c = stream.table.c["line_item"]
#
#        self.assertEqual(123, c.type.length)
