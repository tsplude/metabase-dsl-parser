import unittest
from dsl_parser import *

FIELDS = {
  1: "id",
  2: "name",
  3: "date_joined",
  4: "age"
}

class TestParser(unittest.TestCase):

    def test_eq(self):
        p = DSLParser()
        res = p.generate_sql(dialect='postgres', fields=FIELDS, query='{:where [:= [:field 3] nil]}')
        expected = '"SELECT * FROM data WHERE "date_joined" IS NULL;"'
        self.assertEqual(res, expected)

    def test_gt(self):
        p = DSLParser()
        res = p.generate_sql(dialect='postgres', fields=FIELDS, query='{:where [:> [:field 4] 35]}')
        expected = '"SELECT * FROM data WHERE "age" > 35;"'
        self.assertEqual(res, expected)

    def test_and(self):
        p = DSLParser()
        res = p.generate_sql(dialect='postgres', fields=FIELDS, query='{:where [:and [:< [:field 1] 5] [:= [:field 2] "joe"]]}')
        expected = '"SELECT * FROM data WHERE "id" < 5 AND "name" = \'joe\';"'
        self.assertEqual(res, expected)

    def test_or(self):
        p = DSLParser()
        res = p.generate_sql(dialect='postgres', fields=FIELDS, query='{:where [:or [:!= [:field 3] "2015-11-01"] [:= [:field 1] 456]]}')
        expected = '"SELECT * FROM data WHERE "date_joined" <> \'2015-11-01\' OR "id" = 456;"'
        self.assertEqual(res, expected)

    def test_and_or(self):
        p = DSLParser()
        res = p.generate_sql(dialect='postgres', fields=FIELDS, query='{:where [:and [:!= [:field 3] nil] [:or [:> [:field 4] 25] [:= [:field 2] "Jerry"]]]}')
        expected = '"SELECT * FROM data WHERE "date_joined" IS NOT NULL AND ("age" > 25 OR "name" = \'Jerry\');"'
        self.assertEqual(res, expected)

    def test_in(self):
        p = DSLParser()
        res = p.generate_sql(dialect='postgres', fields=FIELDS, query='{:where [:= [:field 4] 25 26 27]}')
        expected = '"SELECT * FROM data WHERE "age" IN (25, 26, 27);"'
        self.assertEqual(res, expected)

    def test_eq_str(self):
        p = DSLParser()
        res = p.generate_sql(dialect='postgres', fields=FIELDS, query='{:where [:= [:field 2] "cam"]}')
        expected = '"SELECT * FROM data WHERE "name" = \'cam\';"'
        self.assertEqual(res, expected)

    def test_mysql_with_limit(self):
        p = DSLParser()
        res = p.generate_sql(dialect='mysql', fields=FIELDS, query='{:where [:= [:field 2] "cam"], :limit 10}')
        expected = '"SELECT * FROM data WHERE `name` = \'cam\' LIMIT 10;"'
        self.assertEqual(res, expected)

    def test_mysql_no_where(self):
        p = DSLParser()
        res = p.generate_sql(dialect='mysql', fields=FIELDS, query='{:limit 20}')
        expected = '"SELECT * FROM data LIMIT 20;"'
        self.assertEqual(res, expected)

    def test_sqlserver_no_where(self):
        p = DSLParser()
        res = p.generate_sql(dialect='sqlserver', fields=FIELDS, query='{:limit 20}')
        expected = '"SELECT TOP 20 * FROM data;"'
        self.assertEqual(res, expected)


if __name__ == '__main__':
    unittest.main()