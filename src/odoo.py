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

    def get_campus_name(self, email):
        email = email.lower()

        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.url))
        res = models.execute_kw(self.db, self.uid, self.password, 'res.partner', 'search_read', [[['email', '=', email]]], {'fields': ['category_id'], 'limit': 1})

        # Ensure return type is list
        if not isinstance(res, list):
            return False

        # Check if any ID
        if len(res) == 0:
            return False
        
        tags = models.execute_kw(
            self.db, self.uid, self.password,
            'res.partner.category', 'search_read',
            [[]],
            {'fields': ['name']}
        )
        
        category_id = res[0]["category_id"]
        
        if len(category_id) == 0:
            return False
        
        tag_id = category_id[0]
        tag = next(iter([r for r in tags if r['id'] == tag_id]), None)
        
        if not tag:
            return False
        return tag['name']
