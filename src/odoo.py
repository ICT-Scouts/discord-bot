import os
import xmlrpc.client


class Odoo:
    def __init__(self):
        self.url = "https://portal.ict-scouts.ch"
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.url))
        self.db = "live"
        self.username = os.getenv("ODOO_API_USER")
        self.password = os.getenv("ODOO_API_KEY")
        self.uid = common.authenticate(self.db, self.username, self.password, {})


    def get_campus_id(self, email):
        email = email.lower()

        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.url))
        res = models.execute_kw(self.db, self.uid, self.password, 'res.partner', 'search_read', [[['google_mail', '=',email]]], {'fields': ['category_id'], 'limit': 1})

        # Ensure return type is list
        if not isinstance(res, list):
            return False

        # Check if any ID
        if len(res) == 0:
            return False

        # Get campus id
        return res[0]["category_id"][1]
