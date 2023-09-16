import os
import xmlrpc.client


class Odoo:
    def __init__(self):
        self.url = "https://ict-scouts.edudoo.ch"
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.url))
        self.db = "ict-scouts"
        self.username = "discord@ict-scouts.ch"
        self.password = os.getenv("ODOO_API_KEY")
        self.uid = common.authenticate(self.db, self.username, self.password, {})


    def get_campus_id(self, email):
        email = email.lower()

        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.url))
        res = models.execute_kw(self.db, self.uid, self.password, 'op.student', 'search_read', [[['google_mail', '=',email]]], {'fields': ['campus_id'], 'limit': 1})

        # Ensure return type is list
        if not isinstance(res, list):
            return False

        # Check if any ID
        if len(res) == 0:
            return False

        # Get campus id
        return res[0]["campus_id"][1]
