class CrmConnectionManager(object):
    def __init__(self, base_url):
        self.base_url = base_url
        self.connection = self.get_connection()

    def get_connection(self):
        pass

    def add_user_to_crm(self, lists, email, first_name, last_name):
        pass

    def change_user_email(self, uid, new_email):
        pass

    def add_user_to_mailing_lists(self, uid, lists):
        pass

    def sync_sustainers(self):
        pass
